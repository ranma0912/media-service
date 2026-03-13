"""
重建scan_paths表，确保列顺序正确
"""
import sqlite3
from pathlib import Path
import shutil
from datetime import datetime

# 数据库路径
db_path = Path(__file__).parent.parent / "data" / "db" / "media_service.db"

def rebuild_scan_paths_table():
    """重建scan_paths表"""
    print(f"连接数据库: {db_path}")

    # 备份数据库
    backup_path = db_path.with_suffix('.db.backup')
    print(f"备份数据库到: {backup_path}")
    shutil.copy2(db_path, backup_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 备份现有数据
        print("备份现有数据...")
        cursor.execute("SELECT * FROM scan_paths")
        old_data = cursor.fetchall()
        print(f"备份了 {len(old_data)} 条记录")

        # 删除旧表
        print("删除旧表...")
        cursor.execute("DROP TABLE IF EXISTS scan_paths")

        # 创建新表（正确的列顺序）
        print("创建新表...")
        cursor.execute("""
            CREATE TABLE scan_paths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path VARCHAR(500) UNIQUE NOT NULL,
                path_name VARCHAR(100),
                enabled BOOLEAN DEFAULT 1,
                scan_type VARCHAR(20) DEFAULT 'incremental',
                recursive BOOLEAN DEFAULT 1,
                scan_interval INTEGER DEFAULT 300,
                monitoring_enabled BOOLEAN DEFAULT 1,
                monitoring_debounce INTEGER DEFAULT 5,
                ignore_patterns TEXT,
                last_scan_at DATETIME,
                last_scan_batch_id VARCHAR(36),
                total_scans INTEGER DEFAULT 0,
                total_files_found INTEGER DEFAULT 0,
                created_at DATETIME,
                updated_at DATETIME
            )
        """)

        # 恢复数据
        print("恢复数据...")
        for row in old_data:
            # 旧数据结构: id, path, recursive, enabled, last_scan_at, last_scan_batch_id, created_at, updated_at, path_name
            # 新数据结构: id, path, path_name, enabled, scan_type, recursive, scan_interval, monitoring_enabled, monitoring_debounce, ignore_patterns, last_scan_at, last_scan_batch_id, total_scans, total_files_found, created_at, updated_at
            cursor.execute("""
                INSERT INTO scan_paths (
                    id, path, path_name, enabled, scan_type, recursive, scan_interval,
                    monitoring_enabled, monitoring_debounce, ignore_patterns,
                    last_scan_at, last_scan_batch_id, total_scans, total_files_found,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row[0],  # id
                row[1],  # path
                row[8] if len(row) > 8 else None,  # path_name
                row[3],  # enabled
                'incremental',  # scan_type (默认值)
                row[2],  # recursive
                300,  # scan_interval (默认值)
                True,  # monitoring_enabled (默认值)
                5,  # monitoring_debounce (默认值)
                None,  # ignore_patterns (默认值)
                row[4],  # last_scan_at
                row[5],  # last_scan_batch_id
                0,  # total_scans (默认值)
                0,  # total_files_found (默认值)
                row[6],  # created_at
                row[7],  # updated_at
            ))

        conn.commit()
        print("重建完成！")
        print(f"已恢复 {len(old_data)} 条记录")

    except Exception as e:
        print(f"重建失败: {e}")
        conn.rollback()
        print("正在从备份恢复...")
        shutil.copy2(backup_path, db_path)
        print("已从备份恢复")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    rebuild_scan_paths_table()
