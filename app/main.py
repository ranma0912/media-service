"""
MediaService 主程序入口
"""
import sys
import argparse
from pathlib import Path
from loguru import logger

from app.core.config import config_manager
from app.core.paths import paths
from app.db import init_db
from app.core.daemon import ProcessManager


def setup_logging():
    """配置日志"""
    log_config = config_manager.config.logging

    # 确保日志目录存在
    paths.log_dir.mkdir(parents=True, exist_ok=True)

    # 配置日志格式和输出
    logger.remove()  # 移除默认处理器

    # 添加控制台输出
    logger.add(
        sys.stdout,
        format=log_config.format,
        level=log_config.level,
        colorize=True
    )

    # 添加文件输出
    logger.add(
        paths.get_path(log_config.files.app),
        format=log_config.format,
        level=log_config.level,
        rotation=log_config.rotation,
        retention=log_config.retention,
        encoding="utf-8"
    )

    # 添加错误日志
    logger.add(
        paths.get_path(log_config.files.error),
        format=log_config.format,
        level="ERROR",
        rotation=log_config.rotation,
        retention=log_config.retention,
        encoding="utf-8"
    )


def init_app():
    """初始化应用"""
    # 确保必要的目录存在
    paths.data_dir.mkdir(parents=True, exist_ok=True)
    paths.db_dir.mkdir(parents=True, exist_ok=True)
    paths.temp_dir.mkdir(parents=True, exist_ok=True)
    paths.cache_dir.mkdir(parents=True, exist_ok=True)
    paths.backup_dir.mkdir(parents=True, exist_ok=True)

    # 初始化数据库
    init_db()

    logger.info(f"{config_manager.config.app.name} v{config_manager.config.app.version} 初始化完成")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MediaService - Windows流媒体服务")
    parser.add_argument("--config", help="配置文件路径", default=str(paths.app_config))
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--init-db", action="store_true", help="初始化数据库")
    args = parser.parse_args()

    # 加载配置
    if args.config:
        config_manager._config_file = Path(args.config)

    config = config_manager.load()

    # 调试模式覆盖
    if args.debug:
        config.app.debug = True
        config.logging.level = "DEBUG"

    # 配置日志
    setup_logging()

    # 初始化数据库
    if args.init_db:
        init_app()
        logger.info("数据库初始化完成")
        return

    # 初始化应用
    init_app()

    # 进程管理
    process_manager = ProcessManager(paths.pid_file)

    # 检查是否已有实例在运行
    if process_manager.is_running():
        logger.error(f"服务已在运行中，PID: {process_manager.read_pid()}")
        sys.exit(1)

    # 写入PID文件
    process_manager.write_pid()

    # 设置信号处理器
    process_manager.setup_signal_handlers()

    # 启动服务
    logger.info("正在启动服务...")
    from app.api.server import create_app
    app = create_app()

    import uvicorn
    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        workers=config.server.workers,
        reload=config.server.reload,
        log_level=config.logging.level.lower()
    )


if __name__ == "__main__":
    main()
