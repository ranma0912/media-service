# -*- coding: utf-8 -*-
"""
扫描相关API接口 - v3重构版本
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, ConfigDict, field_validator, model_validator, BeforeValidator
from typing import Optional, List, Dict, Any, Union, Annotated
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session
from pathlib import Path

from app.modules.scanner.scan_manager import get_scan_manager
from app.db.models import ScanHistory, MediaFile, ScanPath, ScanProgress, FileTask, SubtitleFile
from app.db import get_db, get_db_context
from app.core.websocket import manager


router = APIRouter(tags=["扫描管理"])


def to_int_list(value: Any) -> List[int]:
    """将值转换为整数列表的验证函数"""
    if value is None:
        return []
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, int):
                result.append(item)
            elif isinstance(item, str):
                try:
                    result.append(int(item))
                except (ValueError, TypeError):
                    raise ValueError(f"无法将字符串 '{item}' 转换为整数")
            elif isinstance(item, float):
                result.append(int(item))
            else:
                raise ValueError(f"不支持的数据类型: {type(item)}")
        return result
    raise ValueError(f"预期的列表类型，得到: {type(value)}")


# 定义可接受int或str的列表类型
IntList = Annotated[List[int], BeforeValidator(to_int_list)]


# ========== 扫描请求/响应模型 ==========


class ManualScanRequest(BaseModel):
    """手动扫描请求"""
    path: str  # 扫描路径（使用路径ID或直接路径）
    use_default_strategy: bool = True  # 是否使用默认扫描策略
    scan_type: Optional[str] = None  # 扫描类型（use_default_strategy=False时必填）
    recursive: Optional[bool] = None  # 是否递归（use_default_strategy=False时必填）
    skip_strategy: Optional[str] = None  # 跳过策略（use_default_strategy=False时必填）


class ManualScanResponse(BaseModel):
    """手动扫描响应"""
    task_id: int
    batch_id: str
    status: str
    message: str


class DefaultScanConfigResponse(BaseModel):
    """默认扫描配置响应"""
    scan_type: str
    recursive: bool
    skip_strategy: str
    scan_subdirectories: bool
    scan_debounce_time: int
    monitoring_enabled: bool
    monitoring_mode: str
    monitoring_debounce: int
    auto_recognize: bool
    auto_organize: bool


class ScanPathConfigResponse(BaseModel):
    """扫描路径配置响应"""
    id: int
    path: str
    path_name: Optional[str]
    enabled: bool
    scan_type: str
    recursive: bool
    skip_strategy: str
    scan_subdirectories: bool
    scan_debounce_time: int
    monitoring_enabled: bool
    monitoring_mode: Optional[str]
    monitoring_debounce: int
    auto_recognize: bool
    auto_organize: bool
    ignore_patterns: Optional[List[str]]
    last_scan_at: Optional[str]
    last_scan_batch_id: Optional[str]
    total_scans: int
    total_files_found: int
    created_at: str
    updated_at: str


class FileTaskResponse(BaseModel):
    """文件任务响应"""
    id: int
    batch_id: Optional[str]
    media_file_id: int
    target_path: str
    file_name: str
    scan_type: Optional[str]
    recursive: Optional[bool]
    skip_strategy: Optional[str]
    status: str
    scan_progress: float
    scan_started_at: Optional[str]
    scan_completed_at: Optional[str]
    scan_error: Optional[str]
    video_tracks: int
    audio_tracks: int
    subtitle_tracks: int
    video_codec: Optional[str]
    audio_codec: Optional[str]
    has_external_subtitle: bool
    external_subtitle_name: Optional[str]
    scan_result: Optional[str]
    created_at: str
    updated_at: str


class ScanResultDetailResponse(BaseModel):
    """扫描结果详情响应"""
    file_name: str
    file_size: int
    file_type: str
    file_path: str
    scan_started_at: Optional[str]
    scan_completed_at: Optional[str]
    file_encoding_format: Optional[str]
    video_tracks: int
    audio_tracks: int
    subtitle_tracks: int
    has_external_subtitle: bool
    external_subtitle_name: Optional[str]
    scan_result: Optional[str]
    file_hash: Optional[str]
    scan_task_id: int
    video_codec: Optional[str]
    audio_codec: Optional[str]


# ========== 扫描触发 ==========


@router.post("/trigger", response_model=ManualScanResponse)
async def trigger_manual_scan(
    request: ManualScanRequest,
    background_tasks: BackgroundTasks
):
    """
    手动触发扫描
    
    - **path**: 扫描路径（可以是路径ID或直接路径）
    - **use_default_strategy**: 是否使用默认扫描策略
    - **scan_type**: 扫描类型（use_default_strategy=False时必填）
    - **recursive**: 是否递归（use_default_strategy=False时必填）
    - **skip_strategy**: 跳过策略（use_default_strategy=False时必填）
    """
    try:
        scan_manager = get_scan_manager()
        
        # 检查路径是否存在
        scan_path_obj = Path(request.path)
        if not scan_path_obj.exists():
            raise HTTPException(status_code=404, detail="扫描路径不存在")
        if not scan_path_obj.is_dir():
            raise HTTPException(status_code=400, detail="扫描路径不是目录")
        
        # 获取扫描策略
        if request.use_default_strategy:
            # 使用默认扫描策略
            from app.core.config import config_manager
            scanner_config = config_manager.get("scanner", {})
            
            scan_type = scanner_config.get("default_scan_type", "incremental")
            recursive = scanner_config.get("default_recursive", True)
            skip_strategy = scanner_config.get("default_skip_strategy", "keyword")
            scan_subdirectories = scanner_config.get("scan_subdirectories", True)
            scan_debounce_time = scanner_config.get("scan_debounce_time", 30)
        else:
            # 使用请求参数
            if not request.scan_type or not request.recursive or not request.skip_strategy:
                raise HTTPException(
                    status_code=400,
                    detail="use_default_strategy=False时，必须提供scan_type、recursive和skip_strategy参数"
                )
            
            scan_type = request.scan_type
            recursive = request.recursive
            skip_strategy = request.skip_strategy
            scan_subdirectories = True  # 默认值
            scan_debounce_time = 30  # 默认值
        
        # 启动扫描任务
        task_id = scan_manager.start_scan(
            target_path=request.path,
            scan_type=scan_type,
            recursive=recursive,
            skip_strategy=skip_strategy,
            scan_subdirectories=scan_subdirectories,
            scan_debounce_time=scan_debounce_time
        )
        
        # 获取批次ID
        with get_db_context() as db:
            task = db.query(ScanHistory).filter_by(id=task_id).first()
            batch_id = task.batch_id if task else ""
        
        return ManualScanResponse(
            task_id=task_id,
            batch_id=batch_id,
            status="accepted",
            message="扫描任务已启动"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"触发扫描失败: {e}")
        raise HTTPException(status_code=500, detail=f"扫描触发失败: {str(e)}")



# ========== 默认扫描策略配置 ==========


@router.get("/config/default", response_model=DefaultScanConfigResponse)
async def get_default_scan_config():
    """
    获取默认扫描策略配置
    """
    try:
        from app.core.config import config_manager
        scanner_config = config_manager.get("scanner", {})
        
        return DefaultScanConfigResponse(
            scan_type=scanner_config.get("default_scan_type", "incremental"),
            recursive=scanner_config.get("default_recursive", True),
            skip_strategy=scanner_config.get("default_skip_strategy", "keyword"),
            scan_subdirectories=scanner_config.get("scan_subdirectories", True),
            scan_debounce_time=scanner_config.get("scan_debounce_time", 30),
            monitoring_enabled=scanner_config.get("monitoring_enabled", False),
            monitoring_mode=scanner_config.get("monitoring_mode", "watchdog"),
            monitoring_debounce=scanner_config.get("monitoring_debounce", 5),
            auto_recognize=scanner_config.get("auto_recognize", False),
            auto_organize=scanner_config.get("auto_organize", False)
        )
    except Exception as e:
        logger.error(f"获取默认扫描策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.put("/config/default")
async def update_default_scan_config(
    scan_type: Optional[str] = None,
    recursive: Optional[bool] = None,
    skip_strategy: Optional[str] = None,
    scan_subdirectories: Optional[bool] = None,
    scan_debounce_time: Optional[int] = None,
    monitoring_enabled: Optional[bool] = None,
    monitoring_mode: Optional[str] = None,
    monitoring_debounce: Optional[int] = None,
    auto_recognize: Optional[bool] = None,
    auto_organize: Optional[bool] = None
):
    """
    更新默认扫描策略配置
    """
    try:
        from app.core.config import config_manager
        scanner_config = config_manager.get("scanner", {})
        
        # 更新配置项
        if scan_type is not None:
            scanner_config["default_scan_type"] = scan_type
        if recursive is not None:
            scanner_config["default_recursive"] = recursive
        if skip_strategy is not None:
            scanner_config["default_skip_strategy"] = skip_strategy
        if scan_subdirectories is not None:
            scanner_config["scan_subdirectories"] = scan_subdirectories
        if scan_debounce_time is not None:
            scanner_config["scan_debounce_time"] = scan_debounce_time
        if monitoring_enabled is not None:
            scanner_config["monitoring_enabled"] = monitoring_enabled
        if monitoring_mode is not None:
            scanner_config["monitoring_mode"] = monitoring_mode
        if monitoring_debounce is not None:
            scanner_config["monitoring_debounce"] = monitoring_debounce
        if auto_recognize is not None:
            scanner_config["auto_recognize"] = auto_recognize
        if auto_organize is not None:
            scanner_config["auto_organize"] = auto_organize
        
        # 保存配置
        config_manager.set("scanner", scanner_config)
        
        logger.info(f"更新默认扫描策略: {scanner_config}")
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
        from app.core.config import config_manager
        
        default_config = {
            "default_scan_type": "incremental",
            "default_recursive": True,
            "default_skip_strategy": "keyword",
            "scan_subdirectories": True,
            "scan_debounce_time": 30,
            "monitoring_enabled": False,
            "monitoring_mode": "watchdog",
            "monitoring_debounce": 5,
            "auto_recognize": False,
            "auto_organize": False
        }
        
        config_manager.set("scanner", default_config)
        
        logger.info("重置默认扫描策略为系统默认值")
        return {"message": "配置已重置"}
    except Exception as e:
        logger.error(f"重置默认扫描策略失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置配置失败: {str(e)}")


# ========== 扫描路径管理 ==========


class ScanPathCreate(BaseModel):
    """创建扫描路径请求"""
    path: str
    path_name: Optional[str] = None
    enabled: bool = True
    scan_type: str = "incremental"
    recursive: bool = True
    skip_strategy: str = "keyword"
    scan_subdirectories: bool = True
    scan_debounce_time: int = 30
    monitoring_enabled: bool = False
    monitoring_mode: str = "watchdog"
    monitoring_debounce: int = 5
    auto_recognize: bool = False
    auto_organize: bool = False
    ignore_patterns: Optional[List[str]] = None


class ScanPathUpdate(BaseModel):
    """更新扫描路径请求"""
    path: Optional[str] = None
    path_name: Optional[str] = None
    enabled: Optional[bool] = None
    scan_type: Optional[str] = None
    recursive: Optional[bool] = None
    skip_strategy: Optional[str] = None
    scan_subdirectories: Optional[bool] = None
    scan_debounce_time: Optional[int] = None
    monitoring_enabled: Optional[bool] = None
    monitoring_mode: Optional[str] = None
    monitoring_debounce: Optional[int] = None
    auto_recognize: Optional[bool] = None
    auto_organize: Optional[bool] = None
    ignore_patterns: Optional[List[str]] = None


@router.get("/paths", response_model=List[ScanPathConfigResponse])
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
        ScanPathConfigResponse(
            id=path.id,
            path=path.path,
            path_name=path.path_name,
            enabled=path.enabled,
            scan_type=path.scan_type,
            recursive=path.recursive,
            skip_strategy=path.skip_strategy,
            scan_subdirectories=path.scan_subdirectories,
            scan_debounce_time=path.scan_debounce_time,
            monitoring_enabled=path.monitoring_enabled,
            monitoring_mode=path.monitoring_mode,
            monitoring_debounce=path.monitoring_debounce,
            auto_recognize=path.auto_recognize,
            auto_organize=path.auto_organize,
            ignore_patterns=path.ignore_patterns,
            last_scan_at=path.last_scan_at.isoformat() if path.last_scan_at else None,
            last_scan_batch_id=path.last_scan_batch_id,
            total_scans=path.total_scans,
            total_files_found=path.total_files_found,
            created_at=path.created_at.isoformat() if path.created_at else "",
            updated_at=path.updated_at.isoformat() if path.updated_at else ""
        )
        for path in paths
    ]


@router.get("/paths/{path_id}", response_model=ScanPathConfigResponse)
async def get_scan_path(
    path_id: int,
    db: Session = Depends(get_db)
):
    """
    获取单个扫描路径配置
    
    - **path_id**: 路径ID
    """
    scan_path = db.query(ScanPath).filter(ScanPath.id == path_id).first()
    if not scan_path:
        raise HTTPException(status_code=404, detail="扫描路径不存在")
    
    return ScanPathConfigResponse(
        id=scan_path.id,
        path=scan_path.path,
        path_name=scan_path.path_name,
        enabled=scan_path.enabled,
        scan_type=scan_path.scan_type,
        recursive=scan_path.recursive,
        skip_strategy=scan_path.skip_strategy,
        scan_subdirectories=scan_path.scan_subdirectories,
        scan_debounce_time=scan_path.scan_debounce_time,
        monitoring_enabled=scan_path.monitoring_enabled,
        monitoring_mode=scan_path.monitoring_mode,
        monitoring_debounce=scan_path.monitoring_debounce,
        auto_recognize=scan_path.auto_recognize,
        auto_organize=scan_path.auto_organize,
        ignore_patterns=scan_path.ignore_patterns,
        last_scan_at=scan_path.last_scan_at.isoformat() if scan_path.last_scan_at else None,
        last_scan_batch_id=scan_path.last_scan_batch_id,
        total_scans=scan_path.total_scans,
        total_files_found=scan_path.total_files_found,
        created_at=scan_path.created_at.isoformat() if scan_path.created_at else "",
        updated_at=scan_path.updated_at.isoformat() if scan_path.updated_at else ""
    )


@router.post("/paths", response_model=ScanPathConfigResponse)
async def create_scan_path(
    path_data: ScanPathCreate,
    db: Session = Depends(get_db)
):
    """
    添加扫描路径
    
    - **path**: 扫描路径
    - **path_name**: 路径名称（可选）
    - **enabled**: 是否启用
    - **scan_type**: 扫描类型
    - **recursive**: 是否递归
    - **skip_strategy**: 跳过策略
    - **scan_subdirectories**: 是否扫描子目录
    - **scan_debounce_time**: 扫描防抖时间
    - **monitoring_enabled**: 是否启用监控
    - **monitoring_mode**: 监控模式
    - **monitoring_debounce**: 监控防抖时间
    - **auto_recognize**: 扫描完成后是否自动识别
    - **auto_organize**: 扫描完成后是否自动整理
    - **ignore_patterns**: 忽略文件模式列表
    """
    # 检查路径是否已存在
    existing = db.query(ScanPath).filter(ScanPath.path == path_data.path).first()
    if existing:
        raise HTTPException(status_code=400, detail="扫描路径已存在")
    
    # 验证路径是否存在
    scan_path_obj = Path(path_data.path)
    if not scan_path_obj.exists():
        raise HTTPException(status_code=404, detail="路径不存在")
    if not scan_path_obj.is_dir():
        raise HTTPException(status_code=400, detail="路径不是目录")
    
    # 创建扫描路径
    scan_path = ScanPath(
        path=path_data.path,
        path_name=path_data.path_name,
        enabled=path_data.enabled,
        scan_type=path_data.scan_type,
        recursive=path_data.recursive,
        skip_strategy=path_data.skip_strategy,
        scan_subdirectories=path_data.scan_subdirectories,
        scan_debounce_time=path_data.scan_debounce_time,
        monitoring_enabled=path_data.monitoring_enabled,
        monitoring_mode=path_data.monitoring_mode,
        monitoring_debounce=path_data.monitoring_debounce,
        auto_recognize=path_data.auto_recognize,
        auto_organize=path_data.auto_organize,
        ignore_patterns=path_data.ignore_patterns
    )
    db.add(scan_path)
    db.commit()
    db.refresh(scan_path)
    
    logger.info(f"添加扫描路径: {path_data.path}")
    
    return ScanPathConfigResponse(
        id=scan_path.id,
        path=scan_path.path,
        path_name=scan_path.path_name,
        enabled=scan_path.enabled,
        scan_type=scan_path.scan_type,
        recursive=scan_path.recursive,
        skip_strategy=scan_path.skip_strategy,
        scan_subdirectories=scan_path.scan_subdirectories,
        scan_debounce_time=scan_path.scan_debounce_time,
        monitoring_enabled=scan_path.monitoring_enabled,
        monitoring_mode=scan_path.monitoring_mode,
        monitoring_debounce=scan_path.monitoring_debounce,
        auto_recognize=scan_path.auto_recognize,
        auto_organize=scan_path.auto_organize,
        ignore_patterns=scan_path.ignore_patterns,
        last_scan_at=scan_path.last_scan_at.isoformat() if scan_path.last_scan_at else None,
        last_scan_batch_id=scan_path.last_scan_batch_id,
        total_scans=scan_path.total_scans,
        total_files_found=scan_path.total_files_found,
        created_at=scan_path.created_at.isoformat() if scan_path.created_at else "",
        updated_at=scan_path.updated_at.isoformat() if scan_path.updated_at else ""
    )


@router.put("/paths/{path_id}", response_model=ScanPathConfigResponse)
async def update_scan_path(
    path_id: int,
    path_data: ScanPathUpdate,
    db: Session = Depends(get_db)
):
    """
    更新扫描路径
    
    - **path_id**: 路径ID
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
        scan_path_obj = Path(path_data.path)
        if not scan_path_obj.exists():
            raise HTTPException(status_code=404, detail="路径不存在")
        if not scan_path_obj.is_dir():
            raise HTTPException(status_code=400, detail="路径不是目录")
        
        scan_path.path = path_data.path
    
    if path_data.path_name is not None:
        scan_path.path_name = path_data.path_name
    if path_data.enabled is not None:
        scan_path.enabled = path_data.enabled
    if path_data.scan_type is not None:
        scan_path.scan_type = path_data.scan_type
    if path_data.recursive is not None:
        scan_path.recursive = path_data.recursive
    if path_data.skip_strategy is not None:
        scan_path.skip_strategy = path_data.skip_strategy
    if path_data.scan_subdirectories is not None:
        scan_path.scan_subdirectories = path_data.scan_subdirectories
    if path_data.scan_debounce_time is not None:
        scan_path.scan_debounce_time = path_data.scan_debounce_time
    if path_data.monitoring_enabled is not None:
        scan_path.monitoring_enabled = path_data.monitoring_enabled
    if path_data.monitoring_mode is not None:
        scan_path.monitoring_mode = path_data.monitoring_mode
    if path_data.monitoring_debounce is not None:
        scan_path.monitoring_debounce = path_data.monitoring_debounce
    if path_data.auto_recognize is not None:
        scan_path.auto_recognize = path_data.auto_recognize
    if path_data.auto_organize is not None:
        scan_path.auto_organize = path_data.auto_organize
    if path_data.ignore_patterns is not None:
        scan_path.ignore_patterns = path_data.ignore_patterns
    
    scan_path.updated_at = datetime.now()
    db.commit()
    db.refresh(scan_path)
    
    logger.info(f"更新扫描路径: {path_id}")
    
    return ScanPathConfigResponse(
        id=scan_path.id,
        path=scan_path.path,
        path_name=scan_path.path_name,
        enabled=scan_path.enabled,
        scan_type=scan_path.scan_type,
        recursive=scan_path.recursive,
        skip_strategy=scan_path.skip_strategy,
        scan_subdirectories=scan_path.scan_subdirectories,
        scan_debounce_time=scan_path.scan_debounce_time,
        monitoring_enabled=scan_path.monitoring_enabled,
        monitoring_mode=scan_path.monitoring_mode,
        monitoring_debounce=scan_path.monitoring_debounce,
        auto_recognize=scan_path.auto_recognize,
        auto_organize=scan_path.auto_organize,
        ignore_patterns=scan_path.ignore_patterns,
        last_scan_at=scan_path.last_scan_at.isoformat() if scan_path.last_scan_at else None,
        last_scan_batch_id=scan_path.last_scan_batch_id,
        total_scans=scan_path.total_scans,
        total_files_found=scan_path.total_files_found,
        created_at=scan_path.created_at.isoformat() if scan_path.created_at else "",
        updated_at=scan_path.updated_at.isoformat() if scan_path.updated_at else ""
    )


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


