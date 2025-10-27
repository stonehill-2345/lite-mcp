# 环境配置指南

## 概述

LiteMCP 前端使用环境变量来管理 API 端点和配置设置。这允许在不同环境（开发、测试、生产）之间灵活部署，无需修改代码。

## 环境变量

### API 配置

| 变量 | 描述 | 默认值 | 示例 |
|------|------|--------|------|
| `VITE_API_BASE_URL` | 后端 API 服务器地址 | `http://localhost:9000` | `https://api.your-domain.com` |
| `VITE_API_TIMEOUT` | API 请求超时时间（毫秒） | `40000` | `30000` |
| `VITE_PROXY_BASE_URL` | 代理服务器地址 | `http://localhost:1888` | `https://proxy.your-domain.com` |

### 应用配置

| 变量 | 描述 | 默认值 | 示例 |
|------|------|--------|------|
| `VITE_APP_TITLE` | 应用标题 | `LiteMCP Configuration` | `我的 MCP 控制台` |
| `VITE_APP_VERSION` | 应用版本 | `1.0.0` | `2.1.0` |

### 调试配置

| 变量 | 描述 | 默认值 | 示例 |
|------|------|--------|------|
| `VITE_DEBUG_MODE` | 启用调试模式 | `true` | `false` |
| `VITE_LOG_LEVEL` | 日志级别 | `info` | `error` |

## 环境文件

### 开发环境 (.env.development)

```bash
# 开发环境
VITE_API_BASE_URL=http://localhost:9000
VITE_PROXY_BASE_URL=http://localhost:1888
VITE_DEBUG_MODE=true
VITE_LOG_LEVEL=debug
```

### 生产环境 (.env.production)

```bash
# 生产环境
VITE_API_BASE_URL=https://api.your-domain.com
VITE_PROXY_BASE_URL=https://proxy.your-domain.com
VITE_DEBUG_MODE=false
VITE_LOG_LEVEL=error
```

### 测试环境 (.env.staging)

```bash
# 测试环境
VITE_API_BASE_URL=https://staging-api.your-domain.com
VITE_PROXY_BASE_URL=https://staging-proxy.your-domain.com
VITE_DEBUG_MODE=true
VITE_LOG_LEVEL=info
```

## 设置说明

### 1. 创建环境文件

复制示例文件并根据您的环境进行修改：

```bash
# 复制示例文件
cp env.example .env

# 编辑文件
nano .env
```

### 2. 设置环境变量

#### 方式 A：使用 .env 文件（推荐）

创建特定环境的文件：
- `.env.development` - 开发环境
- `.env.production` - 生产环境
- `.env.staging` - 测试环境

#### 方式 B：系统环境变量

在系统或 CI/CD 流水线中设置环境变量：

```bash
export VITE_API_BASE_URL=https://api.your-domain.com
export VITE_PROXY_BASE_URL=https://proxy.your-domain.com
```

#### 方式 C：Docker 环境

```dockerfile
# 在 Dockerfile 中
ENV VITE_API_BASE_URL=https://api.your-domain.com
ENV VITE_PROXY_BASE_URL=https://proxy.your-domain.com
```

或在 docker-compose.yml 中：

```yaml
services:
  frontend:
    build: .
    environment:
      - VITE_API_BASE_URL=https://api.your-domain.com
      - VITE_PROXY_BASE_URL=https://proxy.your-domain.com
```

## 构建命令

### 开发环境

```bash
npm run dev
# 或
yarn dev
```

### 生产构建

```bash
# 使用生产环境构建
npm run build
# 或
yarn build

# 使用特定环境构建
npm run build --mode production
npm run build --mode staging
```

## 代码中的使用

### 导入配置

```javascript
import { API_CONFIG, getApiUrl, getProxyUrl } from '@/services/config/ApiConfig'

// 使用配置
console.log('API 基础地址:', API_CONFIG.BASE_URL)
console.log('完整 API 地址:', getApiUrl('/api/v1/config'))
console.log('代理地址:', getProxyUrl('/proxy/status'))
```

### 环境检测

```javascript
import { getCurrentEnvironment, isDevelopment, isProduction } from '@/services/config/ApiConfig'

if (isDevelopment()) {
  console.log('运行在开发模式')
}

if (isProduction()) {
  // 生产环境特定代码
}
```

## 部署示例

### Nginx 部署

```nginx
server {
    listen 80;
    server_name your-frontend-domain.com;
    
    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
    }
    
    # 代理 API 请求到后端
    location /api/ {
        proxy_pass http://your-backend-server:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Docker 部署

```dockerfile
# 多阶段构建
FROM node:18-alpine as builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .

# 使用环境变量构建
ARG VITE_API_BASE_URL
ARG VITE_PROXY_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_PROXY_BASE_URL=$VITE_PROXY_BASE_URL

RUN npm run build

# 生产阶段
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
```

### CI/CD 流水线（GitHub Actions）

```yaml
name: 部署前端

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: 设置 Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          
      - name: 安装依赖
        run: npm ci
        
      - name: 构建
        env:
          VITE_API_BASE_URL: ${{ secrets.API_BASE_URL }}
          VITE_PROXY_BASE_URL: ${{ secrets.PROXY_BASE_URL }}
        run: npm run build
        
      - name: 部署
        # 您的部署步骤
```

## 故障排除

### 常见问题

1. **环境变量未加载**
   - 确保变量以 `VITE_` 开头
   - 检查文件命名（`.env`、`.env.production` 等）
   - 修改后重启开发服务器

2. **API 调用失败**
   - 验证 `VITE_API_BASE_URL` 是否正确
   - 检查后端的 CORS 设置
   - 确保后端可从前端访问

3. **构建问题**
   - 环境变量在构建时嵌入
   - 修改环境变量后需要重新构建
   - 检查变量名是否有拼写错误

### 调试配置

启用调试模式查看配置值：

```bash
VITE_DEBUG_MODE=true npm run dev
```

检查浏览器控制台的配置输出。

## 安全注意事项

- 永远不要提交包含敏感数据的 `.env` 文件
- 使用 `.env.example` 作为文档
- 环境变量会嵌入到构建中，对用户可见
- 不要在前端环境变量中存储密钥
- 敏感配置使用后端环境变量
