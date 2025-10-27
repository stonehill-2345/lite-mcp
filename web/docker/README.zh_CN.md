# LiteMCP 前端 Docker 部署

本目录包含用于部署 LiteMCP 前端的 Docker 相关文件。

## 文件概览

- `Dockerfile` - 多阶段 Docker 构建配置
- `docker-compose.yml` - Docker Compose 配置
- `nginx.conf` - 生产环境 Nginx 配置
- `README.md` - 英文文档
- `README.zh_CN.md` - 本中文文档

## 快速开始

### 1. 使用部署脚本（推荐）

使用 `deploy.sh` 脚本是部署前端的最简单方式：

```bash
# 🚀 一键构建并启动前端服务
./deploy.sh up

# 🚀 使用自定义 API 地址构建并启动
./deploy.sh up --api-url https://api.example.com --proxy-url https://proxy.example.com

# 🔨 仅构建应用（用于开发）
./deploy.sh build

# 🛑 停止服务
./deploy.sh down

# 📋 查看日志
./deploy.sh logs

# 📊 检查状态
./deploy.sh status
```

**主要特性：**
- ✅ **一键部署**：`up` 命令自动构建并启动服务
- ✅ **Docker 构建**：在 Docker 中使用 Node.js 18 确保构建一致性
- ✅ **环境变量**：通过命令行选项轻松配置
- ✅ **服务管理**：完整的生命周期管理（启动/停止/重启/日志/状态）

#### 可用命令：
- `up` - **一键构建并启动前端服务**（默认）🚀
- `down` - 停止前端服务
- `restart` - 重启前端服务
- `logs` - 显示前端服务日志
- `status` - 显示前端服务状态
- `build` - 仅构建前端应用（用于开发）

#### 可用选项：
- `-e, --environment` - 环境（development|staging|production）[默认: production]
- `-a, --api-url` - API 基础地址
- `-p, --proxy-url` - 代理基础地址
- `-b, --build-only` - 仅构建，不部署
- `-h, --help` - 显示帮助信息

### 2. 手动 Docker 命令

如果你更喜欢手动 Docker 命令：

```bash
# 使用默认设置构建
docker build -t litemcp-frontend .

# 使用自定义 API 地址构建
docker build -t litemcp-frontend \
  --build-arg VITE_API_BASE_URL=https://api.your-domain.com \
  --build-arg VITE_PROXY_BASE_URL=https://proxy.your-domain.com \
  .

# 运行容器
docker run -d -p 2345:80 --name litemcp-frontend litemcp-frontend
```

### 3. 使用部署脚本（推荐）

配置和部署前端最简单的方式是使用 `deploy.sh` 脚本：

```bash
# 复制示例文件（可选，用于自定义配置）
cp .env.example .env

# 编辑配置（可选）
nano .env

# 使用部署脚本启动服务
./deploy.sh up

# 停止服务
./deploy.sh down
```

部署脚本自动处理Docker Compose操作并提供额外功能：

```bash
# 使用自定义API地址启动
./deploy.sh up --api-url https://api.your-domain.com --proxy-url https://proxy.your-domain.com

# 以开发模式启动
./deploy.sh up --environment development

# 仅构建（不部署）
./deploy.sh build

# 查看日志
./deploy.sh logs

# 检查状态
./deploy.sh status

# 重启服务
./deploy.sh restart
```

### 4. 直接使用 Docker Compose（高级）

如果您更喜欢直接使用Docker Compose：

```bash
# 复制示例文件
cp .env.example .env

# 编辑配置
nano .env

# 启动服务
docker-compose up -d

# 停止服务
docker-compose down
```

## 配置说明

### 构建参数

| 参数 | 描述 | 默认值 |
|------|------|--------|
| `VITE_API_BASE_URL` | 后端 API 服务器地址 | `http://localhost:9000` |
| `VITE_PROXY_BASE_URL` | 代理服务器地址 | `http://localhost:1888` |
| `VITE_DEBUG_MODE` | 启用调试模式 | `false` |
| `VITE_LOG_LEVEL` | 日志级别 | `error` |

