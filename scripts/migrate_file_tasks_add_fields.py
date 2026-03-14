# -*- coding: utf-8 -*-
"""
修复FileTask表结构 - 添加缺失的字段
添加字段：video_tracks, audio_tracks, subtitle_tracks, video_codec, audio_codec,
         has_external_subtitle, external_subtitle_name, scan_result
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
                
                # 需要添加的字段
                columns_to_add = {
                    'video_tracks': 'INTEGER DEFAULT 0',
                    'audio_tracks': 'INTEGER DEFAULT 0',
                    'subtitle_tracks': 'INTEGER DEFAULT 0',
                    'video_codec': 'VARCHAR(50)',
                    'audio_codec': 'VARCHAR(50)',
                    'has_external_subtitle': 'BOOLEAN DEFAULT 0',
                    'external_subtitle_name': 'VARCHAR(255)',
                    'scan_result': 'VARCHAR(20)'
                }
                
                # SQLite支持ALTER TABLE ADD COLUMN
                for column_name, column_def in columns_to_add.items():
                    if column_name not in file_tasks_columns:
                        logger.info(f"添加file_tasks.{column_name}字段...")
                        conn.execute(text(f"""
                            ALTER TABLE file_tasks 
                            ADD COLUMN {column_name} {column_def}
                        """))
                    else:
                        logger.info(f"file_tasks.{column_name}字段已存在，跳过")
                
                # 提交事务
                trans.commit()
                logger.info("file_tasks表字段添加完成！")
                
                # 验证
                logger.info("验证字段是否添加成功...")
                inspector = inspect(engine)
                new_columns = [col['name'] for col in inspector.get_columns('file_tasks')]
                logger.info(f"更新后的file_tasks表的列: {new_columns}")
                
                missing_columns = [col for col in columns_to_add.keys() if col not in new_columns]
                if missing_columns:
                    logger.error(f"以下字段仍然缺失: {missing_columns}")
                else:
                    logger.success("所有必需的字段都已添加！")
                
            except Exception as e:
                trans.rollback()
                logger.error(f"迁移失败，已回滚: {e}")
                raise
                
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        raise


if __name__ == "__main__":
    migrate()