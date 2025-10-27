# LiteMCP 全栈 Docker 部署

本目录包含用于部署完整 LiteMCP 技术栈（后端 + 前端）的 Docker 相关文件。

## 文件概览

- `Dockerfile` - 后端多阶段 Docker 构建配置
- `docker-compose.yml` - 全栈 Docker Compose 配置
- `deploy.sh` - 具有完整生命周期管理的部署脚本
- `README.md` - 英文文档
- `README.zh_CN.md` - 本中文文档

## 快速开始

### 1. 使用部署脚本（推荐）

使用 `deploy.sh` 脚本是部署 LiteMCP 的最简单方式：

```bash
# 🚀 一键部署全栈
./docker/deploy.sh up

# 🚀 使用自定义URL部署
PROXY_BASE_URL=https://proxy.your-domain.com \
API_BASE_URL=https://api.your-domain.com \
./docker/deploy.sh up

# 🛑 停止所有服务
./docker/deploy.sh down

# 📋 查看日志
./docker/deploy.sh logs

# 📊 检查状态
./docker/deploy.sh status
```

**主要特性：**
- ✅ **全栈部署**：一个命令部署后端 + 前端
- ✅ **环境配置**：通过环境变量轻松设置
- ✅ **网络兼容性**：自动解析内网域名
- ✅ **服务管理**：完整的生命周期管理

#### 可用命令：
- `up` - **启动所有服务**（默认）🚀
- `down` - 停止所有服务
- `restart` - 重启所有服务
- `logs` - 显示服务日志
- `status` - 显示服务状态
- `clean` - 清理容器和卷

### 2. 手动 Docker Compose

如果您更喜欢手动 Docker Compose 命令：

```bash
# 启动服务
docker-compose -f docker/docker-compose.yml up -d

# 停止服务
docker-compose -f docker/docker-compose.yml down

# 查看日志
docker-compose -f docker/docker-compose.yml logs -f
```

## 配置说明

### 环境变量

| 变量 | 描述 | 默认值 |
|------|------|--------|
| `PROXY_HOST` | 代理服务器主机 | `0.0.0.0` |
| `PROXY_PORT` | 代理服务器端口 | `1888` |
| `API_HOST` | API服务器主机 | `0.0.0.0` |
| `API_PORT` | API服务器端口 | `9000` |
| `FRONTEND_PORT` | 前端端口 | `2345` |
| `API_BASE_URL` | 前端API基础地址 | `http://localhost:9000` |
| `PROXY_BASE_URL` | 前端代理基础地址 | `http://localhost:1888` |
| `MCP_SERVER_HOST` | 客户端配置中的外部MCP服务器地址 | `http://127.0.0.1:1888` |
| `DEBUG_MODE` | 前端调试模式 | `false` |

### 网络配置

部署使用 `network_mode: host` 用于后端以确保：
- **DNS解析**：自动解析内网域名
- **网络兼容性**：与企业网络完全兼容
- **零配置**：无需硬编码IP或DNS服务器

## 生产环境部署

### 1. 环境设置

设置生产环境变量：

```bash
# 生产环境URL
export PROXY_BASE_URL="https://proxy.production.com"
export API_BASE_URL="https://api.production.com"
export MCP_SERVER_HOST="https://proxy.production.com"
export DEBUG_MODE="false"
export FRONTEND_PORT="80"

# 部署
./docker/deploy.sh up
```

### 2. GitLab CI/CD 集成

配置与 GitLab CI/CD 无缝集成：

```yaml
# .gitlab-ci.yml
deploy_production:
  script:
    - export PROXY_BASE_URL="${PRODUCTION_PROXY_URL}"
    - export API_BASE_URL="${PRODUCTION_API_URL}"
    - ./docker/deploy.sh up
```

### 3. 多环境支持

```bash
# 测试环境
PROXY_BASE_URL="https://proxy-staging.com" ./docker/deploy.sh up

# 生产环境
PROXY_BASE_URL="https://proxy.production.com" ./docker/deploy.sh up
```

## 架构说明

### 服务组件

1. **后端服务**
   - 包含所有MCP工具的LiteMCP服务器
   - 统一访问的代理服务器
   - 配置管理的API服务器
   - 使用主机网络确保DNS兼容性

2. **前端服务**
   - Vue.js Web界面
   - 基于Nginx的服务
   - 桥接网络与后端通信

### 网络设计

```
主机网络（后端）
├── 代理服务器 (1888)
├── API服务器 (9000)
└── MCP服务器 (8000+)

桥接网络（前端）
└── Web界面 (2345) → 通过localhost访问后端
```

## 开发环境

### 1. 开发模式

```bash
# 以开发模式启动
DEBUG_MODE=true ./docker/deploy.sh up

# 使用本地后端URL
API_BASE_URL=http://localhost:9000 \
PROXY_BASE_URL=http://localhost:1888 \
./docker/deploy.sh up
```

### 2. 卷挂载

用于实时重载的开发环境：

```bash
# 挂载源代码（修改docker-compose.yml）
volumes:
  - ./src:/app/src
  - ./config:/app/config
```

## 故障排除

### 常见问题

1. **DNS解析失败**
   - **解决方案**：使用 `network_mode: host` 自动解决此问题
   - **验证**：容器继承主机的DNS配置

2. **端口冲突**
   - 检查端口 1888、9000 或 2345 是否被占用
   - 根据需要修改端口环境变量

3. **服务通信**
   - 后端使用主机网络，可通过localhost访问
   - 前端通过localhost URL连接后端

### 调试命令

```bash
# 查看所有容器日志
./docker/deploy.sh logs

# 检查服务状态
./docker/deploy.sh status

# 在后端容器中执行shell
docker exec -it litemcp-backend bash

# 在容器中测试DNS解析
docker exec -it litemcp-backend nslookup your-domain.com
```

## 安全考虑

1. **网络模式**：主机网络提供完整的网络访问权限
2. **环境变量**：不要在构建参数中包含机密信息
3. **防火墙**：为暴露的端口配置主机防火墙
4. **更新**：定期更新基础镜像

## 性能优化

1. **多阶段构建**：优化的Docker镜像
2. **卷持久化**：重启时数据持久化
3. **健康检查**：内置服务监控
4. **资源限制**：根据环境需要进行配置