"""
数据库迁移脚本：添加path_name列到scan_paths表
"""
import sqlite3
from pathlib import Path

# 数据库路径
db_path = Path(__file__).parent.parent / "data" / "db" / "media_service.db"

def migrate():
    """执行迁移"""
    print(f"连接数据库: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 检查path_name列是否已存在
        cursor.execute("PRAGMA table_info(scan_paths)")
        columns = [column[1] for column in cursor.fetchall()]

        if "path_name" in columns:
            print("path_name列已存在，无需迁移")
            return

        # 添加path_name列
        print("添加path_name列...")
        cursor.execute("ALTER TABLE scan_paths ADD COLUMN path_name VARCHAR(100)")

        # 为现有记录设置默认的path_name（使用路径的最后一部分）
        print("更新现有记录的path_name...")
        cursor.execute(r"""
            UPDATE scan_paths 
            SET path_name = (
                CASE 
                    WHEN path LIKE '%\%' THEN substr(path, instr(path, '\', -1) + 1)
                    WHEN path LIKE '%/%' THEN substr(path, instr(path, '/', -1) + 1)
                    ELSE path
                END
            )
        """)

        conn.commit()
        print("迁移完成！")

    except Exception as e:
        print(f"迁移失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()