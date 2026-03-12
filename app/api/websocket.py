
"""
WebSocket API端点
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from loguru import logger

from app.core.websocket import manager


router = APIRouter()


@router.websocket("/ws/scan/{task_id}")
async def scan_progress_websocket(
    websocket: WebSocket,
    task_id: int
):
    """
    扫描进度WebSocket端点

    Args:
        websocket: WebSocket连接
        task_id: 扫描任务ID
    """
    await manager.connect(websocket, task_id)

    try:
        # 保持连接活跃
        while True:
            # 接收客户端消息（心跳）
            data = await websocket.receive_text()
            logger.debug(f"收到WebSocket消息: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket客户端断开连接: task_id={task_id}")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        manager.disconnect(websocket)
