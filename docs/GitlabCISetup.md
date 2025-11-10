# GitLab CI/CD Auto-Deployment Configuration Guide

## Overview

This guide will help you configure GitLab CI/CD to automatically deploy the LiteMCP framework to a specified server using existing Docker deployment scripts after code merge.

**Features**:
- ✅ Directly uses existing `docker/deploy.sh` scripts
- ✅ Supports production and staging environments
- ✅ Manual trigger for production deployment, automatic trigger for staging deployment
- ✅ Simple configuration, easy to maintain

## Prerequisites

### 1. Server Preparation
- Target server has Docker and Docker Compose installed
- Server can access the internet (for pulling images)
- Server can access GitLab repository

### 2. GitLab Project Configuration
- Project has GitLab CI/CD enabled
- Has permission to install GitLab Runner on target server

## Configuration Steps

### 1. Install GitLab Runner on Target Server

#### 1.1 Download and Install GitLab Runner
```bash
# Download GitLab Runner docs: https://docs.gitlab.com/runner/install/linux-manually/#using-debrpm-package
sudo curl -L --output /usr/local/bin/gitlab-runner https://gitlab-runner-downloads.s3.amazonaws.com/latest/binaries/gitlab-runner-linux-amd64

# Set execution permissions
sudo chmod +x /usr/local/bin/gitlab-runner

# Create gitlab-runner user
sudo useradd --comment 'GitLab Runner' --create-home gitlab-runner --shell /bin/bash

# Install and start service
sudo gitlab-runner install --user=gitlab-runner --working-directory=/home/gitlab-runner
sudo gitlab-runner start

# Enable auto-start on boot
sudo systemctl enable gitlab-runner
sudo systemctl start gitlab-runner
```

#### 1.2 Verify Installation
```bash
# Check GitLab Runner status
sudo gitlab-runner status

# Check version
gitlab-runner --version
```

### 2. Register Runner in GitLab

