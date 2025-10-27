# LiteMCP Full Stack Docker Deployment

This directory contains Docker-related files for deploying the complete LiteMCP stack (backend + frontend).

## Files Overview

- `Dockerfile` - Multi-stage Docker build configuration for backend
- `docker-compose.yml` - Docker Compose configuration for full stack
- `deploy.sh` - Deployment script with full lifecycle management
- `README.md` - This documentation
- `README.zh_CN.md` - Chinese documentation

## Quick Start

### 1. Using Deploy Script (Recommended)

The easiest way to deploy LiteMCP is using the `deploy.sh` script:

```bash
# 🚀 One-click deployment of full stack
./docker/deploy.sh up

# 🚀 Deploy with custom URLs
PROXY_BASE_URL=https://proxy.your-domain.com \
API_BASE_URL=https://api.your-domain.com \
./docker/deploy.sh up

# 🛑 Stop all services
./docker/deploy.sh down

# 📋 View logs
./docker/deploy.sh logs

# 📊 Check status
./docker/deploy.sh status
```

**Key Features:**
- ✅ **Full stack deployment**: Backend + Frontend in one command
- ✅ **Environment configuration**: Easy setup via environment variables
- ✅ **Network compatibility**: Automatic DNS resolution for internal domains
- ✅ **Service management**: Complete lifecycle management

#### Available Commands:
- `up` - **Start all services** (default) 🚀
- `down` - Stop all services
- `restart` - Restart all services
- `logs` - Show service logs
- `status` - Show service status
- `clean` - Clean up containers and volumes

### 2. Manual Docker Compose

If you prefer manual Docker Compose commands:

```bash
# Start services
docker-compose -f docker/docker-compose.yml up -d

# Stop services
docker-compose -f docker/docker-compose.yml down

# View logs
docker-compose -f docker/docker-compose.yml logs -f
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROXY_HOST` | Proxy server host | `0.0.0.0` |
| `PROXY_PORT` | Proxy server port | `1888` |
| `API_HOST` | API server host | `0.0.0.0` |
| `API_PORT` | API server port | `9000` |
| `FRONTEND_PORT` | Frontend port | `2345` |
| `API_BASE_URL` | Frontend API base URL | `http://localhost:9000` |
| `PROXY_BASE_URL` | Frontend proxy base URL | `http://localhost:1888` |
| `MCP_SERVER_HOST` | External MCP server URL for client configs | `http://127.0.0.1:1888` |
| `DEBUG_MODE` | Frontend debug mode | `false` |

### Network Configuration

The deployment uses `network_mode: host` for the backend to ensure:
- **DNS Resolution**: Automatic resolution of internal domain names
- **Network Compatibility**: Full compatibility with corporate networks
- **No Configuration**: No need to hardcode IPs or DNS servers

## Production Deployment

### 1. Environment Setup

Set production environment variables:

```bash
# Production URLs
export PROXY_BASE_URL="https://proxy.production.com"
export API_BASE_URL="https://api.production.com"
export MCP_SERVER_HOST="https://proxy.production.com"
export DEBUG_MODE="false"
export FRONTEND_PORT="80"

# Deploy
./docker/deploy.sh up
```

### 2. GitLab CI/CD Integration

The configuration works seamlessly with GitLab CI/CD:

```yaml
# .gitlab-ci.yml
deploy_production:
  script:
    - export PROXY_BASE_URL="${PRODUCTION_PROXY_URL}"
    - export API_BASE_URL="${PRODUCTION_API_URL}"
    - ./docker/deploy.sh up
```

### 3. Multiple Environment Support

```bash
# Staging
PROXY_BASE_URL="https://proxy-staging.com" ./docker/deploy.sh up

# Production
PROXY_BASE_URL="https://proxy.production.com" ./docker/deploy.sh up
```

## Architecture

### Services

1. **Backend Service**
   - LiteMCP server with all MCP tools
   - Proxy server for unified access
   - API server for configuration
   - Uses host network for DNS compatibility

2. **Frontend Service**
   - Vue.js web interface
   - Nginx-based serving
   - Bridge network with backend communication

### Network Design

```
Host Network (Backend)
├── Proxy Server (1888)
├── API Server (9000)
└── MCP Servers (8000+)

Bridge Network (Frontend)
└── Web Interface (2345) → Backend via localhost
```

## Development

### 1. Development Mode

```bash
# Start in development mode
DEBUG_MODE=true ./docker/deploy.sh up

# With local backend URLs
API_BASE_URL=http://localhost:9000 \
PROXY_BASE_URL=http://localhost:1888 \
./docker/deploy.sh up
```

### 2. Volume Mounting

For development with live reload:

```bash
# Mount source code (modify docker-compose.yml)
volumes:
  - ./src:/app/src
  - ./config:/app/config
```

## Troubleshooting

### Common Issues

1. **DNS Resolution Failures**
   - **Solution**: Using `network_mode: host` automatically resolves this
   - **Verification**: Container inherits host's DNS configuration

2. **Port Conflicts**
   - Check if ports 1888, 9000, or 2345 are in use
   - Modify port environment variables if needed

3. **Service Communication**
   - Backend uses host network, accessible via localhost
   - Frontend connects to backend via localhost URLs

### Debug Commands

```bash
# View all container logs
./docker/deploy.sh logs

# Check service status
./docker/deploy.sh status

# Execute shell in backend container
docker exec -it litemcp-backend bash

# Test DNS resolution in container
docker exec -it litemcp-backend nslookup your-domain.com
```

## Security Considerations

1. **Network Mode**: Host network provides full network access
2. **Environment Variables**: Don't include secrets in build args
3. **Firewall**: Configure host firewall for exposed ports
4. **Updates**: Regularly update base images

## Performance Optimization

1. **Multi-stage Build**: Optimized Docker images
2. **Volume Persistence**: Data persistence across restarts
3. **Health Checks**: Built-in service monitoring
4. **Resource Limits**: Configure as needed for your environment
