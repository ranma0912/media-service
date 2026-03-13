
"""
文件系统监控模块
使用 watchdog 监控文件系统事件
"""
import asyncio
from pathlib import Path
from typing import List, Set, Dict, Callable, Optional
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from app.core.config import config_manager
from app.modules.scanner.scanner import MEDIA_EXTENSIONS
from loguru import logger


class MediaFileEventHandler(FileSystemEventHandler):
    """媒体文件事件处理器"""

    def __init__(self, scan_callback: Callable[[List[str]], asyncio.Task]):
        """
        初始化事件处理器

        Args:
            scan_callback: 扫描回调函数，接收文件路径列表
        """
        self.scan_callback = scan_callback
        self.debounce_timer: Optional[asyncio.Task] = None
        self.pending_files: Set[str] = set()
        self.debounce_seconds = config_manager.config.scanner.monitoring.debounce_seconds
        self.ignore_patterns = config_manager.config.scanner.monitoring.ignore_patterns

    def on_created(self, event: FileSystemEvent):
        """文件创建事件"""
        if not event.is_directory:
            if self._is_media_file(event.src_path):
                self._debounce_scan(event.src_path)

    def on_modified(self, event: FileSystemEvent):
        """文件修改事件"""
        if not event.is_directory:
            if self._is_media_file(event.src_path):
                self._debounce_scan(event.src_path)

    def on_moved(self, event: FileSystemEvent):
        """文件移动事件"""
        if not event.is_directory:
            if self._is_media_file(event.dest_path):
                self._debounce_scan(event.dest_path)

    def _is_media_file(self, path: str) -> bool:
        """
        检查是否为媒体文件

        Args:
            path: 文件路径

        Returns:
            是否为媒体文件
        """
        # 检查文件扩展名
        file_ext = Path(path).suffix.lower()
        if file_ext not in MEDIA_EXTENSIONS:
            return False

        # 检查忽略模式
        file_name = Path(path).name
        for pattern in self.ignore_patterns:
            if self._match_pattern(file_name, pattern):
                return False

        return True

    def _match_pattern(self, file_name: str, pattern: str) -> bool:
        """
        匹配文件名模式

        Args:
            file_name: 文件名
            pattern: 匹配模式（支持通配符）

        Returns:
            是否匹配
        """
        import fnmatch
        return fnmatch.fnmatch(file_name, pattern)

    def _debounce_scan(self, file_path: str):
        """
        防抖处理，避免频繁扫描

        Args:
            file_path: 文件路径
        """
        self.pending_files.add(file_path)

        # 取消之前的定时器
        if self.debounce_timer and not self.debounce_timer.done():
            self.debounce_timer.cancel()

        # 创建新的定时器
        self.debounce_timer = asyncio.create_task(self._delayed_scan())

    async def _delayed_scan(self):
        """延迟执行扫描"""
        await asyncio.sleep(self.debounce_seconds)

        if self.pending_files:
            file_list = list(self.pending_files)
            self.pending_files.clear()

            logger.info(f"触发扫描: {len(file_list)} 个文件")
            await self.scan_callback(file_list)


class FileSystemMonitor:
    """文件系统监控管理器"""

    def __init__(self):
        self.observer = Observer()
        self.handlers: Dict[str, MediaFileEventHandler] = {}
        self.is_running = False

    def start_monitoring(self, paths: List[str], scan_callback: Callable[[List[str]], asyncio.Task]):
        """
        开始监控指定路径

        Args:
            paths: 要监控的路径列表
            scan_callback: 扫描回调函数
        """
        # 检查是否启用监控
        if not config_manager.config.scanner.monitoring.enabled:
            logger.info("文件系统监控未启用，跳过启动")
            return

        if self.is_running:
            logger.warning("文件监控已在运行中")
            return

        # 为每个路径创建事件处理器
        for path in paths:
            path_obj = Path(path)
            if not path_obj.exists():
                logger.warning(f"监控路径不存在: {path}")
                continue

            handler = MediaFileEventHandler(scan_callback)
            self.handlers[path] = handler

            # 添加监控
            self.observer.schedule(
                handler,
                str(path_obj),
                recursive=config_manager.config.scanner.monitoring.recursive
            )

            logger.info(f"添加监控路径: {path}")

        # 启动观察者
        self.observer.start()
        self.is_running = True

        logger.info("文件系统监控已启动")

    def stop_monitoring(self):
        """停止监控"""
        if not self.is_running:
            return

        self.observer.stop()
        self.observer.join()
        self.is_running = False

        # 清理处理器
        self.handlers.clear()

        logger.info("文件系统监控已停止")

    def add_watch_path(self, path: str, scan_callback: Callable[[List[str]], asyncio.Task]):
        """
        添加新的监控路径

        Args:
            path: 要添加的路径
            scan_callback: 扫描回调函数
        """
        if not self.is_running:
            logger.warning("文件监控未运行，无法添加路径")
            return

        path_obj = Path(path)
        if not path_obj.exists():
            logger.warning(f"监控路径不存在: {path}")
            return

        handler = MediaFileEventHandler(scan_callback)
        self.handlers[path] = handler

        self.observer.schedule(
            handler,
            str(path_obj),
            recursive=config_manager.config.scanner.monitoring.recursive
        )

        logger.info(f"添加监控路径: {path}")

    def remove_watch_path(self, path: str):
        """
        移除监控路径

        Args:
            path: 要移除的路径
        """
        if path not in self.handlers:
            logger.warning(f"监控路径不存在: {path}")
            return

        # watchdog 不支持动态移除路径，需要重启监控
        logger.warning(f"移除监控路径需要重启监控: {path}")
        # TODO: 实现动态移除路径的功能
