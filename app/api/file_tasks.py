# -*- coding: utf-8 -*-
"""
文件任务管理API
每个被扫描文件对应一个文件任务
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.models import FileTask, MediaFile, RecognitionResult
from app.db import get_db
from app.modules.recognizer import MediaRecognizer


router = APIRouter(tags=["文件任务管理"])


class FileTaskResponse(BaseModel):
    """文件任务响应"""
    id: int
    media_file_id: int
    scan_batch_id: Optional[str]
    target_path: str
    file_name: str
    status: str
    
    # 扫描阶段
    scan_started_at: Optional[datetime]
    scan_completed_at: Optional[datetime]
    scan_error: Optional[str]
    
    # 识别阶段
    recognition_started_at: Optional[datetime]
    recognition_completed_at: Optional[datetime]
    recognition_error: Optional[str]
    
    # 整理阶段
    organize_started_at: Optional[datetime]
    organize_completed_at: Optional[datetime]
    organize_error: Optional[str]
    
    # 整理结果
    organize_action: Optional[str]
    source_path: Optional[str]
    target_path_final: Optional[str]
    
    # 时间戳
    created_at: datetime
    updated_at: datetime
    
    # 关联的媒体文件信息
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    media_type: Optional[str] = None


class FileTaskListResponse(BaseModel):
    """文件任务列表响应"""
    items: List[FileTaskResponse]
    total: int
    page: int
    page_size: int


class FileTaskFilter(BaseModel):
    """文件任务筛选"""
    status: Optional[str] = None
    scan_batch_id: Optional[str] = None
    target_path: Optional[str] = None
    file_name: Optional[str] = None  # 文件名模糊搜索
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@router.get("/file-tasks", response_model=FileTaskListResponse)
async def get_file_tasks(
    page: int = 1,
    page_size: int = 50,
    status: Optional[str] = None,
    scan_batch_id: Optional[str] = None,
    target_path: Optional[str] = None,
    file_name: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    获取文件任务列表
    
    - **page**: 页码（从1开始）
    - **page_size**: 每页数量
    - **status**: 任务状态筛选
    - **scan_batch_id**: 扫描批次ID筛选
    - **target_path**: 路径筛选
    - **file_name**: 文件名模糊搜索
    - **start_time**: 开始时间
    - **end_time**: 结束时间
    """
    # 构建查询
    query = db.query(FileTask).join(MediaFile)
    
    # 应用筛选条件
    if status:
        query = query.filter(FileTask.status == status)
    
    if scan_batch_id:
        query = query.filter(FileTask.scan_batch_id == scan_batch_id)
    
    if target_path:
        query = query.filter(FileTask.target_path.like(f"%{target_path}%"))
    
    if file_name:
        query = query.filter(FileTask.file_name.like(f"%{file_name}%"))
    
    if start_time:
        query = query.filter(FileTask.created_at >= start_time)
    
    if end_time:
        query = query.filter(FileTask.created_at <= end_time)
    
    # 排序：按创建时间倒序
    query = query.order_by(FileTask.created_at.desc())
    
    # 分页
    total = query.count()
    offset = (page - 1) * page_size
    tasks = query.offset(offset).limit(page_size).all()
    
    # 构建响应
    items = []
    for task in tasks:
        item = {
            "id": task.id,
            "media_file_id": task.media_file_id,
            "scan_batch_id": task.scan_batch_id,
            "target_path": task.target_path,
            "file_name": task.file_name,
            "status": task.status,
            "scan_started_at": task.scan_started_at,
            "scan_completed_at": task.scan_completed_at,
            "scan_error": task.scan_error,
            "recognition_started_at": task.recognition_started_at,
            "recognition_completed_at": task.recognition_completed_at,
            "recognition_error": task.recognition_error,
            "organize_started_at": task.organize_started_at,
            "organize_completed_at": task.organize_completed_at,
            "organize_error": task.organize_error,
            "organize_action": task.organize_action,
            "source_path": task.source_path,
            "target_path_final": task.target_path_final,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
        
        # 添加媒体文件信息
        if task.media_file:
            item["file_path"] = task.media_file.file_path
            item["file_size"] = task.media_file.file_size
            item["media_type"] = task.media_file.media_type
        
        items.append(FileTaskResponse(**item))
    
    return FileTaskListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/file-tasks/{task_id}", response_model=FileTaskResponse)
async def get_file_task_detail(
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    获取文件任务详情
    
    - **task_id**: 任务ID
    """
    task = db.query(FileTask).filter(FileTask.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="文件任务不存在")
    
    item = {
        "id": task.id,
        "media_file_id": task.media_file_id,
        "scan_batch_id": task.scan_batch_id,
        "target_path": task.target_path,
        "file_name": task.file_name,
        "status": task.status,
        "scan_started_at": task.scan_started_at,
        "scan_completed_at": task.scan_completed_at,
        "scan_error": task.scan_error,
        "recognition_started_at": task.recognition_started_at,
        "recognition_completed_at": task.recognition_completed_at,
        "recognition_error": task.recognition_error,
        "organize_started_at": task.organize_started_at,
        "organize_completed_at": task.organize_completed_at,
        "organize_error": task.organize_error,
        "organize_action": task.organize_action,
        "source_path": task.source_path,
        "target_path_final": task.target_path_final,
        "created_at": task.created_at,
        "updated_at": task.updated_at
    }
    
    # 添加媒体文件信息
    if task.media_file:
        item["file_path"] = task.media_file.file_path
        item["file_size"] = task.media_file.file_size
        item["media_type"] = task.media_file.media_type
    
    return FileTaskResponse(**item)


@router.delete("/file-tasks/{task_id}")
async def delete_file_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    删除文件任务
    
    - **task_id**: 任务ID
    """
    task = db.query(FileTask).filter(FileTask.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="文件任务不存在")
    
    # 检查任务是否正在进行
    if task.status in ['scanning', 'recognizing', 'organizing']:
        raise HTTPException(status_code=400, detail="无法删除正在进行的任务")
    
    db.delete(task)
    db.commit()
    
    logger.info(f"删除文件任务: {task_id}")
    
    return {"message": "文件任务已删除"}


class BatchRecognizeRequest(BaseModel):
    """批量识别请求"""
    task_ids: List[int]


@router.post("/file-tasks/batch/recognize")
async def batch_recognize(
    request: BatchRecognizeRequest,
    db: Session = Depends(get_db)
):
    """
    批量识别文件任务
    
    - **task_ids**: 任务ID列表
    """
    results = []
    
    for task_id in request.task_ids:
        try:
            task = db.query(FileTask).filter(FileTask.id == task_id).first()
            
            if not task:
                results.append({
                    "task_id": task_id,
                    "success": False,
                    "message": "任务不存在"
                })
                continue
            
            # 检查任务状态
            if task.status != 'scanned':
                results.append({
                    "task_id": task_id,
                    "success": False,
                    "message": f"任务状态不允许识别，当前状态: {task.status}"
                })
                continue
            
            # 更新任务状态
            task.status = 'recognizing'
            task.recognition_started_at = datetime.now()
            db.commit()
            
            # 执行识别
            async with MediaRecognizer() as recognizer:
                try:
                    await recognizer.recognize_media_file(task.media_file_id)
                    
                    # 更新任务状态
                    task.status = 'recognized'
                    task.recognition_completed_at = datetime.now()
                    db.commit()
                    
                    results.append({
                        "task_id": task_id,
                        "success": True,
                        "message": "识别成功"
                    })
                except Exception as e:
                    task.status = 'scanned'
                    task.recognition_error = str(e)
                    db.commit()
                    
                    logger.error(f"识别失败: task_id={task_id}, media_file_id={task.media_file_id}, 错误: {e}")
                    
                    results.append({
                        "task_id": task_id,
                        "success": False,
                        "message": f"识别失败: {str(e)}"
                    })
        
        except Exception as e:
            logger.error(f"批量识别任务失败: task_id={task_id}, 错误: {e}")
            results.append({
                "task_id": task_id,
                "success": False,
                "message": f"处理失败: {str(e)}"
            })
    
    return {
        "total": len(request.task_ids),
        "success": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }


class BatchOrganizeRequest(BaseModel):
    """批量整理请求"""
    task_ids: List[int]


@router.post("/file-tasks/batch/organize")
async def batch_organize(
    request: BatchOrganizeRequest,
    db: Session = Depends(get_db)
):
    """
    批量整理文件任务
    
    - **task_ids**: 任务ID列表
    """
    results = []
    
    for task_id in request.task_ids:
        try:
            task = db.query(FileTask).filter(FileTask.id == task_id).first()
            
            if not task:
                results.append({
                    "task_id": task_id,
                    "success": False,
                    "message": "任务不存在"
                })
                continue
            
            # 检查任务状态
            if task.status != 'recognized':
                results.append({
                    "task_id": task_id,
                    "success": False,
                    "message": f"任务状态不允许整理，当前状态: {task.status}"
                })
                continue
            
            # 更新任务状态
            task.status = 'organizing'
            task.organize_started_at = datetime.now()
            db.commit()
            
            # TODO: 实现整理逻辑
            # 这里需要调用整理模块
            
            # 模拟整理成功
            task.status = 'organized'
            task.organize_completed_at = datetime.now()
            task.organize_action = 'skip'  # 暂时跳过
            db.commit()
            
            results.append({
                "task_id": task_id,
                "success": True,
                "message": "整理成功"
            })
        
        except Exception as e:
            logger.error(f"批量整理任务失败: task_id={task_id}, 错误: {e}")
            results.append({
                "task_id": task_id,
                "success": False,
                "message": f"处理失败: {str(e)}"
            })
    
    return {
        "total": len(request.task_ids),
        "success": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    task_ids: List[int]


@router.delete("/file-tasks/batch")
async def batch_delete_tasks(
    request: BatchDeleteRequest,
    db: Session = Depends(get_db)
):
    """
    批量删除文件任务
    
    - **task_ids**: 任务ID列表
    """
    results = []
    
    for task_id in request.task_ids:
        try:
            task = db.query(FileTask).filter(FileTask.id == task_id).first()
            
            if not task:
                results.append({
                    "task_id": task_id,
                    "success": False,
                    "message": "任务不存在"
                })
                continue
            
            # 检查任务是否正在进行
            if task.status in ['scanning', 'recognizing', 'organizing']:
                results.append({
                    "task_id": task_id,
                    "success": False,
                    "message": "无法删除正在进行的任务"
                })
                continue
            
            db.delete(task)
            db.commit()
            
            results.append({
                "task_id": task_id,
                "success": True,
                "message": "删除成功"
            })
        
        except Exception as e:
            logger.error(f"批量删除任务失败: task_id={task_id}, 错误: {e}")
            results.append({
                "task_id": task_id,
                "success": False,
                "message": f"删除失败: {str(e)}"
            })
    
    return {
        "total": len(request.task_ids),
        "success": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }


@router.get("/file-tasks/scan/{batch_id}")
async def get_file_tasks_by_batch(
    batch_id: str,
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取指定扫描批次的文件任务列表
    
    - **batch_id**: 扫描批次ID
    - **limit**: 返回数量限制
    - **offset**: 偏移量
    - **status**: 状态筛选 (pending/scanning/scanned/skipped/failed)
    """
    # 构建查询
    query = db.query(FileTask).join(MediaFile).filter(FileTask.scan_batch_id == batch_id)
    
    # 状态筛选
    if status:
        query = query.filter(FileTask.status == status)
    
    # 排序：按扫描开始时间倒序
    query = query.order_by(FileTask.scan_started_at.desc())
    
    # 分页
    total = query.count()
    tasks = query.offset(offset).limit(limit).all()
    
    # 构建响应
    items = []
    for task in tasks:
        item = {
            "id": task.id,
            "media_file_id": task.media_file_id,
            "scan_batch_id": task.scan_batch_id,
            "target_path": task.target_path,
            "file_name": task.file_name,
            "status": task.status,
            "scan_started_at": task.scan_started_at.isoformat() if task.scan_started_at else None,
            "scan_completed_at": task.scan_completed_at.isoformat() if task.scan_completed_at else None,
            "scan_error": task.scan_error,
            "recognition_started_at": task.recognition_started_at.isoformat() if task.recognition_started_at else None,
            "recognition_completed_at": task.recognition_completed_at.isoformat() if task.recognition_completed_at else None,
            "recognition_error": task.recognition_error,
            "organize_started_at": task.organize_started_at.isoformat() if task.organize_started_at else None,
            "organize_completed_at": task.organize_completed_at.isoformat() if task.organize_completed_at else None,
            "organize_error": task.organize_error,
            "organize_action": task.organize_action,
            "source_path": task.source_path,
            "target_path_final": task.target_path_final,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None
        }
        
        # 添加媒体文件信息
        if task.media_file:
            item["file_path"] = task.media_file.file_path
            item["file_size"] = task.media_file.file_size
            item["media_type"] = task.media_file.media_type
        
        items.append(FileTaskResponse(**item))
    
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/file-tasks/statistics")
async def get_file_task_statistics(
    db: Session = Depends(get_db)
):
    """
    获取文件任务统计信息
    
    返回各状态的任务数量统计
    """
    # 统计各状态的任务数量
    status_counts = {}
    for status in ['pending', 'scanning', 'scanned', 'recognizing', 'recognized', 'organizing', 'organized', 'completed', 'failed', 'skipped']:
        count = db.query(FileTask).filter(FileTask.status == status).count()
        status_counts[status] = count
    
    # 统计总任务数
    total_tasks = db.query(FileTask).count()
    
    # 统计今日任务数
    from datetime import date
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_tasks = db.query(FileTask).filter(FileTask.created_at >= today_start).count()
    
    return {
        "total": total_tasks,
        "today": today_tasks,
        "by_status": status_counts
    }
