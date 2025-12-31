#!/bin/bash
# ============================================================
# 🚀 AI Document Review - 一键启动脚本 (Linux/Mac)
# ============================================================
# 功能：同时启动后端 API 和前端 UI
# 用法：chmod +x start.sh && ./start.sh
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        🚀 AI Document Review - 一键启动                  ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}📁 项目目录: $SCRIPT_DIR${NC}"
echo ""

# ========== 环境检查 ==========
echo -e "${YELLOW}🔍 环境检查...${NC}"

# 检查 Node.js
if command -v node &> /dev/null 2>&1; then
    NODE_VERSION=$(node --version 2>&1)
    echo -e "${GREEN}✅ Node.js: $NODE_VERSION${NC}"
else
    echo -e "${RED}❌ Node.js 未安装，请先安装 Node.js${NC}"
    exit 1
fi

# 检查 Python (优先使用 conda 环境 doc-review-310)
echo -e "${YELLOW}   检查 Python...${NC}"
PYTHON_CMD=""
CONDA_ENV_NAME="doc-review-310"

# 检测 conda 安装路径
CONDA_BASE=""
if [ -d "$HOME/anaconda3" ]; then
    CONDA_BASE="$HOME/anaconda3"
elif [ -d "$HOME/miniconda3" ]; then
    CONDA_BASE="$HOME/miniconda3"
elif [ -n "$CONDA_PREFIX" ]; then
    # 如果 conda 已激活，使用 CONDA_PREFIX 的父目录
    CONDA_BASE="$(dirname "$(dirname "$CONDA_PREFIX")")"
fi

# 优先使用 conda 环境
if [ -n "$CONDA_BASE" ] && [ -f "$CONDA_BASE/envs/$CONDA_ENV_NAME/bin/python" ]; then
    PYTHON_CMD="$CONDA_BASE/envs/$CONDA_ENV_NAME/bin/python"
    echo -e "${GREEN}✅ 检测到 conda 环境: $CONDA_ENV_NAME${NC}"
elif [ -n "$CONDA_BASE" ] && [ -f "$CONDA_BASE/envs/$CONDA_ENV_NAME/bin/python3" ]; then
    PYTHON_CMD="$CONDA_BASE/envs/$CONDA_ENV_NAME/bin/python3"
    echo -e "${GREEN}✅ 检测到 conda 环境: $CONDA_ENV_NAME${NC}"
# 回退到系统 Python
elif command -v python &> /dev/null 2>&1; then
    PYTHON_CMD="python"
    echo -e "${YELLOW}⚠️  使用系统 Python (建议使用 conda 环境)${NC}"
elif command -v python3 &> /dev/null 2>&1; then
    PYTHON_CMD="python3"
    echo -e "${YELLOW}⚠️  使用系统 Python3 (建议使用 conda 环境)${NC}"
else
    echo -e "${RED}❌ Python 未安装，请先安装 Python${NC}"
    exit 1
fi

# 获取 Python 版本
echo -e "${YELLOW}   获取 Python 版本...${NC}"
if PYTHON_VERSION=$($PYTHON_CMD --version 2>&1); then
    echo -e "${GREEN}✅ $PYTHON_VERSION${NC}"
    echo -e "${WHITE}   Python 路径: $PYTHON_CMD${NC}"
else
    echo -e "${YELLOW}⚠️  无法获取 Python 版本，但继续执行...${NC}"
    echo -e "${YELLOW}   使用 Python 命令: $PYTHON_CMD${NC}"
fi

echo ""

# 检查环境变量文件
if [ ! -f "app/api/.env" ]; then
    echo -e "${YELLOW}⚠️  未找到 app/api/.env 文件${NC}"
    echo -e "${YELLOW}   请复制 app/api/.env.tpl 并重命名为 .env，然后配置 API Key${NC}"
    echo ""
fi

# ========== 启动后端 ==========
echo -e "${CYAN}🔧 启动后端服务 (FastAPI)...${NC}"

# 检查并清理端口 1231 的占用
BACKEND_PORT=1231
MAX_RETRIES=3
RETRY_COUNT=0

