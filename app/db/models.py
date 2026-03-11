"""
数据库模型定义
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Date, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db import Base


class MediaFile(Base):
    """媒体文件表"""
    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(String(500), unique=True, nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_stem = Column(String(255), nullable=True)
    file_extension = Column(String(20), nullable=True)
    file_size = Column(Integer, nullable=True, default=0)
    sha256_hash = Column(String(64), nullable=True, index=True)
    media_type = Column(String(20), nullable=True, index=True)
    create_time = Column(DateTime, nullable=True)
    modify_time = Column(DateTime, nullable=True, index=True)
    access_time = Column(DateTime, nullable=True)
    duration = Column(Float, nullable=True, default=0)
    width = Column(Integer, nullable=True, default=0)
    height = Column(Integer, nullable=True, default=0)
    video_codec = Column(String(50), nullable=True)
    video_bitrate = Column(Integer, nullable=True, default=0)
    frame_rate = Column(Float, nullable=True, default=0)
    audio_codec = Column(String(50), nullable=True)
    audio_channels = Column(Integer, nullable=True, default=0)
    audio_bitrate = Column(Integer, nullable=True, default=0)
    has_embedded_subtitle = Column(String(20), nullable=True, default="unknown")
    embedded_subtitle_langs = Column(String(100), nullable=True)
    scan_batch_id = Column(String(36), nullable=True, index=True)
    scanned_at = Column(DateTime, nullable=True, default=datetime.now)
    updated_at = Column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now)


class SubtitleFile(Base):
    """字幕文件表"""
    __tablename__ = "subtitle_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    media_file_id = Column(Integer, ForeignKey("media_files.id"), nullable=False, index=True)
    file_path = Column(String(500), unique=True, nullable=False)
    file_name = Column(String(255), nullable=False)
    file_extension = Column(String(20), nullable=True)
    file_size = Column(Integer, nullable=True, default=0)
    language = Column(String(10), nullable=True, index=True)
    language_name = Column(String(50), nullable=True)
    is_default = Column(Boolean, nullable=True, default=False)
    is_forced = Column(Boolean, nullable=True, default=False)
    scanned_at = Column(DateTime, nullable=True, default=datetime.now)


class RecognitionResult(Base):
    """识别结果表"""
    __tablename__ = "recognition_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    media_file_id = Column(Integer, ForeignKey("media_files.id"), nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)
    source_id = Column(String(50), nullable=True)
    media_type = Column(String(20), nullable=True)
    title = Column(String(255), nullable=True)
    original_title = Column(String(255), nullable=True)
    year = Column(Integer, nullable=True)
    season_number = Column(Integer, nullable=True)
    episode_number = Column(Integer, nullable=True)
    episode_title = Column(String(255), nullable=True)
    overview = Column(Text, nullable=True)
    poster_url = Column(String(500), nullable=True)
    backdrop_url = Column(String(500), nullable=True)
    genres = Column(String(255), nullable=True)
    directors = Column(String(500), nullable=True)
    actors = Column(String(1000), nullable=True)
    rating = Column(Float, nullable=True, default=0)
    confidence = Column(Float, nullable=True, default=0)
    is_manual = Column(Boolean, nullable=True, default=False)
    is_selected = Column(Boolean, nullable=True, default=False, index=True)
    recognized_at = Column(DateTime, nullable=True, default=datetime.now)


class OrganizeTask(Base):
    """整理任务表"""
    __tablename__ = "organize_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    media_file_id = Column(Integer, ForeignKey("media_files.id"), nullable=False, index=True)
    source_path = Column(String(500), nullable=False)
    target_path = Column(String(500), nullable=True)
    action_type = Column(String(20), nullable=False)
    task_status = Column(String(20), nullable=False, default="pending", index=True)
    conflict_strategy = Column(String(20), nullable=True, default="skip")
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True, default=datetime.now)


class ScanHistory(Base):
    """扫描历史表"""
    __tablename__ = "scan_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(36), unique=True, nullable=False, index=True)
    target_path = Column(String(500), nullable=False)
    scan_type = Column(String(20), nullable=False)
    recursive = Column(Boolean, nullable=True, default=True)
    total_files = Column(Integer, nullable=True, default=0)
    new_files = Column(Integer, nullable=True, default=0)
    updated_files = Column(Integer, nullable=True, default=0)
    skipped_files = Column(Integer, nullable=True, default=0)
    failed_files = Column(Integer, nullable=True, default=0)
    duration_seconds = Column(Integer, nullable=True, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class KeywordLibrary(Base):
    """关键词库表"""
    __tablename__ = "keyword_libraries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    library_code = Column(String(50), unique=True, nullable=False)
    library_name = Column(String(100), nullable=False)
    library_type = Column(String(20), nullable=False, index=True)
    description = Column(String(255), nullable=True)
    priority = Column(Integer, nullable=True, default=0)
    is_enabled = Column(Boolean, nullable=True, default=True, index=True)
    is_builtin = Column(Boolean, nullable=True, default=False)
    created_at = Column(DateTime, nullable=True, default=datetime.now)
    updated_at = Column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now)


class KeywordRule(Base):
    """关键词规则表"""
    __tablename__ = "keyword_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    library_id = Column(Integer, ForeignKey("keyword_libraries.id"), nullable=False, index=True)
    rule_name = Column(String(100), nullable=False)
    rule_code = Column(String(50), nullable=True)
    pattern = Column(String(500), nullable=False)
    replacement = Column(String(500), nullable=True)
    description = Column(String(255), nullable=True)
    priority = Column(Integer, nullable=True, default=0, index=True)
    is_regex = Column(Boolean, nullable=True, default=True)
    is_case_sensitive = Column(Boolean, nullable=True, default=False)
    match_mode = Column(String(20), nullable=True, default="all")
    is_enabled = Column(Boolean, nullable=True, default=True, index=True)
    hit_count = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, nullable=True, default=datetime.now)
    updated_at = Column(DateTime, nullable=True, default=datetime.now, onupdate=datetime.now)


class KeywordMapping(Base):
    """关键词映射表"""
    __tablename__ = "keyword_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_pattern = Column(String(500), unique=True, nullable=False)
    target_media_id = Column(String(50), nullable=False)
    target_source = Column(String(50), nullable=False, default="tmdb")
    media_type = Column(String(20), nullable=True)
    season_number = Column(Integer, nullable=True)
    episode_number = Column(Integer, nullable=True)
    title = Column(String(255), nullable=True)
    description = Column(String(255), nullable=True)
    is_regex = Column(Boolean, nullable=True, default=False)
    is_enabled = Column(Boolean, nullable=True, default=True, index=True)
    hit_count = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, nullable=True, default=datetime.now)


class SeasonEpisodeRule(Base):
    """季集提取规则表"""
    __tablename__ = "season_episode_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_name = Column(String(100), nullable=False)
    pattern = Column(String(500), nullable=False)
    season_group = Column(Integer, nullable=True, default=1)
    episode_group = Column(Integer, nullable=True, default=2)
    description = Column(String(255), nullable=True)
    priority = Column(Integer, nullable=True, default=0, index=True)
    is_enabled = Column(Boolean, nullable=True, default=True, index=True)
    hit_count = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, nullable=True, default=datetime.now)


class NotificationLog(Base):
    """通知日志表"""
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(36), unique=True, nullable=False)
    channel = Column(String(50), nullable=False, index=True)
    level = Column(String(20), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    recipient = Column(String(255), nullable=True)
    is_sent = Column(Boolean, nullable=True, default=False)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True, default=datetime.now, index=True)


class ConfigHistory(Base):
    """配置历史表"""
    __tablename__ = "config_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), nullable=False, index=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    change_type = Column(String(20), nullable=False)
    changed_by = Column(String(100), nullable=True)
    change_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=True, default=datetime.now, index=True)
    rolled_back = Column(Boolean, nullable=True, default=False)


class OperationLog(Base):
    """通用操作日志表"""
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(String(36), unique=True, nullable=False)
    module_name = Column(String(50), nullable=False, index=True)
    operation_type = Column(String(50), nullable=False, index=True)
    operation_action = Column(String(100), nullable=True)
    media_file_id = Column(Integer, ForeignKey("media_files.id"), nullable=True, index=True)
    task_id = Column(String(36), nullable=True, index=True)
    source_path = Column(String(500), nullable=True)
    target_path = Column(String(500), nullable=True)
    operation_status = Column(String(20), nullable=False, index=True)
    log_level = Column(String(10), nullable=False, default="info", index=True)
    input_data = Column(Text, nullable=True)
    output_data = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    execution_time_ms = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, nullable=True, default=datetime.now, index=True)
