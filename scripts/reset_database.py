"""
重置数据库脚本：清空数据库并重新初始化
"""
import sys
import os
import shutil

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import get_db_context, Base, engine
from app.db.models import (
    ScanHistory, MediaFile, ScanPath, ScanProgress,
    SubtitleFile, RecognitionResult, OrganizeTask
)
from loguru import logger


def reset_database():
    """重置数据库"""
    try:
        # 获取数据库文件路径
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'db', 'media_service.db')

        # 关闭所有数据库连接
        engine.dispose()

        # 删除数据库文件
        if os.path.exists(db_path):
            logger.info(f"正在删除数据库文件: {db_path}")
            os.remove(db_path)
            logger.success("数据库文件已删除")
        else:
            logger.warning(f"数据库文件不存在: {db_path}")

        # 重新创建所有表
        logger.info("正在创建数据库表...")
        Base.metadata.create_all(bind=engine)
        logger.success("数据库表创建完成")

        logger.success("数据库重置完成！")

    except Exception as e:
        logger.error(f"重置数据库失败: {e}")
        raise


if __name__ == "__main__":
    logger.info("开始重置数据库...")
    reset_database()
