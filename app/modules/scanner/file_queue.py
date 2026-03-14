# -*- coding: utf-8 -*-
"""
文件队列管理器 - 基于磁盘的扫描队列
"""
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Set
from queue import Queue, Empty
from datetime import datetime
from loguru import logger
import uuid


class DiskQueue:
    """
    基于磁盘的文件队列
    每个磁盘一个独立的队列
    """
    
    def __init__(self, disk_path: str):
        """
        初始化磁盘队列
        
        Args:
            disk_path: 磁盘根路径
        """
        self.disk_path = disk_path
        self.queue = Queue()
        self.processing: Set[Path] = set()  # 正在处理的文件
        self.processed: Set[str] = set()  # 已处理的文件哈希值
        self.lock = threading.Lock()
        self.total_files = 0
        self.scanned_files = 0
        self.failed_files = 0
        self.skipped_files = 0
        
    def add_file(self, file_path: Path):
        """
        添加文件到队列
        
        Args:
            file_path: 文件路径
        """
        with self.lock:
            self.queue.put(file_path)
            self.total_files += 1
            logger.debug(f"文件加入队列: {file_path} (磁盘: {self.disk_path})")
    
    def get_file(self, timeout: float = None) -> Optional[Path]:
        """
        从队列获取文件
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            文件路径，队列为空返回None
        """
        try:
            file_path = self.queue.get(timeout=timeout)
            
            with self.lock:
                # 检查文件是否已在处理中
                if file_path in self.processing:
                    logger.debug(f"文件已在处理中: {file_path}")
                    self.queue.put(file_path)  # 放回队列
                    return None
                
                self.processing.add(file_path)
                
            return file_path
            
        except Empty:
            return None
    
    def mark_completed(self, file_path: Path, status: str = "scanned"):
        """
        标记文件为已完成
        
        Args:
            file_path: 文件路径
            status: 状态 (scanned/skipped/failed)
        """
        with self.lock:
            if file_path in self.processing:
                self.processing.remove(file_path)
                
            self.scanned_files += 1
            
            if status == "skipped":
                self.skipped_files += 1
            elif status == "failed":
                self.failed_files += 1
                
            logger.debug(f"文件扫描完成: {file_path} (状态: {status})")
    
    def get_progress(self) -> Dict:
        """
        获取队列进度
        
        Returns:
            进度信息字典
        """
        with self.lock:
            return {
                "total_files": self.total_files,
                "scanned_files": self.scanned_files,
                "processing_files": len(self.processing),
                "failed_files": self.failed_files,
                "skipped_files": self.skipped_files,
                "queue_size": self.queue.qsize(),
                "progress": self.scanned_files / self.total_files * 100 if self.total_files > 0 else 0
            }
    
    def clear(self):
        """清空队列"""
        with self.lock:
            self.queue = Queue()
            self.processing.clear()
            self.total_files = 0
            self.scanned_files = 0
            self.failed_files = 0
            self.skipped_files = 0


class FileQueueManager:
    """
    文件队列管理器
    管理多个磁盘的扫描队列
    """
    
    def __init__(self):
        """初始化文件队列管理器"""
        self.disk_queues: Dict[str, DiskQueue] = {}  # disk_path -> DiskQueue
        self.lock = threading.Lock()
        self._stopped = False
        
    def _get_disk_path(self, file_path: Path) -> str:
        """
        获取文件所在的磁盘路径
        
        Args:
            file_path: 文件路径
            
        Returns:
            磁盘根路径
        """
        # Windows系统获取驱动器号
        if os.name == 'nt':
            return file_path.drive + '\\' if file_path.drive else file_path.anchor
        else:
            # Unix系统获取挂载点
            # 简化处理：返回根路径
            return str(file_path.anchor)
    
    def add_files(self, file_paths: List[Path]):
        """
        批量添加文件到队列
        
        Args:
            file_paths: 文件路径列表
        """
        with self.lock:
            for file_path in file_paths:
                disk_path = self._get_disk_path(file_path)
                
                if disk_path not in self.disk_queues:
                    self.disk_queues[disk_path] = DiskQueue(disk_path)
                    logger.info(f"创建新磁盘队列: {disk_path}")
                
                self.disk_queues[disk_path].add_file(file_path)
    
    def get_file(self, timeout: float = None) -> Optional[Path]:
        """
        从任意磁盘队列获取文件
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            文件路径，所有队列都为空返回None
        """
        if self._stopped:
            return None
            
        with self.lock:
            # 轮询所有磁盘队列
            for disk_path, queue in self.disk_queues.items():
                file_path = queue.get_file(timeout=0.1)  # 短暂等待
                if file_path:
                    logger.debug(f"从磁盘 {disk_path} 获取文件: {file_path}")
                    return file_path
            
        # 所有队列都为空，返回None
        return None
    
    def mark_completed(self, file_path: Path, status: str = "scanned"):
        """
        标记文件为已完成
        
        Args:
            file_path: 文件路径
            status: 状态 (scanned/skipped/failed)
        """
        disk_path = self._get_disk_path(file_path)
        
        with self.lock:
            if disk_path in self.disk_queues:
                self.disk_queues[disk_path].mark_completed(file_path, status)
    
    def get_progress(self) -> Dict:
        """
        获取整体进度
        
        Returns:
            进度信息字典
        """
        with self.lock:
            total_files = 0
            scanned_files = 0
            processing_files = 0
            failed_files = 0
            skipped_files = 0
            queue_size = 0
            
            for queue in self.disk_queues.values():
                progress = queue.get_progress()
                total_files += progress["total_files"]
                scanned_files += progress["scanned_files"]
                processing_files += progress["processing_files"]
                failed_files += progress["failed_files"]
                skipped_files += progress["skipped_files"]
                queue_size += progress["queue_size"]
            
            return {
                "total_files": total_files,
                "scanned_files": scanned_files,
                "processing_files": processing_files,
                "failed_files": failed_files,
                "skipped_files": skipped_files,
                "queue_size": queue_size,
                "progress": scanned_files / total_files * 100 if total_files > 0 else 0,
                "disk_count": len(self.disk_queues)
            }
    
    def is_empty(self) -> bool:
        """
        检查所有队列是否为空
        
        Returns:
            是否所有队列都为空
        """
        with self.lock:
            for queue in self.disk_queues.values():
                if queue.queue.qsize() > 0 or len(queue.processing) > 0:
                    return False
            return True
    
    def stop(self):
        """停止队列处理"""
        self._stopped = True
        logger.info("文件队列管理器已停止")
    
    def clear(self):
        """清空所有队列"""
        with self.lock:
            for queue in self.disk_queues.values():
                queue.clear()
            self._stopped = False
            logger.info("所有文件队列已清空")


# 全局单例
_queue_manager = None
_queue_lock = threading.Lock()


def get_queue_manager() -> FileQueueManager:
    """
    获取文件队列管理器单例
    
    Returns:
        文件队列管理器实例
    """
    global _queue_manager
    
    if _queue_manager is None:
        with _queue_lock:
            if _queue_manager is None:
                _queue_manager = FileQueueManager()
    
    return _queue_manager


def reset_queue_manager():
    """重置文件队列管理器（用于测试或特殊情况）"""
    global _queue_manager
    
    with _queue_lock:
        if _queue_manager:
            _queue_manager.clear()
        _queue_manager = None