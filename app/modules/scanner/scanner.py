
"""
本地文件扫描器核心实现
"""
import os
import hashlib
from pathlib import Path
from typing import List, Optional, Set, Dict, Any
from datetime import datetime
from loguru import logger
from pymediainfo import MediaInfo

from app.db.models import MediaFile, SubtitleFile, ScanHistory
from app.db.session import get_db
from app.core.config import config_manager


# 支持的媒体文件扩展名
MEDIA_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.rmvb', '.ts', '.m2ts', '.mts',
    '.wmv', '.flv', '.f4v', '.webm', '.vob', '.iso', '.divx', '.xvid',
    '.3gp', '.3g2', '.ogv'
}

# 支持的字幕文件扩展名
SUBTITLE_EXTENSIONS = {
    '.ass', '.srt', '.ssa', '.sub'
}


class FileScanner:
    """文件扫描器"""

    def __init__(self):
        self.scanned_files: Set[Path] = set()
        self.new_files: List[Dict[str, Any]] = []
        self.updated_files: List[Dict[str, Any]] = []
        self.skipped_files: int = 0
        self.failed_files: List[Dict[str, Any]] = []

    def is_media_file(self, path: Path) -> bool:
        """检查是否为媒体文件"""
        return path.suffix.lower() in MEDIA_EXTENSIONS

    def is_subtitle_file(self, path: Path) -> bool:
        """检查是否为字幕文件"""
        return path.suffix.lower() in SUBTITLE_EXTENSIONS

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

            # 获取视频轨道
            video_track = next((t for t in media_info.tracks if t.track_type == 'Video'), None)
            # 获取音频轨道
            audio_track = next((t for t in media_info.tracks if t.track_type == 'Audio'), None)
            # 获取字幕轨道
            subtitle_tracks = [t for t in media_info.tracks if t.track_type == 'Text']

            metadata = {
                'file_size': path.stat().st_size,
                'duration': float(video_track.duration) / 1000 if video_track else 0,
                'width': int(video_track.width) if video_track else 0,
                'height': int(video_track.height) if video_track else 0,
                'video_codec': video_track.codec_id if video_track else None,
                'video_bitrate': int(video_track.bit_rate) if video_track else 0,
                'frame_rate': float(video_track.frame_rate) if video_track else 0,
                'audio_codec': audio_track.codec_id if audio_track else None,
                'audio_channels': int(audio_track.channel_s) if audio_track else 0,
                'audio_bitrate': int(audio_track.bit_rate) if audio_track else 0,
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

    def scan_directory(
        self,
        path: str,
        recursive: bool = True,
        scan_type: str = 'full',
        batch_id: Optional[str] = None
    ) -> ScanHistory:
        """
        扫描指定目录

        Args:
            path: 要扫描的目录路径
            recursive: 是否递归扫描子目录
            scan_type: 扫描类型 (full/incremental)
            batch_id: 扫描批次ID

        Returns:
            扫描历史记录
        """
        start_time = datetime.now()
        scan_path = Path(path)

        if not scan_path.exists():
            logger.error(f"扫描路径不存在: {path}")
            raise FileNotFoundError(f"扫描路径不存在: {path}")

        if not scan_path.is_dir():
            logger.error(f"扫描路径不是目录: {path}")
            raise NotADirectoryError(f"扫描路径不是目录: {path}")

        # 生成批次ID
        if not batch_id:
            import uuid
            batch_id = str(uuid.uuid4())

        logger.info(f"开始扫描: {path} (类型: {scan_type}, 递归: {recursive}, 批次ID: {batch_id})")

        # 遍历目录
        if recursive:
            files = scan_path.rglob('*')
        else:
            files = scan_path.glob('*')

        # 扫描文件
        for file_path in files:
            if not file_path.is_file():
                continue

            # 处理媒体文件
            if self.is_media_file(file_path):
                self._process_media_file(file_path, scan_type)
            # 处理字幕文件
            elif self.is_subtitle_file(file_path):
                self._process_subtitle_file(file_path)

        # 保存扫描结果到数据库
        end_time = datetime.now()
        duration = int((end_time - start_time).total_seconds())

        scan_history = ScanHistory(
            batch_id=batch_id,
            target_path=str(scan_path),
            scan_type=scan_type,
            recursive=recursive,
            total_files=len(self.scanned_files),
            new_files=len(self.new_files),
            updated_files=len(self.updated_files),
            skipped_files=self.skipped_files,
            failed_files=len(self.failed_files),
            duration_seconds=duration,
            started_at=start_time,
            completed_at=end_time
        )

        # 保存到数据库
        with get_db() as db:
            db.add(scan_history)
            db.commit()

        logger.info(f"扫描完成: 总计 {len(self.scanned_files)} 个文件, "
                   f"新增 {len(self.new_files)} 个, "
                   f"更新 {len(self.updated_files)} 个, "
                   f"跳过 {self.skipped_files} 个, "
                   f"失败 {len(self.failed_files)} 个, "
                   f"耗时 {duration} 秒")

        return scan_history

    def _process_media_file(self, file_path: Path, scan_type: str):
        """
        处理媒体文件

        Args:
            file_path: 媒体文件路径
            scan_type: 扫描类型
        """
        try:
            self.scanned_files.add(file_path)

            # 提取文件基本信息
            file_stat = file_path.stat()
            file_data = {
                'file_path': str(file_path.absolute()),
                'file_name': file_path.name,
                'file_stem': file_path.stem,
                'file_extension': file_path.suffix.lstrip('.').lower(),
                'file_size': file_stat.st_size,
                'create_time': datetime.fromtimestamp(file_stat.st_ctime),
                'modify_time': datetime.fromtimestamp(file_stat.st_mtime),
                'access_time': datetime.fromtimestamp(file_stat.st_atime),
            }

            # 提取媒体元数据
            metadata = self.extract_media_metadata(file_path)
            file_data.update(metadata)

            # 检查文件是否已存在
            with get_db() as db:
                existing_file = db.query(MediaFile).filter_by(
                    file_path=file_data['file_path']
                ).first()

                if existing_file:
                    # 增量扫描：检查文件是否更新
                    if scan_type == 'incremental':
                        # 比较修改时间和文件大小
                        if (existing_file.modify_time == file_data['modify_time'] and
                            existing_file.file_size == file_data['file_size']):
                            self.skipped_files += 1
                            return

                    # 计算哈希值进行精确比对
                    file_hash = self.calculate_file_hash(file_path)
                    if file_hash:
                        file_data['sha256_hash'] = file_hash

                        if existing_file.sha256_hash == file_hash:
                            self.skipped_files += 1
                            return

                    # 文件已更新
                    for key, value in file_data.items():
                        setattr(existing_file, key, value)
                    existing_file.updated_at = datetime.now()
                    self.updated_files.append(file_data)
                    logger.debug(f"更新文件: {file_path.name}")
                else:
                    # 新文件
                    file_hash = self.calculate_file_hash(file_path)
                    if file_hash:
                        file_data['sha256_hash'] = file_hash

                    new_file = MediaFile(**file_data)
                    db.add(new_file)
                    self.new_files.append(file_data)
                    logger.debug(f"发现新文件: {file_path.name}")

                db.commit()

        except Exception as e:
            logger.error(f"处理媒体文件失败 {file_path}: {e}")
            self.failed_files.append({
                'file_path': str(file_path),
                'error': str(e)
            })

    def _process_subtitle_file(self, file_path: Path):
        """
        处理字幕文件

        Args:
            file_path: 字幕文件路径
        """
        try:
            # 查找关联的媒体文件
            media_file = None
            with get_db() as db:
                # 尝试通过文件名匹配
                media_file = db.query(MediaFile).filter(
                    MediaFile.file_path.like(f"{file_path.parent}%{file_path.stem}%")
                ).first()

                if not media_file:
                    return

                # 检查字幕文件是否已存在
                existing_subtitle = db.query(SubtitleFile).filter_by(
                    file_path=str(file_path.absolute())
                ).first()

                if existing_subtitle:
                    return

                # 创建字幕文件记录
                file_stat = file_path.stat()
                subtitle_file = SubtitleFile(
                    media_file_id=media_file.id,
                    file_path=str(file_path.absolute()),
                    file_name=file_path.name,
                    file_extension=file_path.suffix.lstrip('.').lower(),
                    file_size=file_stat.st_size,
                    language=self._detect_subtitle_language(file_path),
                    scanned_at=datetime.now()
                )

                db.add(subtitle_file)
                db.commit()
                logger.debug(f"发现字幕文件: {file_path.name}")

        except Exception as e:
            logger.error(f"处理字幕文件失败 {file_path}: {e}")

    def _detect_subtitle_language(self, file_path: Path) -> Optional[str]:
        """
        检测字幕文件语言

        Args:
            file_path: 字幕文件路径

        Returns:
            语言代码 (zh, en, ja等)
        """
        # 从文件名中提取语言标识
        # 例如: Movie.zh.srt -> zh
        parts = file_path.stem.split('.')
        if len(parts) > 1:
            lang_code = parts[-1].lower()
            if len(lang_code) == 2:
                return lang_code

        # 默认返回None
        return None
