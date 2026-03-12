"""
数据库初始化脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db import init_db


def main():
    """主函数"""
    print("开始初始化数据库...")

    # 初始化数据库
    init_db()

    print("数据库初始化完成！")
    print(f"数据库路径: {project_root / 'data' / 'media_service.db'}")


if __name__ == "__main__":
    main()
