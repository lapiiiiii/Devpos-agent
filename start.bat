@echo off
echo ========================================
echo DevOps Agent 启动脚本
echo ========================================

echo.
echo [1/4] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python未安装或未添加到PATH
    pause
    exit /b 1
)
echo OK: Python已安装

echo.
echo [2/4] 检查依赖包...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖包...
    pip install -r requirements.txt
)
echo OK: 依赖已检查

echo.
echo [3/4] 创建数据目录...
if not exist "data" mkdir data
echo OK: 数据目录已创建

echo.
echo [4/4] 启动服务...
echo.
echo ========================================
echo 服务将在 http://localhost:8000 启动
echo API文档: http://localhost:8000/docs
echo 按Ctrl+C停止服务
echo ========================================
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
