
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
    path_name: Optional[str] = None  # 路径名称
    scan_type: str = "incremental"  # full/incremental
    recursive: bool = True
    scan_interval: int = 300  # 扫描间隔（秒）
    monitoring_enabled: bool = True  # 是否启用监控
    monitoring_debounce: int = 5  # 监控防抖延迟（秒）
    ignore_patterns: Optional[List[str]] = None  # 忽略文件模式列表
    enabled: bool = True


class ScanPathUpdate(BaseModel):
    """更新扫描路径请求"""
    path: Optional[str] = None
    path_name: Optional[str] = None  # 路径名称
    scan_type: Optional[str] = None  # full/incremental
    recursive: Optional[bool] = None
    scan_interval: Optional[int] = None  # 扫描间隔（秒）
    monitoring_enabled: Optional[bool] = None  # 是否启用监控
    monitoring_debounce: Optional[int] = None  # 监控防抖延迟（秒）
    ignore_patterns: Optional[List[str]] = None  # 忽略文件模式列表
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
            "path_name": path.path_name,
            "scan_type": path.scan_type,
            "recursive": path.recursive,
            "scan_interval": path.scan_interval,
            "monitoring_enabled": path.monitoring_enabled,
            "monitoring_debounce": path.monitoring_debounce,
            "ignore_patterns": path.ignore_patterns,
            "enabled": path.enabled,
            "last_scan_at": path.last_scan_at.isoformat() if path.last_scan_at else None,
            "last_scan_batch_id": path.last_scan_batch_id,
            "total_scans": path.total_scans,
            "total_files_found": path.total_files_found,
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
        path_name=path_data.path_name,
        scan_type=path_data.scan_type,
        recursive=path_data.recursive,
        scan_interval=path_data.scan_interval,
        monitoring_enabled=path_data.monitoring_enabled,
        monitoring_debounce=path_data.monitoring_debounce,
        ignore_patterns=path_data.ignore_patterns,
        enabled=path_data.enabled
    )
    db.add(scan_path)
    db.commit()
    db.refresh(scan_path)

    logger.info(f"添加扫描路径: {path_data.path}")

    return {
        "id": scan_path.id,
        "path": scan_path.path,
        "path_name": scan_path.path_name,
        "scan_type": scan_path.scan_type,
        "recursive": scan_path.recursive,
        "scan_interval": scan_path.scan_interval,
        "monitoring_enabled": scan_path.monitoring_enabled,
        "monitoring_debounce": scan_path.monitoring_debounce,
        "ignore_patterns": scan_path.ignore_patterns,
        "enabled": scan_path.enabled,
        "last_scan_at": scan_path.last_scan_at.isoformat() if scan_path.last_scan_at else None,
        "last_scan_batch_id": scan_path.last_scan_batch_id,
        "total_scans": scan_path.total_scans,
        "total_files_found": scan_path.total_files_found,
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

    if path_data.path_name is not None:
        scan_path.path_name = path_data.path_name
    if path_data.scan_type is not None:
        scan_path.scan_type = path_data.scan_type
    if path_data.recursive is not None:
        scan_path.recursive = path_data.recursive
    if path_data.scan_interval is not None:
        scan_path.scan_interval = path_data.scan_interval
    if path_data.monitoring_enabled is not None:
        scan_path.monitoring_enabled = path_data.monitoring_enabled
    if path_data.monitoring_debounce is not None:
        scan_path.monitoring_debounce = path_data.monitoring_debounce
    if path_data.ignore_patterns is not None:
        scan_path.ignore_patterns = path_data.ignore_patterns
    if path_data.enabled is not None:
        scan_path.enabled = path_data.enabled

    scan_path.updated_at = datetime.now()
    db.commit()
    db.refresh(scan_path)

    logger.info(f"更新扫描路径: {path_id}")

    return {
        "id": scan_path.id,
        "path": scan_path.path,
        "path_name": scan_path.path_name,
        "scan_type": scan_path.scan_type,
        "recursive": scan_path.recursive,
        "scan_interval": scan_path.scan_interval,
        "monitoring_enabled": scan_path.monitoring_enabled,
        "monitoring_debounce": scan_path.monitoring_debounce,
        "ignore_patterns": scan_path.ignore_patterns,
        "enabled": scan_path.enabled,
        "last_scan_at": scan_path.last_scan_at.isoformat() if scan_path.last_scan_at else None,
        "last_scan_batch_id": scan_path.last_scan_batch_id,
        "total_scans": scan_path.total_scans,
        "total_files_found": scan_path.total_files_found,
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


# ========== 默认扫描策略配置 ==========

from app.core.config import config_manager


@router.get("/config/default")
async def get_default_scan_config():
    """
    获取默认扫描策略配置
    """
    try:
        config = config_manager.get("scanner", {})
        
        default_config = {
            "default_scan_type": config.get("default_scan_type", "full"),
            "default_recursive": config.get("default_recursive", True),
            "default_skip_mode": config.get("default_skip_mode", "keyword"),
            "default_ignore_patterns": config.get("default_ignore_patterns", [])
        }
        
        return default_config
    except Exception as e:
        logger.error(f"获取默认扫描策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.put("/config/default")
async def update_default_scan_config(
    default_scan_type: Optional[str] = None,
    default_recursive: Optional[bool] = None,
    default_skip_mode: Optional[str] = None,
    default_ignore_patterns: Optional[List[str]] = None
):
    """
    更新默认扫描策略配置
    """
    try:
        # 获取当前scanner配置
        config = config_manager.get("scanner", {})
        
        # 更新配置项
        if default_scan_type is not None:
            config["default_scan_type"] = default_scan_type
        if default_recursive is not None:
            config["default_recursive"] = default_recursive
        if default_skip_mode is not None:
            config["default_skip_mode"] = default_skip_mode
        if default_ignore_patterns is not None:
            config["default_ignore_patterns"] = default_ignore_patterns
        
        # 保存配置
        config_manager.set("scanner", config)
        
        logger.info(f"更新默认扫描策略: {config}")
        return {"message": "配置已更新"}
    except Exception as e:
        logger.error(f"更新默认扫描策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")

@router.post("/config/default/reset")
async def reset_default_scan_config():
    """
    重置默认扫描策略为系统默认值
    """
    try:
        # 重置为系统默认值
        default_config = {
            "default_scan_type": "full",
            "default_recursive": True,
            "default_skip_mode": "keyword",
            "default_ignore_patterns": []
        }
        
        # 保存配置
        config_manager.set("scanner", default_config)
        
        logger.info("重置默认扫描策略为系统默认值")
        return {"message": "配置已重置"}
    except Exception as e:
        logger.error(f"重置默认扫描策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置配置失败: {str(e)}")


# ========== 扫描任务管理 ==========


class TaskCreateRequest(BaseModel):
    """创建扫描任务请求"""
    path_id: Optional[int] = None
    path: Optional[str] = None
    recursive: bool = True
    scan_type: str = "incremental"  # full / incremental
    skip_mode: str = "keyword"  # keyword/record/none


class RescanOptions(BaseModel):
    """重新扫描选项"""
    rescan_type: str = "all"  # all/failed/selected
    file_list: List[str] = []  # 仅rescan_type=selected时使用
    force_update: bool = True
    skip_keywords: bool = True
    skip_scanned: bool = False
    use_ignore_patterns: bool = True


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
    scanner = FileScanner(task_id=task_id, batch_id=batch_id, skip_mode=request.skip_mode)

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
    停止扫描任务（等待实际停止）

    - **task_id**: 任务ID
    """
    import time
    
    task = db.query(ScanHistory).filter(ScanHistory.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="扫描任务不存在")

    if task.completed_at:
        raise HTTPException(status_code=400, detail="任务已完成或已停止")

    # 标记任务为停止中
    stop_requested_at = datetime.now()
    
    # 更新扫描进度状态为停止中
    with get_db_context() as progress_db:
        progress_db.query(ScanProgress).filter_by(task_id=task_id).update({
            "status": "stopping"
        })
        progress_db.commit()

    logger.info(f"请求停止扫描任务: {task_id} at {stop_requested_at}")

    # 等待实际停止
    timeout_seconds = 60
    elapsed = 0
    check_interval = 1  # 每秒检查一次

    while elapsed < timeout_seconds:
        # 刷新任务状态
        db.refresh(task)
        
        # 检查任务是否已完成
        if task.completed_at:
            stop_time = task.completed_at
            stop_duration = int((stop_time - stop_requested_at).total_seconds())
            
            # 更新扫描进度为已停止
            with get_db_context() as progress_db:
                progress_db.query(ScanProgress).filter_by(task_id=task_id).update({
                    "status": "stopped",
                    "completed_at": stop_time
                })
                progress_db.commit()
            
            logger.info(f"扫描任务已停止: {task_id}, 耗时: {stop_duration}秒")
            
            return {
                "success": True,
                "message": "扫描任务已停止",
                "stop_time": stop_time.isoformat(),
                "stop_duration": stop_duration
            }
        
        # 等待一段时间再检查
        time.sleep(check_interval)
        elapsed += check_interval

    # 超时处理
    logger.warning(f"停止任务超时: {task_id}, 已等待{timeout_seconds}秒")
    
    # 返回部分成功
    return {
        "success": False,
        "message": "停止请求已发送，但任务可能仍在运行中", 
        "stop_requested_at": stop_requested_at.isoformat(),
        "timeout": timeout_seconds
    }


@router.post("/tasks/{task_id}/retry")
async def retry_scan_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    options: RescanOptions = None
):
    # 如果没有提供 options，使用默认值
    if options is None:
        options = RescanOptions()
    """
    重新扫描任务（仅对选中任务涉及的文件进行重新扫描）

    - **task_id**: 任务ID
    - **options**: 重新扫描选项
    """
    original_task = db.query(ScanHistory).filter(ScanHistory.id == task_id).first()
    if not original_task:
        raise HTTPException(status_code=404, detail="扫描任务不存在")

    # 查询该任务扫描到的所有文件
    scanned_files = db.query(MediaFile).filter(
        MediaFile.scan_batch_id == original_task.batch_id
    ).all()
    
    if not scanned_files:
        # 如果没有扫描到任何文件，重新执行完整扫描
        logger.info(f"任务 {task_id} 没有扫描到任何文件，重新执行完整扫描")

        # 生成新的批次ID
        import uuid
        batch_id = str(uuid.uuid4())

        # 创建扫描历史记录
        scan_history = ScanHistory(
            batch_id=batch_id,
            target_path=original_task.target_path,
            scan_type="full",
            recursive=original_task.recursive,
            started_at=datetime.now()
        )
        db.add(scan_history)
        db.commit()

        # 创建扫描进度记录
        scan_progress = ScanProgress(
            batch_id=batch_id,
            task_id=scan_history.id,
            target_path=original_task.target_path,
            scan_type="full",
            status="pending",
            started_at=datetime.now()
        )
        db.add(scan_progress)
        db.commit()

        # 创建扫描器实例
        # 根据 RescanOptions 确定跳过模式
        skip_mode = "none"
        if options.skip_keywords and options.skip_scanned:
            skip_mode = "record"
        elif options.skip_keywords:
            skip_mode = "keyword"

        scanner = FileScanner(task_id=scan_history.id, batch_id=batch_id, skip_mode=skip_mode)

        # 在后台任务中执行扫描
        async def scan_task():
            try:
                # 更新状态为运行中
                with get_db_context() as db:
                    db.query(ScanProgress).filter_by(batch_id=batch_id).update({
                        "status": "running"
                    })
                    db.commit()

                await manager.send_progress(scan_history.id, {
                    "batch_id": batch_id,
                    "task_id": scan_history.id,
                    "status": "running"
                })

                await scanner.scan_directory(
                    path=original_task.target_path,
                    recursive=original_task.recursive,
                    scan_type="full",
                    batch_id=batch_id
                )
                logger.info(f"重新扫描任务完成: {batch_id}")
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
            "message": "重新扫描任务已创建，正在后台执行"
        }

    # 根据重新扫描选项过滤文件
    files_to_rescan = []
    if options.rescan_type == "all":
        # 重新扫描所有文件
        files_to_rescan = scanned_files
    elif options.rescan_type == "failed":
        # 仅重新扫描失败的文件（假设未扫描的文件为失败）
        files_to_rescan = [f for f in scanned_files if not f.scanned_at]
    elif options.rescan_type == "selected":
        # 仅重新扫描指定的文件
        files_to_rescan = [f for f in scanned_files if f.file_path in options.file_list]
    else:
        files_to_rescan = scanned_files

    if not files_to_rescan:
        raise HTTPException(status_code=404, detail="没有符合条件的文件需要重新扫描")

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
    scanner.total_files = len(files_to_rescan)

    # 在后台任务中执行扫描
    def scan_task():
        try:
            # 只对选中任务涉及的文件进行重新扫描
            for media_file in files_to_rescan:
                file_path = Path(media_file.file_path)
                if file_path.exists():
                    # 重新处理文件
                    scanner._process_media_file(file_path, "rescan")
            
            # 更新扫描历史记录
            with get_db_context() as db:
                db.query(ScanHistory).filter(ScanHistory.batch_id == batch_id).update({
                    "total_files": len(files_to_rescan),
                    "new_files": 0,  # 重新扫描不算新增
                    "updated_files": len(scanner.updated_files),
                    "skipped_files": 0,
                    "failed_files": len(scanner.failed_files),
                    "completed_at": datetime.now()
                })
                db.commit()
            
            logger.info(f"重新扫描任务完成: {batch_id}, 共处理 {len(files_to_rescan)} 个文件")
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
        "message": f"重新扫描任务已创建，将对 {len(files_to_rescan)} 个文件进行重新扫描"
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


# ========== 文件系统监控 ==========


# 全局监控器字典: path_id -> FileMonitor
_monitors = {}


@router.post("/monitoring/{path_id}/start")
async def start_monitoring(
    path_id: int,
    db: Session = Depends(get_db)
):
    """
    启动文件系统监控

    - **path_id**: 扫描路径ID
    """
    # 查询扫描路径
    scan_path = db.query(ScanPath).filter(ScanPath.id == path_id).first()
    if not scan_path:
        raise HTTPException(status_code=404, detail="扫描路径不存在")
    
    if not scan_path.enabled:
        raise HTTPException(status_code=400, detail="扫描路径未启用")
    
    # 检查监控是否已在运行
    if path_id in _monitors:
        raise HTTPException(status_code=400, detail="该路径的监控已在运行")
    
    try:
        # 导入文件监控模块
        from app.modules.scanner.file_monitor import FileMonitor
        
        # 定义监控回调函数
        def on_file_change(event_type: str, file_path: str):
            """文件变化回调"""
            logger.info(f"监控到文件变化: {event_type} - {file_path}")
            
            # TODO: 根据变化类型触发相应的扫描或处理
            # 例如：
            # - created: 创建新文件，触发扫描
            # - modified: 文件修改，触发重新识别
            # - deleted: 文件删除，更新数据库
        
        # 创建监控器
        monitor = FileMonitor(
            path=scan_path.path,
            callback=on_file_change,
            debounce_seconds=scan_path.monitoring_debounce if hasattr(scan_path, 'monitoring_debounce') else 5
        )
        
        # 启动监控
        monitor.start()
        
        # 保存监控器
        _monitors[path_id] = monitor
        
        logger.info(f"已启动文件系统监控: path_id={path_id}, path={scan_path.path}")
        
        return {
            "success": True,
            "message": "文件系统监控已启动",
            "path_id": path_id,
            "path": scan_path.path
        }
    
    except Exception as e:
        logger.error(f"启动文件系统监控失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动监控失败: {str(e)}")


@router.post("/monitoring/{path_id}/stop")
async def stop_monitoring(
    path_id: int,
    db: Session = Depends(get_db)
):
    """
    停止文件系统监控

    - **path_id**: 扫描路径ID
    """
    # 查询扫描路径
    scan_path = db.query(ScanPath).filter(ScanPath.id == path_id).first()
    if not scan_path:
        raise HTTPException(status_code=404, detail="扫描路径不存在")
    
    # 检查监控是否在运行
    if path_id not in _monitors:
        raise HTTPException(status_code=400, detail="该路径的监控未在运行")
    
    try:
        # 停止监控器
        monitor = _monitors[path_id]
        monitor.stop()
        
        # 从监控器字典中移除
        del _monitors[path_id]
        
        logger.info(f"已停止文件系统监控: path_id={path_id}, path={scan_path.path}")
        
        return {
            "success": True,
            "message": "文件系统监控已停止",
            "path_id": path_id
        }
    
    except Exception as e:
        logger.error(f"停止文件系统监控失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止监控失败: {str(e)}")


@router.get("/monitoring/{path_id}/status")
async def get_monitoring_status(
    path_id: int,
    db: Session = Depends(get_db)
):
    """
    获取文件系统监控状态

    - **path_id**: 扫描路径ID
    """
    # 查询扫描路径
    scan_path = db.query(ScanPath).filter(ScanPath.id == path_id).first()
    if not scan_path:
        raise HTTPException(status_code=404, detail="扫描路径不存在")
    
    # 检查监控状态
    is_running = path_id in _monitors
    is_alive = False
    
    if is_running:
        is_alive = _monitors[path_id].is_alive()
    
    return {
        "path_id": path_id,
        "path": scan_path.path,
        "is_running": is_running,
        "is_alive": is_alive,
        "monitoring_enabled": getattr(scan_path, 'monitoring_enabled', False),
        "monitoring_debounce": getattr(scan_path, 'monitoring_debounce', 5)
    }


@router.get("/monitoring")
async def list_monitoring_status(db: Session = Depends(get_db)):
    """
    获取所有路径的监控状态
    """
    paths = db.query(ScanPath).all()
    
    status_list = []
    for path in paths:
        is_running = path.id in _monitors
        is_alive = False
        
        if is_running:
            is_alive = _monitors[path.id].is_alive()
        
        status_list.append({
            "path_id": path.id,
            "path": path.path,
            "is_running": is_running,
            "is_alive": is_alive,
            "monitoring_enabled": getattr(path, 'monitoring_enabled', False),
            "monitoring_debounce": getattr(path, 'monitoring_debounce', 5)
        })
    
    return {
        "total": len(status_list),
        "running": sum(1 for s in status_list if s["is_running"]),
        "items": status_list
    }


# ========== 批量操作 ==========


class BatchStopRequest(BaseModel):
    """批量停止任务请求"""
    task_ids: List[int]


@router.post("/tasks/batch/stop")
async def batch_stop_tasks(
    request: BatchStopRequest,
    db: Session = Depends(get_db)
):
    """
    批量停止扫描任务

    - **task_ids**: 任务ID列表
    """
    import time
    
    results = []
    
    for task_id in request.task_ids:
        try:
            task = db.query(ScanHistory).filter(ScanHistory.id == task_id).first()
            if not task:
                results.append({
                    "task_id": task_id,
                    "success": False,
                    "message": "任务不存在"
                })
                continue
            
            if task.completed_at:
                results.append({
                    "task_id": task_id,
                    "success": False,
                    "message": "任务已完成或已停止"
                })
                continue
            
            # 标记任务为停止中
            stop_requested_at = datetime.now()
            
            # 更新扫描进度状态为停止中
            with get_db_context() as progress_db:
                progress_db.query(ScanProgress).filter_by(task_id=task_id).update({
                    "status": "stopping"
                })
                progress_db.commit()
            
            logger.info(f"请求停止扫描任务: {task_id} at {stop_requested_at}")
            
            # 等待实际停止
            timeout_seconds = 60
            elapsed = 0
            check_interval = 1
            
            stopped = False
            while elapsed < timeout_seconds:
                db.refresh(task)
                if task.completed_at:
                    stop_time = task.completed_at
                    stop_duration = int((stop_time - stop_requested_at).total_seconds())
                    
                    # 更新扫描进度为已停止
                    with get_db_context() as progress_db:
                        progress_db.query(ScanProgress).filter_by(task_id=task_id).update({
                            "status": "stopped",
                            "completed_at": stop_time
                        })
                        progress_db.commit()
                    
                    logger.info(f"扫描任务已停止: {task_id}, 耗时: {stop_duration}秒")
                    
                    results.append({
                        "task_id": task_id,
                        "success": True,
                        "message": "扫描任务已停止",
                        "stop_time": stop_time.isoformat(),
                        "stop_duration": stop_duration
                    })
                    stopped = True
                    break
                
                time.sleep(check_interval)
                elapsed += check_interval
            
            if not stopped:
                logger.warning(f"停止任务超时: {task_id}, 已等待{timeout_seconds}秒")
                results.append({
                    "task_id": task_id,
                    "success": False,
                    "message": "停止请求已发送，但任务可能仍在运行中",
                    "stop_requested_at": stop_requested_at.isoformat(),
                    "timeout": timeout_seconds
                })
        
        except Exception as e:
            logger.error(f"批量停止任务失败: {task_id}, 错误: {e}")
            results.append({
                "task_id": task_id,
                "success": False,
                "message": f"停止失败: {str(e)}"
            })
    
    return {
        "total": len(request.task_ids),
        "success": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }


class BatchDeleteRequest(BaseModel):
    """批量删除任务请求"""
    task_ids: List[int]


@router.delete("/tasks/batch")
async def batch_delete_tasks(
    request: BatchDeleteRequest,
    db: Session = Depends(get_db)
):
    """
    批量删除扫描任务

    - **task_ids**: 任务ID列表
    """
    results = []
    
    for task_id in request.task_ids:
        try:
            task = db.query(ScanHistory).filter(ScanHistory.id == task_id).first()
            if not task:
                results.append({
                    "task_id": task_id,
                    "success": False,
                    "message": "任务不存在"
                })
                continue
            
            # 检查任务是否正在运行
            if not task.completed_at:
                results.append({
                    "task_id": task_id,
                    "success": False,
                    "message": "无法删除正在运行的扫描任务"
                })
                continue
            
            # 删除关联的扫描进度记录
            db.query(ScanProgress).filter(ScanProgress.task_id == task_id).delete()
            
            # 删除扫描任务记录
            db.delete(task)
            db.commit()
            
            logger.info(f"删除扫描任务: {task_id}")
            
            results.append({
                "task_id": task_id,
                "success": True,
                "message": "扫描任务已删除"
            })
        
        except Exception as e:
            logger.error(f"批量删除任务失败: {task_id}, 错误: {e}")
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


# ========== 默认扫描策略 ==========


class DefaultScanConfig(BaseModel):
    """默认扫描配置"""
    scan_type: str = "incremental"  # full/incremental
    recursive: bool = True
    skip_keywords: bool = True
    skip_scanned: bool = False
    use_ignore_patterns: bool = True
    monitoring_enabled: bool = False
    monitoring_debounce: int = 5


@router.get("/config/default")
async def get_default_scan_config():
    """
    获取默认扫描策略配置

    返回系统默认的扫描策略配置
    """
    return {
        "scan_type": "incremental",
        "recursive": True,
        "skip_keywords": True,
        "skip_scanned": False,
        "use_ignore_patterns": True,
        "monitoring_enabled": False,
        "monitoring_debounce": 5,
        "description": "默认扫描策略配置"
    }


@router.put("/config/default")
async def update_default_scan_config(config: DefaultScanConfig):
    """
    更新默认扫描策略配置

    - **scan_type**: 扫描类型 (full/incremental)
    - **recursive**: 是否递归扫描
    - **skip_keywords**: 是否跳过关键词库文件
    - **skip_scanned**: 是否跳过已扫描文件
    - **use_ignore_patterns**: 是否使用忽略模式
    - **monitoring_enabled**: 是否启用监控
    - **monitoring_debounce**: 监控防抖时间（秒）
    """
    # TODO: 将配置保存到数据库或配置文件
    logger.info(f"更新默认扫描策略: {config.dict()}")
    
    return {
        "message": "默认扫描策略已更新",
        "config": config.dict()
    }


@router.post("/config/default/reset")
async def reset_default_scan_config():
    """
    重置默认扫描策略为系统默认值

    将所有配置项恢复为系统默认值
    """
    default_config = {
        "scan_type": "incremental",
        "recursive": True,
        "skip_keywords": True,
        "skip_scanned": False,
        "use_ignore_patterns": True,
        "monitoring_enabled": False,
        "monitoring_debounce": 5
    }
    
    logger.info("重置默认扫描策略为系统默认值")
    
    return {
        "message": "默认扫描策略已重置",
        "config": default_config
    }


# ========== 扫描任务调度器 ==========


@router.get("/scheduler/status")
async def get_scheduler_status():
    """
    获取调度器状态

    返回调度器的运行状态和所有定时任务
    """
    from app.core.scheduler import scheduler
    
    return {
        "is_running": scheduler.is_running,
        "jobs": scheduler.get_scheduled_jobs(),
        "total_jobs": len(scheduler.get_scheduled_jobs())
    }


@router.post("/scheduler/start")
async def start_scheduler():
    """
    启动调度器

    启动扫描任务调度器，开始执行定时扫描任务
    """
    from app.core.scheduler import scheduler
    
    try:
        scheduler.start()
        return {
            "success": True,
            "message": "调度器已启动",
            "is_running": scheduler.is_running
        }
    except Exception as e:
        logger.error(f"启动调度器失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动调度器失败: {str(e)}")


@router.post("/scheduler/stop")
async def stop_scheduler():
    """
    停止调度器

    停止扫描任务调度器，暂停所有定时扫描任务
    """
    from app.core.scheduler import scheduler
    
    try:
        scheduler.stop()
        return {
            "success": True,
            "message": "调度器已停止",
            "is_running": scheduler.is_running
        }
    except Exception as e:
        logger.error(f"停止调度器失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止调度器失败: {str(e)}")


@router.get("/scheduler/jobs/{path_id}")
async def get_scheduled_job(path_id: int):
    """
    获取指定路径的定时任务状态

    - **path_id**: 扫描路径ID
    """
    from app.core.scheduler import scheduler
    
    job_status = scheduler.get_job_status(path_id)
    
    if not job_status:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    
    return job_status


# ========== 目录浏览 ==========


@router.get("/browse")
async def browse_directory(path: str = ""):
    """
    浏览服务器端目录

    - **path**: 要浏览的目录路径（空字符串表示根目录）
    """
    from pathlib import Path
    import platform

    # 获取系统根目录
    if not path:
        if platform.system() == "Windows":
            # Windows: 返回所有可用驱动器
            drives = []
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                drive = f"{letter}:\\"
                if Path(drive).exists():
                    drives.append({
                        "name": drive,
                        "path": drive,
                        "is_dir": True,
                        "size": 0,
                        "modified_time": None
                    })
            return drives
        else:
            # Unix-like: 返回根目录
            path = "/"
    
    # 规范化路径
    try:
        path_obj = Path(path)
    except (ValueError, OSError):
        raise HTTPException(status_code=400, detail="无效的路径")
    
    # 检查路径是否存在
    if not path_obj.exists():
        raise HTTPException(status_code=404, detail="路径不存在")
    
    # 检查是否是目录
    if not path_obj.is_dir():
        raise HTTPException(status_code=400, detail="不是目录")
    
    # 遍历目录内容
    items = []
    try:
        for entry in path_obj.iterdir():
            try:
                # 获取文件信息
                stat = entry.stat()
                name = entry.name
                is_dir = entry.is_dir()
                size = stat.st_size if not is_dir else 0
                
                # 获取修改时间
                from datetime import datetime
                modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()
                
                items.append({
                    "name": name,
                    "path": str(entry),
                    "is_dir": is_dir,
                    "size": size,
                    "modified_time": modified_time
                })
            except (PermissionError, OSError):
                # 跳过无权限访问的文件/目录
                continue
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问该目录")
    
    # 排序：目录在前，文件在后，名称按字母顺序
    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    
    return items
