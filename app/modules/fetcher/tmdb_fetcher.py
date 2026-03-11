
"""
TMDB媒体信息获取器
"""
import httpx
from typing import List, Dict, Any, Optional
from loguru import logger
from cachetools import TTLCache

from app.core.config import config_manager


class TMDBFetcher:
    """TMDB数据获取器"""

    def __init__(self):
        self.config = config_manager.config.recognition.sources.tmdb
        self.api_key = self.config.api_key
        self.base_url = "https://api.themoviedb.org/3"
        self.language = self.config.language

        # 缓存配置
        if self.config.cache_enabled:
            self.cache = TTLCache(maxsize=1000, ttl=self.config.cache_ttl)
        else:
            self.cache = None

        # HTTP客户端
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                'Accept': 'application/json',
                'User-Agent': 'MediaService/1.6.0'
            }
        )

    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()

    def _get_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """生成缓存键"""
        import hashlib
        param_str = '&'.join(f"{k}={v}" for k, v in sorted(params.items()))
        cache_str = f"{endpoint}:{param_str}"
        return hashlib.md5(cache_str.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """从缓存获取数据"""
        if self.cache:
            return self.cache.get(cache_key)
        return None

    def _set_cache(self, cache_key: str, data: Dict[str, Any]):
        """设置缓存"""
        if self.cache:
            self.cache[cache_key] = data

    async def _request(
        self,
        endpoint: str,
        params: Dict[str, Any],
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        发送HTTP请求

        Args:
            endpoint: API端点
            params: 请求参数
            use_cache: 是否使用缓存

        Returns:
            API响应数据
        """
        # 检查缓存
        if use_cache:
            cache_key = self._get_cache_key(endpoint, params)
            cached_data = self._get_from_cache(cache_key)
            if cached_data:
                logger.debug(f"从缓存获取数据: {endpoint}")
                return cached_data

        # 添加API密钥
        params['api_key'] = self.api_key

        try:
            response = await self.client.get(
                f"{self.base_url}/{endpoint}",
                params=params
            )
            response.raise_for_status()
            data = response.json()

            # 设置缓存
            if use_cache:
                self._set_cache(cache_key, data)

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"TMDB API请求失败: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"TMDB API请求错误: {e}")
            raise

    async def search_movie(
        self,
        query: str,
        year: Optional[int] = None,
        language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索电影

        Args:
            query: 搜索关键词
            year: 发行年份（可选）
            language: 语言代码（可选，默认使用配置）

        Returns:
            电影列表
        """
        params = {
            'query': query,
            'language': language or self.language
        }

        if year:
            params['year'] = year

        data = await self._request('search/movie', params)
        return data.get('results', [])

    async def search_tv(
        self,
        query: str,
        year: Optional[int] = None,
        language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索电视剧

        Args:
            query: 搜索关键词
            year: 首播年份（可选）
            language: 语言代码（可选，默认使用配置）

        Returns:
            电视剧列表
        """
        params = {
            'query': query,
            'language': language or self.language
        }

        if year:
            params['first_air_date_year'] = year

        data = await self._request('search/tv', params)
        return data.get('results', [])

    async def get_movie_details(
        self,
        movie_id: int,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取电影详情

        Args:
            movie_id: TMDB电影ID
            language: 语言代码（可选，默认使用配置）

        Returns:
            电影详情
        """
        params = {
            'language': language or self.language
        }

        return await self._request(f'movie/{movie_id}', params)

    async def get_tv_details(
        self,
        tv_id: int,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取电视剧详情

        Args:
            tv_id: TMDB电视剧ID
            language: 语言代码（可选，默认使用配置）

        Returns:
            电视剧详情
        """
        params = {
            'language': language or self.language
        }

        return await self._request(f'tv/{tv_id}', params)

    async def get_tv_season_details(
        self,
        tv_id: int,
        season_number: int,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取电视剧季详情

        Args:
            tv_id: TMDB电视剧ID
            season_number: 季数
            language: 语言代码（可选，默认使用配置）

        Returns:
            季详情
        """
        params = {
            'language': language or self.language
        }

        return await self._request(f'tv/{tv_id}/season/{season_number}', params)

    async def get_tv_episode_details(
        self,
        tv_id: int,
        season_number: int,
        episode_number: int,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取电视剧剧集详情

        Args:
            tv_id: TMDB电视剧ID
            season_number: 季数
            episode_number: 集数
            language: 语言代码（可选，默认使用配置）

        Returns:
            剧集详情
        """
        params = {
            'language': language or self.language
        }

        return await self._request(
            f'tv/{tv_id}/season/{season_number}/episode/{episode_number}',
            params
        )

    async def get_movie_images(
        self,
        movie_id: int,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取电影图片

        Args:
            movie_id: TMDB电影ID
            language: 语言代码（可选，默认使用配置）

        Returns:
            图片数据
        """
        params = {
            'language': language or self.language,
            'include_image_language': language or self.language
        }

        return await self._request(f'movie/{movie_id}/images', params)

    async def get_tv_images(
        self,
        tv_id: int,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取电视剧图片

        Args:
            tv_id: TMDB电视剧ID
            language: 语言代码（可选，默认使用配置）

        Returns:
            图片数据
        """
        params = {
            'language': language or self.language,
            'include_image_language': language or self.language
        }

        return await self._request(f'tv/{tv_id}/images', params)

    def format_recognition_result(
        self,
        tmdb_data: Dict[str, Any],
        media_type: str,
        confidence: float = 0.8
    ) -> Dict[str, Any]:
        """
        格式化TMDB数据为识别结果

        Args:
            tmdb_data: TMDB API返回的数据
            media_type: 媒体类型 (movie/tv)
            confidence: 识别置信度

        Returns:
            格式化后的识别结果
        """
        result = {
            'source': 'tmdb',
            'source_id': str(tmdb_data.get('id')),
            'media_type': media_type,
            'title': tmdb_data.get('title') or tmdb_data.get('name'),
            'original_title': tmdb_data.get('original_title') or tmdb_data.get('original_name'),
            'year': int(tmdb_data.get('release_date', '')[:4]) if tmdb_data.get('release_date') else None,
            'season_number': None,
            'episode_number': None,
            'episode_title': None,
            'overview': tmdb_data.get('overview'),
            'poster_url': self._get_image_url(tmdb_data.get('poster_path')),
            'backdrop_url': self._get_image_url(tmdb_data.get('backdrop_path')),
            'genres': ','.join([g['name'] for g in tmdb_data.get('genres', [])]),
            'directors': '',
            'actors': '',
            'rating': float(tmdb_data.get('vote_average', 0)),
            'confidence': confidence,
            'is_manual': False,
            'is_selected': False
        }

        return result

    def _get_image_url(self, path: Optional[str], size: str = 'original') -> Optional[str]:
        """
        获取完整图片URL

        Args:
            path: 图片路径
            size: 图片尺寸

        Returns:
            完整URL
        """
        if not path:
            return None
        return f"https://image.tmdb.org/t/p/{size}{path}"
