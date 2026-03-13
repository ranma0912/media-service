"""
清理数据库脚本：删除所有扫描任务和媒体文件记录
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import get_db_context
from app.db.models import ScanHistory, MediaFile
from loguru import logger


def clear_database():
    """清理数据库中的所有扫描任务和媒体文件记录"""
    try:
        with get_db_context() as db:
            # 删除所有媒体文件记录
            media_count = db.query(MediaFile).count()
            db.query(MediaFile).delete()
            logger.info(f"已删除 {media_count} 条媒体文件记录")

            # 删除所有扫描历史记录
            history_count = db.query(ScanHistory).count()
            db.query(ScanHistory).delete()
            logger.info(f"已删除 {history_count} 条扫描历史记录")

            # 提交更改
            db.commit()
            logger.success("数据库清理完成！")

    except Exception as e:
        logger.error(f"清理数据库失败: {e}")
        raise


if __name__ == "__main__":
    logger.info("开始清理数据库...")
    clear_database()
