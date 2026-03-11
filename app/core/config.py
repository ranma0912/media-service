"""
配置管理模块
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, Field
from loguru import logger

from app.core.paths import paths


class AppConfig(BaseModel):
    """应用配置"""
    name: str = "MediaService"
    version: str = "1.6.0"
    debug: bool = False

    class Paths(BaseModel):
        data: str = "./data"
        logs: str = "./logs"
        temp: str = "./data/temp"
        cache: str = "./data/cache"
        db: str = "./data/db"
        backups: str = "./data/backups"

    class Runtime(BaseModel):
        pid_file: str = "./data/app.pid"
        lock_file: str = "./data/app.lock"

    paths: Paths = Field(default_factory=Paths)
    runtime: Runtime = Field(default_factory=Runtime)


class ServerConfig(BaseModel):
    """服务器配置"""
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 1
    reload: bool = False


class DatabaseConfig(BaseModel):
    """数据库配置"""
    url: str = "sqlite:///./data/db/media_service.db"
    echo: bool = False
    pool_size: int = 5


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} | {message}"
    rotation: str = "10 MB"
    retention: str = "30 days"

    class Files(BaseModel):
        app: str = "./logs/app.log"
        error: str = "./logs/error.log"
        access: str = "./logs/access.log"

    files: Files = Field(default_factory=Files)


class ScannerConfig(BaseModel):
    """扫描配置"""
    watch_paths: list = Field(default_factory=lambda: ["D:/Downloads"])
    recursive: bool = True
    interval: int = 300

    class Monitoring(BaseModel):
        enabled: bool = True
        recursive: bool = True
        debounce_seconds: int = 5
        ignore_patterns: list = Field(default_factory=lambda: ["*.tmp", "*.part", ".*"])

    class Scheduled(BaseModel):
        enabled: bool = True

        class Fallback(BaseModel):
            enabled: bool = True
            interval: int = 3600

        class DeepScan(BaseModel):
            enabled: bool = True
            cron: str = "0 3 * * 0"

        fallback: Fallback = Field(default_factory=Fallback)
        deep_scan: DeepScan = Field(default_factory=DeepScan)

    monitoring: Monitoring = Field(default_factory=Monitoring)
    scheduled: Scheduled = Field(default_factory=Scheduled)


class RecognitionConfig(BaseModel):
    """识别配置"""
    mode: str = "manual"  # auto / manual

    class Auto(BaseModel):
        delay_after_scan: int = 30
        auto_ai_recognition: bool = False
        low_confidence_threshold: float = 0.7
        auto_organize: bool = False

    class Manual(BaseModel):
        notify_after_scan: bool = True
        default_select: str = "unrecognized"
        batch_max_files: int = 50

    class Sources(BaseModel):
        class Tmdb(BaseModel):
            enabled: bool = True
            api_key: str = ""
            language: str = "zh-CN"
            cache_enabled: bool = True
            cache_ttl: int = 86400

        tmdb: Tmdb = Field(default_factory=Tmdb)

    auto: Auto = Field(default_factory=Auto)
    manual: Manual = Field(default_factory=Manual)
    sources: Sources = Field(default_factory=Sources)


class OrganizeConfig(BaseModel):
    """整理配置"""
    mode: str = "manual"  # auto / manual
    action_type: str = "move"  # move / rename / hardlink / copy
    conflict_strategy: str = "rename_new"  # skip / overwrite / backup / rename_new / merge

    class Auto(BaseModel):
        auto_organize_after_recognition: bool = False
        confirm_before_organize: bool = False
        conflict_strategy: str = "rename_new"

    class Manual(BaseModel):
        show_preview: bool = True
        default_select: str = "recognized"
        batch_max_files: int = 20
        require_confirm: bool = True

    auto: Auto = Field(default_factory=Auto)
    manual: Manual = Field(default_factory=Manual)


class SecurityConfig(BaseModel):
    """安全配置"""

    class PasswordPolicy(BaseModel):
        min_length: int = 8
        require_uppercase: bool = True
        require_lowercase: bool = True
        require_numbers: bool = True
        require_special: bool = False
        max_age_days: int = 90
        prevent_reuse: int = 5

    class Session(BaseModel):
        max_concurrent: int = 3
        idle_timeout: int = 1800

    class Jwt(BaseModel):
        secret: str = ""
        algorithm: str = "HS256"
        access_token_expire: int = 3600
        refresh_token_expire: int = 604800

    password_policy: PasswordPolicy = Field(default_factory=PasswordPolicy)
    session: Session = Field(default_factory=Session)
    jwt: Jwt = Field(default_factory=Jwt)


class Config(BaseModel):
    """完整配置"""
    app: AppConfig = Field(default_factory=AppConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    scanner: ScannerConfig = Field(default_factory=ScannerConfig)
    recognition: RecognitionConfig = Field(default_factory=RecognitionConfig)
    organize: OrganizeConfig = Field(default_factory=OrganizeConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        self._config: Optional[Config] = None
        self._config_file: Path = paths.app_config
        self._naming_rules: Dict[str, Any] = {}
        self._naming_rules_file: Path = paths.naming_rules_config

    def load(self) -> Config:
        """加载配置"""
        if self._config is None:
            self._reload()
        return self._config

    def _reload(self):
        """重新加载配置"""
        if not self._config_file.exists():
            logger.warning(f"配置文件不存在: {self._config_file}")
            self._config = Config()
            return

        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)

            self._config = Config(**config_data)
            logger.info(f"配置加载成功: {self._config_file}")
        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            self._config = Config()

    def reload(self) -> Config:
        """重新加载配置"""
        self._reload()
        return self._config

    def save(self, config: Config):
        """保存配置"""
        try:
            config_data = config.model_dump(mode='json')
            with open(self._config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)
            self._config = config
            logger.info(f"配置保存成功: {self._config_file}")
        except Exception as e:
            logger.error(f"配置保存失败: {e}")
            raise

    def load_naming_rules(self) -> Dict[str, Any]:
        """加载命名规则"""
        if not self._naming_rules_file.exists():
            logger.warning(f"命名规则文件不存在: {self._naming_rules_file}")
            return {}

        try:
            with open(self._naming_rules_file, 'r', encoding='utf-8') as f:
                self._naming_rules = yaml.safe_load(f) or {}
            logger.info(f"命名规则加载成功: {self._naming_rules_file}")
            return self._naming_rules
        except Exception as e:
            logger.error(f"命名规则加载失败: {e}")
            return {}

    def save_naming_rules(self, rules: Dict[str, Any]):
        """保存命名规则"""
        try:
            with open(self._naming_rules_file, 'w', encoding='utf-8') as f:
                yaml.dump(rules, f, allow_unicode=True, default_flow_style=False)
            self._naming_rules = rules
            logger.info(f"命名规则保存成功: {self._naming_rules_file}")
        except Exception as e:
            logger.error(f"命名规则保存失败: {e}")
            raise

    @property
    def config(self) -> Config:
        """获取当前配置"""
        if self._config is None:
            self.load()
        return self._config


# 全局配置管理器实例
config_manager = ConfigManager()
config = config_manager.config
