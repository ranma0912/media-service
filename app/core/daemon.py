"""
进程管理器 - 绿色部署下的进程控制
"""
import os
import sys
import atexit
import signal
from pathlib import Path
from loguru import logger
import psutil


class ProcessManager:
    """进程管理器"""

    def __init__(self, pid_file: Path):
        self.pid_file = pid_file
        self.pid = os.getpid()

    def write_pid(self):
        """写入 PID 文件"""
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pid_file, 'w') as f:
            f.write(str(self.pid))
        # 注册退出时清理
        atexit.register(self.cleanup)

    def read_pid(self) -> int | None:
        """读取 PID"""
        if not self.pid_file.exists():
            return None
        try:
            with open(self.pid_file, 'r') as f:
                return int(f.read().strip())
        except (ValueError, IOError):
            return None

    def is_running(self) -> bool:
        """检查是否已有实例在运行"""
        pid = self.read_pid()
        if pid is None:
            return False
        try:
            process = psutil.Process(pid)
            return process.is_running() and 'python' in process.name().lower()
        except psutil.NoSuchProcess:
            return False

    def cleanup(self):
        """清理 PID 文件"""
        try:
            if self.pid_file.exists():
                current = self.read_pid()
                if current == self.pid:
                    self.pid_file.unlink()
        except OSError:
            pass

    def setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，正在关闭...")
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Windows 特定信号
        if sys.platform == 'win32':
            signal.signal(signal.SIGBREAK, signal_handler)
