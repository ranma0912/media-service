"""
清理数据库脚本：删除所有扫描任务和媒体文件记录
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import get_db_context
from app.db.models import (
    ScanHistory, MediaFile, ScanPath, ScanProgress,
    SubtitleFile, RecognitionResult, OrganizeTask
)
from loguru import logger


def clear_database():
    """清理数据库中的所有扫描任务和媒体文件记录"""
    try:
        with get_db_context() as db:
            # 删除所有整理任务记录
            organize_count = db.query(OrganizeTask).count()
            db.query(OrganizeTask).delete()
            logger.info(f"已删除 {organize_count} 条整理任务记录")

            # 删除所有识别结果记录
            recognition_count = db.query(RecognitionResult).count()
            db.query(RecognitionResult).delete()
            logger.info(f"已删除 {recognition_count} 条识别结果记录")

            # 删除所有字幕文件记录
            subtitle_count = db.query(SubtitleFile).count()
            db.query(SubtitleFile).delete()
            logger.info(f"已删除 {subtitle_count} 条字幕文件记录")

            # 删除所有媒体文件记录
            media_count = db.query(MediaFile).count()
            db.query(MediaFile).delete()
            logger.info(f"已删除 {media_count} 条媒体文件记录")

            # 删除所有扫描进度记录
            progress_count = db.query(ScanProgress).count()
            db.query(ScanProgress).delete()
            logger.info(f"已删除 {progress_count} 条扫描进度记录")

            # 删除所有扫描历史记录
            history_count = db.query(ScanHistory).count()
            db.query(ScanHistory).delete()
            logger.info(f"已删除 {history_count} 条扫描历史记录")

            # 删除所有扫描路径记录
            path_count = db.query(ScanPath).count()
            db.query(ScanPath).delete()
            logger.info(f"已删除 {path_count} 条扫描路径记录")

            # 提交更改
            db.commit()
            logger.success("数据库清理完成！")

    except Exception as e:
        logger.error(f"清理数据库失败: {e}")
        raise


if __name__ == "__main__":
    logger.info("开始清理数据库...")
    clear_database()
