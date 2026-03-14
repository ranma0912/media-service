# -*- coding: utf-8 -*-
"""
清理数据库所有扫描相关数据
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from app.db import get_db_context
from app.db.models import MediaFile, ScanPath, ScanHistory, ScanProgress, FileTask, SubtitleFile


def clear_all_scan_data():
    """清理所有扫描相关数据"""
    try:
        with get_db_context() as db:
            logger.info("开始清理扫描数据...")
            
            # 统计需要删除的数据量
            media_files_count = db.query(MediaFile).count()
            scan_paths_count = db.query(ScanPath).count()
            scan_history_count = db.query(ScanHistory).count()
            scan_progress_count = db.query(ScanProgress).count()
            file_tasks_count = db.query(FileTask).count()
            subtitle_files_count = db.query(SubtitleFile).count()
            
            logger.info(f"当前数据统计：")
            logger.info(f"  媒体文件: {media_files_count} 条")
            logger.info(f"  扫描路径: {scan_paths_count} 条")
            logger.info(f"  扫描历史: {scan_history_count} 条")
            logger.info(f"  扫描进度: {scan_progress_count} 条")
            logger.info(f"  文件任务: {file_tasks_count} 条")
            logger.info(f"  字幕文件: {subtitle_files_count} 条")
            
            # 删除字幕文件
            logger.info("正在删除字幕文件...")
            db.query(SubtitleFile).delete()
            db.commit()
            
            # 删除文件任务
            logger.info("正在删除文件任务...")
            db.query(FileTask).delete()
            db.commit()
            
            # 删除扫描进度
            logger.info("正在删除扫描进度...")
            db.query(ScanProgress).delete()
            db.commit()
            
            # 删除扫描历史
            logger.info("正在删除扫描历史...")
            db.query(ScanHistory).delete()
            db.commit()
            
            # 删除扫描路径
            logger.info("正在删除扫描路径...")
            db.query(ScanPath).delete()
            db.commit()
            
            # 删除媒体文件
            logger.info("正在删除媒体文件...")
            db.query(MediaFile).delete()
            db.commit()
            
            logger.success("所有扫描数据已清理完成！")
            
    except Exception as e:
        logger.error(f"清理数据失败: {e}")
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库扫描数据清理工具')
    parser.add_argument('--yes', '-y', action='store_true', help='跳过确认，直接执行清理')
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("数据库扫描数据清理工具")
    logger.info("=" * 60)
    logger.warning("此操作将删除所有扫描相关数据，包括：")
    logger.warning("  1. 媒体文件记录")
    logger.warning("  2. 扫描路径配置")
    logger.warning("  3. 扫描历史记录")
    logger.warning("  4. 扫描进度记录")
    logger.warning("  5. 文件任务记录")
    logger.warning("  6. 字幕文件记录")
    logger.warning("此操作不可恢复！")
    logger.info("=" * 60)
    
    # 检查是否跳过确认
    if args.yes:
        logger.info("使用 --yes 参数，跳过确认，直接执行清理...")
        logger.info("正在清理...")
        clear_all_scan_data()
        logger.success("清理完成！")
    else:
        # 询问用户确认
        try:
            confirm = input("\n确认要清理所有扫描数据吗？(yes/no): ")
            
            if confirm.lower() in ['yes', 'y']:
                logger.info("正在清理...")
                clear_all_scan_data()
                logger.success("清理完成！")
            else:
                logger.info("已取消操作")
        except EOFError:
            logger.error("无法获取用户输入，请使用 --yes 参数跳过确认")
            logger.info("使用示例: python scripts/clear_scan_data.py --yes")
            sys.exit(1)