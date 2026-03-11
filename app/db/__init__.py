"""
数据库模块
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import config_manager

# 获取数据库配置
db_config = config_manager.config.database

# 创建数据库引擎
engine = create_engine(
    db_config.url,
    echo=db_config.echo,
    pool_size=db_config.pool_size
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from app.db.models import *  # noqa: F401

def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)
