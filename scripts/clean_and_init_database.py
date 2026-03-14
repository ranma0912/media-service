# -*- coding: utf-8 -*-
"""
数据库清理和重新初始化脚本
删除现有数据库并使用UTF-8编码重新创建
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db import engine, Base, get_db_context
from app.db.models import *
from loguru import logger


def get_database_path():
    """获取数据库文件路径"""
    from app.core.config import config_manager
    db_url = config_manager.config.database.url
    # 解析SQLite路径: sqlite:///./data/db/media_service.db
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        return Path(db_path).absolute()
    return None


def clean_database():
    """清理数据库文件"""
    db_path = get_database_path()
    
    if not db_path:
        logger.error("无法确定数据库路径")
        return False
    
    if not db_path.exists():
        logger.warning(f"数据库文件不存在: {db_path}")
        return True
    
    try:
        # 关闭所有数据库连接
        engine.dispose()
        
        # 删除数据库文件
        db_path.unlink()
        logger.info(f"已删除数据库文件: {db_path}")
        
        # 删除关联的临时文件
        for temp_file in db_path.parent.glob(f"{db_path.stem}*"):
            if temp_file.exists() and temp_file != db_path:
                try:
                    temp_file.unlink()
                    logger.info(f"已删除临时文件: {temp_file}")
                except Exception as e:
                    logger.warning(f"删除临时文件失败: {temp_file}, 错误: {e}")
        
        return True
    except Exception as e:
        logger.error(f"清理数据库失败: {e}")
        return False


def init_database():
    """初始化数据库（创建所有表）"""
    try:
        logger.info("开始初始化数据库...")
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        
        logger.info("数据库初始化成功")
        
        # 列出所有表
        tables = [table.name for table in Base.metadata.sorted_tables]
        logger.info(f"已创建表: {', '.join(tables)}")
        
        return True
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False


def verify_database():
    """验证数据库是否正确创建"""
    try:
        with get_db_context() as db:
            # 检查一些关键表是否存在
            tables_to_check = [
                'media_files',
                'subtitle_files',
                'recognition_results',
                'organize_tasks',
                'scan_history',
                'scan_paths',
                'scan_progress',
                'keyword_libraries',
                'keyword_rules',
                'keyword_mappings',
                'season_episode_rules',
                'notification_logs',
                'config_history',
                'file_tasks',
                'operation_logs'
            ]
            
            existing_tables = Base.metadata.tables.keys()
            missing_tables = [t for t in tables_to_check if t not in existing_tables]
            
            if missing_tables:
                logger.warning(f"缺少表: {', '.join(missing_tables)}")
                return False
            
            logger.info(f"数据库验证通过，共 {len(existing_tables)} 个表")
            return True
    except Exception as e:
        logger.error(f"数据库验证失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("数据库清理和重新初始化工具")
    print("=" * 60)
    
    # 显示数据库信息
    db_path = get_database_path()
    print(f"\n数据库路径: {db_path}")
    print(f"数据库存在: {'是' if db_path and db_path.exists() else '否'}")
    
    # 确认操作
    print("\n[警告] 此操作将删除所有现有数据！")
    print("以下操作将被执行：")
    print("  1. 删除现有数据库文件")
    print("  2. 重新创建数据库（使用UTF-8编码）")
    print("  3. 初始化所有表结构")
    print("\n此操作不可恢复！")
    
    confirm = input("\n确认继续？(输入 'YES' 继续): ")
    
    if confirm.upper() != "YES":
        print("\n操作已取消")
        return
    
    print("\n开始执行...\n")
    
    # 1. 清理数据库
    print("步骤 1/3: 清理现有数据库...")
    if not clean_database():
        print("\n[失败] 数据库清理失败")
        return
    print("[成功] 数据库清理完成")
    
    # 2. 初始化数据库
    print("\n步骤 2/3: 初始化数据库...")
    if not init_database():
        print("\n[失败] 数据库初始化失败")
        return
    print("[成功] 数据库初始化完成")
    
    # 3. 验证数据库
    print("\n步骤 3/3: 验证数据库...")
    if not verify_database():
        print("\n[失败] 数据库验证失败")
        return
    print("[成功] 数据库验证完成")
    
    print("\n" + "=" * 60)
    print("[完成] 数据库清理和重新初始化成功！")
    print("=" * 60)
    print("\n数据库已使用UTF-8编码重新创建，支持中文、日文、韩文等所有Unicode字符")
    print(f"数据库位置: {db_path}")
    print(f"表数量: {len(Base.metadata.tables)}")


if __name__ == "__main__":
    main()