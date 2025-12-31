#!/bin/bash
# ============================================================
# 🛑 AI Document Review - 停止服务脚本 (Linux/Mac)
# ============================================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        🛑 AI Document Review - 停止所有服务              ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}🔍 正在查找运行中的服务...${NC}"
echo ""

# 从 PID 文件停止进程
STOPPED=0

# 停止后端
echo -e "${CYAN}🔧 停止后端服务...${NC}"
BACKEND_STOPPED=0

# 从 PID 文件停止
if [ -f ".backend.pid" ]; then
    BACKEND_PID=$(cat .backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID 2>/dev/null
        echo -e "${GREEN}   ✅ 后端服务已停止 (PID: $BACKEND_PID)${NC}"
        BACKEND_STOPPED=1
    fi
    rm -f .backend.pid
fi

# 通过端口查找并停止所有占用 1231 端口的进程
BACKEND_PIDS=$(lsof -ti:1231 2>/dev/null)
if [ -n "$BACKEND_PIDS" ]; then
    for pid in $BACKEND_PIDS; do
        if kill -0 $pid 2>/dev/null; then
            kill $pid 2>/dev/null
            echo -e "${GREEN}   ✅ 已停止占用端口 1231 的进程 (PID: $pid)${NC}"
            BACKEND_STOPPED=1
        fi
    done
fi

if [ $BACKEND_STOPPED -eq 0 ]; then
        echo -e "${WHITE}   ⚪ 后端服务未运行${NC}"
fi

# 停止前端
echo -e "${CYAN}🎨 停止前端服务...${NC}"
FRONTEND_STOPPED=0

# 从 PID 文件停止
if [ -f ".frontend.pid" ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID 2>/dev/null
        echo -e "${GREEN}   ✅ 前端服务已停止 (PID: $FRONTEND_PID)${NC}"
        FRONTEND_STOPPED=1
    fi
    rm -f .frontend.pid
fi

# 通过端口查找并停止所有占用 1230 端口的进程
FRONTEND_PIDS=$(lsof -ti:1230 2>/dev/null)
if [ -n "$FRONTEND_PIDS" ]; then
    for pid in $FRONTEND_PIDS; do
        if kill -0 $pid 2>/dev/null; then
            kill $pid 2>/dev/null
            echo -e "${GREEN}   ✅ 已停止占用端口 1230 的进程 (PID: $pid)${NC}"
            FRONTEND_STOPPED=1
        fi
    done
fi

if [ $FRONTEND_STOPPED -eq 0 ]; then
        echo -e "${WHITE}   ⚪ 前端服务未运行${NC}"
    fi

# 清理可能残留的进程
echo -e "${CYAN}🐍 清理残留进程...${NC}"
UVICORN_KILLED=0

# 清理所有 uvicorn 相关进程（使用 -9 强制终止）
pkill -9 -f "uvicorn main:app" 2>/dev/null && UVICORN_KILLED=1 || true
pkill -9 -f "multiprocessing.spawn" 2>/dev/null && UVICORN_KILLED=1 || true
pkill -9 -f "multiprocessing.resource_tracker" 2>/dev/null && UVICORN_KILLED=1 || true
pkill -9 -f "vite" 2>/dev/null && UVICORN_KILLED=1 || true

# 强制清理端口（如果还有残留）
sleep 1
REMAINING_1231=$(lsof -ti:1231 2>/dev/null)
if [ -n "$REMAINING_1231" ]; then
    for pid in $REMAINING_1231; do
        kill -9 $pid 2>/dev/null && echo -e "${YELLOW}   ⚠️  强制停止占用端口 1231 的进程 (PID: $pid)${NC}" || true
    done
    sleep 1
    # 再次检查，如果还有残留，尝试更激进的方法
    STILL_REMAINING=$(lsof -ti:1231 2>/dev/null)
    if [ -n "$STILL_REMAINING" ]; then
        lsof -ti:1231 2>/dev/null | xargs kill -9 2>/dev/null || true
        echo -e "${YELLOW}   ⚠️  使用强制方法清理端口 1231${NC}"
    fi
fi

REMAINING_1230=$(lsof -ti:1230 2>/dev/null)
if [ -n "$REMAINING_1230" ]; then
    for pid in $REMAINING_1230; do
        kill -9 $pid 2>/dev/null && echo -e "${YELLOW}   ⚠️  强制停止占用端口 1230 的进程 (PID: $pid)${NC}" || true
    done
    sleep 1
    # 再次检查
    STILL_REMAINING=$(lsof -ti:1230 2>/dev/null)
    if [ -n "$STILL_REMAINING" ]; then
        lsof -ti:1230 2>/dev/null | xargs kill -9 2>/dev/null || true
        echo -e "${YELLOW}   ⚠️  使用强制方法清理端口 1230${NC}"
    fi
fi

if [ $UVICORN_KILLED -eq 1 ]; then
    echo -e "${GREEN}   ✅ 清理残留进程完成${NC}"
else
    echo -e "${WHITE}   ⚪ 无残留进程${NC}"
fi

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ 所有服务已停止${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

