
"""
媒体文件整理器核心实现
"""
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
from jinja2 import Template

from app.db.models import MediaFile, RecognitionResult, OrganizeTask, SubtitleFile
from app.db.session import get_db
from app.core.config import config_manager
from app.core.paths import paths


class MediaOrganizer:
    """媒体文件整理器"""

    def __init__(self):
        self.config = config_manager.config.organize
        self.naming_config = config_manager.config.naming_rules

    async def organize_media_file(
        self,
        media_file_id: int,
        recognition_result_id: Optional[int] = None
    ) -> OrganizeTask:
        """
        整理媒体文件

        Args:
            media_file_id: 媒体文件ID
            recognition_result_id: 识别结果ID（可选，默认使用选中的结果）

        Returns:
            整理任务
        """
        with get_db() as db:
            media_file = db.query(MediaFile).filter_by(id=media_file_id).first()
            if not media_file:
                logger.error(f"媒体文件不存在: {media_file_id}")
                raise ValueError(f"媒体文件不存在: {media_file_id}")

            # 获取识别结果
            if recognition_result_id:
                recognition = db.query(RecognitionResult).filter_by(
                    id=recognition_result_id
                ).first()
            else:
                recognition = db.query(RecognitionResult).filter(
                    RecognitionResult.media_file_id == media_file_id,
                    RecognitionResult.is_selected == True
                ).first()

            if not recognition:
                logger.error(f"未找到识别结果: {media_file_id}")
                raise ValueError(f"未找到识别结果: {media_file_id}")

            # 生成目标路径
            target_path = self._generate_target_path(media_file, recognition)

            # 创建整理任务
            task = OrganizeTask(
                media_file_id=media_file_id,
                source_path=media_file.file_path,
                target_path=target_path,
                action_type=self.config.action_type,
                conflict_strategy=self.config.conflict_strategy,
                task_status='pending'
            )

            db.add(task)
            db.commit()

            logger.info(f"创建整理任务: {media_file.file_name} -> {target_path}")
            return task

    async def execute_organize_task(
        self,
        task_id: int
    ) -> bool:
        """
        执行整理任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功
        """
        with get_db() as db:
            task = db.query(OrganizeTask).filter_by(id=task_id).first()
            if not task:
                logger.error(f"整理任务不存在: {task_id}")
                return False

            if task.task_status != 'pending':
                logger.warning(f"任务状态不是pending: {task.task_status}")
                return False

            # 更新任务状态
            task.task_status = 'running'
            task.started_at = datetime.now()
            db.commit()

            try:
                # 执行整理操作
                success = await self._execute_organize_action(task)

                if success:
                    task.task_status = 'completed'
                    task.completed_at = datetime.now()
                    logger.info(f"整理任务完成: {task.source_path}")
                else:
                    task.task_status = 'failed'
                    task.error_message = "整理操作失败"
                    logger.error(f"整理任务失败: {task.source_path}")

                db.commit()
                return success

            except Exception as e:
                task.task_status = 'failed'
                task.error_message = str(e)
                task.completed_at = datetime.now()
                db.commit()
                logger.error(f"执行整理任务异常: {e}")
                return False

    async def _execute_organize_action(self, task: OrganizeTask) -> bool:
        """
        执行具体的整理操作

        Args:
            task: 整理任务

        Returns:
            是否成功
        """
        source_path = Path(task.source_path)
        target_path = Path(task.target_path)

        # 检查源文件是否存在
        if not source_path.exists():
            logger.error(f"源文件不存在: {source_path}")
            return False

        # 创建目标目录
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 处理冲突
        if target_path.exists():
            if task.conflict_strategy == 'skip':
                logger.info(f"目标文件已存在，跳过: {target_path}")
                return True
            elif task.conflict_strategy == 'overwrite':
                target_path.unlink()
            elif task.conflict_strategy == 'rename_new':
                counter = 1
                while target_path.exists():
                    stem = target_path.stem
                    suffix = target_path.suffix
                    target_path = target_path.with_name(f"{stem}_{counter}{suffix}")
                    counter += 1
            elif task.conflict_strategy == 'backup':
                backup_path = target_path.with_suffix(f'.bak{datetime.now().strftime("%Y%m%d%H%M%S")}')
                shutil.move(str(target_path), str(backup_path))

        # 执行整理动作
        action_type = task.action_type.lower()

        if action_type in ['move', 'rename_and_move']:
            shutil.move(str(source_path), str(target_path))
            logger.info(f"移动文件: {source_path} -> {target_path}")

        elif action_type in ['copy', 'rename_and_copy']:
            shutil.copy2(str(source_path), str(target_path))
            logger.info(f"复制文件: {source_path} -> {target_path}")

        elif action_type in ['rename', 'rename_only']:
            source_path.rename(target_path)
            logger.info(f"重命名文件: {source_path} -> {target_path}")

        elif action_type in ['hardlink', 'rename_and_hardlink']:
            try:
                os.link(str(source_path), str(target_path))
                logger.info(f"创建硬链接: {source_path} -> {target_path}")
            except OSError as e:
                logger.error(f"创建硬链接失败: {e}")
                return False

        # 处理关联的字幕文件
        await self._organize_subtitles(source_path, target_path, action_type)

        return True

    async def _organize_subtitles(
        self,
        source_path: Path,
        target_path: Path,
        action_type: str
    ):
        """
        整理关联的字幕文件

        Args:
            source_path: 源媒体文件路径
            target_path: 目标媒体文件路径
            action_type: 整理动作类型
        """
        with get_db() as db:
            media_file = db.query(MediaFile).filter_by(
                file_path=str(source_path)
            ).first()

            if not media_file:
                return

            # 获取关联的字幕文件
            subtitles = db.query(SubtitleFile).filter_by(
                media_file_id=media_file.id
            ).all()

            for subtitle in subtitles:
                subtitle_path = Path(subtitle.file_path)

                if not subtitle_path.exists():
                    continue

                # 生成目标字幕路径
                subtitle_target = target_path.with_suffix(f'.{subtitle.language}{target_path.suffix}')

                # 创建目标目录
                subtitle_target.parent.mkdir(parents=True, exist_ok=True)

                # 执行整理动作
                if action_type in ['move', 'rename_and_move']:
                    shutil.move(str(subtitle_path), str(subtitle_target))
                elif action_type in ['copy', 'rename_and_copy']:
                    shutil.copy2(str(subtitle_path), str(subtitle_target))
                elif action_type in ['hardlink', 'rename_and_hardlink']:
                    try:
                        os.link(str(subtitle_path), str(subtitle_target))
                    except OSError as e:
                        logger.warning(f"创建字幕硬链接失败: {e}")

                # 更新字幕文件路径
                subtitle.file_path = str(subtitle_target)

            db.commit()

    def _generate_target_path(
        self,
        media_file: MediaFile,
        recognition: RecognitionResult
    ) -> str:
        """
        生成目标路径

        Args:
            media_file: 媒体文件
            recognition: 识别结果

        Returns:
            目标路径
        """
        # 准备模板变量
        template_vars = {
            'title': recognition.title or 'Unknown',
            'original_title': recognition.original_title or '',
            'year': recognition.year or '',
            'season': recognition.season_number or '',
            'episode': recognition.episode_number or '',
            'episode_title': recognition.episode_title or '',
            'quality': self._extract_quality_from_file(media_file.file_name),
            'source': self._extract_source_from_file(media_file.file_name),
            'codec': media_file.video_codec or '',
            'audio': media_file.audio_codec or '',
            'release_group': self._extract_release_group(media_file.file_name),
            'language': self._extract_language(media_file),
            'audio_language': self._extract_audio_language(media_file),
            'subtitle_language': self._extract_subtitle_language(media_file),
            'country': '',
            'region': '',
            'resolution': f"{media_file.width}x{media_file.height}" if media_file.width and media_file.height else '',
            'bitdepth': '',
            'hdr': '',
            'primary_category': recognition.media_type or 'undefined',
            'sub_category': 'pending',
            'genre': recognition.genres or '',
            'file_name': media_file.file_name,
            'file_stem': media_file.file_stem or '',
            'file_extension': media_file.file_extension or '',
            'content_rating': '',
            'studio': ''
        }

        # 选择命名规则模板
        media_type = recognition.media_type or 'undefined'
        if media_type == 'tv':
            naming_template = self.naming_config.tv.default
        elif media_type == 'anime':
            naming_template = self.naming_config.anime.default
        else:
            naming_template = self.naming_config.movie.default

        # 渲染文件名
        try:
            template = Template(naming_template)
            file_name = template.render(**template_vars)
        except Exception as e:
            logger.warning(f"渲染命名模板失败: {e}")
            file_name = template_vars['title']

        # 添加文件扩展名
        file_name = f"{file_name}.{media_file.file_extension}" if media_file.file_extension else file_name

        # 选择目录规则
        directory_template = self.naming_config.directory_rules.get(media_type, f'/media/{media_type}')

        # 渲染目录路径
        try:
            dir_template = Template(directory_template)
            directory = dir_template.render(**template_vars)
        except Exception as e:
            logger.warning(f"渲染目录模板失败: {e}")
            directory = f'/media/{media_type}'

        # 组合完整路径
        target_path = str(paths.get_path(directory) / file_name)

        return target_path

    def _extract_quality_from_file(self, filename: str) -> str:
        """从文件名提取质量信息"""
        quality_patterns = [
            r'4K',
            r'2160p',
            r'1080p',
            r'720p',
            r'480p'
        ]

        for pattern in quality_patterns:
            import re
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return match.group(0).upper()

        return ''

    def _extract_source_from_file(self, filename: str) -> str:
        """从文件名提取来源信息"""
        source_patterns = [
            r'BluRay',
            r'WEB-DL',
            r'HDTV',
            r'DVDRip'
        ]

        for pattern in source_patterns:
            import re
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                return match.group(0).upper()

        return ''

    def _extract_release_group(self, filename: str) -> str:
        """从文件名提取发布组"""
        import re
        match = re.search(r'\[(.*?)\]', filename)
        if match:
            return match.group(1)
        return ''

    def _extract_language(self, media_file: MediaFile) -> str:
        """提取媒体文件语言"""
        if media_file.embedded_subtitle_langs:
            langs = media_file.embedded_subtitle_langs.split(',')
            return langs[0] if langs else ''
        return ''

    def _extract_audio_language(self, media_file: MediaFile) -> str:
        """提取音频语言"""
        # 这里可以根据实际情况从元数据中提取
        return 'zh'  # 默认返回中文

    def _extract_subtitle_language(self, media_file: MediaFile) -> str:
        """提取字幕语言"""
        if media_file.embedded_subtitle_langs:
            langs = media_file.embedded_subtitle_langs.split(',')
            return langs[0] if langs else ''
        return ''

    def preview_organize(
        self,
        media_file_id: int,
        recognition_result_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        预览整理结果

        Args:
            media_file_id: 媒体文件ID
            recognition_result_id: 识别结果ID（可选）

        Returns:
            预览信息
        """
        with get_db() as db:
            media_file = db.query(MediaFile).filter_by(id=media_file_id).first()
            if not media_file:
                raise ValueError(f"媒体文件不存在: {media_file_id}")

            # 获取识别结果
            if recognition_result_id:
                recognition = db.query(RecognitionResult).filter_by(
                    id=recognition_result_id
                ).first()
            else:
                recognition = db.query(RecognitionResult).filter(
                    RecognitionResult.media_file_id == media_file_id,
                    RecognitionResult.is_selected == True
                ).first()

            if not recognition:
                raise ValueError(f"未找到识别结果: {media_file_id}")

            # 生成目标路径
            target_path = self._generate_target_path(media_file, recognition)

            return {
                'source_path': media_file.file_path,
                'target_path': target_path,
                'action_type': self.config.action_type,
                'conflict_strategy': self.config.conflict_strategy,
                'file_size': media_file.file_size,
                'recognition': {
                    'title': recognition.title,
                    'year': recognition.year,
                    'season': recognition.season_number,
                    'episode': recognition.episode_number
                }
            }