#### 2.1 Get Registration Information
1. Go to GitLab project page
2. Click `Settings` → `CI/CD` → `Runner`
3. Expand the `Expand` button to find the following information:
   - **Register the runner with this URL**: `https://gitlab.com/` (usually use your private GitLab instance address, paid version uses https://gitlab.com/)
   - **registration token**: `xxxxxxxxxxxxxxxxxxxx`

#### 2.2 Register Runner
```bash
# Execute registration command on target server
sudo gitlab-runner register

# Enter the following information as prompted:
# GitLab instance URL: [URL copied from GitLab]
# Registration token: [Token copied from GitLab]
# Description: LiteMCP Deploy Runner
# Tags: litemcp,production  # Add more tags as needed, separated by commas
# Executor: shell  # Use shell if runner machine and docker for deployment are on the same machine, otherwise configure ssh or other methods as prompted
```
![GitLabRunners.png](GitLabRunners.png)

#### 2.3 Verify Registration
```bash
# View registered Runners
sudo gitlab-runner list

# Check Runner status
sudo gitlab-runner verify
```

### 3. Configure Runner Permissions

#### 3.1 Add gitlab-runner user to docker group
```bash
# Add user to docker group
sudo usermod -aG docker gitlab-runner

# Restart GitLab Runner service
sudo systemctl restart gitlab-runner

# Verify permissions
sudo -u gitlab-runner docker ps
```

#### 3.2 Configure Working Directory Permissions
```bash
# Ensure gitlab-runner user has permission to create directories
sudo chown gitlab-runner:gitlab-runner /home/gitlab-runner

# Note: Deployment directories will be automatically created during CI/CD execution, no manual creation needed
```

### 4. Configure GitLab CI/CD Environment Variables

#### 4.1 Set Project Environment Variables
Configure the required environment variables for deployment in your GitLab project:

1. Go to GitLab project page
2. Click `Settings` → `CI/CD` → `Variables`
3. Add the following variables:

| Variable Name | Value | Description | Environment |
|---------------|-------|-------------|-------------|
| `PRODUCTION_API_URL` | `https://api.your-domain.com` | Production environment API server URL | Production |
| `PRODUCTION_PROXY_URL` | `https://proxy.your-domain.com` | Production environment proxy server URL | Production |
| `STAGING_API_URL` | `https://api-staging.your-domain.com` | Staging environment API server URL | Staging |
| `STAGING_PROXY_URL` | `https://proxy-staging.your-domain.com` | Staging environment proxy server URL | Staging |

**Important Notes**:
- These URLs should be externally accessible addresses, not `localhost`
- If your API and proxy services are deployed on the same server, you can use the server's public IP or domain name
- For example: `https://your-server-ip:9000` or `https://api.your-domain.com`

#### 4.2 Environment Variable Configuration Examples

**Production Environment Configuration**:
```bash
PRODUCTION_API_URL=https://api.production.com:9000
PRODUCTION_PROXY_URL=https://proxy.production.com:1888
```

**Staging Environment Configuration**:
```bash
STAGING_API_URL=https://api-staging.production.com:9000
STAGING_PROXY_URL=https://proxy-staging.production.com:1888
```

### 5. Test Configuration

#### 5.1 Manual Runner Testing
```bash
# Switch to gitlab-runner user
sudo su - gitlab-runner

# Test Docker permissions
docker ps

# Test directory creation permissions
mkdir -p /home/gitlab-runner/test
rm -rf /home/gitlab-runner/test

# Note: Deployment scripts will automatically sync code and execute during CI/CD execution
```

## Deployment Process Description

### Auto-Deployment Trigger Conditions

| Branch | Environment | Trigger Method | Port Configuration |
|--------|-------------|----------------|-------------------|
| `main` | Production | Manual Trigger | 9000, 1888, 2345 |
| `develop` | Staging | Automatic Trigger | 9000, 1888, 2345 |

### Deployment Process

1. **Code Push** → GitLab detects code changes
2. **Runner Execution** → Execute tasks in `.gitlab-ci.yml` on target server
3. **Environment Variable Setup** → Set API and proxy server addresses based on branch
4. **Code Sync** → Pull latest code from GitLab repository
5. **Docker Build** → Build frontend with environment variables to ensure correct API addresses
6. **Service Startup** → Use `docker/deploy.sh` script to start services
7. **Health Check** → Verify services are running normally

### Environment Variable Flow

```
GitLab CI Variables → Environment Export → deploy.sh Script → docker-compose → Dockerfile → Vite Build → Frontend Application
```

**Key Points**:
- Frontend compiles API addresses into static files during build time
- Correct environment variables must be passed during Docker build stage
- API addresses cannot be dynamically modified at runtime

## Port Configuration

### Unified Port Configuration
- **Frontend Service**: `2345`
- **Backend API**: `9000`
- **Proxy Service**: `1888`

### Environment Differentiation
- **Production Environment**: Deploy to `/home/gitlab-runner/litemcp` directory
- **Staging Environment**: Deploy to `/home/gitlab-runner/litemcp-staging` directory

## Monitoring and Logs

### 1. Deployment Logs
- **GitLab CI/CD Logs**: View on GitLab project page
- **Server Logs**: `/home/gitlab-runner/litemcp/runtime/logs/`

### 2. Health Check
```bash
# Check service status
curl http://localhost:9000/api/v1/health
curl http://localhost:2345

# Check Docker container status
docker ps
docker logs litemcp-backend
docker logs litemcp-frontend
```

### 3. Monitoring Script
```bash
#!/bin/bash
# Create monitoring script
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

## Troubleshooting

### Common Issues

1. **Runner Connection Failed**
   - Check GitLab Runner service status: `sudo systemctl status gitlab-runner`
   - Verify Runner registration: `sudo gitlab-runner list`
   - View Runner logs: `sudo journalctl -u gitlab-runner`

2. **Docker Permission Issues**
   - Ensure gitlab-runner user is in docker group: `groups gitlab-runner`
   - Restart GitLab Runner service: `sudo systemctl restart gitlab-runner`

3. **Port Conflicts**
   - Check port usage: `netstat -tlnp | grep :9000`
   - Stop conflicting services: `docker stop $(docker ps -q)`

4. **Deployment Failed**
   - View GitLab CI/CD logs
   - Check server disk space: `df -h`
   - Verify network connection: `ping gitlab.com`

### Rollback Operations

If deployment issues occur:

1. **Use GitLab Rollback**:
   - Find failed deployment on GitLab project page
   - Click "Rollback" button

2. **Manual Rollback**:
   ```bash
   # Switch to gitlab-runner user
   sudo su - gitlab-runner
   
   # Stop current services
   cd /home/gitlab-runner/litemcp
   ./docker/deploy.sh down
   
   # Rollback to previous version
   git reset --hard HEAD~1
   
   # Redeploy
   ./docker/deploy.sh up
   ```

## Verify Deployment

### 1. Check Runner Status
```bash
# View Runner status
sudo gitlab-runner status

# View registered Runners
sudo gitlab-runner list
```

### 2. Test CI/CD Process
1. Push code to `develop` branch → Should automatically trigger staging environment deployment
2. Merge to `main` branch → Manually trigger production environment deployment in GitLab interface

### 3. Verify Service Running
```bash
# Check if services are running normally
curl http://localhost:9000/api/v1/health
curl http://localhost:2345

# View Docker container status
docker ps
```

## Contact Support

If you encounter issues during configuration, please:
1. View GitLab CI/CD logs
2. Check Runner logs: `sudo journalctl -u gitlab-runner`
3. Refer to project documentation
4. Submit an Issue to the project repository
