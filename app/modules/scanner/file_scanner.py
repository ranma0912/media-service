# -*- coding: utf-8 -*-
"""
文件扫描器 - 单文件批次扫描
每个文件一个独立的扫描任务
"""
import os
import hashlib
import threading
from pathlib import Path
from typing import List, Optional, Set, Dict, Any
from datetime import datetime
from loguru import logger
from pymediainfo import MediaInfo

from app.db.models import MediaFile, SubtitleFile, ScanHistory, ScanProgress, FileTask, KeywordRule
from app.db import get_db_context
from app.core.config import config_manager
from app.core.websocket import manager


# 支持的视频文件扩展名（根据需求文档）
VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.rmvb', '.ts', '.m2ts', '.mts',
    '.wmv', '.flv', '.webm', '.vob', '.ogv', '.ogg', '.mpg', '.mpeg',
    '.m4v', '.3gp', '.3g2', '.f4v', '.f4p'
}

# 支持的视频编码格式
VIDEO_CODECS = {
    'mpeg-1', 'mpeg-2', 'mpeg-4', 'mpeg4', 'h264', 'h.264', 'x264', 'avc',
    'h265', 'h.265', 'x265', 'hevc', 'av1', 'vc1', 'vc9', 'vp8', 'vp9'
}

# 支持的字幕文件扩展名
SUBTITLE_EXTENSIONS = {
    '.ass', '.srt', '.ssa', '.sub'
}