echo -e "${YELLOW}   检查端口 $BACKEND_PORT 状态...${NC}"
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # 检查端口占用情况（添加错误处理）
    OLD_PIDS=$(lsof -ti:$BACKEND_PORT 2>/dev/null || echo "")
    if [ -z "$OLD_PIDS" ]; then
        echo -e "${GREEN}   ✅ 端口 $BACKEND_PORT 可用${NC}"
        break  # 端口已释放
    fi
    
    if [ $RETRY_COUNT -eq 0 ]; then
        echo -e "${YELLOW}   ⚠️  端口 $BACKEND_PORT 已被占用，正在清理...${NC}"
    fi
    
    # 先尝试正常终止
    for pid in $OLD_PIDS; do
        if kill -0 $pid 2>/dev/null; then
            kill $pid 2>/dev/null && echo -e "${GREEN}   ✅ 已停止进程 (PID: $pid)${NC}" || true
        fi
    done
    
    # 额外清理 uvicorn 和相关的 Python 进程
    pkill -9 -f "uvicorn main:app" 2>/dev/null || true
    pkill -9 -f "multiprocessing.spawn" 2>/dev/null || true
    pkill -9 -f "multiprocessing.resource_tracker" 2>/dev/null || true
    # 清理所有来自项目目录的 Python 进程（谨慎使用）
    pkill -9 -f "app/api.*python" 2>/dev/null || true
    # 清理所有占用目标端口的进程（无论是什么）
    lsof -ti:$BACKEND_PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
    
    sleep 2
    
    # 检查是否还有残留，如果有则强制终止
    REMAINING_PIDS=$(lsof -ti:$BACKEND_PORT 2>/dev/null)
    if [ -n "$REMAINING_PIDS" ]; then
        for pid in $REMAINING_PIDS; do
            kill -9 $pid 2>/dev/null && echo -e "${YELLOW}   ⚠️  强制停止进程 (PID: $pid)${NC}" || true
        done
        sleep 1
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

# 最终验证端口是否释放
echo -e "${YELLOW}   最终验证端口状态...${NC}"
FINAL_PIDS=$(lsof -ti:$BACKEND_PORT 2>/dev/null || echo "")
if [ -n "$FINAL_PIDS" ]; then
    echo -e "${RED}   ❌ 无法释放端口 $BACKEND_PORT，以下进程仍在占用:${NC}"
    for pid in $FINAL_PIDS; do
        echo -e "${RED}      PID: $pid${NC}"
        # 显示进程信息（使用 || true 防止 set -e 中断）
        ps -p $pid -o pid,comm,args 2>/dev/null | tail -1 || echo "         (进程信息无法获取)"
    done
    echo ""
    echo -e "${YELLOW}   💡 解决方案：${NC}"
    echo -e "${WHITE}      1. 手动清理: lsof -ti:1231 | xargs kill -9${NC}"
    echo -e "${WHITE}      2. 或运行: ./stop.sh${NC}"
    echo -e "${WHITE}      3. 如果进程是僵尸进程，可能需要重启终端或系统${NC}"
    echo ""
    # 检查是否在交互式终端中，如果不是则自动尝试清理
    if [ -t 0 ]; then
        read -p "是否尝试强制清理？(y/N): " FORCE_CLEAN || FORCE_CLEAN="n"
    else
        echo -e "${YELLOW}   非交互式模式，自动尝试强制清理...${NC}"
        FORCE_CLEAN="y"
    fi
    if [ "$FORCE_CLEAN" = "y" ] || [ "$FORCE_CLEAN" = "Y" ]; then
        echo -e "${YELLOW}   正在强制清理...${NC}"
        lsof -ti:$BACKEND_PORT 2>/dev/null | xargs kill -9 2>/dev/null || true
        sleep 2
        FINAL_CHECK=$(lsof -ti:$BACKEND_PORT 2>/dev/null)
        if [ -n "$FINAL_CHECK" ]; then
            echo -e "${RED}   ❌ 强制清理失败，请手动处理或重启系统${NC}"
            exit 1
        else
            echo -e "${GREEN}   ✅ 端口已释放${NC}"
        fi
    else
        exit 1
    fi
fi

# 进入后端目录（添加错误处理）
echo -e "${YELLOW}   进入后端目录...${NC}"
if ! cd app/api; then
    echo -e "${RED}❌ 无法进入 app/api 目录${NC}"
    exit 1
fi
echo -e "${GREEN}   ✅ 已进入后端目录${NC}"

