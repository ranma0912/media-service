"""
完全重新初始化数据库脚本
删除所有表并重新创建正确的表结构
"""
import sqlite3
from pathlib import Path

# 数据库路径
db_path = Path(__file__).parent.parent / "data" / "db" / "media_service.db"

def drop_all_tables(cursor):
    """删除所有表"""
    print("删除所有表...")

    # 获取所有表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()

    # 禁用外键约束
    cursor.execute("PRAGMA foreign_keys = OFF")

    # 删除所有表
    for table in tables:
        table_name = table[0]
        if not table_name.startswith('sqlite_'):
            print(f"  删除表: {table_name}")
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

    # 重新启用外键约束
    cursor.execute("PRAGMA foreign_keys = ON")

def create_media_files_table(cursor):
    """创建媒体文件表"""
    print("创建表: media_files")
    cursor.execute("""
        CREATE TABLE media_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path VARCHAR(500) UNIQUE NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            file_stem VARCHAR(255),
            file_extension VARCHAR(20),
            file_size INTEGER DEFAULT 0,
            sha256_hash VARCHAR(64),
            media_type VARCHAR(20),
            create_time DATETIME,
            modify_time DATETIME,
            access_time DATETIME,
            duration REAL DEFAULT 0,
            width INTEGER DEFAULT 0,
            height INTEGER DEFAULT 0,
            video_codec VARCHAR(50),
            video_bitrate INTEGER DEFAULT 0,
            frame_rate REAL DEFAULT 0,
            audio_codec VARCHAR(50),
            audio_channels INTEGER DEFAULT 0,
            audio_bitrate INTEGER DEFAULT 0,
            has_embedded_subtitle VARCHAR(20) DEFAULT 'unknown',
            embedded_subtitle_langs VARCHAR(100),
            scan_batch_id VARCHAR(36),
            scanned_at DATETIME,
            updated_at DATETIME
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX idx_media_files_file_path ON media_files(file_path)")
    cursor.execute("CREATE INDEX idx_media_files_sha256_hash ON media_files(sha256_hash)")
    cursor.execute("CREATE INDEX idx_media_files_media_type ON media_files(media_type)")
    cursor.execute("CREATE INDEX idx_media_files_modify_time ON media_files(modify_time)")
    cursor.execute("CREATE INDEX idx_media_files_scan_batch_id ON media_files(scan_batch_id)")

def create_subtitle_files_table(cursor):
    """创建字幕文件表"""
    print("创建表: subtitle_files")
    cursor.execute("""
        CREATE TABLE subtitle_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_file_id INTEGER NOT NULL,
            file_path VARCHAR(500) UNIQUE NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            file_extension VARCHAR(20),
            file_size INTEGER DEFAULT 0,
            language VARCHAR(10),
            language_name VARCHAR(50),
            is_default BOOLEAN DEFAULT 0,
            is_forced BOOLEAN DEFAULT 0,
            scanned_at DATETIME,
            FOREIGN KEY (media_file_id) REFERENCES media_files(id)
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX idx_subtitle_files_media_file_id ON subtitle_files(media_file_id)")
    cursor.execute("CREATE INDEX idx_subtitle_files_language ON subtitle_files(language)")

def create_recognition_results_table(cursor):
    """创建识别结果表"""
    print("创建表: recognition_results")
    cursor.execute("""
        CREATE TABLE recognition_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_file_id INTEGER NOT NULL,
            source VARCHAR(50) NOT NULL,
            source_id VARCHAR(50),
            media_type VARCHAR(20),
            title VARCHAR(255),
            original_title VARCHAR(255),
            year INTEGER,
            season_number INTEGER,
            episode_number INTEGER,
            episode_title VARCHAR(255),
            overview TEXT,
            poster_url VARCHAR(500),
            backdrop_url VARCHAR(500),
            genres VARCHAR(255),
            directors VARCHAR(500),
            actors VARCHAR(1000),
            rating REAL DEFAULT 0,
            confidence REAL DEFAULT 0,
            is_manual BOOLEAN DEFAULT 0,
            is_selected BOOLEAN DEFAULT 0,
            recognized_at DATETIME,
            FOREIGN KEY (media_file_id) REFERENCES media_files(id)
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX idx_recognition_results_media_file_id ON recognition_results(media_file_id)")
    cursor.execute("CREATE INDEX idx_recognition_results_source ON recognition_results(source)")
    cursor.execute("CREATE INDEX idx_recognition_results_is_selected ON recognition_results(is_selected)")

def create_organize_tasks_table(cursor):
    """创建整理任务表"""
    print("创建表: organize_tasks")
    cursor.execute("""
        CREATE TABLE organize_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_file_id INTEGER NOT NULL,
            source_path VARCHAR(500) NOT NULL,
            target_path VARCHAR(500),
            action_type VARCHAR(20) NOT NULL,
            task_status VARCHAR(20) DEFAULT 'pending',
            conflict_strategy VARCHAR(20) DEFAULT 'skip',
            error_message TEXT,
            started_at DATETIME,
            completed_at DATETIME,
            created_at DATETIME,
            FOREIGN KEY (media_file_id) REFERENCES media_files(id)
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX idx_organize_tasks_media_file_id ON organize_tasks(media_file_id)")
    cursor.execute("CREATE INDEX idx_organize_tasks_task_status ON organize_tasks(task_status)")

def create_scan_history_table(cursor):
    """创建扫描历史表"""
    print("创建表: scan_history")
    cursor.execute("""
        CREATE TABLE scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id VARCHAR(36) UNIQUE NOT NULL,
            target_path VARCHAR(500) NOT NULL,
            scan_type VARCHAR(20) NOT NULL,
            recursive BOOLEAN DEFAULT 1,
            total_files INTEGER DEFAULT 0,
            new_files INTEGER DEFAULT 0,
            updated_files INTEGER DEFAULT 0,
            skipped_files INTEGER DEFAULT 0,
            failed_files INTEGER DEFAULT 0,
            duration_seconds INTEGER DEFAULT 0,
            error_message TEXT,
            started_at DATETIME,
            completed_at DATETIME
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX idx_scan_history_batch_id ON scan_history(batch_id)")

def create_scan_paths_table(cursor):
    """创建扫描路径表"""
    print("创建表: scan_paths")
    cursor.execute("""
        CREATE TABLE scan_paths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path VARCHAR(500) UNIQUE NOT NULL,
            path_name VARCHAR(100),
            enabled BOOLEAN DEFAULT 1,
            scan_type VARCHAR(20) NOT NULL DEFAULT 'incremental',
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

    # 创建索引
    cursor.execute("CREATE INDEX idx_scan_paths_path ON scan_paths(path)")
    cursor.execute("CREATE INDEX idx_scan_paths_enabled ON scan_paths(enabled)")

def create_scan_progress_table(cursor):
    """创建扫描进度表"""
    print("创建表: scan_progress")
    cursor.execute("""
        CREATE TABLE scan_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id VARCHAR(36) UNIQUE NOT NULL,
            task_id INTEGER NOT NULL,
            target_path VARCHAR(500) NOT NULL,
            scan_type VARCHAR(20) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            total_files INTEGER DEFAULT 0,
            scanned_files INTEGER DEFAULT 0,
            new_files INTEGER DEFAULT 0,
            updated_files INTEGER DEFAULT 0,
            skipped_files INTEGER DEFAULT 0,
            failed_files INTEGER DEFAULT 0,
            current_file VARCHAR(500),
            started_at DATETIME,
            completed_at DATETIME,
            last_updated_at DATETIME
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX idx_scan_progress_batch_id ON scan_progress(batch_id)")
    cursor.execute("CREATE INDEX idx_scan_progress_task_id ON scan_progress(task_id)")

def create_keyword_libraries_table(cursor):
    """创建关键词库表"""
    print("创建表: keyword_libraries")
    cursor.execute("""
        CREATE TABLE keyword_libraries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            library_code VARCHAR(50) UNIQUE NOT NULL,
            library_name VARCHAR(100) NOT NULL,
            library_type VARCHAR(20) NOT NULL,
            description VARCHAR(255),
            priority INTEGER DEFAULT 0,
            is_enabled BOOLEAN DEFAULT 1,
            is_builtin BOOLEAN DEFAULT 0,
            created_at DATETIME,
            updated_at DATETIME
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX idx_keyword_libraries_library_type ON keyword_libraries(library_type)")
    cursor.execute("CREATE INDEX idx_keyword_libraries_is_enabled ON keyword_libraries(is_enabled)")

def create_keyword_rules_table(cursor):
    """创建关键词规则表"""
    print("创建表: keyword_rules")
    cursor.execute("""
        CREATE TABLE keyword_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            library_id INTEGER NOT NULL,
            rule_name VARCHAR(100) NOT NULL,
            rule_code VARCHAR(50),
            pattern VARCHAR(500) NOT NULL,
            replacement VARCHAR(500),
            description VARCHAR(255),
            priority INTEGER DEFAULT 0,
            is_regex BOOLEAN DEFAULT 1,
            is_case_sensitive BOOLEAN DEFAULT 0,
            match_mode VARCHAR(20) DEFAULT 'all',
            is_enabled BOOLEAN DEFAULT 1,
            hit_count INTEGER DEFAULT 0,
            created_at DATETIME,
            updated_at DATETIME,
            FOREIGN KEY (library_id) REFERENCES keyword_libraries(id)
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX idx_keyword_rules_library_id ON keyword_rules(library_id)")
    cursor.execute("CREATE INDEX idx_keyword_rules_priority ON keyword_rules(priority)")
    cursor.execute("CREATE INDEX idx_keyword_rules_is_enabled ON keyword_rules(is_enabled)")

def create_keyword_mappings_table(cursor):
    """创建关键词映射表"""
    print("创建表: keyword_mappings")
    cursor.execute("""
        CREATE TABLE keyword_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_pattern VARCHAR(500) UNIQUE NOT NULL,
            target_media_id VARCHAR(50) NOT NULL,
            target_source VARCHAR(50) DEFAULT 'tmdb',
            media_type VARCHAR(20),
            season_number INTEGER,
            episode_number INTEGER,
            title VARCHAR(255),
            description VARCHAR(255),
            is_regex BOOLEAN DEFAULT 0,
            is_enabled BOOLEAN DEFAULT 1,
            hit_count INTEGER DEFAULT 0,
            created_at DATETIME
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX idx_keyword_mappings_is_enabled ON keyword_mappings(is_enabled)")

def create_season_episode_rules_table(cursor):
    """创建季集提取规则表"""
    print("创建表: season_episode_rules")
    cursor.execute("""
        CREATE TABLE season_episode_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name VARCHAR(100) NOT NULL,
            pattern VARCHAR(500) NOT NULL,
            season_group INTEGER DEFAULT 1,
            episode_group INTEGER DEFAULT 2,
            description VARCHAR(255),
            priority INTEGER DEFAULT 0,
            is_enabled BOOLEAN DEFAULT 1,
            hit_count INTEGER DEFAULT 0,
            created_at DATETIME
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX idx_season_episode_rules_priority ON season_episode_rules(priority)")
    cursor.execute("CREATE INDEX idx_season_episode_rules_is_enabled ON season_episode_rules(is_enabled)")

def create_notification_logs_table(cursor):
    """创建通知日志表"""
    print("创建表: notification_logs")
    cursor.execute("""
        CREATE TABLE notification_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id VARCHAR(36) UNIQUE NOT NULL,
            channel VARCHAR(50) NOT NULL,
            level VARCHAR(20) NOT NULL,
            category VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            recipient VARCHAR(255),
            is_sent BOOLEAN DEFAULT 0,
            error_message TEXT,
            sent_at DATETIME,
            created_at DATETIME
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX idx_notification_logs_channel ON notification_logs(channel)")
    cursor.execute("CREATE INDEX idx_notification_logs_level ON notification_logs(level)")
    cursor.execute("CREATE INDEX idx_notification_logs_created_at ON notification_logs(created_at)")

def create_config_history_table(cursor):
    """创建配置历史表"""
    print("创建表: config_history")
    cursor.execute("""
        CREATE TABLE config_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key VARCHAR(100) NOT NULL,
            old_value TEXT,
            new_value TEXT,
            change_type VARCHAR(20) NOT NULL,
            changed_by VARCHAR(100),
            change_reason VARCHAR(255),
            created_at DATETIME,
            rolled_back BOOLEAN DEFAULT 0
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX idx_config_history_config_key ON config_history(config_key)")
    cursor.execute("CREATE INDEX idx_config_history_created_at ON config_history(created_at)")

def create_operation_logs_table(cursor):
    """创建操作日志表"""
    print("创建表: operation_logs")
    cursor.execute("""
        CREATE TABLE operation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id VARCHAR(36) UNIQUE NOT NULL,
            module_name VARCHAR(50) NOT NULL,
            operation_type VARCHAR(50) NOT NULL,
            operation_action VARCHAR(100),
            media_file_id INTEGER,
            task_id VARCHAR(36),
            source_path VARCHAR(500),
            target_path VARCHAR(500),
            operation_status VARCHAR(20) NOT NULL,
            log_level VARCHAR(10) DEFAULT 'info',
            input_data TEXT,
            output_data TEXT,
            error_message TEXT,
            error_code VARCHAR(50),
            execution_time_ms INTEGER DEFAULT 0,
            FOREIGN KEY (media_file_id) REFERENCES media_files(id)
        )
    """)

    # 创建索引
    cursor.execute("CREATE INDEX idx_operation_logs_module_name ON operation_logs(module_name)")
    cursor.execute("CREATE INDEX idx_operation_logs_operation_type ON operation_logs(operation_type)")
    cursor.execute("CREATE INDEX idx_operation_logs_media_file_id ON operation_logs(media_file_id)")
    cursor.execute("CREATE INDEX idx_operation_logs_task_id ON operation_logs(task_id)")
    cursor.execute("CREATE INDEX idx_operation_logs_operation_status ON operation_logs(operation_status)")
    cursor.execute("CREATE INDEX idx_operation_logs_log_level ON operation_logs(log_level)")

def reinit_database():
    """重新初始化数据库"""
    print(f"连接数据库: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 删除所有表
        drop_all_tables(cursor)

        # 创建所有表
        create_media_files_table(cursor)
        create_subtitle_files_table(cursor)
        create_recognition_results_table(cursor)
        create_organize_tasks_table(cursor)
        create_scan_history_table(cursor)
        create_scan_paths_table(cursor)
        create_scan_progress_table(cursor)
        create_keyword_libraries_table(cursor)
        create_keyword_rules_table(cursor)
        create_keyword_mappings_table(cursor)
        create_season_episode_rules_table(cursor)
        create_notification_logs_table(cursor)
        create_config_history_table(cursor)
        create_operation_logs_table(cursor)

        # 提交更改
        conn.commit()
        print("数据库重新初始化完成！")

    except Exception as e:
        print(f"错误: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    reinit_database()