class FileScanner:
    """文件扫描器 - 单文件批次扫描"""

    def __init__(self):
        self._stopped = False
        self.ignore_keywords = self._load_ignore_keywords()
    
    def _load_ignore_keywords(self) -> Set[str]:
        """
        加载忽略关键词
        
        Returns:
            关键词集合
        """
        keywords = set()
        try:
            with get_db_context() as db:
                # 先查找关键词库
                from app.db.models import KeywordLibrary
                library = db.query(KeywordLibrary).filter_by(
                    library_code='scan_ignore',
                    is_enabled=True
                ).first()
                
                if library:
                    # 再查找该库下的规则
                    rules = db.query(KeywordRule).filter_by(
                        library_id=library.id,
                        is_enabled=True
                    ).all()
                    
                    for rule in rules:
                        keywords.add(rule.pattern)
                    
                    logger.debug(f"加载了 {len(keywords)} 个忽略关键词")
                else:
                    logger.warning("未找到scan_ignore关键词库")
                    
        except Exception as e:
            logger.error(f"加载忽略关键词失败: {e}")
        
        return keywords

    def is_video_file(self, path: Path) -> bool:
        """
        检查是否为视频文件（扩展名检查）
        
        Args:
            path: 文件路径
            
        Returns:
            是否为视频文件
        """
        return path.suffix.lower() in VIDEO_EXTENSIONS

    def is_subtitle_file(self, path: Path) -> bool:
        """
        检查是否为字幕文件
        
        Args:
            path: 文件路径
            
        Returns:
            是否为字幕文件
        """
        return path.suffix.lower() in SUBTITLE_EXTENSIONS

    def check_video_codec(self, path: Path) -> bool:
        """
        检查视频编码格式是否支持
        
        Args:
            path: 文件路径
            
        Returns:
            是否支持的视频编码格式
        """
        try:
            media_info = MediaInfo.parse(str(path))
            video_track = next((t for t in media_info.tracks if t.track_type == 'Video'), None)
            
            if not video_track or not video_track.codec_id:
                return False
            
            # 检查编码格式是否在支持列表中
            codec_id = video_track.codec_id.lower()
            
            # 直接匹配
            if codec_id in VIDEO_CODECS:
                return True
            
            # 模糊匹配
            for supported_codec in VIDEO_CODECS:
                if supported_codec.lower() in codec_id or codec_id in supported_codec.lower():
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"检查视频编码格式失败 {path}: {e}")
            return False

    def is_valid_video_file(self, path: Path) -> bool:
        """
        双重判定是否为有效的视频文件
        必须同时满足：扩展名匹配 + 编码格式匹配
        
        Args:
            path: 文件路径
            
        Returns:
            是否为有效的视频文件
        """
        # 检查扩展名
        if not self.is_video_file(path):
            logger.debug(f"文件扩展名不支持: {path.suffix}")
            return False
        
        # 检查编码格式
        if not self.check_video_codec(path):
            logger.debug(f"视频编码格式不支持: {path}")
            return False
        
        return True

    def should_ignore_file(self, file_name: str) -> bool:
        """
        检查文件是否应该被忽略（命中关键词库）
        
        Args:
            file_name: 文件名
            
        Returns:
            是否应该忽略
        """
        file_name_lower = file_name.lower()
        
        for keyword in self.ignore_keywords:
            if keyword.lower() in file_name_lower:
                logger.debug(f"文件命中忽略关键词: {file_name} -> {keyword}")
                return True
        
        return False

    def calculate_file_hash(self, path: Path, chunk_size: int = 8192) -> Optional[str]:
        """
        计算文件的SHA-256哈希值
        
        Args:
            path: 文件路径
            chunk_size: 每次读取的块大小（字节）
            
        Returns:
            文件的SHA-256哈希值，失败返回None
        """
        try:
            sha256_hash = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败 {path}: {e}")
            return None

    def extract_media_metadata(self, path: Path) -> Dict[str, Any]:
        """
        提取媒体文件元数据
        
        Args:
            path: 媒体文件路径
            
        Returns:
            包含元数据的字典
        """
        try:
            media_info = MediaInfo.parse(str(path))

            # 获取所有视频轨道
            video_tracks = [t for t in media_info.tracks if t.track_type == 'Video']
            # 获取所有音频轨道
            audio_tracks = [t for t in media_info.tracks if t.track_type == 'Audio']
            # 获取所有字幕轨道
            subtitle_tracks = [t for t in media_info.tracks if t.track_type == 'Text']

            # 使用第一个视频轨道
            video_track = video_tracks[0] if video_tracks else None
            # 使用第一个音频轨道
            audio_track = audio_tracks[0] if audio_tracks else None

            # 获取编码格式
            video_codec = None
            if video_track and video_track.codec_id:
                video_codec = video_track.codec_id.lower()
                # 标准化编码格式名称
                for codec in VIDEO_CODECS:
                    if codec.lower() in video_codec:
                        video_codec = codec.lower()
                        break

            metadata = {
                'file_size': path.stat().st_size,
                'duration': float(video_track.duration) / 1000 if video_track else 0,
                'width': int(video_track.width) if video_track else 0,
                'height': int(video_track.height) if video_track else 0,
                'video_codec': video_codec,
                'video_bitrate': int(video_track.bit_rate) if video_track else 0,
                'frame_rate': float(video_track.frame_rate) if video_track else 0,
                'audio_codec': audio_track.codec_id.lower() if audio_track else None,
                'audio_channels': int(audio_track.channel_s) if audio_track else 0,
                'audio_bitrate': int(audio_track.bit_rate) if audio_track else 0,
                
                # 轨道信息
                'video_tracks': len(video_tracks),
                'audio_tracks': len(audio_tracks),
                'subtitle_tracks': len(subtitle_tracks),
            }

            # 检测内嵌字幕
            if subtitle_tracks:
                metadata['has_embedded_subtitle'] = 'embedded'
                subtitle_langs = [t.language for t in subtitle_tracks if t.language]
                metadata['embedded_subtitle_langs'] = ','.join(subtitle_langs) if subtitle_langs else None
            else:
                metadata['has_embedded_subtitle'] = 'none'
                metadata['embedded_subtitle_langs'] = None

            return metadata

        except Exception as e:
            logger.error(f"提取媒体元数据失败 {path}: {e}")
            return {}

    def scan_file(
        self,
        file_path: Path,
        batch_id: str,
        scan_type: str = 'full',
        skip_strategy: str = 'keyword'
    ) -> Dict[str, Any]:
        """
        扫描单个文件
        
        Args:
            file_path: 文件路径
            batch_id: 批次ID
            scan_type: 扫描类型 (full/incremental/rescan/custom)
            skip_strategy: 跳过策略 (keyword/keyword_or_scanned/none)
            
        Returns:
            扫描结果字典
        """
        result = {
            'file_path': str(file_path),
            'file_name': file_path.name,
            'status': 'scanned',
            'error': None,
            'media_file_id': None
        }
        
        scan_start_time = datetime.now()
        file_task = None
        
        try:
            # 1. 双重判定文件类型
            if not self.is_valid_video_file(file_path):
                result['status'] = 'failed'
                result['error'] = '无效的视频文件（扩展名或编码格式不支持）'
                return result
            
            # 2. 检查是否命中关键词库
            if skip_strategy in ['keyword', 'keyword_or_scanned'] and self.should_ignore_file(file_path.name):
                result['status'] = 'skipped'
                result['error'] = '命中关键词库'
                return result
            
            # 3. 计算文件哈希
            file_hash = self.calculate_file_hash(file_path)
            if not file_hash:
                result['status'] = 'failed'
                result['error'] = '计算文件哈希失败'
                return result
            
            # 4. 检查是否已扫描（基于哈希值）
            with get_db_context() as db:
                existing_file = db.query(MediaFile).filter_by(sha256_hash=file_hash).first()
                
                # 跳过策略：keyword_or_scanned
                if skip_strategy == 'keyword_or_scanned' and existing_file and scan_type != 'rescan':
                    result['status'] = 'skipped'
                    result['error'] = '已扫描文件'
                    result['media_file_id'] = existing_file.id
                    return result
                
                # 增量扫描：检查文件是否更新
                if scan_type == 'incremental' and existing_file:
                    file_stat = file_path.stat()
                    if (existing_file.modify_time == datetime.fromtimestamp(file_stat.st_mtime) and
                        existing_file.file_size == file_stat.st_size):
                        result['status'] = 'skipped'
                        result['error'] = '文件未变化'
                        result['media_file_id'] = existing_file.id
                        return result
                
                # 5. 提取媒体元数据
                metadata = self.extract_media_metadata(file_path)
                if not metadata:
                    result['status'] = 'failed'
                    result['error'] = '提取媒体元数据失败'
                    return result
                
                # 6. 准备文件数据
                file_stat = file_path.stat()
                file_data = {
                    'file_path': str(file_path.absolute()),
                    'file_name': file_path.name,
                    'file_stem': file_path.stem,
                    'file_extension': file_path.suffix.lstrip('.').lower(),
                    'file_size': file_stat.st_size,
                    'sha256_hash': file_hash,
                    'media_type': 'video',
                    'create_time': datetime.fromtimestamp(file_stat.st_ctime),
                    'modify_time': datetime.fromtimestamp(file_stat.st_mtime),
                    'access_time': datetime.fromtimestamp(file_stat.st_atime),
                }
                file_data.update(metadata)
                
                # 7. 创建或更新媒体文件记录
                if existing_file:
                    # 更新现有记录
                    for key, value in file_data.items():
                        if hasattr(existing_file, key):
                            setattr(existing_file, key, value)
                    existing_file.updated_at = datetime.now()
                    media_file_id = existing_file.id
                else:
                    # 创建新记录
                    new_file = MediaFile(**file_data)
                    db.add(new_file)
                    db.flush()
                    media_file_id = new_file.id
                
                # 8. 创建文件任务记录
                file_task = FileTask(
                    batch_id=batch_id,
                    media_file_id=media_file_id,
                    target_path=str(file_path.parent),
                    file_name=file_path.name,
                    status='scanned',
                    scan_progress=100,
                    scan_started_at=scan_start_time,
                    scan_completed_at=datetime.now(),
                    video_tracks=metadata.get('video_tracks', 0),
                    audio_tracks=metadata.get('audio_tracks', 0),
                    subtitle_tracks=metadata.get('subtitle_tracks', 0),
                    video_codec=metadata.get('video_codec'),
                    audio_codec=metadata.get('audio_codec'),
                    scan_result='success'
                )
                db.add(file_task)
                db.commit()
                
                result['media_file_id'] = media_file_id
                
                # 9. 检查外挂字幕文件
                self._check_external_subtitles(file_path, media_file_id, db)
                
                logger.info(f"文件扫描成功: {file_path.name} (ID: {media_file_id})")
                
        except Exception as e:
            logger.error(f"扫描文件失败 {file_path}: {e}")
            result['status'] = 'failed'
            result['error'] = str(e)
            
            # 如果创建了文件任务，更新错误状态
            if file_task:
                try:
                    with get_db_context() as db:
                        task = db.query(FileTask).filter_by(id=file_task.id).first()
                        if task:
                            task.status = 'failed'
                            task.scan_error = str(e)
                            task.scan_result = 'failed'
                            db.commit()
                except:
                    pass
        
        return result

    def _check_external_subtitles(self, video_path: Path, media_file_id: int, db):
        """
        检查并记录外挂字幕文件
        
        Args:
            video_path: 视频文件路径
            media_file_id: 媒体文件ID
            db: 数据库会话
        """
        try:
            video_dir = video_path.parent
            video_stem = video_path.stem
            
            # 查找同名的字幕文件
            for ext in SUBTITLE_EXTENSIONS:
                subtitle_path = video_dir / f"{video_stem}{ext}"
                if subtitle_path.exists():
                    # 检查是否已存在
                    existing_subtitle = db.query(SubtitleFile).filter_by(
                        file_path=str(subtitle_path.absolute())
                    ).first()
                    
                    if not existing_subtitle:
                        file_stat = subtitle_path.stat()
                        subtitle_file = SubtitleFile(
                            media_file_id=media_file_id,
                            file_path=str(subtitle_path.absolute()),
                            file_name=subtitle_path.name,
                            file_extension=subtitle_path.suffix.lstrip('.').lower(),
                            file_size=file_stat.st_size,
                            language=self._detect_subtitle_language(subtitle_path),
                            scanned_at=datetime.now()
                        )
                        db.add(subtitle_file)
                        db.commit()
                        logger.debug(f"发现外挂字幕: {subtitle_path.name}")
                        
                        # 更新文件任务记录
                        file_task = db.query(FileTask).filter_by(
                            media_file_id=media_file_id,
                            batch_id=media_file_id  # 注意：这里batch_id应该从外部传入
                        ).order_by(FileTask.created_at.desc()).first()
                        
                        if file_task:
                            file_task.has_external_subtitle = True
                            file_task.external_subtitle_name = subtitle_path.name
                            db.commit()
        
        except Exception as e:
            logger.error(f"检查外挂字幕失败 {video_path}: {e}")

    def _detect_subtitle_language(self, path: Path) -> Optional[str]:
        """
        检测字幕文件语言
        
        Args:
            path: 字幕文件路径
            
        Returns:
            语言代码 (zh, en, ja等)
        """
        # 从文件名中提取语言标识
        parts = path.stem.split('.')
        if len(parts) > 1:
            lang_code = parts[-1].lower()
            if len(lang_code) == 2:
                return lang_code

        # 默认返回None
        return None

    def stop(self):
        """停止扫描"""
        self._stopped = True
        logger.info("文件扫描器已停止")


# 全局单例
_scanner = None
_scanner_lock = threading.Lock()


def get_file_scanner() -> FileScanner:
    """
    获取文件扫描器单例
    
    Returns:
        文件扫描器实例
    """
    global _scanner
    
    if _scanner is None:
        with _scanner_lock:
            if _scanner is None:
                _scanner = FileScanner()
    
    return _scanner