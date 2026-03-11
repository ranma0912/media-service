"""
应用路径管理器 - 确保所有路径基于应用根目录
"""
import os
from pathlib import Path


class AppPaths:
    """应用路径管理器"""

    def __init__(self):
        # 应用根目录：从当前文件向上两级
        self.root = Path(__file__).parent.parent.parent.resolve()

    def get_path(self, relative_path: str) -> Path:
        """获取绝对路径"""
        if os.path.isabs(relative_path):
            return Path(relative_path)
        return self.root / relative_path

    def ensure_dir(self, relative_path: str) -> Path:
        """确保目录存在并返回路径"""
        path = self.get_path(relative_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def data_dir(self) -> Path:
        """数据目录"""
        return self.ensure_dir("./data")

    @property
    def db_path(self) -> Path:
        """数据库文件路径"""
        return self.get_path("./data/db/media_service.db")

    @property
    def db_dir(self) -> Path:
        """数据库目录"""
        return self.ensure_dir("./data/db")

    @property
    def log_dir(self) -> Path:
        """日志目录"""
        return self.ensure_dir("./logs")

    @property
    def config_dir(self) -> Path:
        """配置目录"""
        return self.ensure_dir("./config")

    @property
    def pid_file(self) -> Path:
        """PID文件路径"""
        return self.get_path("./data/app.pid")

    @property
    def lock_file(self) -> Path:
        """锁文件路径"""
        return self.get_path("./data/app.lock")

    @property
    def temp_dir(self) -> Path:
        """临时目录"""
        return self.ensure_dir("./data/temp")

    @property
    def cache_dir(self) -> Path:
        """缓存目录"""
        return self.ensure_dir("./data/cache")

    @property
    def backup_dir(self) -> Path:
        """备份目录"""
        return self.ensure_dir("./data/backups")

    @property
    def app_config(self) -> Path:
        """主配置文件路径"""
        return self.get_path("./config/app.yaml")

    @property
    def naming_rules_config(self) -> Path:
        """命名规则配置文件路径"""
        return self.get_path("./config/naming_rules.yaml")


# 全局路径管理器实例
paths = AppPaths()
