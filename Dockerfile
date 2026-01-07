# ============================================================
# 多阶段构建 Dockerfile
# 阶段1: 构建前端 React 应用
# 阶段2: 构建并运行后端 FastAPI 应用
# ============================================================

# ========== 阶段1: 前端构建 ==========
FROM node:20-alpine AS frontend-builder

WORKDIR /app/ui

# 配置 npm 使用国内镜像源（解决网络连接问题）
RUN npm config set registry https://registry.npmmirror.com && \
    npm config set fetch-retries 5 && \
    npm config set fetch-retry-mintimeout 20000 && \
    npm config set fetch-retry-maxtimeout 120000

# 复制前端依赖文件
COPY app/ui/package.json app/ui/package-lock.json ./

# 安装前端依赖（npm ci 默认会安装所有依赖，包括 devDependencies）
RUN npm ci

# esbuild 权限修复在官方镜像通常不需要，若遇到权限问题可按需启用
# RUN chmod +x /app/ui/node_modules/@esbuild/linux-x64/bin/esbuild || true

# 复制前端源代码
COPY app/ui/ ./

# 构建前端应用（输出到 ../api/www，相对于 /app/ui）
RUN npm run build

# ========== 阶段2: 后端服务 ==========
FROM python:3.10-slim AS backend

# 设置工作目录
WORKDIR /app

# 配置 Debian 国内镜像源（解决 502 Bad Gateway 问题）
# 优先尝试替换现有源配置，如果失败则创建新的 sources.list
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources && \
        sed -i 's|https://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
        sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list && \
        sed -i 's|https://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list && \
        sed -i 's|http://security.debian.org|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list && \
        sed -i 's|https://security.debian.org|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list; \
    fi

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制 common 模块（项目根目录，需要在安装依赖前复制以便设置 PYTHONPATH）
COPY common/ ./common/

# 复制后端依赖文件
COPY app/api/requirements.txt ./app/api/

# 安装 Python 依赖（排除本地 common 包，因为已通过文件复制方式包含）
# 使用 grep 过滤掉 common==0.1.0，因为它是本地包，已通过文件复制方式包含
RUN grep -v "^common==" app/api/requirements.txt > /tmp/requirements.txt && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# 复制后端源代码
COPY app/api/ ./app/api/

# 复制本地 env（用于传入 DeepSeek/MinerU 等密钥）
# 若 .env 不存在或被 .dockerignore 排除，不会影响构建
COPY app/api/.env ./app/api/.env

# 从前端构建阶段复制构建产物（vite 输出到 ../api/www，即 /app/api/www）
COPY --from=frontend-builder /app/api/www ./app/api/www

# 创建数据目录
RUN mkdir -p app/api/app/data/documents \
    app/api/app/data/mineru

# 设置环境变量
ENV PYTHONPATH=/app:/app/app
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 1231

# 设置工作目录为后端目录
WORKDIR /app/app/api

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:1231/api/health')" || exit 1

# 启动命令
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "1231"]
