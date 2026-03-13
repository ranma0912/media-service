"""
扫描任务调度器
支持定时扫描任务的调度和管理
"""
import threading
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
from loguru import logger
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from app.db import SessionLocal, ScanPath, ScanHistory
from app.modules.scanner import FileScanner


class ScanScheduler:
    """扫描任务调度器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化调度器"""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.scheduler = None
        self.is_running = False
        
        # 配置调度器
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(max_workers=10)
        }
        job_defaults = {
            'coalesce': True,  # 合并积压的任务
            'max_instances': 3,  # 每个任务最多3个实例
            'misfire_grace_time': 300  # 错过执行后的宽限时间（秒）
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='Asia/Shanghai'
        )
        
        logger.info("扫描任务调度器已初始化")
    
    def start(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("调度器已在运行")
            return
        
        try:
            self.scheduler.start()
            self.is_running = True
            logger.info("扫描任务调度器已启动")
            
            # 加载并启动所有启用的定时扫描任务
            self.load_scheduled_tasks()
        except Exception as e:
            logger.error(f"启动调度器失败: {e}")
            raise
    
    def stop(self):
        """停止调度器"""
        if not self.is_running:
            return
        
        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("扫描任务调度器已停止")
        except Exception as e:
            logger.error(f"停止调度器失败: {e}")
            raise
    
    def load_scheduled_tasks(self):
        """加载所有启用的定时扫描任务"""
        db = SessionLocal()
        try:
            # 查询所有启用且配置了扫描间隔的路径
            paths = db.query(ScanPath).filter(
                ScanPath.enabled == True,
                ScanPath.scan_interval > 0
            ).all()
            
            for path in paths:
                try:
                    self.add_scheduled_scan(path.id, path.scan_interval)
                    logger.info(f"已加载定时扫描任务: path_id={path.id}, interval={path.scan_interval}分钟")
                except Exception as e:
                    logger.error(f"加载定时扫描任务失败: path_id={path.id}, error={e}")
        
        finally:
            db.close()
    
    def add_scheduled_scan(self, path_id: int, interval_minutes: int):
        """
        添加定时扫描任务
        
        Args:
            path_id: 扫描路径ID
            interval_minutes: 扫描间隔（分钟）
        """
        if interval_minutes <= 0:
            raise ValueError("扫描间隔必须大于0")
        
        # 移除已存在的任务
        job_id = f'scan_path_{path_id}'
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        # 添加新的定时任务
        self.scheduler.add_job(
            self._execute_scheduled_scan,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=job_id,
            args=[path_id],
            name=f'定时扫描路径 {path_id}',
            replace_existing=True
        )
        
        logger.info(f"已添加定时扫描任务: path_id={path_id}, interval={interval_minutes}分钟")
    
    def remove_scheduled_scan(self, path_id: int):
        """
        移除定时扫描任务
        
        Args:
            path_id: 扫描路径ID
        """
        job_id = f'scan_path_{path_id}'
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"已移除定时扫描任务: path_id={path_id}")
        else:
            logger.warning(f"定时扫描任务不存在: path_id={path_id}")
    
    def update_scheduled_scan(self, path_id: int, interval_minutes: int):
        """
        更新定时扫描任务
        
        Args:
            path_id: 扫描路径ID
            interval_minutes: 扫描间隔（分钟）
        """
        if interval_minutes <= 0:
            # 如果间隔为0，移除任务
            self.remove_scheduled_scan(path_id)
        else:
            # 否则更新任务
            self.add_scheduled_scan(path_id, interval_minutes)
    
    def _execute_scheduled_scan(self, path_id: int):
        """
        执行定时扫描任务
        
        Args:
            path_id: 扫描路径ID
        """
        db = SessionLocal()
        try:
            # 查询扫描路径
            scan_path = db.query(ScanPath).filter(ScanPath.id == path_id).first()
            if not scan_path:
                logger.error(f"扫描路径不存在: path_id={path_id}")
                return
            
            if not scan_path.enabled:
                logger.warning(f"扫描路径已禁用，跳过扫描: path_id={path_id}")
                return
            
            # 创建扫描历史记录
            import uuid
            batch_id = str(uuid.uuid4())
            
            scan_history = ScanHistory(
                batch_id=batch_id,
                target_path=scan_path.path,
                scan_type='incremental',  # 定时扫描默认为增量扫描
                recursive=scan_path.recursive,
                started_at=datetime.now()
            )
            db.add(scan_history)
            db.commit()
            
            task_id = scan_history.id
            
            # 执行扫描
            scanner = FileScanner(task_id=task_id, batch_id=batch_id)
            
            logger.info(f"开始执行定时扫描: path_id={path_id}, batch_id={batch_id}")
            
            scanner.scan_directory(
                path=scan_path.path,
                recursive=scan_path.recursive,
                scan_type='incremental',
                batch_id=batch_id
            )
            
            # 更新扫描路径的最后扫描时间
            scan_path.last_scan_at = datetime.now()
            scan_path.last_scan_batch_id = batch_id
            db.commit()
            
            logger.info(f"定时扫描完成: path_id={path_id}, batch_id={batch_id}, files={scanner.total_files}")
            
        except Exception as e:
            logger.error(f"执行定时扫描失败: path_id={path_id}, error={e}")
            
            # 更新扫描历史记录的错误信息
            try:
                if 'scan_history' in locals():
                    scan_history.error_message = str(e)
                    scan_history.completed_at = datetime.now()
                    db.commit()
            except:
                pass
        
        finally:
            db.close()
    
    def get_scheduled_jobs(self) -> list:
        """获取所有定时任务"""
        jobs = []
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time if hasattr(job, 'next_run_time') else None
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': next_run.isoformat() if next_run else None
            })
        return jobs
    
    def get_job_status(self, path_id: int) -> Optional[dict]:
        """
        获取指定路径的定时任务状态
        
        Args:
            path_id: 扫描路径ID
        
        Returns:
            任务状态信息，如果任务不存在则返回None
        """
        job_id = f'scan_path_{path_id}'
        job = self.scheduler.get_job(job_id)
        
        if not job:
            return None
        
        next_run = job.next_run_time if hasattr(job, 'next_run_time') else None
        return {
            'id': job.id,
            'name': job.name,
            'next_run_time': next_run.isoformat() if next_run else None
        }


# 创建全局调度器实例
scheduler = ScanScheduler()