# GitLab CI/CD 自动部署配置指南

## 概述

本指南将帮助您配置GitLab CI/CD，使用现有的Docker部署脚本实现代码合并后自动部署LiteMCP框架到指定服务器。

**特点**：
- ✅ 直接使用现有的 `docker/deploy.sh` 脚本
- ✅ 支持生产环境和测试环境
- ✅ 手动触发生产部署，自动触发测试部署
- ✅ 简单的配置，易于维护

## 前置条件

### 1. 服务器准备
- 目标服务器已安装Docker和Docker Compose
- 服务器可以访问互联网（用于拉取镜像）
- 服务器可以访问GitLab仓库

### 2. GitLab项目配置
- 项目已启用GitLab CI/CD
- 有权限在目标服务器上安装GitLab Runner

## 配置步骤

### 1. 在目标服务器上安装GitLab Runner

#### 1.1 下载并安装GitLab Runner
```bash
# 下载GitLab Runner docs: https://docs.gitlab.com/runner/install/linux-manually/#using-debrpm-package
sudo curl -L --output /usr/local/bin/gitlab-runner https://gitlab-runner-downloads.s3.amazonaws.com/latest/binaries/gitlab-runner-linux-amd64

# 设置执行权限
sudo chmod +x /usr/local/bin/gitlab-runner

# 创建gitlab-runner用户
sudo useradd --comment 'GitLab Runner' --create-home gitlab-runner --shell /bin/bash

# 安装并启动服务
sudo gitlab-runner install --user=gitlab-runner --working-directory=/home/gitlab-runner
sudo gitlab-runner start

# 开机自启
sudo systemctl enable gitlab-runner
sudo systemctl start gitlab-runner
```

#### 1.2 验证安装
```bash
# 检查GitLab Runner状态
sudo gitlab-runner status

# 查看版本
gitlab-runner --version
```

### 2. 在GitLab中注册Runner