# 如果使用的是 conda 环境，不需要激活 venv
# 如果使用的是系统 Python，尝试激活 venv（如果存在）
if [[ "$PYTHON_CMD" != *"envs/$CONDA_ENV_NAME"* ]] && [ -f "venv/bin/activate" ]; then
    echo -e "${YELLOW}   激活虚拟环境 venv...${NC}"
    source venv/bin/activate || true
fi

# 验证 uvicorn 是否可用
echo -e "${YELLOW}   检查 uvicorn 是否安装...${NC}"
if ! $PYTHON_CMD -c "import uvicorn" 2>/dev/null; then
    echo -e "${RED}❌ uvicorn 未安装，正在安装依赖...${NC}"
    $PYTHON_CMD -m pip install -q -r requirements.txt || {
        echo -e "${RED}❌ 依赖安装失败${NC}"
        exit 1
    }
    echo -e "${GREEN}   ✅ 依赖安装完成${NC}"
else
    echo -e "${GREEN}   ✅ uvicorn 已安装${NC}"
fi

# 在后台启动后端
echo -e "${YELLOW}   启动 uvicorn 服务...${NC}"
echo -e "${WHITE}   命令: $PYTHON_CMD -m uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --reload${NC}"
$PYTHON_CMD -m uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --reload &
BACKEND_PID=$!
echo -e "${GREEN}   ✅ 后端进程已启动 (PID: $BACKEND_PID)${NC}"

echo -e "${GREEN}   ✅ 后端服务已启动 (PID: $BACKEND_PID)${NC}"
echo -e "${WHITE}   📍 API 地址: http://localhost:1231${NC}"
echo -e "${WHITE}   📍 API 文档: http://localhost:1231/docs${NC}"
echo ""

cd "$SCRIPT_DIR"

# 等待后端启动
echo -e "${YELLOW}⏳ 等待后端服务启动 (3秒)...${NC}"
sleep 3

# ========== 启动前端 ==========
echo -e "${CYAN}🎨 启动前端服务 (Vite)...${NC}"

cd app/ui

# 在后台启动前端
npm run dev &
FRONTEND_PID=$!

echo -e "${GREEN}   ✅ 前端服务已启动 (PID: $FRONTEND_PID)${NC}"
echo -e "${WHITE}   📍 前端地址: http://localhost:1230${NC}"
echo ""

cd "$SCRIPT_DIR"

# ========== 保存 PID ==========
echo "$BACKEND_PID" > .backend.pid
echo "$FRONTEND_PID" > .frontend.pid

# ========== 完成 ==========
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 所有服务已启动！${NC}"
echo ""
echo -e "${YELLOW}📌 服务地址:${NC}"
echo -e "${WHITE}   • 前端 UI:  http://localhost:1230${NC}"
echo -e "${WHITE}   • 后端 API: http://localhost:1231${NC}"
echo -e "${WHITE}   • API 文档: http://localhost:1231/docs${NC}"
echo ""
echo -e "${YELLOW}📌 进程 PID:${NC}"
echo -e "${WHITE}   • 后端: $BACKEND_PID${NC}"
echo -e "${WHITE}   • 前端: $FRONTEND_PID${NC}"
echo ""
echo -e "${YELLOW}📌 停止服务:${NC}"
echo -e "${WHITE}   • 运行 ./stop.sh${NC}"
echo -e "${WHITE}   • 或按 Ctrl+C${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# 询问是否打开浏览器
read -p "是否打开浏览器？(Y/n): " OPEN_BROWSER
if [ "$OPEN_BROWSER" != "n" ] && [ "$OPEN_BROWSER" != "N" ]; then
    # 跨平台打开浏览器
    if command -v xdg-open &> /dev/null; then
        xdg-open "http://localhost:1230" &
    elif command -v open &> /dev/null; then
        open "http://localhost:1230" &
    fi
fi

echo ""
echo -e "${WHITE}按 Ctrl+C 停止所有服务...${NC}"

# 捕获 Ctrl+C 信号
trap 'echo ""; echo "🛑 正在停止服务..."; kill $BACKEND_PID 2>/dev/null; kill $FRONTEND_PID 2>/dev/null; rm -f .backend.pid .frontend.pid; echo "✅ 服务已停止"; exit 0' SIGINT SIGTERM

# 等待进程
wait

