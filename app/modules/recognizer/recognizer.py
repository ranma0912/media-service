
"""
媒体识别器核心实现
"""
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger

from app.db.models import MediaFile, RecognitionResult, KeywordLibrary, KeywordRule, KeywordMapping, SeasonEpisodeRule
from app.db.session import get_db
from app.modules.fetcher import TMDBFetcher
from app.core.config import config_manager


class MediaRecognizer:
    """媒体识别器"""

    def __init__(self):
        self.tmdb_fetcher = None
        self.config = config_manager.config.recognition

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.tmdb_fetcher = TMDBFetcher()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.tmdb_fetcher:
            await self.tmdb_fetcher.close()

    async def recognize_media_file(
        self,
        media_file_id: int,
        force: bool = False
    ) -> List[RecognitionResult]:
        """
        识别媒体文件

        Args:
            media_file_id: 媒体文件ID
            force: 是否强制重新识别

        Returns:
            识别结果列表
        """
        with get_db() as db:
            media_file = db.query(MediaFile).filter_by(id=media_file_id).first()
            if not media_file:
                logger.error(f"媒体文件不存在: {media_file_id}")
                return []

            # 检查是否已有识别结果
            if not force:
                existing_results = db.query(RecognitionResult).filter_by(
                    media_file_id=media_file_id
                ).all()
                if existing_results:
                    logger.debug(f"文件已有识别结果: {media_file.file_name}")
                    return existing_results

            # 清理旧的识别结果
            if force:
                db.query(RecognitionResult).filter_by(
                    media_file_id=media_file_id
                ).delete()
                db.commit()

            # 解析文件名
            file_info = self._parse_filename(media_file.file_name)

            # 检查手动映射
            manual_mapping = self._check_manual_mapping(media_file.file_name)
            if manual_mapping:
                result = await self._recognize_by_mapping(manual_mapping, media_file_id)
                if result:
                    db.add(result)
                    db.commit()
                    return [result]

            # 从TMDB搜索
            results = await self._search_from_tmdb(file_info, media_file_id)

            # 保存识别结果
            for result in results:
                db.add(result)

            db.commit()

            logger.info(f"识别完成: {media_file.file_name}, 找到 {len(results)} 个结果")
            return results

    def _parse_filename(self, filename: str) -> Dict[str, Any]:
        """
        解析文件名提取信息

        Args:
            filename: 文件名

        Returns:
            解析后的信息字典
        """
        # 去除扩展名
        name = Path(filename).stem

        # 应用关键词规则处理
        name = self._apply_keyword_rules(name)

        # 提取季集信息
        season, episode = self._extract_season_episode(name)

        # 提取年份
        year = self._extract_year(name)

        # 提取质量信息
        quality = self._extract_quality(name)

        # 清理文件名（去除质量、年份等信息）
        clean_name = self._clean_filename(name)

        return {
            'original_name': name,
            'clean_name': clean_name,
            'year': year,
            'season': season,
            'episode': episode,
            'quality': quality
        }

    def _apply_keyword_rules(self, name: str) -> str:
        """
        应用关键词规则

        Args:
            name: 原始文件名

        Returns:
            处理后的文件名
        """
        processed_name = name

        with get_db() as db:
            # 获取所有启用的规则
            rules = db.query(KeywordRule).join(KeywordLibrary).filter(
                KeywordRule.is_enabled == True,
                KeywordLibrary.is_enabled == True
            ).order_by(KeywordLibrary.priority.desc(), KeywordRule.priority.desc()).all()

            for rule in rules:
                try:
                    if rule.is_regex:
                        if rule.is_case_sensitive:
                            processed_name = re.sub(
                                rule.pattern,
                                rule.replacement or '',
                                processed_name
                            )
                        else:
                            processed_name = re.sub(
                                rule.pattern,
                                rule.replacement or '',
                                processed_name,
                                flags=re.IGNORECASE
                            )
                    else:
                        # 普通字符串替换
                        if rule.is_case_sensitive:
                            processed_name = processed_name.replace(
                                rule.pattern,
                                rule.replacement or ''
                            )
                        else:
                            processed_name = processed_name.lower().replace(
                                rule.pattern.lower(),
                                (rule.replacement or '').lower()
                            )

                    # 更新命中次数
                    rule.hit_count += 1

                except Exception as e:
                    logger.warning(f"应用关键词规则失败: {rule.rule_name}, 错误: {e}")

            db.commit()

        return processed_name

    def _extract_season_episode(self, name: str) -> Tuple[Optional[int], Optional[int]]:
        """
        提取季集信息

        Args:
            name: 文件名

        Returns:
            (季数, 集数)
        """
        with get_db() as db:
            rules = db.query(SeasonEpisodeRule).filter(
                SeasonEpisodeRule.is_enabled == True
            ).order_by(SeasonEpisodeRule.priority.desc()).all()

            for rule in rules:
                try:
                    match = re.search(rule.pattern, name, re.IGNORECASE)
                    if match:
                        season = int(match.group(rule.season_group)) if rule.season_group <= len(match.groups()) else None
                        episode = int(match.group(rule.episode_group)) if rule.episode_group <= len(match.groups()) else None
                        return season, episode
                except Exception as e:
                    logger.warning(f"提取季集信息失败: {rule.rule_name}, 错误: {e}")

        return None, None

    def _extract_year(self, name: str) -> Optional[int]:
        """
        提取年份信息

        Args:
            name: 文件名

        Returns:
            年份
        """
        # 匹配4位数字年份 (1900-2099)
        match = re.search(r'(19\d{2}|20\d{2})', name)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= 2099:
                return year
        return None

    def _extract_quality(self, name: str) -> Optional[str]:
        """
        提取质量信息

        Args:
            name: 文件名

        Returns:
            质量标识 (1080p, 4K等)
        """
        # 常见质量标识
        quality_patterns = [
            r'4K',
            r'2160p',
            r'1080p',
            r'720p',
            r'480p'
        ]

        for pattern in quality_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                return match.group(0).upper()

        return None

    def _clean_filename(self, name: str) -> str:
        """
        清理文件名，去除特殊字符和质量标识

        Args:
            name: 原始文件名

        Returns:
            清理后的文件名
        """
        # 去除常见标识
        patterns = [
            r'\[.*?\]',  # 方括号内容
            r'\(.*?\)',  # 圆括号内容
            r'(4K|2160p|1080p|720p|480p|BluRay|WEB-DL|HDTV|DVDRip)',  # 质量和来源标识
            r'(x264|x265|H\.264|H\.265|HEVC)',  # 编码标识
            r'(AAC|AC3|DTS|DDP)',  # 音频标识
            r'\.+\.',  # 多个点
            r'[_\-\.]+',  # 多个分隔符
            r'\s+',  # 多个空格
        ]

        cleaned = name
        for pattern in patterns:
            cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)

        # 去除首尾空格和点
        cleaned = cleaned.strip('. ')

        return cleaned

    def _check_manual_mapping(self, filename: str) -> Optional[KeywordMapping]:
        """
        检查手动映射

        Args:
            filename: 文件名

        Returns:
            手动映射记录
        """
        with get_db() as db:
            # 精确匹配
            mapping = db.query(KeywordMapping).filter(
                KeywordMapping.source_pattern == filename,
                KeywordMapping.is_enabled == True
            ).first()

            if mapping:
                return mapping

            # 正则匹配
            mappings = db.query(KeywordMapping).filter(
                KeywordMapping.is_enabled == True,
                KeywordMapping.is_regex == True
            ).all()

            for mapping in mappings:
                try:
                    if re.search(mapping.source_pattern, filename, re.IGNORECASE):
                        return mapping
                except Exception:
                    continue

        return None

    async def _recognize_by_mapping(
        self,
        mapping: KeywordMapping,
        media_file_id: int
    ) -> Optional[RecognitionResult]:
        """
        通过手动映射识别

        Args:
            mapping: 手动映射记录
            media_file_id: 媒体文件ID

        Returns:
            识别结果
        """
        try:
            # 根据映射类型获取详细信息
            if mapping.target_source == 'tmdb':
                if mapping.media_type == 'movie':
                    details = await self.tmdb_fetcher.get_movie_details(
                        int(mapping.target_media_id)
                    )
                else:
                    details = await self.tmdb_fetcher.get_tv_details(
                        int(mapping.target_media_id)
                    )

                # 格式化结果
                result = self.tmdb_fetcher.format_recognition_result(
                    details,
                    mapping.media_type or 'movie',
                    confidence=1.0  # 手动映射置信度为1.0
                )

                # 更新季集信息
                if mapping.season_number:
                    result['season_number'] = mapping.season_number
                if mapping.episode_number:
                    result['episode_number'] = mapping.episode_number
                if mapping.title:
                    result['title'] = mapping.title

                # 创建识别结果对象
                recognition_result = RecognitionResult(
                    media_file_id=media_file_id,
                    **result
                )

                # 更新命中次数
                mapping.hit_count += 1

                return recognition_result

        except Exception as e:
            logger.error(f"手动映射识别失败: {e}")

        return None

    async def _search_from_tmdb(
        self,
        file_info: Dict[str, Any],
        media_file_id: int
    ) -> List[RecognitionResult]:
        """
        从TMDB搜索

        Args:
            file_info: 文件信息
            media_file_id: 媒体文件ID

        Returns:
            识别结果列表
        """
        results = []

        try:
            # 判断媒体类型
            media_type = 'tv' if file_info.get('season') else 'movie'

            # 搜索
            if media_type == 'movie':
                tmdb_results = await self.tmdb_fetcher.search_movie(
                    query=file_info['clean_name'],
                    year=file_info.get('year')
                )
            else:
                tmdb_results = await self.tmdb_fetcher.search_tv(
                    query=file_info['clean_name'],
                    year=file_info.get('year')
                )

            # 格式化结果
            for tmdb_data in tmdb_results[:5]:  # 最多返回5个结果
                # 根据季集信息获取详细信息
                if media_type == 'tv' and file_info.get('season'):
                    try:
                        # 获取季详情
                        season_details = await self.tmdb_fetcher.get_tv_season_details(
                            int(tmdb_data['id']),
                            file_info['season']
                        )

                        # 如果有集数，获取剧集详情
                        if file_info.get('episode'):
                            episode_data = next(
                                (ep for ep in season_details.get('episodes', [])
                                 if ep.get('episode_number') == file_info['episode']),
                                None
                            )
                            if episode_data:
                                tmdb_data['episode_title'] = episode_data.get('name')
                                tmdb_data['overview'] = episode_data.get('overview') or tmdb_data.get('overview')
                    except Exception as e:
                        logger.warning(f"获取季集详情失败: {e}")

                # 格式化识别结果
                result = self.tmdb_fetcher.format_recognition_result(
                    tmdb_data,
                    media_type,
                    confidence=self._calculate_confidence(tmdb_data, file_info)
                )

                # 更新季集信息
                if file_info.get('season'):
                    result['season_number'] = file_info['season']
                if file_info.get('episode'):
                    result['episode_number'] = file_info['episode']
                if tmdb_data.get('episode_title'):
                    result['episode_title'] = tmdb_data['episode_title']

                # 创建识别结果对象
                recognition_result = RecognitionResult(
                    media_file_id=media_file_id,
                    **result
                )
                results.append(recognition_result)

        except Exception as e:
            logger.error(f"TMDB搜索失败: {e}")

        return results

    def _calculate_confidence(
        self,
        tmdb_data: Dict[str, Any],
        file_info: Dict[str, Any]
    ) -> float:
        """
        计算识别置信度

        Args:
            tmdb_data: TMDB数据
            file_info: 文件信息

        Returns:
            置信度 (0-1)
        """
        confidence = 0.5  # 基础置信度

        # 年份匹配加分
        tmdb_year = int(tmdb_data.get('release_date', '')[:4]) if tmdb_data.get('release_date') else None
        if tmdb_year and file_info.get('year'):
            if tmdb_year == file_info['year']:
                confidence += 0.3
            elif abs(tmdb_year - file_info['year']) <= 1:
                confidence += 0.1

        # 标题相似度加分
        tmdb_title = tmdb_data.get('title') or tmdb_data.get('name', '').lower()
        file_title = file_info['clean_name'].lower()

        # 简单包含检查
        if tmdb_title in file_title or file_title in tmdb_title:
            confidence += 0.2

        # 确保置信度在0-1之间
        return min(max(confidence, 0.0), 1.0)
