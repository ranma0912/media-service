"""
检查数据库中所有表的结构
"""
import sqlite3
from pathlib import Path

# 数据库路径
db_path = Path(__file__).parent.parent / "data" / "db" / "media_service.db"

def check_all_tables():
    """检查所有表结构"""
    print(f"连接数据库: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        print(f"\n数据库中共有 {len(tables)} 个表:")

        for table in tables:
            table_name = table[0]
            print(f"\n=== {table_name} ===")

            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            print(f"列数: {len(columns)}")
            print("列详情:")
            for col in columns:
                print(f"  - {col[1]}: {col[2]} (nullable: {not col[3]}, default: {col[4]}, pk: {col[5]})")

            # 获取索引信息
            cursor.execute(f"PRAGMA index_list({table_name})")
            indexes = cursor.fetchall()
            if indexes:
                print("\n索引:")
                for idx in indexes:
                    print(f"  - {idx[1]} (unique: {idx[2]})")

    except Exception as e:
        print(f"错误: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    check_all_tables()