
"""
浏览目录API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import sys
from pathlib import Path

from app.db.session import get_db

router = APIRouter()


class DirectoryItem:
    """目录项"""
    def __init__(self, name: str, path: str, is_dir: bool, size: int = 0, modified_time: Optional[str] = None):
        self.name = name
        self.path = path
        self.is_dir = is_dir
        self.size = size
        self.modified_time = modified_time


@router.get("/scan/browse")
async def browse_directory(path: str = ""):
    """
    浏览目录

    Args:
        path: 要浏览的目录路径，空字符串表示根目录

    Returns:
        目录项列表
    """
    try:
        # 如果路径为空，使用系统根目录
        if not path or path.strip() == "":
            if sys.platform == "win32":
                # Windows: 返回所有驱动器
                drives = []
                for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                    drive = f"{letter}:\\"
                    if os.path.exists(drive):
                        drives.append(DirectoryItem(
                            name=drive,
                            path=drive,
                            is_dir=True,
                            size=0,
                            modified_time=None
                        ))
                return drives
            else:
                # Unix-like: 使用根目录
                path = "/"

        # 规范化路径
        normalized_path = os.path.normpath(path)

        # 检查路径是否存在
        if not os.path.exists(normalized_path):
            raise HTTPException(status_code=404, detail=f"路径不存在: {path}")

        # 检查路径是否为目录
        if not os.path.isdir(normalized_path):
            raise HTTPException(status_code=400, detail=f"路径不是目录: {path}")

        # 获取目录内容
        items = []
        try:
            for entry in os.scandir(normalized_path):
                try:
                    # 获取文件/目录信息
                    stat = entry.stat()
                    modified_time = None
                    try:
                        from datetime import datetime
                        modified_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        pass

                    # 创建目录项
                    item = DirectoryItem(
                        name=entry.name,
                        path=entry.path,
                        is_dir=entry.is_dir(),
                        size=stat.st_size if not entry.is_dir() else 0,
                        modified_time=modified_time
                    )
                    items.append(item)
                except (OSError, PermissionError) as e:
                    # 跳过无权限访问的项
                    continue
        except (OSError, PermissionError) as e:
            raise HTTPException(status_code=403, detail=f"无法访问目录: {str(e)}")

        # 排序：目录在前，文件在后；同类型按名称排序
        items.sort(key=lambda x: (not x.is_dir, x.name.lower()))

        return items

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"浏览目录失败: {str(e)}")
