# -*- coding: utf-8 -*-
"""
扫描任务管理器 - 协调整个扫描流程
"""
import os
import threading
import uuid
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger

from app.db.models import ScanPath, ScanHistory, ScanProgress, FileTask
from app.db import get_db_context
from app.core.websocket import manager
from app.modules.scanner.file_queue import get_queue_manager, reset_queue_manager
from app.modules.scanner.file_scanner import get_file_scanner, VIDEO_EXTENSIONS


class ScanTaskManager:
    """扫描任务管理器"""

    def __init__(self):
        """初始化扫描任务管理器"""
        self.queue_manager = get_queue_manager()
        self.scanner = get_file_scanner()
        self.scan_threads: Dict[str, threading.Thread] = {}  # task_id -> thread
        self.lock = threading.Lock()
        self._stopped = False
        
    def _collect_files(
        self,
        target_path: Path,
        recursive: bool = True,
        scan_subdirectories: bool = True
    ) -> List[Path]:
        """
        收集待扫描文件
        
        Args:
            target_path: 目标路径
            recursive: 是否递归扫描
            scan_subdirectories: 是否扫描子目录
            
        Returns:
            文件路径列表
        """
        files = []
        
        try:
            # 收集所有视频文件
            if recursive and scan_subdirectories:
                # 递归扫描
                files = list(target_path.rglob('*'))
            elif recursive:
                # 只扫描当前目录及其子目录中的文件
                files = list(target_path.glob('**/*'))
            else:
                # 只扫描当前目录
                files = list(target_path.glob('*'))
            
            # 过滤出视频文件
            files = [f for f in files if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS]
            
            logger.info(f"在路径 {target_path} 中找到 {len(files)} 个视频文件")
            
        except Exception as e:
            logger.error(f"收集文件失败 {target_path}: {e}")
        
        return files

    def _discover_files(
        self,
        target_path: Path,
        recursive: bool = True,
        scan_subdirectories: bool = True
    ) -> List[Path]:
        """
        发现待扫描文件（过滤已扫描文件）
        
        Args:
            target_path: 目标路径
            recursive: 是否递归扫描
            scan_subdirectories: 是否扫描子目录
            
        Returns:
            文件路径列表
        """
        files = self._collect_files(target_path, recursive, scan_subdirectories)
        
        # 基于文件哈希过滤已扫描文件
        scanned_hashes = set()
        try:
            with get_db_context() as db:
                # 获取该路径下所有已扫描文件的哈希值
                media_files = db.query(FileTask).filter(
                    FileTask.target_path.like(f"{target_path}%")
                ).all()
                
                for task in media_files:
                    media_file = task.media_file
                    if media_file and media_file.sha256_hash:
                        scanned_hashes.add(media_file.sha256_hash)
                
                logger.debug(f"已扫描文件哈希数: {len(scanned_hashes)}")
        except Exception as e:
            logger.error(f"获取已扫描文件哈希失败: {e}")
        
        return files  # 返回所有文件，跳过逻辑在扫描时处理

    async def _update_progress(
        self,
        task_id: int,
        batch_id: str,
        progress: Dict[str, Any],
        force: bool = False
    ):
        """
        更新扫描进度
        
        Args:
            task_id: 任务ID
            batch_id: 批次ID
            progress: 进度数据
            force: 是否强制更新
        """
        try:
            # 更新数据库
            with get_db_context() as db:
                db_progress = db.query(ScanProgress).filter_by(batch_id=batch_id).first()
                if db_progress:
                    # 只更新ScanProgress模型支持的字段
                    supported_fields = [
                        "task_id", "batch_id", "target_path", "scan_type", "status",
                        "total_files", "scanned_files", "new_files", "updated_files",
                        "skipped_files", "failed_files", "progress", "current_file",
                        "started_at", "completed_at", "last_updated_at"
                    ]
                    for key, value in progress.items():
                        if key in supported_fields and hasattr(db_progress, key):
                            setattr(db_progress, key, value)
                    db_progress.last_updated_at = datetime.now()
                else:
                    # 只使用ScanProgress模型支持的字段创建新记录
                    progress_data = {}
                    for key in ["task_id", "batch_id", "target_path", "scan_type", "status",
                                   "total_files", "scanned_files", "new_files", "updated_files",
                                   "skipped_files", "failed_files", "progress", "current_file",
                                   "started_at", "completed_at", "last_updated_at"]:
                        if key in progress:
                            progress_data[key] = progress[key]
                    progress_data["task_id"] = task_id
                    progress_data["batch_id"] = batch_id
                    db_progress = ScanProgress(**progress_data)
                    db.add(db_progress)
                db.commit()
            
            # 通过WebSocket推送进度
            await manager.send_progress(task_id, progress)
            
        except Exception as e:
            logger.error(f"更新扫描进度失败: {e}")

    def _scan_worker(
        self,
        task_id: int,
        target_path: str,
        scan_type: str,
        recursive: bool,
        skip_strategy: str,
        scan_subdirectories: bool,
        scan_debounce_time: int,
        files: Optional[List[Path]] = None
    ):
        """
        扫描工作线程
        
        Args:
            task_id: 任务ID
            target_path: 目标路径
            scan_type: 扫描类型
            recursive: 是否递归
            skip_strategy: 跳过策略
            scan_subdirectories: 是否扫描子目录
            scan_debounce_time: 扫描防抖时间
            files: 要扫描的文件列表（可选，如果提供则只扫描这些文件）
        """
        batch_id = str(uuid.uuid4())
        scan_start_time = datetime.now()
        last_progress_update = datetime.min
        target_path_obj = Path(target_path)
        
        try:
            logger.info(f"开始扫描任务: task_id={task_id}, batch_id={batch_id}, path={target_path}")
            
            # 1. 发现文件或使用提供的文件列表
            if files is not None:
                logger.info(f"使用指定的文件列表进行扫描: {len(files)} 个文件")
            else:
                files = self._discover_files(target_path_obj, recursive, scan_subdirectories)
            
            if not files:
                logger.info(f"未发现任何待扫描文件: {target_path}")
                
                # 更新进度
                progress = {
                    "batch_id": batch_id,
                    "task_id": task_id,
                    "target_path": target_path,
                    "scan_type": scan_type,
                    "status": "completed",
                    "total_files": 0,
                    "scanned_files": 0,
                    "new_files": 0,
                    "updated_files": 0,
                    "skipped_files": 0,
                    "failed_files": 0,
                    "progress": 100,
                    "current_file": None,
                    "started_at": scan_start_time,
                    "completed_at": datetime.now(),
                    "last_updated_at": datetime.now()
                }
                
                # 异步更新进度
                asyncio.run(self._update_progress(task_id, batch_id, progress, force=True))
                
                # 更新扫描历史
                self._update_scan_history(
                    task_id, batch_id, target_path, scan_type, recursive,
                    progress, scan_start_time, datetime.now()
                )
                
                return
            
            # 2. 添加文件到队列
            self.queue_manager.add_files(files)
            
            # 3. 开始扫描循环
            new_files = 0
            updated_files = 0
            skipped_files = 0
            failed_files = 0
            scanned_files = 0
            
            while not self._stopped:
                # 从队列获取文件
                file_path = self.queue_manager.get_file(timeout=1.0)
                
                if file_path is None:
                    # 队列为空，退出循环
                    break
                
                # 扫描文件
                result = self.scanner.scan_file(
                    file_path,
                    batch_id,
                    scan_type,
                    skip_strategy
                )
                
                scanned_files += 1
                
                # 统计结果
                if result['status'] == 'scanned':
                    # 检查是新文件还是更新
                    with get_db_context() as db:
                        media_file = db.query(FileTask).filter_by(
                            batch_id=batch_id,
                            media_file_id=result['media_file_id']
                        ).first()
                        if media_file and media_file.media_file:
                            # 检查是否是新文件（通过扫描时间）
                            if media_file.scan_completed_at and media_file.scan_completed_at >= scan_start_time:
                                new_files += 1
                            else:
                                updated_files += 1
                elif result['status'] == 'skipped':
                    skipped_files += 1
                elif result['status'] == 'failed':
                    failed_files += 1
                
                # 标记文件完成
                self.queue_manager.mark_completed(file_path, result['status'])
                
                # 检查是否需要更新进度
                now = datetime.now()
                if now - last_progress_update >= timedelta(seconds=scan_debounce_time):
                    queue_progress = self.queue_manager.get_progress()
                    # 只使用ScanProgress模型支持的字段
                    progress = {
                        "total_files": queue_progress.get("total_files", 0),
                        "scanned_files": queue_progress.get("scanned_files", 0),
                        "new_files": new_files,
                        "updated_files": updated_files,
                        "skipped_files": skipped_files,
                        "failed_files": failed_files,
                        "progress": queue_progress.get("progress", 0),
                        "batch_id": batch_id,
                        "task_id": task_id,
                        "target_path": target_path,
                        "scan_type": scan_type,
                        "status": "running",
                        "current_file": str(file_path),
                        "started_at": scan_start_time,
                        "last_updated_at": now
                    }
                    
                    # 异步更新进度
                    asyncio.run(self._update_progress(task_id, batch_id, progress))
                    
                    last_progress_update = now
                
                # 检查停止状态
                if self._check_stop_status(task_id):
                    logger.info(f"检测到停止请求: task_id={task_id}")
                    break
            
            # 4. 扫描完成
            scan_end_time = datetime.now()
            duration = int((scan_end_time - scan_start_time).total_seconds())
            
            # 更新最终进度
            queue_progress = self.queue_manager.get_progress()
            # 只使用ScanProgress模型支持的字段
            final_progress = {
                "total_files": queue_progress.get("total_files", 0),
                "scanned_files": queue_progress.get("scanned_files", 0),
                "new_files": new_files,
                "updated_files": updated_files,
                "skipped_files": skipped_files,
                "failed_files": failed_files,
                "progress": 100,
                "batch_id": batch_id,
                "task_id": task_id,
                "target_path": target_path,
                "scan_type": scan_type,
                "status": "stopped" if self._stopped else "completed",
                "current_file": None,
                "started_at": scan_start_time,
                "completed_at": scan_end_time,
                "last_updated_at": scan_end_time
            }
            
            # 异步更新进度
            asyncio.run(self._update_progress(task_id, batch_id, final_progress, force=True))
            
            # 更新扫描历史
            self._update_scan_history(
                task_id, batch_id, target_path, scan_type, recursive,
                final_progress, scan_start_time, scan_end_time, duration
            )
            
            # 更新ScanPath记录
            self._update_scan_path(target_path, batch_id, final_progress)
            
            logger.info(f"扫描任务完成: task_id={task_id}, batch_id={batch_id}, "
                       f"总计 {scanned_files} 个文件, "
                       f"新增 {new_files} 个, "
                       f"更新 {updated_files} 个, "
                       f"跳过 {skipped_files} 个, "
                       f"失败 {failed_files} 个, "
                       f"耗时 {duration} 秒")
            
        except Exception as e:
            logger.error(f"扫描任务失败: task_id={task_id}, error={e}")
            
            # 更新失败状态
            try:
                queue_progress = self.queue_manager.get_progress()
                # 只使用ScanProgress模型支持的字段
                progress = {
                    "total_files": queue_progress.get("total_files", 0),
                    "scanned_files": queue_progress.get("scanned_files", 0),
                    "new_files": 0,
                    "updated_files": 0,
                    "skipped_files": 0,
                    "failed_files": 0,
                    "progress": queue_progress.get("progress", 0),
                    "batch_id": batch_id,
                    "task_id": task_id,
                    "target_path": target_path,
                    "scan_type": scan_type,
                    "status": "failed",
                    "current_file": None,
                    "started_at": scan_start_time,
                    "completed_at": datetime.now(),
                    "last_updated_at": datetime.now()
                }
                
                asyncio.run(self._update_progress(task_id, batch_id, progress, force=True))
            except:
                pass

    def _check_stop_status(self, task_id: int) -> bool:
        """
        检查任务是否被请求停止
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否应该停止
        """
        if self._stopped:
            return True
        
        try:
            with get_db_context() as db:
                # 检查ScanProgress的状态
                progress = db.query(ScanProgress).filter_by(task_id=task_id).first()
                if progress and progress.status == "stopped":
                    return True
        except:
            pass
        
        return False

    def _update_scan_history(
        self,
        task_id: int,
        batch_id: str,
        target_path: str,
        scan_type: str,
        recursive: bool,
        progress: Dict[str, Any],
        started_at: datetime,
        completed_at: datetime,
        duration: int = 0
    ):
        """
        更新扫描历史记录
        
        Args:
            task_id: 任务ID
            batch_id: 批次ID
            target_path: 目标路径
            scan_type: 扫描类型
            recursive: 是否递归
            progress: 进度数据
            started_at: 开始时间
            completed_at: 完成时间
            duration: 持续时间（秒）
        """
        try:
            with get_db_context() as db:
                scan_history = db.query(ScanHistory).filter_by(id=task_id).first()
                if scan_history:
                    scan_history.batch_id = batch_id
                    scan_history.target_path = target_path
                    scan_history.scan_type = scan_type
                    scan_history.recursive = recursive
                    scan_history.total_files = progress.get("total_files", 0)
                    scan_history.new_files = progress.get("new_files", 0)
                    scan_history.updated_files = progress.get("updated_files", 0)
                    scan_history.skipped_files = progress.get("skipped_files", 0)
                    scan_history.failed_files = progress.get("failed_files", 0)
                    scan_history.duration_seconds = duration
                    scan_history.started_at = started_at
                    scan_history.completed_at = completed_at
                    scan_history.error_message = progress.get("error")
                    db.commit()
                else:
                    scan_history = ScanHistory(
                        id=task_id,
                        batch_id=batch_id,
                        target_path=target_path,
                        scan_type=scan_type,
                        recursive=recursive,
                        total_files=progress.get("total_files", 0),
                        new_files=progress.get("new_files", 0),
                        updated_files=progress.get("updated_files", 0),
                        skipped_files=progress.get("skipped_files", 0),
                        failed_files=progress.get("failed_files", 0),
                        duration_seconds=duration,
                        error_message=progress.get("error"),
                        started_at=started_at,
                        completed_at=completed_at
                    )
                    db.add(scan_history)
                    db.commit()
        except Exception as e:
            logger.error(f"更新扫描历史失败: {e}")

    def _update_scan_path(
        self,
        target_path: str,
        batch_id: str,
        progress: Dict[str, Any]
    ):
        """
        更新扫描路径记录
        
        Args:
            target_path: 目标路径
            batch_id: 批次ID
            progress: 进度数据
        """
        try:
            with get_db_context() as db:
                scan_path = db.query(ScanPath).filter_by(path=target_path).first()
                if scan_path:
                    scan_path.last_scan_at = datetime.now()
                    scan_path.last_scan_batch_id = batch_id
                    scan_path.total_scans = (scan_path.total_scans or 0) + 1
                    scan_path.total_files_found = (scan_path.total_files_found or 0) + progress.get("new_files", 0)
                    db.commit()
        except Exception as e:
            logger.error(f"更新扫描路径失败: {e}")

    def start_scan(
        self,
        target_path: str,
        scan_type: str = 'full',
        recursive: bool = True,
        skip_strategy: str = 'keyword',
        scan_subdirectories: bool = True,
        scan_debounce_time: int = 30,
        task_id: Optional[int] = None,
        files: Optional[List[Path]] = None
    ) -> int:
        """
        开始扫描任务
        
        Args:
            target_path: 目标路径
            scan_type: 扫描类型
            recursive: 是否递归
            skip_strategy: 跳过策略
            scan_subdirectories: 是否扫描子目录
            scan_debounce_time: 扫描防抖时间
            task_id: 任务ID（可选，如果未提供则创建新任务）
            files: 要扫描的文件列表（可选，如果提供则只扫描这些文件）
            
        Returns:
            任务ID
        """
        # 如果未提供task_id，创建新任务
        if task_id is None:
            task_id = self._create_scan_history(
                target_path, scan_type, recursive
            )
        
        # 创建扫描线程
        thread = threading.Thread(
            target=self._scan_worker,
            args=(
                task_id,
                target_path,
                scan_type,
                recursive,
                skip_strategy,
                scan_subdirectories,
                scan_debounce_time,
                files  # 传递文件列表
            ),
            name=f"ScanThread-{task_id}"
        )
        
        with self.lock:
            self.scan_threads[task_id] = thread
        
        thread.start()
        logger.info(f"扫描任务已启动: task_id={task_id}")
        
        return task_id

    def _create_scan_history(
        self,
        target_path: str,
        scan_type: str,
        recursive: bool
    ) -> int:
        """
        创建扫描历史记录
        
        Args:
            target_path: 目标路径
            scan_type: 扫描类型
            recursive: 是否递归
            
        Returns:
            任务ID
        """
        try:
            with get_db_context() as db:
                # 生成临时batch_id（会在_scan_worker中更新为真正的batch_id）
                temp_batch_id = f"temp-{uuid.uuid4()}"
                
                # 先创建ScanHistory记录
                scan_history = ScanHistory(
                    batch_id=temp_batch_id,
                    target_path=target_path,
                    scan_type=scan_type,
                    recursive=recursive,
                    started_at=datetime.now()
                )
                db.add(scan_history)
                db.flush()  # 获取ID但不提交
                
                task_id = scan_history.id
                
                # 再创建ScanProgress记录，用于跟踪任务状态
                scan_progress = ScanProgress(
                    batch_id=temp_batch_id,
                    task_id=task_id,
                    target_path=target_path,
                    scan_type=scan_type,
                    status="running",
                    total_files=0,
                    scanned_files=0,
                    new_files=0,
                    updated_files=0,
                    skipped_files=0,
                    failed_files=0,
                    progress=0,
                    started_at=datetime.now()
                )
                db.add(scan_progress)
                db.commit()
                db.refresh(scan_history)
                return scan_history.id
        except Exception as e:
            logger.error(f"创建扫描历史失败: {e}")
            raise

    def stop_scan(self, task_id: int):
        """
        停止扫描任务
        
        Args:
            task_id: 任务ID
        """
        try:
            # 更新ScanProgress状态为stopped
            with get_db_context() as db:
                progress = db.query(ScanProgress).filter_by(task_id=task_id).first()
                if progress:
                    progress.status = "stopped"
                    progress.completed_at = datetime.now()
                    db.commit()
            
            # 停止队列
            self.queue_manager.stop()
            
            logger.info(f"扫描任务停止请求已发送: task_id={task_id}")
            
        except Exception as e:
            logger.error(f"停止扫描任务失败: {e}")

    def stop_all(self):
        """停止所有扫描任务"""
        self._stopped = True
        self.queue_manager.stop()
        logger.info("所有扫描任务已停止")

    def get_scan_status(self, task_id: int) -> Optional[Dict]:
        """
        获取扫描任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态字典
        """
        try:
            with get_db_context() as db:
                scan_history = db.query(ScanHistory).filter_by(id=task_id).first()
                if not scan_history:
                    return None
                
                scan_progress = db.query(ScanProgress).filter_by(
                    task_id=task_id
                ).order_by(ScanProgress.last_updated_at.desc()).first()
                
                status = {
                    "task_id": scan_history.id,
                    "batch_id": scan_history.batch_id,
                    "target_path": scan_history.target_path,
                    "scan_type": scan_history.scan_type,
                    "recursive": scan_history.recursive,
                    "status": scan_progress.status if scan_progress else "unknown",
                    "total_files": scan_history.total_files,
                    "new_files": scan_history.new_files,
                    "updated_files": scan_history.updated_files,
                    "skipped_files": scan_history.skipped_files,
                    "failed_files": scan_history.failed_files,
                    "duration_seconds": scan_history.duration_seconds,
                    "started_at": scan_history.started_at.isoformat() if scan_history.started_at else None,
                    "completed_at": scan_history.completed_at.isoformat() if scan_history.completed_at else None,
                    "error_message": scan_history.error_message
                }
                
                if scan_progress:
                    status.update({
                        "progress": scan_progress.progress,
                        "current_file": scan_progress.current_file,
                        "last_updated_at": scan_progress.last_updated_at.isoformat() if scan_progress.last_updated_at else None
                    })
                
                return status
                
        except Exception as e:
            logger.error(f"获取扫描状态失败: {e}")
            return None


# 全局单例
_scan_manager = None
_scan_manager_lock = threading.Lock()


def get_scan_manager() -> ScanTaskManager:
    """
    获取扫描任务管理器单例
    
    Returns:
        扫描任务管理器实例
    """
    global _scan_manager
    
    if _scan_manager is None:
        with _scan_manager_lock:
            if _scan_manager is None:
                _scan_manager = ScanTaskManager()
    
    return _scan_manager