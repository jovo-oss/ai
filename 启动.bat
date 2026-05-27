@echo off
chcp 65001 >nul
title AI聊天系统 - 一键启动

echo ========================================
echo   AI聊天系统 - 一键启动
echo ========================================
echo.

:: 激活虚拟环境
echo [1/3] 激活虚拟环境...
call "%~dp0..\.venv\Scripts\activate.bat"
if errorlevel 1 (
    call "%~dp0..\..\.venv\Scripts\activate.bat"
    if errorlevel 1 (
        echo [提示] 未找到虚拟环境，使用系统Python
    ) else (
        echo [完成] 虚拟环境已激活
    )
) else (
    echo [完成] 虚拟环境已激活
)

echo.

:: 切换到backend目录检查依赖
cd /d "%~dp0backend"

echo [2/3] 检查依赖...
echo.

:: 检查关键依赖
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖包...
    pip install -r requirements.txt -q
    echo [完成] 依赖安装完成
) else (
    echo [完成] 依赖检查通过
)

echo.
echo [3/3] 启动服务...
echo.

:: 获取局域网IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4" ^| findstr /v "127.0.0.1"') do (
    set LOCAL_IP=%%a
    goto :found_ip
)
:found_ip
for /f "tokens=* delims= " %%a in ("%LOCAL_IP%") do set LOCAL_IP=%%a

echo 局域网IP: %LOCAL_IP%
echo.

:: 启动后端服务（后台运行）
echo 正在启动后端服务...
start /B python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

:: 等待后端启动
timeout /t 2 /nobreak >nul

echo.
echo 打开浏览器...
echo.

:: 打开浏览器（使用后端端口，避免跨域问题）
start "" "http://localhost:8000"

:: 显示访问信息
echo ========================================
echo   启动完成！
echo ========================================
echo.
echo 电脑端访问: http://localhost:8000
echo 移动端访问: http://%LOCAL_IP%:8000
echo.
echo 提示:
echo   - 关闭此窗口将停止所有服务
echo   - 手机和电脑需在同一WiFi网络
echo   - 按 Ctrl+C 可停止服务
echo.
echo ========================================
echo.

:: 保持窗口运行
pause
