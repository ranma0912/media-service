"""
检查数据库表结构
"""
import sqlite3
from pathlib import Path

# 数据库路径
db_path = Path(__file__).parent.parent / "data" / "db" / "media_service.db"

def check_table_structure():
    """检查表结构"""
    print(f"连接数据库: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 检查scan_paths表结构
        cursor.execute("PRAGMA table_info(scan_paths)")
        columns = cursor.fetchall()

        print(f"列数: {len(columns)}")
        print("列详情:")
        for col in columns:
            print(f"  - {col[1]}: {col[2]} (nullable: {not col[3]}, default: {col[4]}, pk: {col[5]})")

        # 检查是否有path_name列
        column_names = [col[1] for col in columns]
        if "path_name" in column_names:
            print("path_name列存在")
        else:
            print("path_name列不存在")

        # 查看表中的数据
        print("scan_paths表数据:")
        cursor.execute("SELECT * FROM scan_paths")
        rows = cursor.fetchall()
        print(f"记录数: {len(rows)}")
        for row in rows:
            print(f"  ID: {row[0]}, Path: {row[1]}")
            if len(row) > 2:
                print(f"  path_name: {row[2]}")

    except Exception as e:
        print(f"错误: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    check_table_structure()
