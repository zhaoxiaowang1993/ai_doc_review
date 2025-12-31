@echo off
chcp 65001 >nul 2>&1
title AI Document Review - 安装依赖

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║        📦 AI Document Review - 安装依赖                  ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"
echo 📁 项目目录: %CD%
echo.

:: ========== 检查环境 ==========
echo ┌──────────────────────────────────────────────────────────┐
echo │ 🔍 环境检查                                              │
echo └──────────────────────────────────────────────────────────┘

:: 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js 未安装
    echo    请访问 https://nodejs.org/ 下载安装
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do echo ✅ Node.js: %%i

:: 检查 npm
npm --version >nul 2>&1
if errorlevel 1 (
    echo ❌ npm 未安装
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('npm --version') do echo ✅ npm: %%i

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 未安装
    echo    请访问 https://www.python.org/ 下载安装
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo ✅ Python: %%i

echo.

:: ========== 后端依赖 ==========
echo ┌──────────────────────────────────────────────────────────┐
echo │ 🔧 安装后端依赖 (Python)                                 │
echo └──────────────────────────────────────────────────────────┘

cd app\api

:: 创建虚拟环境（如果不存在）
if not exist "venv" (
    echo 📦 创建 Python 虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo ✅ 虚拟环境已创建
)

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 安装依赖
echo 📦 安装 Python 依赖...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo ❌ 安装 Python 依赖失败
    pause
    exit /b 1
)
echo ✅ Python 依赖安装完成

:: 检查 .env 文件
if not exist ".env" (
    if exist ".env.tpl" (
        echo.
        echo ⚠️  未找到 .env 文件，正在从模板创建...
        copy .env.tpl .env >nul
        echo ✅ 已创建 .env 文件，请编辑并配置 API Key
    )
)

cd ..\..
echo.

:: ========== 前端依赖 ==========
echo ┌──────────────────────────────────────────────────────────┐
echo │ 🎨 安装前端依赖 (Node.js)                                │
echo └──────────────────────────────────────────────────────────┘

cd app\ui

:: 安装 npm 依赖
echo 📦 安装 npm 依赖...
call npm install
if errorlevel 1 (
    echo ❌ 安装 npm 依赖失败
    pause
    exit /b 1
)
echo ✅ npm 依赖安装完成

cd ..\..
echo.

:: ========== 完成 ==========
echo ═══════════════════════════════════════════════════════════
echo 🎉 所有依赖安装完成！
echo.
echo 📌 下一步:
echo    1. 编辑 app\api\.env 文件，配置必要的 API Key
echo    2. 运行 start.bat 启动服务
echo ═══════════════════════════════════════════════════════════
echo.

pause

