# -*- coding: utf-8 -*-
"""
添加文件任务表的数据库迁移脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db import Base, engine, get_db_context
from app.db.models import FileTask
from loguru import logger


def migrate():
    """执行数据库迁移"""
    try:
        logger.info("开始添加 file_tasks 表...")
        
        # 创建新表
        FileTask.__table__.create(engine, checkfirst=True)
        
        logger.info("file_tasks 表创建成功")
        logger.info("数据库迁移完成")
        
        return True
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        return False


if __name__ == "__main__":
    success = migrate()
    if success:
        print("数据库迁移成功")
    else:
        print("数据库迁移失败")
        exit(1)
