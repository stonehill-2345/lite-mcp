# LiteMCP Frontend Docker Deployment

This directory contains Docker-related files for deploying the LiteMCP frontend.

## Files Overview

- `Dockerfile` - Multi-stage Docker build configuration
- `docker-compose.yml` - Docker Compose configuration
- `nginx.conf` - Nginx configuration for production
- `README.md` - This documentation
- `README.zh_CN.md` - Chinese documentation

## Quick Start

### 1. Using Deploy Script (Recommended)

The easiest way to deploy the frontend is using the `deploy.sh` script:

```bash
# 🚀 One-click build and start frontend service
./deploy.sh up

# 🚀 Build and start with custom API URLs
./deploy.sh up --api-url https://api.example.com --proxy-url https://proxy.example.com

# 🔨 Only build the application (for development)
./deploy.sh build

# 🛑 Stop the service
./deploy.sh down

# 📋 View logs
./deploy.sh logs

# 📊 Check status
./deploy.sh status
```

**Key Features:**
- ✅ **One-click deployment**: `up` command automatically builds and starts the service
- ✅ **Docker-based build**: Uses Node.js 18 in Docker for consistent builds
- ✅ **Environment variables**: Easy configuration via command-line options
- ✅ **Service management**: Full lifecycle management (up/down/restart/logs/status)

#### Available Commands:
- `up` - **One-click build and start frontend service** (default) 🚀
- `down` - Stop frontend service
- `restart` - Restart frontend service
- `logs` - Show frontend service logs
- `status` - Show frontend service status
- `build` - Build frontend application only (for development)

#### Available Options:
- `-e, --environment` - Environment (development|staging|production) [default: production]
- `-a, --api-url` - API base URL
- `-p, --proxy-url` - Proxy base URL
- `-b, --build-only` - Only build, don't deploy
- `-h, --help` - Show help message

### 2. Manual Docker Commands

If you prefer manual Docker commands:

```bash
# Build with default settings
docker build -t litemcp-frontend .

# Build with custom API URLs
docker build -t litemcp-frontend \
  --build-arg VITE_API_BASE_URL=https://api.your-domain.com \
  --build-arg VITE_PROXY_BASE_URL=https://proxy.your-domain.com \
  .

# Run container
docker run -d -p 2345:80 --name litemcp-frontend litemcp-frontend
```

### 3. Using Deploy Script (Recommended)

The easiest way to configure and deploy the frontend is using the `deploy.sh` script:

```bash
# Copy the example file (optional, for custom configuration)
cp .env.example .env

# Edit the configuration (optional)
nano .env

# Start services using deploy script
./deploy.sh up

# Stop services
./deploy.sh down
```

The deploy script automatically handles Docker Compose operations and provides additional features:

```bash
# Start with custom API URLs
./deploy.sh up --api-url https://api.your-domain.com --proxy-url https://proxy.your-domain.com

# Start in development mode
./deploy.sh up --environment development

# Build only (without deployment)
./deploy.sh build

# View logs
./deploy.sh logs

# Check status
./deploy.sh status

# Restart service
./deploy.sh restart
```

### 4. Direct Docker Compose (Advanced)

If you prefer to use Docker Compose directly:

```bash
# Copy the example file
cp .env.example .env

# Edit the configuration
nano .env

# Start services
docker-compose up -d

# Stop services
docker-compose down
```

## Configuration

### Build Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API server URL | `http://localhost:9000` |
| `VITE_PROXY_BASE_URL` | Proxy server URL | `http://localhost:1888` |
| `VITE_DEBUG_MODE` | Enable debug mode | `false` |
| `VITE_LOG_LEVEL` | Logging level | `error` |

### Environment Variables

The same variables can be set as environment variables when running the container.

## Production Deployment

### 1. Deploy with Deploy Script (Recommended)

The easiest way to deploy for production is using the deploy script:

```bash
# Deploy with production URLs
./deploy.sh up --environment production \
  --api-url https://api.production.com \
  --proxy-url https://proxy.production.com
```

Or create a `.env` file for custom configuration:

```bash
# Copy example file
cp .env.example .env

# Edit for production
nano .env
# Set:
# VITE_API_BASE_URL=https://api.production.com
# VITE_PROXY_BASE_URL=https://proxy.production.com
# VITE_DEBUG_MODE=false
# VITE_LOG_LEVEL=error

# Deploy
./deploy.sh up --environment production
```

### 2. Build Only for Production

If you only want to build without deploying:

```bash
# Build for production
./deploy.sh build --environment production \
  --api-url https://api.production.com \
  --proxy-url https://proxy.production.com
```

### 3. Direct Docker Build (Advanced)

If you prefer manual Docker commands:

```bash
docker build -t litemcp-frontend:latest \
  --build-arg VITE_API_BASE_URL=https://api.production.com \
  --build-arg VITE_PROXY_BASE_URL=https://proxy.production.com \
  --build-arg VITE_DEBUG_MODE=false \
  --build-arg VITE_LOG_LEVEL=error \
  .
```

### 3. Behind a Reverse Proxy

If you're using a reverse proxy (like Nginx or Traefik), you can configure it to route traffic to the container:

```nginx
# Nginx configuration
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

## Development

### 1. Development with Deploy Script (Recommended)

```bash
# Start in development mode
./deploy.sh up --environment development

# Or with custom API URLs
./deploy.sh up --environment development \
  --api-url http://localhost:9000 \
  --proxy-url http://localhost:1888
```

### 2. Development with Docker (Advanced)

```bash
# Build development image
docker build -t litemcp-frontend:dev \
  --build-arg VITE_DEBUG_MODE=true \
  --build-arg VITE_LOG_LEVEL=debug \
  .

# Run development container
docker run -d -p 2345:80 --name litemcp-frontend-dev litemcp-frontend:dev
```

### 2. Volume Mounting for Development

For development with live reload, you can mount the source code:

```bash
docker run -d -p 2345:3000 \
  -v $(pwd):/app \
  -w /app \
  node:18-alpine \
  npm run dev
```

## Troubleshooting

### Common Issues

1. **Container fails to start**
   - Check if port 2345 is already in use
   - Verify environment variables are set correctly
   - Check Docker logs: `docker logs litemcp-frontend`

2. **API calls failing**
   - Verify `VITE_API_BASE_URL` is accessible from the browser
   - Check CORS settings on the backend
   - Ensure the backend server is running

3. **Build fails**
   - Check if all dependencies are available
   - Verify Node.js version compatibility
   - Check for syntax errors in source code

### Debug Commands

```bash
# View container logs
docker logs litemcp-frontend

# Execute shell in container
docker exec -it litemcp-frontend sh

# Check container status
docker ps

# View container details
docker inspect litemcp-frontend
```

## Security Considerations

1. **Environment Variables**: Don't include sensitive data in build arguments as they are visible in the image
2. **Nginx Configuration**: The included nginx.conf has basic security headers
3. **Network**: Consider using Docker networks for service communication
4. **Updates**: Regularly update the base images for security patches

## Performance Optimization

1. **Multi-stage Build**: The Dockerfile uses multi-stage build to reduce image size
2. **Nginx Compression**: Gzip compression is enabled for better performance
3. **Static Asset Caching**: Long-term caching for static assets
4. **Health Checks**: Built-in health check for container monitoring
