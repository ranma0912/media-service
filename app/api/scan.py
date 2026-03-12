
"""
扫描相关API接口
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session

from app.modules.scanner import FileScanner
from app.modules.recognizer import MediaRecognizer
from app.db.models import ScanHistory, MediaFile, ScanPath, ScanProgress
from app.db import get_db, get_db_context
from app.core.websocket import manager


router = APIRouter(tags=["扫描管理"])


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
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    获取扫描任务列表

    - **limit**: 返回数量限制
    - **offset**: 偏移量
    """
    tasks = db.query(ScanHistory).order_by(
        ScanHistory.started_at.desc()
    ).offset(offset).limit(limit).all()

    return {
        "items": [
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
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "status": "completed" if task.completed_at else "running"
            }
            for task in tasks
        ],
        "total": len(tasks)
    }


@router.get("/tasks/{task_id}")
async def get_scan_task_detail(
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    获取扫描任务详情

    - **task_id**: 任务ID
    """
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
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    获取待识别文件列表

    - **limit**: 返回数量限制
    - **offset**: 偏移量
    """
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


# ========== 扫描路径管理 ==========


class ScanPathCreate(BaseModel):
    """创建扫描路径请求"""
    path: str
    recursive: bool = True
    enabled: bool = True


class ScanPathUpdate(BaseModel):
    """更新扫描路径请求"""
    path: Optional[str] = None
    recursive: Optional[bool] = None
    enabled: Optional[bool] = None


@router.get("/paths")
async def get_scan_paths(
    enabled_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    获取扫描路径列表

    - **enabled_only**: 是否只返回启用的路径
    """
    query = db.query(ScanPath)
    if enabled_only:
        query = query.filter(ScanPath.enabled == True)

    paths = query.order_by(ScanPath.id).all()

    return [
        {
            "id": path.id,
            "path": path.path,
            "recursive": path.recursive,
            "enabled": path.enabled,
            "last_scan_at": path.last_scan_at.isoformat() if path.last_scan_at else None,
            "last_scan_batch_id": path.last_scan_batch_id,
            "created_at": path.created_at.isoformat() if path.created_at else None,
            "updated_at": path.updated_at.isoformat() if path.updated_at else None
        }
        for path in paths
    ]


@router.post("/paths")
async def create_scan_path(
    path_data: ScanPathCreate,
    db: Session = Depends(get_db)
):
    """
    添加扫描路径

    - **path**: 扫描路径
    - **recursive**: 是否递归扫描
    - **enabled**: 是否启用
    """
    # 检查路径是否已存在
    existing = db.query(ScanPath).filter(ScanPath.path == path_data.path).first()
    if existing:
        raise HTTPException(status_code=400, detail="扫描路径已存在")

    # 验证路径是否存在
    from pathlib import Path
    scan_path = Path(path_data.path)
    if not scan_path.exists():
        raise HTTPException(status_code=404, detail="路径不存在")
    if not scan_path.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")

    # 创建扫描路径
    scan_path = ScanPath(
        path=path_data.path,
        recursive=path_data.recursive,
        enabled=path_data.enabled
    )
    db.add(scan_path)
    db.commit()
    db.refresh(scan_path)

    logger.info(f"添加扫描路径: {path_data.path}")

    return {
        "id": scan_path.id,
        "path": scan_path.path,
        "recursive": scan_path.recursive,
        "enabled": scan_path.enabled,
        "last_scan_at": scan_path.last_scan_at.isoformat() if scan_path.last_scan_at else None,
        "last_scan_batch_id": scan_path.last_scan_batch_id,
        "created_at": scan_path.created_at.isoformat() if scan_path.created_at else None,
        "updated_at": scan_path.updated_at.isoformat() if scan_path.updated_at else None
    }


@router.put("/paths/{path_id}")
async def update_scan_path(
    path_id: int,
    path_data: ScanPathUpdate,
    db: Session = Depends(get_db)
):
    """
    更新扫描路径

    - **path_id**: 路径ID
    - **path**: 扫描路径
    - **recursive**: 是否递归扫描
    - **enabled**: 是否启用
    """
    scan_path = db.query(ScanPath).filter(ScanPath.id == path_id).first()
    if not scan_path:
        raise HTTPException(status_code=404, detail="扫描路径不存在")

    # 更新字段
    if path_data.path is not None:
        # 检查新路径是否已被其他路径使用
        existing = db.query(ScanPath).filter(
            ScanPath.path == path_data.path,
            ScanPath.id != path_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="路径已被其他扫描路径使用")

        # 验证路径是否存在
        from pathlib import Path
        new_path = Path(path_data.path)
        if not new_path.exists():
            raise HTTPException(status_code=404, detail="路径不存在")
        if not new_path.is_dir():
            raise HTTPException(status_code=400, detail="路径不是目录")

        scan_path.path = path_data.path

    if path_data.recursive is not None:
        scan_path.recursive = path_data.recursive

    if path_data.enabled is not None:
        scan_path.enabled = path_data.enabled

    scan_path.updated_at = datetime.now()
    db.commit()
    db.refresh(scan_path)

    logger.info(f"更新扫描路径: {path_id}")

    return {
        "id": scan_path.id,
        "path": scan_path.path,
        "recursive": scan_path.recursive,
        "enabled": scan_path.enabled,
        "last_scan_at": scan_path.last_scan_at.isoformat() if scan_path.last_scan_at else None,
        "last_scan_batch_id": scan_path.last_scan_batch_id,
        "created_at": scan_path.created_at.isoformat() if scan_path.created_at else None,
        "updated_at": scan_path.updated_at.isoformat() if scan_path.updated_at else None
    }


@router.delete("/paths/{path_id}")
async def delete_scan_path(
    path_id: int,
    db: Session = Depends(get_db)
):
    """
    删除扫描路径

    - **path_id**: 路径ID
    """
    scan_path = db.query(ScanPath).filter(ScanPath.id == path_id).first()
    if not scan_path:
        raise HTTPException(status_code=404, detail="扫描路径不存在")

    path_str = scan_path.path
    db.delete(scan_path)
    db.commit()

    logger.info(f"删除扫描路径: {path_str}")

    return {"message": "扫描路径已删除"}


# ========== 扫描任务管理 ==========


class TaskCreateRequest(BaseModel):
    """创建扫描任务请求"""
    path_id: Optional[int] = None
    path: Optional[str] = None
    recursive: bool = True
    scan_type: str = "incremental"  # full / incremental


@router.post("/tasks")
async def create_scan_task(
    request: TaskCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    创建扫描任务

    - **path_id**: 扫描路径ID（与path二选一）
    - **path**: 扫描路径（与path_id二选一）
    - **recursive**: 是否递归扫描
    - **scan_type**: 扫描类型 (incremental/full)
    """
    # 确定扫描路径
    scan_path = None
    if request.path_id:
        # 使用路径ID
        scan_path = db.query(ScanPath).filter(ScanPath.id == request.path_id).first()
        if not scan_path:
            raise HTTPException(status_code=404, detail="扫描路径不存在")
        if not scan_path.enabled:
            raise HTTPException(status_code=400, detail="扫描路径未启用")
        target_path = scan_path.path
        recursive = scan_path.recursive if request.recursive is None else request.recursive
    elif request.path:
        # 使用直接路径
        target_path = request.path
        recursive = request.recursive
    else:
        raise HTTPException(status_code=400, detail="必须指定path_id或path")

    # 验证路径
    from pathlib import Path
    path_obj = Path(target_path)
    if not path_obj.exists():
        raise HTTPException(status_code=404, detail="扫描路径不存在")
    if not path_obj.is_dir():
        raise HTTPException(status_code=400, detail="扫描路径不是目录")

    # 生成批次ID
    import uuid
    batch_id = str(uuid.uuid4())

    # 创建扫描历史记录（初始状态）
    scan_history = ScanHistory(
        batch_id=batch_id,
        target_path=target_path,
        scan_type=request.scan_type,
        recursive=recursive,
        started_at=datetime.now()
    )
    db.add(scan_history)
    db.commit()
    
    task_id = scan_history.id

    # 创建扫描进度记录
    scan_progress = ScanProgress(
        batch_id=batch_id,
        task_id=task_id,
        target_path=target_path,
        scan_type=request.scan_type,
        status="pending",
        started_at=datetime.now()
    )
    db.add(scan_progress)
    db.commit()

    # 创建扫描器实例
    scanner = FileScanner(task_id=task_id, batch_id=batch_id)

    # 在后台任务中执行扫描
    async def scan_task():
        try:
            # 更新状态为运行中
            with get_db_context() as db:
                db.query(ScanProgress).filter_by(batch_id=batch_id).update({
                    "status": "running"
                })
                db.commit()
            
            await manager.send_progress(task_id, {
                "batch_id": batch_id,
                "task_id": task_id,
                "status": "running"
            })
            
            scan_history = await scanner.scan_directory(
                path=target_path,
                recursive=recursive,
                scan_type=request.scan_type,
                batch_id=batch_id
            )
            logger.info(f"扫描任务完成: {batch_id}")

            # 更新扫描路径的最后扫描时间
            if request.path_id:
                with get_db_context() as db:
                    db.query(ScanPath).filter(ScanPath.id == request.path_id).update({
                        "last_scan_at": datetime.now(),
                        "last_scan_batch_id": batch_id
                    })
                    db.commit()
        except Exception as e:
            logger.error(f"扫描任务失败: {batch_id}, 错误: {e}")
            # 更新扫描历史记录的错误信息
            with get_db_context() as db:
                db.query(ScanHistory).filter(ScanHistory.batch_id == batch_id).update({
                    "error_message": str(e),
                    "completed_at": datetime.now()
                })
                db.commit()

    # 添加后台任务
    background_tasks.add_task(scan_task)

    return {
        "task_id": scan_history.id,
        "batch_id": batch_id,
        "status": "accepted",
        "message": "扫描任务已创建，正在后台执行"
    }


@router.post("/tasks/{task_id}/stop")
async def stop_scan_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    停止扫描任务

    - **task_id**: 任务ID
    """
    task = db.query(ScanHistory).filter(ScanHistory.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="扫描任务不存在")

    if task.completed_at:
        raise HTTPException(status_code=400, detail="任务已完成或已停止")

    # 标记任务为已停止
    task.completed_at = datetime.now()
    task.error_message = "任务被用户停止"
    db.commit()

    logger.info(f"停止扫描任务: {task_id}")

    return {"message": "扫描任务已停止"}


@router.post("/tasks/{task_id}/retry")
async def retry_scan_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    重新扫描任务（仅对选中任务涉及的文件进行重新扫描）

    - **task_id**: 任务ID
    """
    original_task = db.query(ScanHistory).filter(ScanHistory.id == task_id).first()
    if not original_task:
        raise HTTPException(status_code=404, detail="扫描任务不存在")

    # 查询该任务扫描到的所有文件
    scanned_files = db.query(MediaFile).filter(
        MediaFile.scan_batch_id == original_task.batch_id
    ).all()
    
    if not scanned_files:
        raise HTTPException(status_code=404, detail="该任务没有扫描到任何文件")

    # 生成新的批次ID
    import uuid
    batch_id = str(uuid.uuid4())

    # 创建扫描历史记录
    scan_history = ScanHistory(
        batch_id=batch_id,
        target_path=original_task.target_path,
        scan_type="rescan",  # 使用重新扫描类型
        recursive=original_task.recursive,
        started_at=datetime.now()
    )
    db.add(scan_history)
    db.commit()

    # 创建新的扫描任务
    scanner = FileScanner()
    
    # 初始化扫描器属性
    scanner.batch_id = batch_id
    scanner.task_id = scan_history.id
    scanner.scanned_files = set()
    scanner.new_files = []
    scanner.updated_files = []
    scanner.failed_files = []
    scanner.skipped_files = 0
    scanner.total_files = len(scanned_files)

    # 在后台任务中执行扫描
    def scan_task():
        try:
            # 只对选中任务涉及的文件进行重新扫描
            for media_file in scanned_files:
                file_path = Path(media_file.file_path)
                if file_path.exists():
                    # 重新处理文件
                    scanner._process_media_file(file_path, "rescan")
            
            # 更新扫描历史记录
            with get_db_context() as db:
                db.query(ScanHistory).filter(ScanHistory.batch_id == batch_id).update({
                    "total_files": len(scanned_files),
                    "new_files": 0,  # 重新扫描不算新增
                    "updated_files": len(scanner.updated_files),
                    "skipped_files": 0,
                    "failed_files": len(scanner.failed_files),
                    "completed_at": datetime.now()
                })
                db.commit()
            
            logger.info(f"重新扫描任务完成: {batch_id}, 共处理 {len(scanned_files)} 个文件")
        except Exception as e:
            logger.error(f"重新扫描任务失败: {batch_id}, 错误: {e}")
            # 更新扫描历史记录的错误信息
            with get_db_context() as db:
                db.query(ScanHistory).filter(ScanHistory.batch_id == batch_id).update({
                    "error_message": str(e),
                    "completed_at": datetime.now()
                })
                db.commit()

    # 添加后台任务
    background_tasks.add_task(scan_task)

    return {
        "task_id": scan_history.id,
        "batch_id": batch_id,
        "status": "accepted",
        "message": f"重新扫描任务已创建，将对 {len(scanned_files)} 个文件进行重新扫描"
    }


@router.delete("/tasks/{task_id}")
async def delete_scan_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    删除扫描任务

    - **task_id**: 任务ID
    """
    task = db.query(ScanHistory).filter(ScanHistory.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="扫描任务不存在")

    # 检查任务是否正在运行
    if not task.completed_at:
        raise HTTPException(status_code=400, detail="无法删除正在运行的扫描任务")

    # 删除关联的扫描进度记录
    db.query(ScanProgress).filter(ScanProgress.task_id == task_id).delete()
    
    # 删除扫描任务记录
    db.delete(task)
    db.commit()

    logger.info(f"删除扫描任务: {task_id}")

    return {"message": "扫描任务已删除"}


@router.get("/history")
async def get_scan_history(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    获取扫描历史

    - **limit**: 返回数量限制
    - **offset**: 偏移量
    """
    history = db.query(ScanHistory).order_by(
        ScanHistory.started_at.desc()
    ).offset(offset).limit(limit).all()

    return {
        "items": [
            {
                "id": h.id,
                "batch_id": h.batch_id,
                "target_path": h.target_path,
                "scan_type": h.scan_type,
                "recursive": h.recursive,
                "total_files": h.total_files,
                "new_files": h.new_files,
                "updated_files": h.updated_files,
                "skipped_files": h.skipped_files,
                "failed_files": h.failed_files,
                "duration_seconds": h.duration_seconds,
                "error_message": h.error_message,
                "started_at": h.started_at.isoformat() if h.started_at else None,
                "completed_at": h.completed_at.isoformat() if h.completed_at else None,
                "status": "completed" if h.completed_at else "running"
            }
            for h in history
        ],
        "total": len(history)
    }


@router.get("/history/{batch_id}")
async def get_scan_history_detail(
    batch_id: str,
    db: Session = Depends(get_db)
):
    """
    获取扫描历史详情

    - **batch_id**: 批次ID
    """
    history = db.query(ScanHistory).filter(ScanHistory.batch_id == batch_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="扫描历史不存在")

    # 获取该批次扫描的文件
    files = db.query(MediaFile).filter(MediaFile.scan_batch_id == batch_id).all()

    return {
        "id": history.id,
        "batch_id": history.batch_id,
        "target_path": history.target_path,
        "scan_type": history.scan_type,
        "recursive": history.recursive,
        "total_files": history.total_files,
        "new_files": history.new_files,
        "updated_files": history.updated_files,
        "skipped_files": history.skipped_files,
        "failed_files": history.failed_files,
        "duration_seconds": history.duration_seconds,
        "error_message": history.error_message,
        "started_at": history.started_at.isoformat() if history.started_at else None,
        "completed_at": history.completed_at.isoformat() if history.completed_at else None,
        "status": "completed" if history.completed_at else "running",
        "files": [
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
    }


# ========== 扫描进度查询 ==========


@router.get("/tasks/{task_id}/progress")
async def get_scan_progress(
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    获取扫描任务进度

    - **task_id**: 任务ID
    """
    task = db.query(ScanHistory).filter(ScanHistory.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="扫描任务不存在")

    # 获取已扫描的文件数
    scanned_count = db.query(MediaFile).filter(
        MediaFile.scan_batch_id == task.batch_id
    ).count()

    # 计算进度
    progress = 0
    if task.total_files and task.total_files > 0:
        progress = (scanned_count / task.total_files) * 100

    return {
        "task_id": task.id,
        "batch_id": task.batch_id,
        "status": "completed" if task.completed_at else "running",
        "total_files": task.total_files,
        "scanned_files": scanned_count,
        "new_files": task.new_files,
        "updated_files": task.updated_files,
        "skipped_files": task.skipped_files,
        "failed_files": task.failed_files,
        "progress": round(progress, 2),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "duration_seconds": task.duration_seconds,
        "error_message": task.error_message
    }


# ========== 原有接口保持兼容 ==========


@router.post("/trigger")
async def trigger_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks
):
    """
    手动触发扫描（兼容接口）

    - **path**: 扫描目录路径
    - **recursive**: 是否递归扫描
    - **scan_type**: 扫描类型 (incremental/full)
    """
    try:
        # 创建扫描器实例
        scanner = FileScanner()

        # 生成批次ID
        import uuid
        batch_id = str(uuid.uuid4())

        # 在后台任务中执行扫描
        def scan_task():
            try:
                scan_history = scanner.scan_directory(
                    path=request.path,
                    recursive=request.recursive,
                    scan_type=request.scan_type,
                    batch_id=batch_id
                )
                logger.info(f"扫描任务完成: {batch_id}")
            except Exception as e:
                logger.error(f"扫描任务失败: {e}")

        # 添加后台任务
        background_tasks.add_task(scan_task)

        return ScanResponse(
            task_id=batch_id,
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
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    获取扫描任务列表（兼容接口）

    - **limit**: 返回数量限制
    - **offset**: 偏移量
    """
    tasks = db.query(ScanHistory).order_by(
        ScanHistory.started_at.desc()
    ).offset(offset).limit(limit).all()

    return {
        "items": [
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
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "status": "completed" if task.completed_at else "running"
            }
            for task in tasks
        ],
        "total": len(tasks)
    }


@router.get("/tasks/{task_id}")
async def get_scan_task_detail(
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    获取扫描任务详情（兼容接口）

    - **task_id**: 任务ID
    """
    task = db.query(ScanHistory).filter(ScanHistory.id == task_id).first()

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
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    获取待识别文件列表

    - **limit**: 返回数量限制
    - **offset**: 偏移量
    """
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
