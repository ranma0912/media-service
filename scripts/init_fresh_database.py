#!/usr/bin/env python3
"""
初始化干净数据库脚本
删除现有数据库并创建全新的表结构
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db import Base, SessionLocal, engine
from app.db.models import (
    MediaFile, SubtitleFile, RecognitionResult, OrganizeTask,
    ScanHistory, ScanPath, ScanProgress, KeywordLibrary,
    KeywordRule, KeywordMapping, SeasonEpisodeRule,
    NotificationLog, ConfigHistory, OperationLog
)
from loguru import logger


def delete_existing_database():
    """删除现有数据库文件"""
    db_path = project_root / "data" / "db" / "media_service.db"
    
    if db_path.exists():
        logger.info(f"删除现有数据库: {db_path}")
        try:
            os.remove(db_path)
            logger.success("数据库文件已删除")
        except Exception as e:
            logger.error(f"删除数据库文件失败: {e}")
            return False
    else:
        logger.info("数据库文件不存在，无需删除")
    
    return True


def create_database_tables():
    """创建所有数据库表"""
    logger.info("开始创建数据库表...")
    
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        logger.success("数据库表创建成功")
        
        # 列出所有创建的表
        tables = Base.metadata.tables.keys()
        logger.info(f"已创建的表: {', '.join(tables)}")
        
        return True
    except Exception as e:
        logger.error(f"创建数据库表失败: {e}")
        return False


def initialize_default_data():
    """初始化默认数据"""
    logger.info("开始初始化默认数据...")
    
    db = SessionLocal()
    try:
        # 检查是否已有数据
        existing_libraries = db.query(KeywordLibrary).count()
        if existing_libraries > 0:
            logger.info("数据库中已有数据，跳过初始化")
            return True
        
        # 创建默认关键词库
        default_libraries = [
            {
                'library_code': 'common_words',
                'library_name': '常用关键词库',
                'library_type': 'common',
                'description': '常见的文件名关键词',
                'priority': 100,
                'is_enabled': True,
                'is_builtin': True
            },
            {
                'library_code': 'quality_tags',
                'library_name': '画质标签库',
                'library_type': 'quality',
                'description': '视频画质相关标签',
                'priority': 90,
                'is_enabled': True,
                'is_builtin': True
            },
            {
                'library_code': 'release_groups',
                'library_name': '发布组名称库',
                'library_type': 'group',
                'description': '常见的发布组名称',
                'priority': 80,
                'is_enabled': True,
                'is_builtin': True
            }
        ]
        
        for lib_data in default_libraries:
            library = KeywordLibrary(**lib_data)
            db.add(library)
            logger.info(f"添加关键词库: {lib_data['library_name']}")
        
        # 创建默认关键词规则
        default_rules = [
            {
                'library_code': 'common_words',
                'rules': [
                    ('1080p', '1080P', '标准化1080p写法'),
                    ('720p', '720P', '标准化720p写法'),
                    ('4K', '4k', '标准化4K写法'),
                    ('2160p', '2160P', '标准化2160p写法'),
                ]
            },
            {
                'library_code': 'quality_tags',
                'rules': [
                    ('BluRay', 'Blu-Ray', '标准化BluRay写法'),
                    ('WEB-DL', 'WEB-DL', '标准化WEB-DL写法'),
                    ('HDTV', 'HDTV', '标准化HDTV写法'),
                ]
            }
        ]
        
        for lib_config in default_rules:
            library = db.query(KeywordLibrary).filter_by(
                library_code=lib_config['library_code']
            ).first()
            
            if library:
                for pattern, replacement, desc in lib_config['rules']:
                    rule = KeywordRule(
                        library_id=library.id,
                        rule_name=f"{pattern}替换",
                        pattern=pattern,
                        replacement=replacement,
                        description=desc,
                        priority=100,
                        is_regex=False,
                        is_case_sensitive=False,
                        match_mode='all',
                        is_enabled=True
                    )
                    db.add(rule)
                    logger.info(f"添加关键词规则: {pattern} -> {replacement}")
        
        db.commit()
        logger.success("默认数据初始化成功")
        return True
        
    except Exception as e:
        logger.error(f"初始化默认数据失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def verify_database():
    """验证数据库结构"""
    logger.info("开始验证数据库结构...")
    
    db = SessionLocal()
    try:
        # 检查所有表是否可访问
        tables_to_check = [
            (MediaFile, 'media_files'),
            (SubtitleFile, 'subtitle_files'),
            (RecognitionResult, 'recognition_results'),
            (OrganizeTask, 'organize_tasks'),
            (ScanHistory, 'scan_history'),
            (ScanPath, 'scan_paths'),
            (ScanProgress, 'scan_progress'),
            (KeywordLibrary, 'keyword_libraries'),
            (KeywordRule, 'keyword_rules'),
            (KeywordMapping, 'keyword_mappings'),
            (SeasonEpisodeRule, 'season_episode_rules'),
            (NotificationLog, 'notification_logs'),
            (ConfigHistory, 'config_history'),
            (OperationLog, 'operation_logs')
        ]
        
        for model, table_name in tables_to_check:
            count = db.query(model).count()
            logger.info(f"表 {table_name}: 记录数 = {count}")
        
        logger.success("数据库结构验证成功")
        return True
        
    except Exception as e:
        logger.error(f"验证数据库结构失败: {e}")
        return False
    finally:
        db.close()


def main():
    """主函数"""
    logger.info("="*60)
    logger.info("开始初始化数据库")
    logger.info("="*60)
    
    # 确保data目录存在
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    
    # 步骤1: 删除现有数据库
    if not delete_existing_database():
        logger.error("删除数据库失败，终止初始化")
        return False
    
    # 步骤2: 创建数据库表
    if not create_database_tables():
        logger.error("创建数据库表失败，终止初始化")
        return False
    
    # 步骤3: 初始化默认数据
    if not initialize_default_data():
        logger.error("初始化默认数据失败，终止初始化")
        return False
    
    # 步骤4: 验证数据库结构
    if not verify_database():
        logger.error("验证数据库结构失败，终止初始化")
        return False
    
    logger.success("="*60)
    logger.success("数据库初始化完成！")
    logger.success("="*60)
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warning("用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"初始化数据库时发生错误: {e}")
        sys.exit(1)