# ========== 文件任务管理 ==========


@router.get("/file-tasks", response_model=List[FileTaskResponse])
async def get_file_tasks(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    batch_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取文件任务列表
    
    - **limit**: 返回数量限制
    - **offset**: 偏移量
    - **status**: 状态筛选
    - **batch_id**: 批次ID筛选
    """
    query = db.query(FileTask)
    
    if status:
        query = query.filter(FileTask.status == status)
    if batch_id:
        query = query.filter(FileTask.batch_id == batch_id)
    
    tasks = query.order_by(FileTask.created_at.desc()).offset(offset).limit(limit).all()
    
    result = []
    for task in tasks:
        # 查找文件所在路径的扫描策略
        scan_path = db.query(ScanPath).filter(
            ScanPath.path.like(f"{task.target_path}%")
        ).first()
        
        scan_type = None
        recursive = None
        skip_strategy = None
        
        if scan_path:
            scan_type = scan_path.scan_type
            recursive = scan_path.recursive
            skip_strategy = scan_path.skip_strategy
        
        result.append(FileTaskResponse(
            id=task.id,
            batch_id=task.batch_id,
            media_file_id=task.media_file_id,
            target_path=task.target_path,
            file_name=task.file_name,
            scan_type=scan_type,
            recursive=recursive,
            skip_strategy=skip_strategy,
            status=task.status,
            scan_progress=task.scan_progress or 0,
            scan_started_at=task.scan_started_at.isoformat() if task.scan_started_at else None,
            scan_completed_at=task.scan_completed_at.isoformat() if task.scan_completed_at else None,
            scan_error=task.scan_error,
            video_tracks=task.video_tracks or 0,
            audio_tracks=task.audio_tracks or 0,
            subtitle_tracks=task.subtitle_tracks or 0,
            video_codec=task.video_codec,
            audio_codec=task.audio_codec,
            has_external_subtitle=task.has_external_subtitle or False,
            external_subtitle_name=task.external_subtitle_name,
            scan_result=task.scan_result,
            created_at=task.created_at.isoformat() if task.created_at else "",
            updated_at=task.updated_at.isoformat() if task.updated_at else ""
        ))
    
    return result


@router.get("/file-tasks/{task_id}", response_model=ScanResultDetailResponse)
async def get_file_task_detail(
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    查看文件扫描结果
    
    - **task_id**: 任务ID
    """
    task = db.query(FileTask).filter(FileTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="文件任务不存在")
    
    media_file = task.media_file
    if not media_file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    return ScanResultDetailResponse(
        file_name=media_file.file_name,
        file_size=media_file.file_size,
        file_type=media_file.media_type,
        file_path=media_file.file_path,
        scan_started_at=task.scan_started_at.isoformat() if task.scan_started_at else None,
        scan_completed_at=task.scan_completed_at.isoformat() if task.scan_completed_at else None,
        file_encoding_format=task.video_codec,  # 使用视频编码格式作为文件编码格式
        video_tracks=task.video_tracks or 0,
        audio_tracks=task.audio_tracks or 0,
        subtitle_tracks=task.subtitle_tracks or 0,
        has_external_subtitle=task.has_external_subtitle or False,
        external_subtitle_name=task.external_subtitle_name,
        scan_result=task.scan_result,
        file_hash=media_file.sha256_hash,
        scan_task_id=task_id,
        video_codec=task.video_codec,
        audio_codec=task.audio_codec
    )


@router.post("/file-tasks/{task_id}/rescan")
async def rescan_file(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    重新扫描文件（只扫描该文件，不扫描整个目录）
    
    - **task_id**: 任务ID
    """
    task = db.query(FileTask).filter(FileTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="文件任务不存在")
    
    media_file = task.media_file
    if not media_file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    # 查找文件所在路径的扫描策略
    scan_path = db.query(ScanPath).filter(
        ScanPath.path.like(f"{task.target_path}%")
    ).first()
    
    if scan_path:
        scan_type = scan_path.scan_type
        recursive = scan_path.recursive
        skip_strategy = scan_path.skip_strategy
        scan_subdirectories = scan_path.scan_subdirectories
        scan_debounce_time = scan_path.scan_debounce_time
    else:
        # 使用默认扫描策略
        from app.core.config import config_manager
        scanner_config = config_manager.get("scanner", {})
        scan_type = scanner_config.get("default_scan_type", "incremental")
        recursive = scanner_config.get("default_recursive", True)
        skip_strategy = scanner_config.get("default_skip_strategy", "keyword")
        scan_subdirectories = True
        scan_debounce_time = 30
    
    # 删除与该文件有关的所有扫描记录
    media_file_id = media_file.id
    db.query(FileTask).filter(FileTask.media_file_id == media_file_id).delete()
    db.query(SubtitleFile).filter(SubtitleFile.media_file_id == media_file_id).delete()
    db.delete(media_file)
    db.commit()
    
    # 只扫描单个文件，不扫描整个目录
    from pathlib import Path
    file_path = Path(media_file.file_path)
    
    # 创建新的扫描任务，只扫描该文件
    scan_manager = get_scan_manager()
    new_task_id = scan_manager.start_scan(
        target_path=task.target_path,
        scan_type=scan_type,
        recursive=recursive,
        skip_strategy=skip_strategy,
        scan_subdirectories=scan_subdirectories,
        scan_debounce_time=scan_debounce_time,
        files=[file_path]  # 只扫描指定的文件
    )
    
    return {
        "task_id": new_task_id,
        "message": "重新扫描任务已创建"
    }


@router.post("/file-tasks/{task_id}/stop")
async def stop_file_scan(
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    停止扫描文件
    
    - **task_id**: 任务ID
    """
    task = db.query(FileTask).filter(FileTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="文件任务不存在")
    
    if task.status not in ["scanning", "pending"]:
        raise HTTPException(status_code=400, detail="任务不在运行中")
    
    # 更新任务状态为停止
    task.status = "stopped"
    task.scan_error = "用户停止"
    db.commit()
    
    # 删除与该文件有关的所有扫描记录
    # 1. 删除文件任务记录
    db.query(FileTask).filter(FileTask.id == task_id).delete()
    # 2. 删除媒体文件记录
    if task.media_file:
        media_file_id = task.media_file.id
        db.query(SubtitleFile).filter(SubtitleFile.media_file_id == media_file_id).delete()
        db.delete(task.media_file)
    db.commit()
    
    return {"message": "文件扫描已停止"}


@router.delete("/file-tasks/{task_id}")
async def delete_file_scan_result(
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    删除扫描结果
    
    - **task_id**: 任务ID
    """
    task = db.query(FileTask).filter(FileTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="文件任务不存在")
    
    if task.status != "scanned":
        raise HTTPException(status_code=400, detail="只能删除已完成扫描的文件结果")
    
    # 删除与该文件有关的所有扫描记录
    # 1. 删除文件任务记录
    db.query(FileTask).filter(FileTask.media_file_id == task.media_file_id).delete()
    # 2. 删除媒体文件记录
    if task.media_file:
        media_file_id = task.media_file.id
        db.query(SubtitleFile).filter(SubtitleFile.media_file_id == media_file_id).delete()
        db.delete(task.media_file)
    db.commit()
    
    return {"message": "扫描结果已删除"}


# ========== 批量操作 ==========


class BatchFileOperationRequest(BaseModel):
    """批量文件操作请求 - 基于媒体文件ID"""
    model_config = ConfigDict(str_strip_whitespace=True)
    media_file_ids: List[Union[int, str]]
    
    def get_int_ids(self) -> List[int]:
        """获取转换后的整数ID列表"""
        result = []
        for item in self.media_file_ids:
            try:
                if isinstance(item, str):
                    result.append(int(item))
                elif isinstance(item, (int, float)):
                    result.append(int(item))
                else:
                    raise ValueError(f"无效的ID类型: {type(item)}")
            except (ValueError, TypeError) as e:
                raise ValueError(f"无法将 '{item}' 转换为整数: {e}")
        return result


# ========== 媒体文件操作（基于media_file_id）==========


@router.post("/files/{media_file_id}/rescan")
async def rescan_media_file(
    media_file_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    重新扫描媒体文件（基于media_file_id）
    
    - **media_file_id**: 媒体文件ID
    """
    # 查找媒体文件
    media_file = db.query(MediaFile).filter(MediaFile.id == media_file_id).first()
    if not media_file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    # 查找文件所在路径的扫描策略
    scan_path = db.query(ScanPath).filter(
        ScanPath.path.like(f"{media_file.file_path}%")
    ).first()
    
    if scan_path:
        scan_type = scan_path.scan_type
        recursive = scan_path.recursive
        skip_strategy = scan_path.skip_strategy
        scan_subdirectories = scan_path.scan_subdirectories
        scan_debounce_time = scan_path.scan_debounce_time
        target_path = scan_path.path
    else:
        # 使用默认扫描策略
        from app.core.config import config_manager
        scanner_config = config_manager.get("scanner", {})
        scan_type = scanner_config.get("default_scan_type", "incremental")
        recursive = scanner_config.get("default_recursive", True)
        skip_strategy = scanner_config.get("default_skip_strategy", "keyword")
        scan_subdirectories = True
        scan_debounce_time = 30
        # 从文件路径提取目录
        target_path = str(Path(media_file.file_path).parent)
    
    # 删除与该文件有关的所有扫描记录
    db.query(FileTask).filter(FileTask.media_file_id == media_file_id).delete()
    db.query(SubtitleFile).filter(SubtitleFile.media_file_id == media_file_id).delete()
    db.delete(media_file)
    db.commit()
    
    # 只扫描单个文件，不扫描整个目录
    file_path = Path(media_file.file_path)
    
    # 创建新的扫描任务，只扫描该文件
    scan_manager = get_scan_manager()
    new_task_id = scan_manager.start_scan(
        target_path=target_path,
        scan_type=scan_type,
        recursive=recursive,
        skip_strategy=skip_strategy,
        scan_subdirectories=scan_subdirectories,
        scan_debounce_time=scan_debounce_time,
        files=[file_path]  # 只扫描指定的文件
    )
    
    return {
        "media_file_id": media_file_id,
        "task_id": new_task_id,
        "message": "重新扫描任务已创建"
    }


@router.post("/files/{media_file_id}/stop")
async def stop_media_file_scan(
    media_file_id: int,
    db: Session = Depends(get_db)
):
    """
    停止扫描媒体文件（基于media_file_id）
    
    - **media_file_id**: 媒体文件ID
    """
    # 查找媒体文件
    media_file = db.query(MediaFile).filter(MediaFile.id == media_file_id).first()
    if not media_file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    # 查找该文件的任务
    task = db.query(FileTask).filter(
        FileTask.media_file_id == media_file_id,
        FileTask.status.in_(["scanning", "pending"])
    ).first()
    
    if not task:
        raise HTTPException(status_code=400, detail="任务不在运行中")
    
    # 更新任务状态为停止
    task.status = "stopped"
    task.scan_error = "用户停止"
    db.commit()
    
    # 删除与该文件有关的所有扫描记录
    db.query(FileTask).filter(FileTask.media_file_id == media_file_id).delete()
    db.query(SubtitleFile).filter(SubtitleFile.media_file_id == media_file_id).delete()
    db.delete(media_file)
    db.commit()
    
    return {"message": "文件扫描已停止"}


@router.delete("/files/{media_file_id}")
async def delete_media_file_scan_result(
    media_file_id: int,
    db: Session = Depends(get_db)
):
    """
    删除媒体文件扫描结果（基于media_file_id）
    
    - **media_file_id**: 媒体文件ID
    """
    # 查找媒体文件
    media_file = db.query(MediaFile).filter(MediaFile.id == media_file_id).first()
    if not media_file:
        raise HTTPException(status_code=404, detail="媒体文件不存在")
    
    # 检查是否有正在扫描的任务
    task = db.query(FileTask).filter(
        FileTask.media_file_id == media_file_id,
        FileTask.status.in_(["scanning", "pending"])
    ).first()
    
    if task:
        raise HTTPException(status_code=400, detail="只能删除已完成扫描的文件结果")
    
    # 删除与该文件有关的所有扫描记录
    db.query(FileTask).filter(FileTask.media_file_id == media_file_id).delete()
    db.query(SubtitleFile).filter(SubtitleFile.media_file_id == media_file_id).delete()
    db.delete(media_file)
    db.commit()
    
    return {"message": "扫描结果已删除"}


# ========== 批量文件操作 ==========


@router.post("/files/batch/rescan")
async def batch_rescan_media_files(
    request: BatchFileOperationRequest,
    db: Session = Depends(get_db)
):
    """
    批量重新扫描媒体文件（对每个文件逐一执行）
    
    - **media_file_ids**: 媒体文件ID列表
    """
    # 转换为整数ID列表
    media_file_ids = request.get_int_ids()
    logger.info(f"[批量重新扫描] 收到请求 - media_file_ids={media_file_ids}, count={len(media_file_ids) if media_file_ids else 0}")
    
    if not media_file_ids or len(media_file_ids) == 0:
        raise HTTPException(status_code=400, detail="媒体文件ID列表不能为空")
    
    results = []
    
    # 对每个文件逐一执行重新扫描操作
    for media_file_id in media_file_ids:
        try:
            # 查找媒体文件
            media_file = db.query(MediaFile).filter(MediaFile.id == media_file_id).first()
            if not media_file:
                results.append({
                    "media_file_id": media_file_id,
                    "success": False,
                    "message": "媒体文件不存在"
                })
                continue
            
            # 查找文件所在路径的扫描策略
            scan_path = db.query(ScanPath).filter(
                ScanPath.path.like(f"{media_file.file_path}%")
            ).first()
            
            if scan_path:
                scan_type = scan_path.scan_type
                recursive = scan_path.recursive
                skip_strategy = scan_path.skip_strategy
                scan_subdirectories = scan_path.scan_subdirectories
                scan_debounce_time = scan_path.scan_debounce_time
                target_path = scan_path.path
            else:
                # 使用默认扫描策略
                from app.core.config import config_manager
                scanner_config = config_manager.get("scanner", {})
                scan_type = scanner_config.get("default_scan_type", "incremental")
                recursive = scanner_config.get("default_recursive", True)
                skip_strategy = scanner_config.get("default_skip_strategy", "keyword")
                scan_subdirectories = True
                scan_debounce_time = 30
                # 从文件路径提取目录
                target_path = str(Path(media_file.file_path).parent)
            
            # 删除与该文件有关的所有扫描记录
            file_path = Path(media_file.file_path)
            db.query(FileTask).filter(FileTask.media_file_id == media_file_id).delete()
            db.query(SubtitleFile).filter(SubtitleFile.media_file_id == media_file_id).delete()
            db.delete(media_file)
            db.commit()
            
            # 只扫描单个文件，不扫描整个目录
            scan_manager = get_scan_manager()
            new_task_id = scan_manager.start_scan(
                target_path=target_path,
                scan_type=scan_type,
                recursive=recursive,
                skip_strategy=skip_strategy,
                scan_subdirectories=scan_subdirectories,
                scan_debounce_time=scan_debounce_time,
                files=[file_path]  # 只扫描指定的文件
            )
            
            results.append({
                "media_file_id": media_file_id,
                "success": True,
                "task_id": new_task_id,
                "message": "重新扫描任务已创建"
            })
            
        except Exception as e:
            logger.error(f"批量重新扫描失败: media_file_id={media_file_id}, 错误: {e}")
            results.append({
                "media_file_id": media_file_id,
                "success": False,
                "message": f"重新扫描失败: {str(e)}"
            })
    
    return {
        "total": len(media_file_ids),
        "success": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }
    

@router.post("/files/batch/stop")
async def batch_stop_media_file_scans(
    request: BatchFileOperationRequest,
    db: Session = Depends(get_db)
):
    """
    批量停止扫描媒体文件（对每个文件逐一执行）
    
    - **media_file_ids**: 媒体文件ID列表
    """
    # 转换为整数ID列表
    media_file_ids = request.get_int_ids()
    logger.info(f"[批量停止扫描] 收到请求 - media_file_ids={media_file_ids}, count={len(media_file_ids) if media_file_ids else 0}")
    
    if not media_file_ids or len(media_file_ids) == 0:
        raise HTTPException(status_code=400, detail="媒体文件ID列表不能为空")
    
    results = []
    
    # 对每个文件逐一执行停止扫描操作
    for media_file_id in media_file_ids:
        try:
            # 查找媒体文件
            media_file = db.query(MediaFile).filter(MediaFile.id == media_file_id).first()
            if not media_file:
                results.append({
                    "media_file_id": media_file_id,
                    "success": False,
                    "message": "媒体文件不存在"
                })
                continue
            
            # 查找该文件的任务
            task = db.query(FileTask).filter(
                FileTask.media_file_id == media_file_id,
                FileTask.status.in_(["scanning", "pending"])
            ).first()
            
            if not task:
                results.append({
                    "media_file_id": media_file_id,
                    "success": False,
                    "message": "任务不在运行中"
                })
                continue
            
            # 更新任务状态为停止
            task.status = "stopped"
            task.scan_error = "用户停止"
            db.commit()
            
            # 删除与该文件有关的所有扫描记录
            db.query(FileTask).filter(FileTask.media_file_id == media_file_id).delete()
            db.query(SubtitleFile).filter(SubtitleFile.media_file_id == media_file_id).delete()
            db.delete(media_file)
            db.commit()
            
            results.append({
                "media_file_id": media_file_id,
                "success": True,
                "message": "文件扫描已停止"
            })
            
        except Exception as e:
            logger.error(f"批量停止扫描失败: media_file_id={media_file_id}, 错误: {e}")
            results.append({
                "media_file_id": media_file_id,
                "success": False,
                "message": f"停止失败: {str(e)}"
            })
    
    return {
        "total": len(media_file_ids),
        "success": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }


@router.delete("/files/batch")
async def batch_delete_media_file_scan_results(
    request: BatchFileOperationRequest,
    db: Session = Depends(get_db)
):
    """
    批量删除媒体文件扫描结果（对每个文件逐一执行）
    
    - **media_file_ids**: 媒体文件ID列表
    """
    # 转换为整数ID列表
    media_file_ids = request.get_int_ids()
    logger.info(f"[批量删除扫描结果] 收到请求 - media_file_ids={media_file_ids}, count={len(media_file_ids) if media_file_ids else 0}")
    
    if not media_file_ids or len(media_file_ids) == 0:
        raise HTTPException(status_code=400, detail="媒体文件ID列表不能为空")
    
    results = []
    
    # 对每个文件逐一执行删除扫描结果操作
    for media_file_id in media_file_ids:
        try:
            # 查找媒体文件
            media_file = db.query(MediaFile).filter(MediaFile.id == media_file_id).first()
            if not media_file:
                results.append({
                    "media_file_id": media_file_id,
                    "success": False,
                    "message": "媒体文件不存在"
                })
                continue
            
            # 检查是否有正在扫描的任务
            task = db.query(FileTask).filter(
                FileTask.media_file_id == media_file_id,
                FileTask.status.in_(["scanning", "pending"])
            ).first()
            
            if task:
                results.append({
                    "media_file_id": media_file_id,
                    "success": False,
                    "message": "只能删除已完成扫描的文件结果"
                })
                continue
            
            # 删除与该文件有关的所有扫描记录
            db.query(FileTask).filter(FileTask.media_file_id == media_file_id).delete()
            db.query(SubtitleFile).filter(SubtitleFile.media_file_id == media_file_id).delete()
            db.delete(media_file)
            db.commit()
            
            results.append({
                "media_file_id": media_file_id,
                "success": True,
                "message": "扫描结果已删除"
            })
            
        except Exception as e:
            logger.error(f"批量删除扫描结果失败: media_file_id={media_file_id}, 错误: {e}")
            results.append({
                "media_file_id": media_file_id,
                "success": False,
                "message": f"删除失败: {str(e)}"
            })
    
    return {
        "total": len(media_file_ids),
        "success": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }
