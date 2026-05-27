@echo off
chcp 65001 >nul
title AI聊天系统 - 停止服务

echo ========================================
echo   AI聊天系统 - 停止服务
echo ========================================
echo.

echo 正在停止后端服务...

:: 关闭占用8000端口的进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
    echo ✅ 已关闭后端进程 PID: %%a
)

echo.
echo 正在停止前端服务...

:: 关闭占用3000端口的进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
    echo ✅ 已关闭前端进程 PID: %%a
)

echo.
echo ========================================
echo   ✅ 所有服务已停止
echo ========================================
echo.
timeout /t 2 /nobreak >nul
