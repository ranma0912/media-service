"""
FastAPI 服务器
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger

from app.core.config import config_manager
from app.api import process, config as config_api, media, scan, recognition, organize


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("服务启动中...")
    yield
    # 关闭时执行
    logger.info("服务关闭中...")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    config = config_manager.config

    app = FastAPI(
        title=config.app.name,
        version=config.app.version,
        debug=config.app.debug,
        lifespan=lifespan
    )

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应限制具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(process.router, prefix="/api/process", tags=["进程管理"])
    app.include_router(config_api.router, prefix="/api/config", tags=["配置管理"])
    app.include_router(media.router, prefix="/api/media", tags=["媒体管理"])
    app.include_router(scan.router, prefix="/api/scan", tags=["扫描管理"])
    app.include_router(recognition.router, prefix="/api/recognition", tags=["识别管理"])
    app.include_router(organize.router, prefix="/api/organize", tags=["整理管理"])

    # 健康检查
    @app.get("/health")
    async def health_check():
        """健康检查接口"""
        return {"status": "healthy", "version": config.app.version}

    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"未处理的异常: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "服务器内部错误"}
        )

    return app
