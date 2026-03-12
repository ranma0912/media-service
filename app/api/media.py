"""
媒体管理 API
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from app.db import get_db
from app.db.models import MediaFile

router = APIRouter()


class MediaFileResponse(BaseModel):
    """媒体文件响应"""
    id: int
    file_path: str
    file_name: str
    file_stem: Optional[str]
    file_extension: Optional[str]
    file_size: Optional[int]
    media_type: Optional[str]
    duration: Optional[float]
    width: Optional[int]
    height: Optional[int]
    video_codec: Optional[str]
    audio_codec: Optional[str]
    scanned_at: Optional[str]

    class Config:
        from_attributes = True


class MediaFileListResponse(BaseModel):
    """媒体文件列表响应"""
    total: int
    page: int
    page_size: int
    items: List[MediaFileResponse]


@router.get("/files", response_model=MediaFileListResponse)
async def list_media_files(
    page: int = 1,
    page_size: int = 50,
    media_type: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取媒体文件列表"""
    try:
        query = db.query(MediaFile)

        # 按类型筛选
        if media_type:
            query = query.filter(MediaFile.media_type == media_type)

        # 搜索
        if search:
            query = query.filter(
                MediaFile.file_name.contains(search) |
                MediaFile.file_path.contains(search)
            )

        # 总数
        total = query.count()

        # 分页
        offset = (page - 1) * page_size
        files = query.order_by(MediaFile.scanned_at.desc()).offset(offset).limit(page_size).all()

        return MediaFileListResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=[MediaFileResponse.model_validate(f) for f in files]
        )
    except Exception as e:
        logger.error(f"获取媒体文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取媒体文件列表失败: {str(e)}")


@router.get("/files/{file_id}", response_model=MediaFileResponse)
async def get_media_file(
    file_id: int,
    db: Session = Depends(get_db)
):
    """获取媒体文件详情"""
    file = db.query(MediaFile).filter(MediaFile.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    return MediaFileResponse.model_validate(file)


@router.delete("/files/{file_id}")
async def delete_media_file(
    file_id: int,
    db: Session = Depends(get_db)
):
    """删除媒体文件记录（不删除实际文件）"""
    file = db.query(MediaFile).filter(MediaFile.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")

    try:
        db.delete(file)
        db.commit()
        logger.info(f"已删除媒体文件记录: {file_id}")
        return {"success": True, "message": "媒体文件记录已删除"}
    except Exception as e:
        db.rollback()
        logger.error(f"删除媒体文件记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除媒体文件记录失败: {str(e)}")


@router.get("/stats")
async def get_media_stats(
    db: Session = Depends(get_db)
):
    """获取媒体库统计信息"""
    try:
        total_files = db.query(MediaFile).count()

        # 按类型统计
        type_stats = db.query(
            MediaFile.media_type,
            func.count(MediaFile.id)
        ).group_by(MediaFile.media_type).all()

        # 总大小
        total_size = db.query(func.sum(MediaFile.file_size)).scalar() or 0

        return {
            "total_files": total_files,
            "total_size": total_size,
            "type_distribution": {
                type_: count for type_, count in type_stats if type_
            }
        }
    except Exception as e:
        logger.error(f"获取媒体库统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取媒体库统计失败: {str(e)}")
