"""
文件系统监控模块
使用watchdog库监控文件系统变化
"""
import time
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent, FileCreatedEvent, FileModifiedEvent, FileDeletedEvent, FileMovedEvent
from loguru import logger


class FileMonitorHandler(FileSystemEventHandler):
    """文件系统事件处理器"""
    
    def __init__(self, callback: Callable[[str, str], None], debounce_seconds: int = 5):
        """
        初始化事件处理器
        
        Args:
            callback: 事件回调函数，接收(event_type, path)参数
            debounce_seconds: 防抖时间（秒）
        """
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.last_event_time = {}
        self.pending_events = set()
    
    def _should_process_event(self, event_path: str) -> bool:
        """
        判断是否应该处理该事件
        
        通过防抖机制，避免短时间内重复处理同一文件
        """
        current_time = time.time()
        
        # 检查是否在防抖时间内
        if event_path in self.last_event_time:
            if current_time - self.last_event_time[event_path] < self.debounce_seconds:
                return False
        
        self.last_event_time[event_path] = current_time
        return True
    
    def _get_event_type(self, event: FileSystemEvent) -> str:
        """获取事件类型"""
        if isinstance(event, FileCreatedEvent):
            return "created"
        elif isinstance(event, FileModifiedEvent):
            return "modified"
        elif isinstance(event, FileDeletedEvent):
            return "deleted"
        elif isinstance(event, FileMovedEvent):
            return "moved"
        else:
            return "other"
    
    def on_created(self, event: FileCreatedEvent):
        """文件创建事件"""
        if not event.is_directory and self._should_process_event(event.src_path):
            logger.debug(f"文件创建: {event.src_path}")
            self.callback("created", event.src_path)
    
    def on_modified(self, event: FileModifiedEvent):
        """文件修改事件"""
        if not event.is_directory and self._should_process_event(event.src_path):
            logger.debug(f"文件修改: {event.src_path}")
            self.callback("modified", event.src_path)
    
    def on_deleted(self, event: FileDeletedEvent):
        """文件删除事件"""
        if not event.is_directory and self._should_process_event(event.src_path):
            logger.debug(f"文件删除: {event.src_path}")
            self.callback("deleted", event.src_path)
    
    def on_moved(self, event: FileMovedEvent):
        """文件移动事件"""
        if not event.is_directory and self._should_process_event(event.dest_path):
            logger.debug(f"文件移动: {event.src_path} -> {event.dest_path}")
            self.callback("moved", event.dest_path)


class FileMonitor:
    """文件系统监控器"""
    
    def __init__(self, path: str, callback: Callable[[str, str], None], debounce_seconds: int = 5):
        """
        初始化文件监控器
        
        Args:
            path: 要监控的目录路径
            callback: 文件变化回调函数，接收(event_type, file_path)参数
            debounce_seconds: 防抖时间（秒）
        """
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"监控路径不存在: {path}")
        if not self.path.is_dir():
            raise NotADirectoryError(f"监控路径不是目录: {path}")
        
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        
        self.observer: Optional[Observer] = None
        self.is_running = False
    
    def start(self):
        """启动监控"""
        if self.is_running:
            logger.warning(f"监控器已在运行: {self.path}")
            return
        
        try:
            # 创建观察者和事件处理器
            self.observer = Observer()
            event_handler = FileMonitorHandler(self.callback, self.debounce_seconds)
            
            # 监控路径
            self.observer.schedule(event_handler, str(self.path), recursive=True)
            
            # 启动观察者
            self.observer.start()
            self.is_running = True
            
            logger.info(f"文件监控已启动: {self.path} (防抖: {self.debounce_seconds}秒)")
        except Exception as e:
            logger.error(f"启动文件监控失败: {e}")
            raise
    
    def stop(self):
        """停止监控"""
        if not self.is_running or not self.observer:
            return
        
        try:
            self.observer.stop()
            self.observer.join()
            self.is_running = False
            logger.info(f"文件监控已停止: {self.path}")
        except Exception as e:
            logger.error(f"停止文件监控失败: {e}")
            raise
    
    def is_alive(self) -> bool:
        """检查监控是否活跃"""
        return self.is_running and self.observer and self.observer.is_alive()