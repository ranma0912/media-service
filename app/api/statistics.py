"""
统计数据 API 接口
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from app.db import get_db
from app.db.models import MediaFile, RecognitionResult, OrganizeTask


router = APIRouter(tags=["统计管理"])


class RecognitionStats(BaseModel):
    """识别统计"""
    total: int  # 待识别文件数
    success: int  # 识别成功数
    processing: int  # 识别中
    failed: int  # 识别失败


class OrganizeStats(BaseModel):
    """整理统计"""
    pending: int  # 待整理文件数
    success: int  # 整理成功数
    processing: int  # 整理中
    failed: int  # 整理失败


class MediaStats(BaseModel):
    """媒体库统计"""
    total_files: int  # 媒体文件总数
    total_size: int  # 媒体库总容量（字节）
    recognized_files: int  # 已识别文件数
    pending_files: int  # 待识别文件数


@router.get("/recognition", response_model=RecognitionStats)
async def get_recognition_stats(db: Session = Depends(get_db)):
    """
    获取识别统计信息

    返回待识别、识别成功、识别中、识别失败的文件数量
    """
    try:
        # 待识别文件：没有识别结果的文件
        pending = db.query(MediaFile.id).filter(
            ~MediaFile.id.in_(
                db.query(RecognitionResult.media_file_id).distinct()
            )
        ).count()

        # 识别成功：有选中识别结果的文件
        success = db.query(MediaFile.id).join(
            RecognitionResult
        ).filter(
            RecognitionResult.is_selected == True
        ).count()

        # 识别中：状态为processing的识别结果对应的文件
        processing = db.query(MediaFile.id).join(
            RecognitionResult
        ).filter(
            RecognitionResult.source == 'processing'
        ).count()

        # 识别失败：有识别结果但未选中，且置信度较低的文件
        failed = db.query(MediaFile.id).join(
            RecognitionResult
        ).filter(
            RecognitionResult.is_selected == False,
            RecognitionResult.confidence < 0.5
        ).count()

        return RecognitionStats(
            total=pending,
            success=success,
            processing=processing,
            failed=failed
        )
    except Exception as e:
        logger.error(f"获取识别统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取识别统计失败: {str(e)}")


@router.get("/organize", response_model=OrganizeStats)
async def get_organize_stats(db: Session = Depends(get_db)):
    """
    获取整理统计信息

    返回待整理、整理成功、整理中、整理失败的文件数量
    """
    try:
        # 待整理文件：有选中识别结果但没有整理任务的文件
        pending = db.query(MediaFile.id).filter(
            MediaFile.id.in_(
                db.query(RecognitionResult.media_file_id).filter(
                    RecognitionResult.is_selected == True
                ).distinct()
            ),
            ~MediaFile.id.in_(
                db.query(OrganizeTask.media_file_id).distinct()
            )
        ).count()

        # 整理成功：状态为completed的整理任务
        success = db.query(OrganizeTask.id).filter(
            OrganizeTask.task_status == 'completed'
        ).count()

        # 整理中：状态为running的整理任务
        processing = db.query(OrganizeTask.id).filter(
            OrganizeTask.task_status == 'running'
        ).count()

        # 整理失败：状态为failed的整理任务
        failed = db.query(OrganizeTask.id).filter(
            OrganizeTask.task_status == 'failed'
        ).count()

        return OrganizeStats(
            pending=pending,
            success=success,
            processing=processing,
            failed=failed
        )
    except Exception as e:
        logger.error(f"获取整理统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取整理统计失败: {str(e)}")


@router.get("/media", response_model=MediaStats)
async def get_media_stats(db: Session = Depends(get_db)):
    """
    获取媒体库统计信息

    返回媒体文件总数、总容量、已识别文件数、待识别文件数
    """
    try:
        # 媒体文件总数
        total_files = db.query(MediaFile).count()

        # 媒体库总容量
        total_size = db.query(func.sum(MediaFile.file_size)).scalar() or 0

        # 已识别文件数：有选中识别结果的文件
        recognized_files = db.query(MediaFile.id).join(
            RecognitionResult
        ).filter(
            RecognitionResult.is_selected == True
        ).count()

        # 待识别文件数：没有识别结果的文件
        pending_files = db.query(MediaFile.id).filter(
            ~MediaFile.id.in_(
                db.query(RecognitionResult.media_file_id).distinct()
            )
        ).count()

        return MediaStats(
            total_files=total_files,
            total_size=total_size,
            recognized_files=recognized_files,
            pending_files=pending_files
        )
    except Exception as e:
        logger.error(f"获取媒体库统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取媒体库统计失败: {str(e)}")


@router.get("/overview")
async def get_stats_overview(db: Session = Depends(get_db)):
    """
    获取统计概览

    返回所有统计数据的汇总信息
    """
    try:
        # 获取各类统计
        recognition_stats = await get_recognition_stats(db)
        organize_stats = await get_organize_stats(db)
        media_stats = await get_media_stats(db)

        return {
            "recognition": recognition_stats,
            "organize": organize_stats,
            "media": media_stats
        }
    except Exception as e:
        logger.error(f"获取统计概览失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计概览失败: {str(e)}")
