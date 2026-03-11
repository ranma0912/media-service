
"""
扫描相关API接口
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from loguru import logger

from app.modules.scanner import FileScanner
from app.modules.recognizer import MediaRecognizer
from app.db.models import ScanHistory, MediaFile
from app.db.session import get_db


router = APIRouter(prefix="/api/scan", tags=["扫描管理"])


class ScanRequest(BaseModel):
    """扫描请求"""
    path: str
    recursive: bool = True
    scan_type: str = "incremental"  # full / incremental


class ScanResponse(BaseModel):
    """扫描响应"""
    task_id: str
    status: str
    message: str


@router.post("/trigger", response_model=ScanResponse)
async def trigger_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks
):
    """
    手动触发扫描

    - **path**: 扫描目录路径
    - **recursive**: 是否递归扫描
    - **scan_type**: 扫描类型 (incremental/full)
    """
    try:
        # 创建扫描器实例
        scanner = FileScanner()

        # 在后台任务中执行扫描
        def scan_task():
            try:
                scan_history = scanner.scan_directory(
                    path=request.path,
                    recursive=request.recursive,
                    scan_type=request.scan_type
                )
                logger.info(f"扫描任务完成: {scan_history.batch_id}")
            except Exception as e:
                logger.error(f"扫描任务失败: {e}")

        # 添加后台任务
        background_tasks.add_task(scan_task)

        return ScanResponse(
            task_id=datetime.now().strftime("%Y%m%d%H%M%S"),
            status="accepted",
            message="扫描任务已接受，正在后台执行"
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NotADirectoryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"触发扫描失败: {e}")
        raise HTTPException(status_code=500, detail=f"扫描触发失败: {str(e)}")


@router.get("/tasks")
async def get_scan_tasks(
    limit: int = 20,
    offset: int = 0
):
    """
    获取扫描任务列表

    - **limit**: 返回数量限制
    - **offset**: 偏移量
    """
    with get_db() as db:
        tasks = db.query(ScanHistory).order_by(
            ScanHistory.started_at.desc()
        ).offset(offset).limit(limit).all()

        return [
            {
                "id": task.id,
                "batch_id": task.batch_id,
                "target_path": task.target_path,
                "scan_type": task.scan_type,
                "recursive": task.recursive,
                "total_files": task.total_files,
                "new_files": task.new_files,
                "updated_files": task.updated_files,
                "skipped_files": task.skipped_files,
                "failed_files": task.failed_files,
                "duration_seconds": task.duration_seconds,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None
            }
            for task in tasks
        ]


@router.get("/tasks/{task_id}")
async def get_scan_task_detail(task_id: int):
    """
    获取扫描任务详情

    - **task_id**: 任务ID
    """
    with get_db() as db:
        task = db.query(ScanHistory).filter_by(id=task_id).first()

        if not task:
            raise HTTPException(status_code=404, detail="扫描任务不存在")

        return {
            "id": task.id,
            "batch_id": task.batch_id,
            "target_path": task.target_path,
            "scan_type": task.scan_type,
            "recursive": task.recursive,
            "total_files": task.total_files,
            "new_files": task.new_files,
            "updated_files": task.updated_files,
            "skipped_files": task.skipped_files,
            "failed_files": task.failed_files,
            "duration_seconds": task.duration_seconds,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message
        }


@router.post("/recognize")
async def recognize_files(
    file_ids: List[int],
    background_tasks: BackgroundTasks
):
    """
    批量识别文件

    - **file_ids**: 媒体文件ID列表
    """
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

    return {
        "status": "accepted",
        "message": f"已提交 {len(file_ids)} 个文件的识别任务",
        "file_count": len(file_ids)
    }


@router.get("/pending")
async def get_pending_files(
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
