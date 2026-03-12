
@echo off
chcp 65001 >nul
echo ====================================
echo MediaService 测试环境启动脚本
echo ====================================
echo.

echo [1/3] 检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python 3.9+
    pause
    exit /b 1
)
echo Python环境检查通过
echo.

echo [2/3] 检查Node.js环境...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Node.js，请先安装Node.js 16+
    pause
    exit /b 1
)
echo Node.js环境检查通过
echo.

echo [3/3] 启动测试环境...
echo.

echo 启动后端服务...
start "MediaService Backend" cmd /k "python -m app.main"

echo 等待后端服务启动...
timeout /t 3 /nobreak >nul

echo 启动前端服务...
start "MediaService Frontend" cmd /k "cd /d %~dp0..\frontend && npm run dev"

echo.
echo ====================================
echo 测试环境启动完成！
echo 后端服务: http://127.0.0.1:8000
echo 前端服务: http://localhost:5173
echo API文档: http://127.0.0.1:8000/docs
echo ====================================
echo.
pause
