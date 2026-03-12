"""
进程管理 API
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from loguru import logger

from app.core.daemon import ProcessManager
from app.core.paths import paths
from app.core.config import config_manager

router = APIRouter()


class ProcessStatus(BaseModel):
    """进程状态"""
    status: str  # running, stopped, error
    pid: Optional[int]
    uptime: Optional[str]
    version: str
    start_time: Optional[str]


class ProcessAction(BaseModel):
    """进程操作"""
    action: str  # start, stop, restart
    force: bool = False


class SystemStats(BaseModel):
    """系统资源统计"""
    cpu: float  # CPU使用率(%)
    memory: float  # 内存使用率(%)
    disk: float  # 磁盘使用率(%)


# 存储历史数据用于计算平均值
class ResourceHistory:
    """资源历史数据"""
    def __init__(self, max_samples=12):
        self.max_samples = max_samples  # 存储最近12个数据点（每5秒一次，共60秒）
        self.cpu_samples = []
        self.memory_samples = []
        self.disk_samples = []

    def add_sample(self, cpu, memory, disk):
        """添加样本数据"""
        self.cpu_samples.append(cpu)
        self.memory_samples.append(memory)
        self.disk_samples.append(disk)

        # 保持样本数量不超过最大值
        if len(self.cpu_samples) > self.max_samples:
            self.cpu_samples.pop(0)
            self.memory_samples.pop(0)
            self.disk_samples.pop(0)

    def get_average(self):
        """获取平均值"""
        if not self.cpu_samples:
            return 0, 0, 0

        avg_cpu = sum(self.cpu_samples) / len(self.cpu_samples)
        avg_memory = sum(self.memory_samples) / len(self.memory_samples)
        avg_disk = sum(self.disk_samples) / len(self.disk_samples)

        return avg_cpu, avg_memory, avg_disk


# 全局资源历史数据实例
resource_history = ResourceHistory()


def format_uptime(timestamp: float) -> str:
    """格式化运行时间"""
    delta = datetime.now() - datetime.fromtimestamp(timestamp)
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}小时{minutes}分钟{seconds}秒"


def format_datetime(timestamp: float) -> str:
    """格式化日期时间"""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


@router.get("/status", response_model=ProcessStatus)
async def get_process_status():
    """获取进程状态"""
    config = config_manager.config
    pid_file = paths.pid_file

    if not pid_file.exists():
        return ProcessStatus(
            status="stopped",
            pid=None,
            uptime=None,
            version=config.app.version,
            start_time=None
        )

    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())

        import psutil
        process = psutil.Process(pid)
        if process.is_running():
            uptime = process.create_time()
            return ProcessStatus(
                status="running",
                pid=pid,
                uptime=format_uptime(uptime),
                version=config.app.version,
                start_time=format_datetime(uptime)
            )
    except (ValueError, ImportError, Exception) as e:
        logger.warning(f"读取进程状态失败: {e}")

    return ProcessStatus(
        status="stopped",
        pid=None,
        uptime=None,
        version=config.app.version,
        start_time=None
    )


@router.get("/stats", response_model=SystemStats)
async def get_system_stats():
    """获取系统资源统计（返回过去一分钟内的平均值）"""
    try:
        import psutil
        import os

        # CPU使用率（不阻塞，立即获取）
        cpu_percent = psutil.cpu_percent(interval=None)

        # 内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent

        # 磁盘使用率（根据配置的监控路径计算）
        disk_percent = 0
        config = config_manager.config

        # 获取监控路径配置
        scan_paths = config.scan.paths if hasattr(config, 'scan') else []

        if scan_paths:
            # 取第一个监控路径所在的磁盘
            first_path = scan_paths[0] if isinstance(scan_paths, list) else scan_paths
            if first_path:
                try:
                    # 获取路径所在的磁盘
                    disk_path = os.path.splitdrive(first_path)[0] + os.sep
                    if not disk_path or not os.path.exists(disk_path):
                        # Windows下如果路径不存在，尝试使用C盘
                        disk_path = 'C:\\' if os.name == 'nt' else '/'
                    disk = psutil.disk_usage(disk_path)
                    disk_percent = disk.percent
                except Exception as e:
                    logger.warning(f"获取监控路径磁盘使用率失败: {e}")
                    # 如果失败，使用项目运行目录
                    try:
                        project_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                        disk_path = os.path.splitdrive(project_dir)[0] + os.sep if os.name == 'nt' else '/'
                        disk = psutil.disk_usage(disk_path)
                        disk_percent = disk.percent
                    except:
                        pass
        else:
            # 如果没有配置监控路径，使用项目运行目录所在磁盘
            try:
                project_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                disk_path = os.path.splitdrive(project_dir)[0] + os.sep if os.name == 'nt' else '/'
                disk = psutil.disk_usage(disk_path)
                disk_percent = disk.percent
            except Exception as e:
                logger.warning(f"获取项目目录磁盘使用率失败: {e}")
                # 如果失败，使用系统根目录
                try:
                    disk = psutil.disk_usage('/')
                    disk_percent = disk.percent
                except:
                    pass

        # 添加样本到历史数据
        resource_history.add_sample(cpu_percent, memory_percent, disk_percent)

        # 获取过去一分钟内的平均值
        avg_cpu, avg_memory, avg_disk = resource_history.get_average()

        return SystemStats(
            cpu=round(avg_cpu, 2),
            memory=round(avg_memory, 2),
            disk=round(avg_disk, 2)
        )
    except Exception as e:
        logger.error(f"获取系统资源统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统资源统计失败: {str(e)}")


@router.post("/control")
async def control_process(action: ProcessAction):
    """控制进程（启动/停止/重启）"""
    if action.action == "start":
        return await start_process()
    elif action.action == "stop":
        return await stop_process(action.force)
    elif action.action == "restart":
        return await restart_process(action.force)
    else:
        raise HTTPException(status_code=400, detail="无效的操作")


async def start_process():
    """启动进程"""
    pid_file = paths.pid_file

    if pid_file.exists():
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            import psutil
            if psutil.pid_exists(pid):
                return {"success": False, "message": "服务已在运行中"}
        except (ValueError, ImportError):
            pass

    logger.info("启动进程...")
    return {"success": True, "message": "进程启动命令已发送"}


async def stop_process(force: bool = False):
    """停止进程"""
    pid_file = paths.pid_file

    if not pid_file.exists():
        return {"success": True, "message": "服务未运行"}

    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())

        import psutil
        if not psutil.pid_exists(pid):
            pid_file.unlink(missing_ok=True)
            return {"success": True, "message": "服务已停止"}

        process = psutil.Process(pid)

        if force:
            process.kill()
        else:
            process.terminate()
            process.wait(timeout=10)

        pid_file.unlink(missing_ok=True)
        logger.info(f"进程已停止: {pid}")
        return {"success": True, "message": "服务已停止"}

    except psutil.TimeoutExpired:
        return {"success": False, "message": "服务停止超时，请尝试强制停止"}
    except Exception as e:
        logger.error(f"停止进程失败: {e}")
        return {"success": False, "message": f"停止失败: {str(e)}"}


async def restart_process(force: bool = False):
    """重启进程"""
    stop_result = await stop_process(force)
    if not stop_result["success"]:
        return stop_result

    import asyncio
    await asyncio.sleep(2)

    return await start_process()
