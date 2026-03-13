
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

from app.db.models import MediaFile, SubtitleFile, ScanHistory, ScanProgress
from app.db import get_db_context
from app.core.config import config_manager
from app.core.websocket import manager


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

    def __init__(self, task_id: int = None, batch_id: str = None, ignore_patterns: List[str] = None, skip_mode: str = "keyword"):
        self.task_id = task_id
        self.batch_id = batch_id
        self.scanned_files: Set[Path] = set()
        self.new_files: List[Dict[str, Any]] = []
        self.updated_files: List[Dict[str, Any]] = []
        self.skipped_files: int = 0
        self.failed_files: List[Dict[str, Any]] = []
        self.total_files: int = 0
        self.last_progress_update: datetime = None
        self.ignore_patterns = ignore_patterns or []
        self.skip_mode = skip_mode  # keyword: 仅跳过关键词库, record: 跳过关键词库和已扫描, none: 不跳过任何文件
        self._stopped = False  # 停止标志

    def is_media_file(self, path: Path) -> bool:
        """检查是否为媒体文件"""
        return path.suffix.lower() in MEDIA_EXTENSIONS

    def is_subtitle_file(self, path: Path) -> bool:
        """检查是否为字幕文件"""
        return path.suffix.lower() in SUBTITLE_EXTENSIONS

    def _check_stop_status(self) -> bool:
        """
        检查任务是否被请求停止

        Returns:
            是否应该停止扫描
        """
        if self._stopped:
            return True
            
        if not self.task_id:
            return False
            
        try:
            with get_db_context() as db:
                task = db.query(ScanHistory).filter_by(id=self.task_id).first()
                if task:
                    # 检查任务状态
                    if hasattr(task, "status") and task.status == "stopping":
                        self._stopped = True
                        logger.info(f"检测到停止请求: task_id={self.task_id}")
                        return True
                    # 检查任务是否已完成
                    if task.completed_at:
                        self._stopped = True
                        logger.info(f"检测到任务已完成: task_id={self.task_id}")
                        return True
        except Exception as e:
            logger.error(f"检查停止状态失败: {e}")
            
        return False

    def should_ignore_file(self, path: Path) -> bool:
        """
        检查文件是否应该被忽略

        Args:
            path: 文件路径

        Returns:
            是否应该忽略该文件
        """
        # 检查用户配置的忽略模式
        if self.ignore_patterns:
            import fnmatch
            file_name = path.name

            # 检查每个忽略模式
            for pattern in self.ignore_patterns:
                if fnmatch.fnmatch(file_name, pattern):
                    logger.debug(f"文件匹配用户忽略模式: {file_name} -> {pattern}")
                    return True

        # 检查是否为关键词库文件（跳过词库文件）
        if self._is_keyword_library_file(path):
            logger.debug(f"跳过关键词库文件: {path.name}")
            return True

        return False

    def _is_keyword_library_file(self, path: Path) -> bool:
        """
        检查是否为关键词库文件

        Args:
            path: 文件路径

        Returns:
            是否为关键词库文件
        """
        # 关键词库文件特征
        keyword_library_patterns = [
            'keywords',
            'keyword_',
            'key_',
            'library',
            'lib_',
            'rules',
            'rule_',
            'mapping',
            'map_',
            'season',
            'episode',
            'naming',
            'name_'
        ]

        file_name_lower = path.stem.lower()

        # 检查文件名是否包含关键词库特征
        for pattern in keyword_library_patterns:
            if pattern in file_name_lower:
                return True

        return False

    async def _update_progress(self, current_file: str = None, force: bool = False):
        """
        更新扫描进度

        Args:
            current_file: 当前正在处理的文件
            force: 是否强制更新（忽略时间限制）
        """
        import asyncio
        from datetime import timedelta


        now = datetime.now()
        
        # 检查是否需要更新（每分钟更新一次，或强制更新）
        if not force and self.last_progress_update:
            if now - self.last_progress_update < timedelta(minutes=1):
                return
        
        self.last_progress_update = now
        
        # 准备进度数据
        progress = {
            "batch_id": self.batch_id,
            "task_id": self.task_id,
            "status": "running",
            "total_files": self.total_files,
            "scanned_files": len(self.scanned_files),
            "new_files": len(self.new_files),
            "updated_files": len(self.updated_files),
            "skipped_files": self.skipped_files,
            "failed_files": len(self.failed_files),
            "current_file": current_file,
            "progress": len(self.scanned_files) / self.total_files * 100 if self.total_files > 0 else 0
        }
        
        # 更新数据库
        try:
            with get_db_context() as db:
                db_progress = db.query(ScanProgress).filter_by(batch_id=self.batch_id).first()
                if db_progress:
                    for key, value in progress.items():
                        if hasattr(db_progress, key):
                            setattr(db_progress, key, value)
                    db_progress.last_updated_at = now
                else:
                    db_progress = ScanProgress(**progress)
                    db.add(db_progress)
                db.commit()
        except Exception as e:
            logger.error(f"更新扫描进度失败: {e}")
        
        # 通过WebSocket推送进度
        try:
            await manager.send_progress(self.task_id, progress)
        except Exception as e:
            logger.error(f"发送进度WebSocket消息失败: {e}")

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

    async def scan_directory(
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
        import asyncio
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
        
        self.batch_id = batch_id

        logger.info(f"开始扫描: {path} (类型: {scan_type}, 递归: {recursive}, 批次ID: {batch_id})")

        # 遍历目录，先统计总文件数
        if recursive:
            files = list(scan_path.rglob('*'))
        else:
            files = list(scan_path.glob('*'))
        
        self.total_files = len([f for f in files if f.is_file() and (self.is_media_file(f) or self.is_subtitle_file(f))])
        
        # 初始化进度
        await self._update_progress(force=True)
        
        # 扫描文件
        for file_path in files:
            # 检查停止状态
            if self._check_stop_status():
                logger.info(f"扫描被停止，退出扫描循环: task_id={self.task_id}")
                break
                
            if not file_path.is_file():
                continue

            # 检查是否应该忽略该文件
            if self.should_ignore_file(file_path):
                self.skipped_files += 1
                logger.debug(f"跳过忽略文件: {file_path.name}")
                continue

            # 更新当前文件
            await self._update_progress(current_file=str(file_path))

            # 再次检查停止状态（在处理文件前）
            if self._check_stop_status():
                logger.info(f"扫描被停止，跳过当前文件: {file_path.name}")
                break

            # 处理媒体文件
            if self.is_media_file(file_path):
                self._process_media_file(file_path, scan_type)
            # 处理字幕文件
            elif self.is_subtitle_file(file_path):
                self._process_subtitle_file(file_path)

        # 保存扫描结果到数据库
        end_time = datetime.now()
        duration = int((end_time - start_time).total_seconds())

        # 确定最终状态
        final_status = "stopped" if self._stopped else "completed"
        error_message = "任务被用户停止" if self._stopped else None

        # 更新最终进度
        final_progress = {
            "batch_id": self.batch_id,
            "task_id": self.task_id,
            "status": final_status,
            "total_files": self.total_files,
            "scanned_files": len(self.scanned_files),
            "new_files": len(self.new_files),
            "updated_files": len(self.updated_files),
            "skipped_files": self.skipped_files,
            "failed_files": len(self.failed_files),
            "current_file": None,
            "progress": len(self.scanned_files) / self.total_files * 100 if self.total_files > 0 else 0
        }
        
        # 更新进度数据库
        try:
            with get_db_context() as db:
                db_progress = db.query(ScanProgress).filter_by(batch_id=self.batch_id).first()
                if db_progress:
                    for key, value in final_progress.items():
                        if hasattr(db_progress, key):
                            setattr(db_progress, key, value)
                    db_progress.completed_at = end_time
                    db_progress.last_updated_at = end_time
                else:
                    final_progress["started_at"] = start_time
                    final_progress["completed_at"] = end_time
                    db_progress = ScanProgress(**final_progress)
                    db.add(db_progress)
                db.commit()
        except Exception as e:
            logger.error(f"更新最终扫描进度失败: {e}")
        
        # 通过WebSocket推送最终进度
        try:
            await manager.send_progress(self.task_id, final_progress)
        except Exception as e:
            logger.error(f"发送最终进度WebSocket消息失败: {e}")

        # 更新或创建扫描历史记录
        with get_db_context() as db:
            if self.task_id:
                # 更新已存在的记录
                scan_history = db.query(ScanHistory).filter_by(id=self.task_id).first()
                if scan_history:
                    scan_history.total_files = self.total_files
                    scan_history.new_files = len(self.new_files)
                    scan_history.updated_files = len(self.updated_files)
                    scan_history.skipped_files = self.skipped_files
                    scan_history.failed_files = len(self.failed_files)
                    scan_history.duration_seconds = duration
                    scan_history.completed_at = end_time
                    db.commit()
                else:
                    # 如果找不到记录，创建新记录
                    scan_history = ScanHistory(
                        batch_id=self.batch_id,
                        target_path=str(scan_path),
                        scan_type=scan_type,
                        recursive=recursive,
                        total_files=self.total_files,
                        new_files=len(self.new_files),
                        updated_files=len(self.updated_files),
                        skipped_files=self.skipped_files,
                        failed_files=len(self.failed_files),
                        duration_seconds=duration,
                        started_at=start_time,
                        completed_at=end_time
                    )
                    db.add(scan_history)
                    db.commit()
            else:
                # 没有 task_id，创建新记录
                scan_history = ScanHistory(
                    batch_id=self.batch_id,
                    target_path=str(scan_path),
                    scan_type=scan_type,
                    recursive=recursive,
                    total_files=self.total_files,
                    new_files=len(self.new_files),
                    updated_files=len(self.updated_files),
                    skipped_files=self.skipped_files,
                    failed_files=len(self.failed_files),
                    duration_seconds=duration,
                    started_at=start_time,
                    completed_at=end_time
                )
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
            scan_type: 扫描类型 (full/incremental/rescan/custom)
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
            with get_db_context() as db:
                existing_file = db.query(MediaFile).filter_by(
                    file_path=file_data['file_path']
                ).first()

                # skip_mode为"record"时，跳过已扫描的文件
                if self.skip_mode == 'record' and existing_file and scan_type != 'rescan':
                    self.skipped_files += 1
                    logger.debug(f"跳过已扫描文件（record模式）: {file_path.name}")
                    return

                if existing_file:
                    # 重新扫描：强制更新文件，不进行任何跳过检查
                    if scan_type == 'rescan':
                        # 强制更新文件元数据
                        for key, value in file_data.items():
                            if hasattr(existing_file, key):
                                setattr(existing_file, key, value)
                        existing_file.updated_at = datetime.now()
                        self.updated_files.append(file_data)
                        logger.debug(f"重新扫描文件: {file_path.name}")
                        db.commit()
                        return

                    # 增量扫描：检查文件是否更新
                    if scan_type == 'incremental':
                        # 比较修改时间和文件大小
                        if (existing_file.modify_time == file_data['modify_time'] and
                            existing_file.file_size == file_data['file_size']):
                            self.skipped_files += 1
                            logger.debug(f"文件未变化，跳过: {file_path.name}")
                            return

                    # 全量扫描或自定义路径扫描：强制更新数据库
                    if scan_type == 'full' or scan_type == 'custom':
                        # 强制更新文件元数据和扫描时间
                        for key, value in file_data.items():
                            if hasattr(existing_file, key):
                                setattr(existing_file, key, value)
                        existing_file.updated_at = datetime.now()
                        existing_file.scanned_at = datetime.now()  # 更新扫描时间
                        self.updated_files.append(file_data)
                        logger.debug(f"强制更新文件: {file_path.name} (扫描类型: {scan_type})")
                        db.commit()
                        return

                    # 其他情况：计算哈希值进行精确比对
                    file_hash = self.calculate_file_hash(file_path)
                    if file_hash:
                        file_data['sha256_hash'] = file_hash

                        if existing_file.sha256_hash == file_hash:
                            self.skipped_files += 1
                            logger.debug(f"文件哈希未变化，跳过: {file_path.name}")
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
            with get_db_context() as db:
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
