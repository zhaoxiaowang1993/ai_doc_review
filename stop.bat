@echo off
chcp 65001 >nul 2>&1
title AI Document Review - 停止服务

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║        🛑 AI Document Review - 停止所有服务              ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

echo 🔍 正在查找运行中的服务...
echo.

:: 停止 Uvicorn (后端)
echo 🔧 停止后端服务 (Uvicorn)...
taskkill /f /im uvicorn.exe >nul 2>&1
if errorlevel 1 (
    echo    ⚪ 后端服务未运行
) else (
    echo    ✅ 后端服务已停止
)

:: 停止 Node (前端)
echo 🎨 停止前端服务 (Node)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":1230" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)
echo    ✅ 前端服务已停止

:: 停止可能残留的 Python 进程（仅限本项目）
echo 🐍 清理 Python 进程...
for /f "tokens=2" %%a in ('tasklist /fi "imagename eq python.exe" /fo list ^| findstr "PID"') do (
    wmic process where "ProcessId=%%a" get CommandLine 2>nul | findstr "uvicorn" >nul
    if not errorlevel 1 (
        taskkill /f /pid %%a >nul 2>&1
    )
)

echo.
echo ═══════════════════════════════════════════════════════════
echo ✅ 所有服务已停止
echo ═══════════════════════════════════════════════════════════
echo.

pause

