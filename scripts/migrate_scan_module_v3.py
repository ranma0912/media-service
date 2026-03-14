# -*- coding: utf-8 -*-
"""
数据库迁移脚本：扫描模块v3重构
添加以下新字段：
- MediaFile: video_tracks, audio_tracks, subtitle_tracks (轨道信息)
- MediaFile.sha256_hash: 添加唯一索引
- ScanPath: skip_strategy, scan_subdirectories, scan_debounce_time, monitoring_mode, 
  monitoring_debounce, auto_recognize, auto_organize, ignore_patterns, 
  last_scan_batch_id, total_scans, total_files_found
- FileTask: batch_id, scan_progress, scan_started_at, scan_completed_at
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text, inspect
from app.db import engine
from loguru import logger


def migrate():
    """执行数据库迁移"""
    try:
        with engine.connect() as conn:
            # 开始事务
            trans = conn.begin()
            
            try:
                logger.info("开始扫描模块v3迁移...")
                
                # 使用SQLAlchemy的inspect来检查表结构
                inspector = inspect(engine)
                
                # 获取media_files表的列信息
                media_files_columns = [col['name'] for col in inspector.get_columns('media_files')]
                logger.info(f"当前media_files表的列: {media_files_columns}")
                
                # 检查并添加MediaFile的轨道信息字段
                if 'video_tracks' not in media_files_columns:
                    logger.info("添加video_tracks字段...")
                    conn.execute(text("""
                        ALTER TABLE media_files 
                        ADD COLUMN video_tracks INTEGER DEFAULT 0
                    """))
                else:
                    logger.info("video_tracks字段已存在，跳过")
                
                if 'audio_tracks' not in media_files_columns:
                    logger.info("添加audio_tracks字段...")
                    conn.execute(text("""
                        ALTER TABLE media_files 
                        ADD COLUMN audio_tracks INTEGER DEFAULT 0
                    """))
                else:
                    logger.info("audio_tracks字段已存在，跳过")
                
                if 'subtitle_tracks' not in media_files_columns:
                    logger.info("添加subtitle_tracks字段...")
                    conn.execute(text("""
                        ALTER TABLE media_files 
                        ADD COLUMN subtitle_tracks INTEGER DEFAULT 0
                    """))
                else:
                    logger.info("subtitle_tracks字段已存在，跳过")
                
                # 更新现有记录的轨道信息
                logger.info("更新现有记录的轨道信息...")
                conn.execute(text("""
                    UPDATE media_files 
                    SET 
                        video_tracks = CASE WHEN video_codec IS NOT NULL THEN 1 ELSE 0 END,
                        audio_tracks = CASE WHEN audio_codec IS NOT NULL THEN 1 ELSE 0 END,
                        subtitle_tracks = CASE WHEN has_embedded_subtitle = 'embedded' THEN 1 ELSE 0 END
                    WHERE video_tracks = 0 OR audio_tracks = 0 OR subtitle_tracks = 0
                """))
                
                # 检查索引
                indexes = inspector.get_indexes('media_files')
                index_names = [idx['name'] for idx in indexes]
                logger.info(f"当前media_files表的索引: {index_names}")
                
                if 'sha256_hash' not in index_names:
                    logger.info("添加sha256_hash索引...")
                    conn.execute(text("""
                        CREATE INDEX sha256_hash ON media_files(sha256_hash)
                    """))
                else:
                    logger.info("sha256_hash索引已存在，跳过")
                
                # SQLite需要创建唯一索引的方式
                if 'uq_media_files_sha256_hash' not in index_names:
                    logger.info("添加sha256_hash唯一索引...")
                    # 先删除可能存在的普通索引
                    conn.execute(text("DROP INDEX IF EXISTS sha256_hash_idx"))
                    # 创建唯一索引
                    conn.execute(text("""
                        CREATE UNIQUE INDEX uq_media_files_sha256_hash ON media_files(sha256_hash)
                    """))
                else:
                    logger.info("uq_media_files_sha256_hash唯一索引已存在，跳过")
                
                # 获取scan_paths表的列信息
                scan_paths_columns = [col['name'] for col in inspector.get_columns('scan_paths')]
                logger.info(f"当前scan_paths表的列: {scan_paths_columns}")
                
                # 检查并添加ScanPath的新字段
                new_scan_path_fields = [
                    ('skip_strategy', 'VARCHAR(20)', 'keyword'),
                    ('scan_subdirectories', 'BOOLEAN', '1'),
                    ('scan_debounce_time', 'INTEGER', '30'),
                    ('monitoring_mode', 'VARCHAR(20)', 'watchdog'),
                    ('monitoring_debounce', 'INTEGER', '5'),
                    ('auto_recognize', 'BOOLEAN', '0'),
                    ('auto_organize', 'BOOLEAN', '0'),
                    ('ignore_patterns', 'TEXT', 'NULL'),
                    ('last_scan_batch_id', 'VARCHAR(64)', 'NULL'),
                    ('total_scans', 'INTEGER', '0'),
                    ('total_files_found', 'INTEGER', '0')
                ]
                
                for field_name, field_type, default_value in new_scan_path_fields:
                    if field_name not in scan_paths_columns:
                        logger.info(f"添加scan_paths.{field_name}字段...")
                        conn.execute(text(f"""
                            ALTER TABLE scan_paths 
                            ADD COLUMN {field_name} {field_type} DEFAULT {default_value}
                        """))
                    else:
                        logger.info(f"scan_paths.{field_name}字段已存在，跳过")
                
                # 获取file_tasks表的列信息
                file_tasks_columns = [col['name'] for col in inspector.get_columns('file_tasks')]
                logger.info(f"当前file_tasks表的列: {file_tasks_columns}")
                
                # 检查并添加FileTask的新字段
                new_file_task_fields = [
                    ('batch_id', 'VARCHAR(64)', 'NULL'),
                    ('scan_progress', 'INTEGER', '0'),
                    ('scan_started_at', 'DATETIME', 'NULL'),
                    ('scan_completed_at', 'DATETIME', 'NULL')
                ]
                
                for field_name, field_type, default_value in new_file_task_fields:
                    if field_name not in file_tasks_columns:
                        logger.info(f"添加file_tasks.{field_name}字段...")
                        conn.execute(text(f"""
                            ALTER TABLE file_tasks 
                            ADD COLUMN {field_name} {field_type} DEFAULT {default_value}
                        """))
                    else:
                        logger.info(f"file_tasks.{field_name}字段已存在，跳过")
                
                # 提交事务
                trans.commit()
                logger.info("扫描模块v3迁移完成！")
                
            except Exception as e:
                trans.rollback()
                logger.error(f"迁移失败，已回滚: {e}")
                raise
                
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        raise


if __name__ == "__main__":
    migrate()