### 环境变量

运行容器时可以设置相同的环境变量。

## 生产环境部署

### 1. 使用部署脚本部署（推荐）

生产环境部署最简单的方式是使用部署脚本：

```bash
# 使用生产环境URL部署
./deploy.sh up --environment production \
  --api-url https://api.production.com \
  --proxy-url https://proxy.production.com
```

或者创建 `.env` 文件进行自定义配置：

```bash
# 复制示例文件
cp .env.example .env

# 编辑为生产环境
nano .env
# 设置：
# VITE_API_BASE_URL=https://api.production.com
# VITE_PROXY_BASE_URL=https://proxy.production.com
# VITE_DEBUG_MODE=false
# VITE_LOG_LEVEL=error

# 部署
./deploy.sh up --environment production
```

### 2. 仅构建生产环境

如果您只想构建而不部署：

```bash
# 构建生产环境
./deploy.sh build --environment production \
  --api-url https://api.production.com \
  --proxy-url https://proxy.production.com
```

### 3. 直接Docker构建（高级）

如果您更喜欢手动Docker命令：

```bash
docker build -t litemcp-frontend:latest \
  --build-arg VITE_API_BASE_URL=https://api.production.com \
  --build-arg VITE_PROXY_BASE_URL=https://proxy.production.com \
  --build-arg VITE_DEBUG_MODE=false \
  --build-arg VITE_LOG_LEVEL=error \
  .
```

### 3. 反向代理配置

如果使用反向代理（如 Nginx 或 Traefik），可以配置路由到容器：

```nginx
# Nginx 配置
server {
    listen 80;
    server_name your-frontend-domain.com;
    
    location / {
        proxy_pass http://localhost:2345;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 开发环境

### 1. 使用部署脚本开发（推荐）

```bash
# 以开发模式启动
./deploy.sh up --environment development

# 或使用自定义API地址
./deploy.sh up --environment development \
  --api-url http://localhost:9000 \
  --proxy-url http://localhost:1888
```

### 2. Docker开发环境（高级）

```bash
# 构建开发镜像
docker build -t litemcp-frontend:dev \
  --build-arg VITE_DEBUG_MODE=true \
  --build-arg VITE_LOG_LEVEL=debug \
  .

# 运行开发容器
docker run -d -p 2345:80 --name litemcp-frontend-dev litemcp-frontend:dev
```

### 2. 开发时挂载卷

对于需要热重载的开发环境，可以挂载源代码：

```bash
docker run -d -p 2345:3000 \
  -v $(pwd):/app \
  -w /app \
  node:18-alpine \
  npm run dev
```

## 故障排除

### 常见问题

1. **容器启动失败**
   - 检查端口 2345 是否被占用
   - 验证环境变量设置是否正确
   - 查看 Docker 日志：`docker logs litemcp-frontend`

2. **API 调用失败**
   - 验证 `VITE_API_BASE_URL` 在浏览器中是否可访问
   - 检查后端的 CORS 设置
   - 确保后端服务器正在运行

3. **构建失败**
   - 检查所有依赖是否可用
   - 验证 Node.js 版本兼容性
   - 检查源代码是否有语法错误

### 调试命令

```bash
# 查看容器日志
docker logs litemcp-frontend

# 在容器中执行 shell
docker exec -it litemcp-frontend sh

# 检查容器状态
docker ps

# 查看容器详情
docker inspect litemcp-frontend
```

## 安全考虑

1. **环境变量**：不要在构建参数中包含敏感数据，因为它们在镜像中可见
2. **Nginx 配置**：包含的 nginx.conf 有基本的安全头设置
3. **网络**：考虑使用 Docker 网络进行服务通信
4. **更新**：定期更新基础镜像以获得安全补丁

## 性能优化

1. **多阶段构建**：Dockerfile 使用多阶段构建减少镜像大小
2. **Nginx 压缩**：启用 Gzip 压缩提高性能
3. **静态资源缓存**：静态资源长期缓存
4. **健康检查**：内置健康检查用于容器监控
