
"""
识别相关API接口
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger

from app.modules.recognizer import MediaRecognizer
from app.modules.fetcher import TMDBFetcher
from app.db.models import RecognitionResult, MediaFile
from app.db.session import get_db


router = APIRouter(tags=["识别管理"])


class RecognitionRequest(BaseModel):
    """识别请求"""
    file_id: int
    force: bool = False


class RecognitionResponse(BaseModel):
    """识别响应"""
    file_id: int
    status: str
    results_count: int
    message: str


class ManualRecognitionRequest(BaseModel):
    """手动识别请求"""
    file_id: int
    media_type: str  # movie / tv
    tmdb_id: int
    season_number: Optional[int] = None
    episode_number: Optional[int] = None


@router.post("/recognize", response_model=RecognitionResponse)
async def recognize_file(
    request: RecognitionRequest,
    background_tasks: BackgroundTasks
):
    """
    识别单个文件

    - **file_id**: 媒体文件ID
    - **force**: 是否强制重新识别
    """
    try:
        async def recognize_task():
            try:
                async with MediaRecognizer() as recognizer:
                    results = await recognizer.recognize_media_file(
                        request.file_id,
                        force=request.force
                    )
                    logger.info(f"识别完成: {request.file_id}, 结果数: {len(results)}")
            except Exception as e:
                logger.error(f"识别失败: {request.file_id}, 错误: {e}")

        background_tasks.add_task(recognize_task)

        return RecognitionResponse(
            file_id=request.file_id,
            status="accepted",
            results_count=0,
            message="识别任务已接受，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交识别任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"提交识别任务失败: {str(e)}")


@router.post("/batch", response_model=RecognitionResponse)
async def batch_recognize(
    file_ids: List[int],
    background_tasks: BackgroundTasks
):
    """
    批量识别文件

    - **file_ids**: 媒体文件ID列表
    """
    try:
        async def recognize_task():
            try:
                async with MediaRecognizer() as recognizer:
                    for file_id in file_ids:
                        try:
                            await recognizer.recognize_media_file(file_id)
                            logger.info(f"识别完成: {file_id}")
                        except Exception as e:
                            logger.error(f"识别失败: {file_id}, 错误: {e}")
            except Exception as e:
                logger.error(f"批量识别任务失败: {e}")

        background_tasks.add_task(recognize_task)

        return RecognitionResponse(
            file_id=0,
            status="accepted",
            results_count=0,
            message=f"已提交 {len(file_ids)} 个文件的识别任务"
        )

    except Exception as e:
        logger.error(f"提交批量识别任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"提交批量识别任务失败: {str(e)}")


@router.post("/manual")
async def manual_recognize(
    request: ManualRecognitionRequest,
    db: Session = Depends(get_db)
):
    """
    手动指定TMDB ID识别

    - **file_id**: 媒体文件ID
    - **media_type**: 媒体类型 (movie/tv)
    - **tmdb_id**: TMDB ID
    - **season_number**: 季数（电视剧）
    - **episode_number**: 集数（电视剧）
    """
    try:
        media_file = db.query(MediaFile).filter_by(id=request.file_id).first()
        if not media_file:
            raise HTTPException(status_code=404, detail="媒体文件不存在")

        # 获取TMDB数据
        async with TMDBFetcher() as fetcher:
            if request.media_type == 'movie':
                tmdb_data = await fetcher.get_movie_details(request.tmdb_id)
            else:
                tmdb_data = await fetcher.get_tv_details(request.tmdb_id)

                # 如果指定了季集，获取季集详情
                if request.season_number and request.episode_number:
                    episode_data = await fetcher.get_tv_episode_details(
                        request.tmdb_id,
                        request.season_number,
                        request.episode_number
                    )
                    tmdb_data['episode_title'] = episode_data.get('name')
                    tmdb_data['season_number'] = request.season_number
                    tmdb_data['episode_number'] = request.episode_number

        # 格式化识别结果
        result_data = fetcher.format_recognition_result(
            tmdb_data,
            request.media_type,
            confidence=1.0  # 手动指定置信度为1.0
        )

        # 更新季集信息
        if request.season_number:
            result_data['season_number'] = request.season_number
        if request.episode_number:
            result_data['episode_number'] = request.episode_number

        # 清除旧的识别结果
        db.query(RecognitionResult).filter_by(
            media_file_id=request.file_id
        ).delete()

        # 创建新的识别结果
        recognition = RecognitionResult(
            media_file_id=request.file_id,
            is_manual=True,
            is_selected=True,
            **result_data
        )

        db.add(recognition)
        db.commit()

        logger.info(f"手动识别完成: {media_file.file_name}, TMDB ID: {request.tmdb_id}")

        return {
            "file_id": request.file_id,
            "status": "success",
            "result": {
                "id": recognition.id,
                "title": recognition.title,
                "year": recognition.year,
                "season": recognition.season_number,
                "episode": recognition.episode_number,
                "confidence": recognition.confidence
            }
        }

    except Exception as e:
        logger.error(f"手动识别失败: {e}")
        raise HTTPException(status_code=500, detail=f"手动识别失败: {str(e)}")


@router.get("/results/{file_id}")
async def get_recognition_results(
    file_id: int,
    db: Session = Depends(get_db)
):
    """
    获取文件的识别结果

    - **file_id**: 媒体文件ID
    """
    results = db.query(RecognitionResult).filter_by(
        media_file_id=file_id
    ).order_by(RecognitionResult.confidence.desc()).all()

    return [
        {
            "id": r.id,
            "source": r.source,
            "source_id": r.source_id,
            "media_type": r.media_type,
            "title": r.title,
            "original_title": r.original_title,
            "year": r.year,
            "season_number": r.season_number,
            "episode_number": r.episode_number,
            "episode_title": r.episode_title,
            "overview": r.overview,
            "poster_url": r.poster_url,
            "backdrop_url": r.backdrop_url,
            "genres": r.genres,
            "directors": r.directors,
            "actors": r.actors,
            "rating": r.rating,
            "confidence": r.confidence,
            "is_manual": r.is_manual,
            "is_selected": r.is_selected,
            "recognized_at": r.recognized_at.isoformat() if r.recognized_at else None
        }
        for r in results
    ]


@router.put("/select/{result_id}")
async def select_recognition_result(
    result_id: int,
    db: Session = Depends(get_db)
):
    """
    选择识别结果

    - **result_id**: 识别结果ID
    """
    try:
        result = db.query(RecognitionResult).filter_by(id=result_id).first()

        if not result:
            raise HTTPException(status_code=404, detail="识别结果不存在")

        # 取消同一文件的其他选择
        db.query(RecognitionResult).filter(
            RecognitionResult.media_file_id == result.media_file_id,
            RecognitionResult.id != result_id
        ).update({"is_selected": False})

        # 选中当前结果
        result.is_selected = True
        db.commit()

        logger.info(f"选择识别结果: {result_id}")

        return {
            "id": result_id,
            "status": "success",
            "message": "已选择识别结果"
        }

    except Exception as e:
        logger.error(f"选择识别结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"选择识别结果失败: {str(e)}")


@router.get("/pending")
async def get_pending_recognitions(
    limit: int = 50,
    offset: int = 0
):
    """
    获取待识别文件列表

    - **limit**: 返回数量限制
    - **offset**: 偏移量
    """
    with get_db() as db:
        # 查询没有识别结果的文件
        files = db.query(MediaFile).filter(
            ~MediaFile.id.in_(
                db.query(MediaFile.id).join(
                    "recognition_results"
                ).distinct()
            )
        ).order_by(
            MediaFile.scanned_at.desc()
        ).offset(offset).limit(limit).all()

        return [
            {
                "id": f.id,
                "file_name": f.file_name,
                "file_path": f.file_path,
                "file_size": f.file_size,
                "media_type": f.media_type,
                "scanned_at": f.scanned_at.isoformat() if f.scanned_at else None
            }
            for f in files
        ]
