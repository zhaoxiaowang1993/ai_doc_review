#!/bin/bash
# ============================================================
# 📦 AI Document Review - 安装依赖脚本 (Linux/Mac)
# ============================================================

set -e

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
echo -e "${CYAN}║        📦 AI Document Review - 安装依赖                  ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}📁 项目目录: $SCRIPT_DIR${NC}"
echo ""

# ========== 环境检查 ==========
echo -e "${CYAN}┌──────────────────────────────────────────────────────────┐${NC}"
echo -e "${CYAN}│ 🔍 环境检查                                              │${NC}"
echo -e "${CYAN}└──────────────────────────────────────────────────────────┘${NC}"

# 检查 Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✅ Node.js: $NODE_VERSION${NC}"
else
    echo -e "${RED}❌ Node.js 未安装${NC}"
    echo -e "${YELLOW}   请安装 Node.js: https://nodejs.org/${NC}"
    exit 1
fi

# 检查 npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo -e "${GREEN}✅ npm: $NPM_VERSION${NC}"
else
    echo -e "${RED}❌ npm 未安装${NC}"
    exit 1
fi

# 检查 Python (优先使用较新版本，SQLite3 将通过 pysqlite3-binary 解决)
if command -v python &> /dev/null; then
    PYTHON_CMD="python"
    PIP_CMD="pip"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
else
    echo -e "${RED}❌ Python 未安装${NC}"
    echo -e "${YELLOW}   请安装 Python 3.9+: https://www.python.org/${NC}"
    exit 1
fi
PYTHON_VERSION=$($PYTHON_CMD --version)
echo -e "${GREEN}✅ $PYTHON_VERSION${NC}"

echo ""

# ========== 后端依赖 ==========
echo -e "${CYAN}┌──────────────────────────────────────────────────────────┐${NC}"
echo -e "${CYAN}│ 🔧 安装后端依赖 (Python)                                 │${NC}"
echo -e "${CYAN}└──────────────────────────────────────────────────────────┘${NC}"

cd app/api

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 创建 Python 虚拟环境...${NC}"
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}✅ 虚拟环境已创建${NC}"
fi

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
echo -e "${YELLOW}📦 升级 pip...${NC}"
pip install --upgrade pip -q

# 安装依赖
echo -e "${YELLOW}📦 安装 Python 依赖...${NC}"
pip install -r requirements.txt -q
echo -e "${GREEN}✅ Python 依赖安装完成${NC}"

# 检查 .env 文件
if [ ! -f ".env" ]; then
    if [ -f ".env.tpl" ]; then
        echo ""
        echo -e "${YELLOW}⚠️  未找到 .env 文件，正在从模板创建...${NC}"
        cp .env.tpl .env
        echo -e "${GREEN}✅ 已创建 .env 文件${NC}"
        echo -e "${YELLOW}   请编辑 app/api/.env 并配置 API Key${NC}"
    fi
fi

cd "$SCRIPT_DIR"
echo ""

# ========== 前端依赖 ==========
echo -e "${CYAN}┌──────────────────────────────────────────────────────────┐${NC}"
echo -e "${CYAN}│ 🎨 安装前端依赖 (Node.js)                                │${NC}"
echo -e "${CYAN}└──────────────────────────────────────────────────────────┘${NC}"

cd app/ui

# 安装 npm 依赖
echo -e "${YELLOW}📦 安装 npm 依赖...${NC}"
npm install
echo -e "${GREEN}✅ npm 依赖安装完成${NC}"

cd "$SCRIPT_DIR"
echo ""

# ========== 设置脚本权限 ==========
echo -e "${CYAN}┌──────────────────────────────────────────────────────────┐${NC}"
echo -e "${CYAN}│ 🔐 设置脚本权限                                          │${NC}"
echo -e "${CYAN}└──────────────────────────────────────────────────────────┘${NC}"

chmod +x start.sh stop.sh install.sh 2>/dev/null || true
echo -e "${GREEN}✅ 脚本权限已设置${NC}"
echo ""

# ========== 完成 ==========
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 所有依赖安装完成！${NC}"
echo ""
echo -e "${YELLOW}📌 下一步:${NC}"
echo -e "${WHITE}   1. 编辑 app/api/.env 文件，配置必要的 API Key${NC}"
echo -e "${WHITE}   2. 运行 ./start.sh 启动服务${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

