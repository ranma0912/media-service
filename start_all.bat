@echo off
chcp 65001 >nul
title Windows流媒体服务 - 启动脚本

echo ============================================================
echo Windows流媒体服务 - 启动脚本
echo ============================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.9+
    pause
    exit /b 1
)

REM 检查Node.js是否安装
node --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Node.js，请先安装Node.js 18+
    pause
    exit /b 1
)

echo [信息] 正在启动后端服务...
start "MediaService-Backend" cmd /k "python -m app.main"

timeout /t 3 /nobreak >nul

echo [信息] 正在启动前端服务...
cd frontend
if not exist "node_modules" (
    echo [信息] 首次启动，正在安装前端依赖...
    call npm install
    if errorlevel 1 (
        echo [错误] 前端依赖安装失败
        pause
        exit /b 1
    )
)
start "MediaService-Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ============================================================
echo 服务启动完成！
echo ============================================================
echo 前端仪表盘: http://localhost:5173
echo 后端 API:   http://127.0.0.1:8000
echo API 文档:   http://127.0.0.1:8000/docs
echo ============================================================
echo.
echo 提示: 按任意键关闭此窗口（前后端服务将继续运行）
pause >nul
