
"""
WebSocket连接管理器
"""
from typing import Dict, List
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        # 存储活动连接：{task_id: [websocket1, websocket2, ...]}
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # 存储连接的task_id映射：{websocket: task_id}
        self.connection_tasks: Dict[WebSocket, int] = {}

    async def connect(self, websocket: WebSocket, task_id: int):
        """
        连接WebSocket
        """
        await websocket.accept()

        if task_id not in self.active_connections:
            self.active_connections[task_id] = []

        self.active_connections[task_id].append(websocket)
        self.connection_tasks[websocket] = task_id
        logger.info(f"WebSocket连接成功: task_id={task_id}, 当前连接数={len(self.active_connections[task_id])}")

    def disconnect(self, websocket: WebSocket):
        """
        断开WebSocket连接
        """
        if websocket in self.connection_tasks:
            task_id = self.connection_tasks[websocket]

            if task_id in self.active_connections:
                self.active_connections[task_id].remove(websocket)
                if not self.active_connections[task_id]:
                    del self.active_connections[task_id]

            del self.connection_tasks[websocket]
            logger.info(f"WebSocket断开连接: task_id={task_id}")

    async def send_progress(self, task_id: int, progress: dict):
        """
        向指定任务的所有连接发送进度更新
        """
        if task_id in self.active_connections:
            disconnected = []

            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(progress)
                except Exception as e:
                    logger.error(f"发送进度失败: {e}")
                    disconnected.append(connection)

            # 清理断开的连接
            for conn in disconnected:
                self.disconnect(conn)

    async def broadcast(self, message: dict):
        """
        向所有连接广播消息
        """
        disconnected = []

        for task_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"广播消息失败: {e}")
                    disconnected.append(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)


# 全局连接管理器实例
manager = ConnectionManager()
