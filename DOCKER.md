# Docker 部署指南

本文档介绍如何使用 Docker 部署和运行 AI 文档审核系统。

## 📋 前置要求

- Docker Engine 20.10+ 或 Docker Desktop
- Docker Compose 2.0+（如果使用 docker-compose）

## 🚀 快速开始

### 方式一：使用 Docker Compose（推荐）

1. **准备环境变量文件**

   在项目根目录创建 `.env` 文件（或复制 `app/api/.env.tpl` 并重命名），配置必要的环境变量：

   ```bash
   # 必需配置
   DEEPSEEK_API_KEY=your_deepseek_api_key
   MINERU_API_KEY=your_mineru_api_key
   
   # 可选配置
   AAD_CLIENT_ID=your_aad_client_id
   AAD_TENANT_ID=your_aad_tenant_id
   ```

2. **构建并启动服务**

   ```bash
   # 构建镜像并启动容器
   docker-compose up -d
   
   # 查看日志
   docker-compose logs -f
   
   # 查看服务状态
   docker-compose ps
   ```

3. **访问应用**

   - 前端 UI: http://localhost:1231
   - API 文档: http://localhost:1231/docs
   - 健康检查: http://localhost:1231/api/health

4. **停止服务**

   ```bash
   docker-compose down
   ```

### 方式二：使用 Docker 命令

1. **构建镜像**

   ```bash
   docker build -t ai-doc-review:latest .
   ```

2. **运行容器**

   ```bash
   docker run -d \
     --name ai-doc-review \
     -p 1231:1231 \
     -e DEEPSEEK_API_KEY=your_deepseek_api_key \
     -e MINERU_API_KEY=your_mineru_api_key \
     -v $(pwd)/app/api/app/data:/app/app/api/app/data \
     --restart unless-stopped \
     ai-doc-review:latest
   ```

3. **查看日志**

   ```bash
   docker logs -f ai-doc-review
   ```

4. **停止容器**

   ```bash
   docker stop ai-doc-review
   docker rm ai-doc-review
   ```

## 🔧 配置说明

### 环境变量

所有配置项都可以通过环境变量设置，主要配置项如下：

| 变量名 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | - | ✅ |
| `MINERU_API_KEY` | MinerU API 密钥 | - | ✅ |
| `MINERU_BASE_URL` | MinerU 服务地址 | `https://mineru.net` | ❌ |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 | `https://api.deepseek.com/v1` | ❌ |
| `DEEPSEEK_MODEL` | DeepSeek 模型名称 | `chatdeepseek` | ❌ |
| `DEBUG` | 调试模式 | `false` | ❌ |
| `LOG_LEVEL` | 日志级别 | `INFO` | ❌ |
| `AAD_CLIENT_ID` | Azure AD 客户端 ID | - | ❌ |
| `AAD_TENANT_ID` | Azure AD 租户 ID | - | ❌ |

### 数据持久化

容器中的数据目录会自动挂载到宿主机，确保数据持久化：

- **数据库**: `./app/api/app/data/app.db`
- **文档存储**: `./app/api/app/data/documents/`
- **MinerU 缓存**: `./app/api/app/data/mineru/`

### 端口配置

默认端口映射：
- 容器端口: `1231`
- 宿主机端口: `1231`

如需修改端口，可以在 `docker-compose.yml` 中修改：

```yaml
ports:
  - "8080:1231"  # 将宿主机端口改为 8080
```

## 🛠️ 开发模式

如果需要开发模式（热重载），可以修改 `docker-compose.yml`：

```yaml
services:
  ai-doc-review:
    # ... 其他配置
    volumes:
      - ./app/api:/app/app/api
      - ./common:/app/common
      - ./app/api/app/data:/app/app/api/app/data
    environment:
      - DEBUG=true
    command: ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "1231", "--reload"]
```

## 📊 监控和日志

### 查看容器日志

```bash
# 实时日志
docker-compose logs -f

# 最近 100 行日志
docker-compose logs --tail=100

# 仅查看错误日志
docker-compose logs | grep ERROR
```

### 健康检查

容器内置健康检查，可以通过以下方式查看：

```bash
# 查看容器健康状态
docker ps

# 手动检查健康状态
curl http://localhost:1231/api/health
```

## 🔍 故障排查

### 1. 容器无法启动

```bash
# 查看详细错误信息
docker-compose logs ai-doc-review

# 检查端口是否被占用
lsof -i :1231

# 检查镜像是否构建成功
docker images | grep ai-doc-review
```

### 2. API 无法访问

```bash
# 检查容器是否运行
docker ps | grep ai-doc-review

# 检查端口映射
docker port ai-doc-review

# 进入容器检查
docker exec -it ai-doc-review bash
```

### 3. 环境变量未生效

```bash
# 检查环境变量
docker exec ai-doc-review env | grep DEEPSEEK

# 验证 .env 文件格式
cat .env
```

### 4. 数据丢失

确保数据目录已正确挂载：

```bash
# 检查挂载点
docker inspect ai-doc-review | grep Mounts

# 检查数据目录权限
ls -la app/api/app/data/
```

## 🧹 清理

### 清理容器和镜像

```bash
# 停止并删除容器
docker-compose down

# 删除镜像
docker rmi ai-doc-review:latest

# 清理未使用的资源
docker system prune -a
```

### 清理数据（谨慎操作）

```bash
# 删除数据目录（会丢失所有数据）
rm -rf app/api/app/data/*
```

## 📝 生产环境建议

1. **使用环境变量文件**: 通过 `docker-compose.yml` 的 `env_file` 选项或 Docker secrets 管理敏感信息
2. **配置反向代理**: 使用 Nginx 或 Traefik 作为反向代理
3. **启用 HTTPS**: 配置 SSL/TLS 证书
4. **资源限制**: 在 `docker-compose.yml` 中设置 CPU 和内存限制
5. **日志管理**: 配置日志轮转和集中式日志收集
6. **备份策略**: 定期备份数据目录

示例生产配置：

```yaml
services:
  ai-doc-review:
    # ... 其他配置
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 🔗 相关链接

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [项目 README](../README.md)

