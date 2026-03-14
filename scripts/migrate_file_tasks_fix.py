# -*- coding: utf-8 -*-
"""
修复FileTask表结构 - 删除不应该存在的字段
删除字段：scan_type, recursive, skip_strategy
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
                logger.info("开始修复file_tasks表结构...")
                
                # 获取file_tasks表的列信息
                inspector = inspect(engine)
                file_tasks_columns = [col['name'] for col in inspector.get_columns('file_tasks')]
                logger.info(f"当前file_tasks表的列: {file_tasks_columns}")
                
                # 检查并删除不应该存在的字段
                columns_to_drop = ['scan_type', 'recursive', 'skip_strategy']
                
                for column_name in columns_to_drop:
                    if column_name in file_tasks_columns:
                        logger.info(f"删除file_tasks.{column_name}字段...")
                        # SQLite不支持DROP COLUMN，需要重建表
                        # 这里我们只是记录，实际需要手动处理
                        logger.warning(f"SQLite不支持DROP COLUMN，需要手动删除字段: {column_name}")
                    else:
                        logger.info(f"file_tasks.{column_name}字段不存在，跳过")
                
                # 对于SQLite，我们需要重建表
                if any(col in file_tasks_columns for col in columns_to_drop):
                    logger.info("检测到需要删除的字段，重建file_tasks表...")
                    
                    # 备份数据
                    backup_data = conn.execute(text("""
                        SELECT * FROM file_tasks
                    """)).fetchall()
                    
                    logger.info(f"备份了 {len(backup_data)} 条数据")
                    
                    # 删除旧表
                    conn.execute(text("DROP TABLE IF EXISTS file_tasks_old"))
                    conn.execute(text("ALTER TABLE file_tasks RENAME TO file_tasks_old"))
                    
                    # 创建新表（不包含不需要的字段）
                    conn.execute(text("""
                        CREATE TABLE file_tasks (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            batch_id VARCHAR(36),
                            media_file_id INTEGER NOT NULL,
                            target_path VARCHAR(500) NOT NULL,
                            file_name VARCHAR(255) NOT NULL,
                            status VARCHAR(20) NOT NULL DEFAULT 'pending',
                            scan_progress FLOAT DEFAULT 0,
                            scan_started_at DATETIME,
                            scan_completed_at DATETIME,
                            scan_error TEXT,
                            video_tracks INTEGER DEFAULT 0,
                            audio_tracks INTEGER DEFAULT 0,
                            subtitle_tracks INTEGER DEFAULT 0,
                            video_codec VARCHAR(50),
                            audio_codec VARCHAR(50),
                            has_external_subtitle BOOLEAN DEFAULT 0,
                            external_subtitle_name VARCHAR(255),
                            scan_result VARCHAR(20),
                            recognition_started_at DATETIME,
                            recognition_completed_at DATETIME,
                            recognition_error TEXT,
                            organize_started_at DATETIME,
                            organize_completed_at DATETIME,
                            organize_error TEXT,
                            organize_action VARCHAR(20),
                            source_path VARCHAR(500),
                            target_path_final VARCHAR(500),
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(media_file_id) REFERENCES media_files(id)
                        )
                    """))
                    
                    # 创建索引
                    conn.execute(text("CREATE INDEX ix_file_tasks_batch_id ON file_tasks(batch_id)"))
                    conn.execute(text("CREATE INDEX ix_file_tasks_media_file_id ON file_tasks(media_file_id)"))
                    conn.execute(text("CREATE INDEX ix_file_tasks_status ON file_tasks(status)"))
                    conn.execute(text("CREATE INDEX ix_file_tasks_created_at ON file_tasks(created_at)"))
                    
                    # 恢复数据（排除删除的字段）
                    for row in backup_data:
                        conn.execute(text("""
                            INSERT INTO file_tasks (
                                id, batch_id, media_file_id, target_path, file_name,
                                status, scan_progress, scan_started_at, scan_completed_at,
                                scan_error, video_tracks, audio_tracks, subtitle_tracks,
                                video_codec, audio_codec, has_external_subtitle,
                                external_subtitle_name, scan_result, recognition_started_at,
                                recognition_completed_at, recognition_error, organize_started_at,
                                organize_completed_at, organize_error, organize_action,
                                source_path, target_path_final, created_at, updated_at
                            ) VALUES (
                                :id, :batch_id, :media_file_id, :target_path, :file_name,
                                :status, :scan_progress, :scan_started_at, :scan_completed_at,
                                :scan_error, :video_tracks, :audio_tracks, :subtitle_tracks,
                                :video_codec, :audio_codec, :has_external_subtitle,
                                :external_subtitle_name, :scan_result, :recognition_started_at,
                                :recognition_completed_at, :recognition_error, :organize_started_at,
                                :organize_completed_at, :organize_error, :organize_action,
                                :source_path, :target_path_final, :created_at, :updated_at
                            )
                        """), {
                            'id': row[0],
                            'batch_id': row[1],
                            'media_file_id': row[2],
                            'target_path': row[3],
                            'file_name': row[4],
                            'status': row[5],
                            'scan_progress': row[6],
                            'scan_started_at': row[7],
                            'scan_completed_at': row[8],
                            'scan_error': row[9],
                            'video_tracks': row[10],
                            'audio_tracks': row[11],
                            'subtitle_tracks': row[12],
                            'video_codec': row[13],
                            'audio_codec': row[14],
                            'has_external_subtitle': row[15],
                            'external_subtitle_name': row[16],
                            'scan_result': row[17],
                            'recognition_started_at': row[18],
                            'recognition_completed_at': row[19],
                            'recognition_error': row[20],
                            'organize_started_at': row[21],
                            'organize_completed_at': row[22],
                            'organize_error': row[23],
                            'organize_action': row[24],
                            'source_path': row[25],
                            'target_path_final': row[26],
                            'created_at': row[27],
                            'updated_at': row[28]
                        })
                    
                    logger.info(f"恢复了 {len(backup_data)} 条数据")
                    
                    # 删除备份表
                    conn.execute(text("DROP TABLE file_tasks_old"))
                    
                    logger.info("file_tasks表重建完成！")
                else:
                    logger.info("file_tasks表结构正确，无需修改")
                
                # 提交事务
                trans.commit()
                logger.info("file_tasks表修复完成！")
                
            except Exception as e:
                trans.rollback()
                logger.error(f"迁移失败，已回滚: {e}")
                raise
                
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        raise


if __name__ == "__main__":
    migrate()