#### 2.1 获取注册信息
1. 进入GitLab项目页面
2. 点击 `设置` → `CI/CD` → `Runner`
3. 展开 `展开` 按钮，找到以下信息：
   - **Register the runner with this URL**: `https://gitlab.com/` (一般使用自己私有部署的GitLab实例地址，付费版本则是https://gitlab.com/)
   - **registration token**: `xxxxxxxxxxxxxxxxxxxx`

#### 2.2 注册Runner
```bash
# 在目标服务器上执行注册命令
sudo gitlab-runner register

# 按提示输入以下信息：
# GitLab instance URL: [从GitLab复制的URL]
# Registration token: [从GitLab复制的令牌]
# Description: LiteMCP Deploy Runner
# Tags: litemcp,production  # 可以按需添加更多标签以英文逗号分隔
# Executor: shell  # runner机器和用于部署的docker在同一台机器则为shell，其他机器则需要按照提示配置ssh或其他方式
```
![GitLabRunners.png](GitLabRunners.png)

#### 2.3 验证注册
```bash
# 查看已注册的Runner
sudo gitlab-runner list

# 检查Runner状态
sudo gitlab-runner verify
```

### 3. 配置Runner权限

#### 3.1 将gitlab-runner用户添加到docker组
```bash
# 添加用户到docker组
sudo usermod -aG docker gitlab-runner

# 重启GitLab Runner服务
sudo systemctl restart gitlab-runner

# 验证权限
sudo -u gitlab-runner docker ps
```

#### 3.2 配置工作目录权限
```bash
# 确保gitlab-runner用户有权限创建目录
sudo chown gitlab-runner:gitlab-runner /home/gitlab-runner

# 注意：部署目录会在CI/CD执行时自动创建，无需手动创建
```

### 4. 配置GitLab CI/CD环境变量

#### 4.1 设置项目环境变量
在GitLab项目中配置部署所需的环境变量：

1. 进入GitLab项目页面
2. 点击 `设置` → `CI/CD` → `变量`
3. 添加以下变量：

| 变量名 | 值 | 描述 | 环境 |
|--------|----|----- |------|
| `PRODUCTION_API_URL` | `https://api.your-domain.com` | 生产环境API服务器地址 | 生产 |
| `PRODUCTION_PROXY_URL` | `https://proxy.your-domain.com` | 生产环境代理服务器地址 | 生产 |
| `STAGING_API_URL` | `https://api-staging.your-domain.com` | 测试环境API服务器地址 | 测试 |
| `STAGING_PROXY_URL` | `https://proxy-staging.your-domain.com` | 测试环境代理服务器地址 | 测试 |

**重要说明**：
- 这些URL应该是外部可访问的地址，不能使用`localhost`
- 如果你的API和代理服务部署在同一台服务器上，可以使用服务器的公网IP或域名
- 例如：`https://your-server-ip:9000` 或 `https://api.your-domain.com`

#### 4.2 环境变量配置示例

**生产环境配置**：
```bash
PRODUCTION_API_URL=https://api.production.com:9000
PRODUCTION_PROXY_URL=https://proxy.production.com:1888
```

**测试环境配置**：
```bash
STAGING_API_URL=https://api-staging.production.com:9000
STAGING_PROXY_URL=https://proxy-staging.production.com:1888
```

### 5. 测试配置

#### 5.1 手动测试Runner
```bash
# 切换到gitlab-runner用户
sudo su - gitlab-runner

# 测试Docker权限
docker ps

# 测试目录创建权限
mkdir -p /home/gitlab-runner/test
rm -rf /home/gitlab-runner/test

# 注意：部署脚本会在CI/CD执行时自动同步代码并执行
```

## 部署流程说明

### 自动部署触发条件

| 分支 | 环境 | 触发方式 | 端口配置 |
|------|------|----------|----------|
| `main` | 生产环境 | 手动触发 | 9000, 1888, 2345 |
| `develop` | 测试环境 | 自动触发 | 9000, 1888, 2345 |

### 部署流程

1. **代码推送** → GitLab检测到代码变更
2. **Runner执行** → 在目标服务器上执行`.gitlab-ci.yml`中的任务
3. **环境变量设置** → 根据分支设置对应的API和代理服务器地址
4. **代码同步** → 从GitLab仓库拉取最新代码
5. **Docker构建** → 使用环境变量构建前端，确保API地址正确
6. **服务启动** → 使用`docker/deploy.sh`脚本启动服务
7. **健康检查** → 验证服务是否正常运行

### 环境变量传递链路

```
GitLab CI变量 → 环境变量导出 → deploy.sh脚本 → docker-compose → Dockerfile → Vite构建 → 前端应用
```

**关键点**：
- 前端在构建时会将API地址编译到静态文件中
- 必须在Docker构建阶段传递正确的环境变量
- 不能在运行时动态修改API地址

## 端口配置

### 统一端口配置
- **前端服务**: `2345`
- **后端API**: `9000`
- **代理服务**: `1888`

### 环境区分
- **生产环境**: 部署到 `/home/gitlab-runner/litemcp` 目录
- **测试环境**: 部署到 `/home/gitlab-runner/litemcp-staging` 目录

## 监控和日志

### 1. 部署日志
- **GitLab CI/CD日志**: 在GitLab项目页面查看
- **服务器日志**: `/home/gitlab-runner/litemcp/runtime/logs/`

### 2. 健康检查
```bash
# 检查服务状态
curl http://localhost:9000/api/v1/health
curl http://localhost:2345

# 检查Docker容器状态
docker ps
docker logs litemcp-backend
docker logs litemcp-frontend
```

### 3. 监控脚本
```bash
#!/bin/bash
# 创建监控脚本
cat > /home/gitlab-runner/litemcp/monitor.sh << 'EOF'
#!/bin/bash
echo "=== LiteMCP Service Status ==="
echo "Backend API:"
curl -s http://localhost:9000/api/v1/health || echo "Backend API is down"
echo "Frontend:"
curl -s http://localhost:2345 || echo "Frontend is down"
echo "Docker Containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
EOF

chmod +x /home/gitlab-runner/litemcp/monitor.sh
```

## 故障排除

### 常见问题

1. **Runner连接失败**
   - 检查GitLab Runner服务状态: `sudo systemctl status gitlab-runner`
   - 验证Runner注册: `sudo gitlab-runner list`
   - 查看Runner日志: `sudo journalctl -u gitlab-runner`

2. **Docker权限问题**
   - 确保gitlab-runner用户在docker组: `groups gitlab-runner`
   - 重启GitLab Runner服务: `sudo systemctl restart gitlab-runner`

3. **端口冲突**
   - 检查端口占用: `netstat -tlnp | grep :9000`
   - 停止冲突服务: `docker stop $(docker ps -q)`

4. **部署失败**
   - 查看GitLab CI/CD日志
   - 检查服务器磁盘空间: `df -h`
   - 验证网络连接: `ping gitlab.com`

### 回滚操作

如果部署出现问题：

1. **使用GitLab回滚**:
   - 在GitLab项目页面找到失败的部署
   - 点击"回滚"按钮

2. **手动回滚**:
   ```bash
   # 切换到gitlab-runner用户
   sudo su - gitlab-runner
   
   # 停止当前服务
   cd /home/gitlab-runner/litemcp
   ./docker/deploy.sh down
   
   # 回滚到上一个版本
   git reset --hard HEAD~1
   
   # 重新部署
   ./docker/deploy.sh up
   ```

## 验证部署

### 1. 检查Runner状态
```bash
# 查看Runner状态
sudo gitlab-runner status

# 查看已注册的Runner
sudo gitlab-runner list
```

### 2. 测试CI/CD流程
1. 推送代码到`develop`分支 → 应该自动触发测试环境部署
2. 合并到`main`分支 → 在GitLab界面手动触发生产环境部署

### 3. 验证服务运行
```bash
# 检查服务是否正常运行
curl http://localhost:9000/api/v1/health
curl http://localhost:2345

# 查看Docker容器状态
docker ps
```

## 联系支持

如果在配置过程中遇到问题，请：
1. 查看GitLab CI/CD日志
2. 检查Runner日志: `sudo journalctl -u gitlab-runner`
3. 参考项目文档
4. 提交Issue到项目仓库
