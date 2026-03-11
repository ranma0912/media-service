
"""
整理相关API接口
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger

from app.modules.organizer import MediaOrganizer
from app.db.models import OrganizeTask, MediaFile
from app.db.session import get_db


router = APIRouter(prefix="/api/organize", tags=["整理管理"])


class OrganizeRequest(BaseModel):
    """整理请求"""
    file_id: int
    recognition_result_id: Optional[int] = None


class OrganizeResponse(BaseModel):
    """整理响应"""
    task_id: int
    status: str
    message: str


@router.post("/create", response_model=OrganizeResponse)
async def create_organize_task(
    request: OrganizeRequest
):
    """
    创建整理任务

    - **file_id**: 媒体文件ID
    - **recognition_result_id**: 识别结果ID（可选）
    """
    try:
        organizer = MediaOrganizer()
        task = await organizer.organize_media_file(
            request.file_id,
            request.recognition_result_id
        )

        return OrganizeResponse(
            task_id=task.id,
            status="created",
            message="整理任务已创建"
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"创建整理任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建整理任务失败: {str(e)}")


@router.post("/batch")
async def batch_create_organize_tasks(
    file_ids: List[int],
    background_tasks: BackgroundTasks
):
    """
    批量创建整理任务

    - **file_ids**: 媒体文件ID列表
    """
    try:
        organizer = MediaOrganizer()

        async def organize_task():
            try:
                for file_id in file_ids:
                    try:
                        await organizer.organize_media_file(file_id)
                        logger.info(f"创建整理任务完成: {file_id}")
                    except Exception as e:
                        logger.error(f"创建整理任务失败: {file_id}, 错误: {e}")
            except Exception as e:
                logger.error(f"批量创建整理任务失败: {e}")

        background_tasks.add_task(organize_task)

        return {
            "status": "accepted",
            "message": f"已提交 {len(file_ids)} 个整理任务",
            "file_count": len(file_ids)
        }

    except Exception as e:
        logger.error(f"提交批量整理任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"提交批量整理任务失败: {str(e)}")


@router.post("/execute/{task_id}")
async def execute_organize_task(
    task_id: int,
    background_tasks: BackgroundTasks
):
    """
    执行整理任务

    - **task_id**: 任务ID
    """
    try:
        async def execute_task():
            try:
                organizer = MediaOrganizer()
                success = await organizer.execute_organize_task(task_id)

                if success:
                    logger.info(f"整理任务执行成功: {task_id}")
                else:
                    logger.error(f"整理任务执行失败: {task_id}")
            except Exception as e:
                logger.error(f"执行整理任务异常: {task_id}, 错误: {e}")

        background_tasks.add_task(execute_task)

        return {
            "task_id": task_id,
            "status": "accepted",
            "message": "整理任务已接受，正在后台执行"
        }

    except Exception as e:
        logger.error(f"提交执行整理任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"提交执行整理任务失败: {str(e)}")


@router.post("/batch-execute")
async def batch_execute_organize_tasks(
    task_ids: List[int],
    background_tasks: BackgroundTasks
):
    """
    批量执行整理任务

    - **task_ids**: 任务ID列表
    """
    try:
        async def execute_task():
            try:
                organizer = MediaOrganizer()
                for task_id in task_ids:
                    try:
                        await organizer.execute_organize_task(task_id)
                        logger.info(f"整理任务执行完成: {task_id}")
                    except Exception as e:
                        logger.error(f"整理任务执行失败: {task_id}, 错误: {e}")
            except Exception as e:
                logger.error(f"批量执行整理任务失败: {e}")

        background_tasks.add_task(execute_task)

        return {
            "status": "accepted",
            "message": f"已提交 {len(task_ids)} 个整理任务",
            "task_count": len(task_ids)
        }

    except Exception as e:
        logger.error(f"提交批量执行整理任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"提交批量执行整理任务失败: {str(e)}")


@router.get("/tasks")
async def get_organize_tasks(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """
    获取整理任务列表

    - **status**: 任务状态筛选 (pending/running/completed/failed)
    - **limit**: 返回数量限制
    - **offset**: 偏移量
    """
    with get_db() as db:
        query = db.query(OrganizeTask)

        if status:
            query = query.filter(OrganizeTask.task_status == status)

        tasks = query.order_by(
            OrganizeTask.created_at.desc()
        ).offset(offset).limit(limit).all()

        return [
            {
                "id": task.id,
                "media_file_id": task.media_file_id,
                "source_path": task.source_path,
                "target_path": task.target_path,
                "action_type": task.action_type,
                "task_status": task.task_status,
                "conflict_strategy": task.conflict_strategy,
                "error_message": task.error_message,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "created_at": task.created_at.isoformat() if task.created_at else None
            }
            for task in tasks
        ]


@router.get("/tasks/{task_id}")
async def get_organize_task_detail(task_id: int):
    """
    获取整理任务详情

    - **task_id**: 任务ID
    """
    with get_db() as db:
        task = db.query(OrganizeTask).filter_by(id=task_id).first()

        if not task:
            raise HTTPException(status_code=404, detail="整理任务不存在")

        # 获取关联的媒体文件信息
        media_file = db.query(MediaFile).filter_by(id=task.media_file_id).first()

        return {
            "id": task.id,
            "media_file_id": task.media_file_id,
            "file_name": media_file.file_name if media_file else None,
            "source_path": task.source_path,
            "target_path": task.target_path,
            "action_type": task.action_type,
            "task_status": task.task_status,
            "conflict_strategy": task.conflict_strategy,
            "error_message": task.error_message,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat() if task.created_at else None
        }


@router.post("/preview")
async def preview_organize(request: OrganizeRequest):
    """
    预览整理结果

    - **file_id**: 媒体文件ID
    - **recognition_result_id**: 识别结果ID（可选）
    """
    try:
        organizer = MediaOrganizer()
        preview = organizer.preview_organize(
            request.file_id,
            request.recognition_result_id
        )

        return preview

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"预览整理失败: {e}")
        raise HTTPException(status_code=500, detail=f"预览整理失败: {str(e)}")


@router.get("/pending")
async def get_pending_organize(
    limit: int = 50,
    offset: int = 0
):
    """
    获取待整理文件列表

    - **limit**: 返回数量限制
    - **offset**: 偏移量
    """
    with get_db() as db:
        # 查询有识别结果但没有整理任务的文件
        files = db.query(MediaFile).filter(
            MediaFile.id.in_(
                db.query(MediaFile.id).join(
                    "recognition_results"
                ).filter(
                    RecognitionResult.is_selected == True
                ).distinct()
            ),
            ~MediaFile.id.in_(
                db.query(OrganizeTask.media_file_id).distinct()
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
