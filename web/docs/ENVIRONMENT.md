# Environment Configuration Guide

## Overview

The LiteMCP frontend uses environment variables to manage API endpoints and configuration settings. This allows for flexible deployment across different environments (development, staging, production) without code changes.

## Environment Variables

### API Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `VITE_API_BASE_URL` | Backend API server URL | `http://localhost:9000` | `https://api.your-domain.com` |
| `VITE_API_TIMEOUT` | API request timeout (ms) | `40000` | `30000` |
| `VITE_PROXY_BASE_URL` | Proxy server URL | `http://localhost:1888` | `https://proxy.your-domain.com` |

### Application Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `VITE_APP_TITLE` | Application title | `LiteMCP Configuration` | `My MCP Dashboard` |
| `VITE_APP_VERSION` | Application version | `1.0.0` | `2.1.0` |

### Debug Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `VITE_DEBUG_MODE` | Enable debug mode | `true` | `false` |
| `VITE_LOG_LEVEL` | Logging level | `info` | `error` |

## Environment Files

### Development (.env.development)

```bash
# Development Environment
VITE_API_BASE_URL=http://localhost:9000
VITE_PROXY_BASE_URL=http://localhost:1888
VITE_DEBUG_MODE=true
VITE_LOG_LEVEL=debug
```

### Production (.env.production)

```bash
# Production Environment
VITE_API_BASE_URL=https://api.your-domain.com
VITE_PROXY_BASE_URL=https://proxy.your-domain.com
VITE_DEBUG_MODE=false
VITE_LOG_LEVEL=error
```

### Staging (.env.staging)

```bash
# Staging Environment
VITE_API_BASE_URL=https://staging-api.your-domain.com
VITE_PROXY_BASE_URL=https://staging-proxy.your-domain.com
VITE_DEBUG_MODE=true
VITE_LOG_LEVEL=info
```

## Setup Instructions

### 1. Create Environment File

Copy the example file and modify according to your environment:

```bash
# Copy example file
cp .env.example .env

# Edit the file
nano .env
```

### 2. Set Environment Variables

#### Option A: Using .env files (Recommended)

Create environment-specific files:
- `.env.development` - for development
- `.env.production` - for production
- `.env.staging` - for staging

#### Option B: System Environment Variables

Set environment variables in your system or CI/CD pipeline:

```bash
export VITE_API_BASE_URL=https://api.your-domain.com
export VITE_PROXY_BASE_URL=https://proxy.your-domain.com
```

#### Option C: Docker Environment

```dockerfile
# In Dockerfile
ENV VITE_API_BASE_URL=https://api.your-domain.com
ENV VITE_PROXY_BASE_URL=https://proxy.your-domain.com
```

Or in docker-compose.yml:

```yaml
services:
  frontend:
    build: .
    environment:
      - VITE_API_BASE_URL=https://api.your-domain.com
      - VITE_PROXY_BASE_URL=https://proxy.your-domain.com
```

## Build Commands

### Development

```bash
npm run dev
# or
yarn dev
```

### Production Build

```bash
# Build with production environment
npm run build
# or
yarn build

# Build with specific environment
npm run build --mode production
npm run build --mode staging
```

## Usage in Code

### Import Configuration

```javascript
import { API_CONFIG, getApiUrl, getProxyUrl } from '@/services/config/ApiConfig'

// Use configuration
console.log('API Base URL:', API_CONFIG.BASE_URL)
console.log('Full API URL:', getApiUrl('/api/v1/config'))
console.log('Proxy URL:', getProxyUrl('/proxy/status'))
```

### Environment Detection

```javascript
import { getCurrentEnvironment, isDevelopment, isProduction } from '@/services/config/ApiConfig'

if (isDevelopment()) {
  console.log('Running in development mode')
}

if (isProduction()) {
  // Production-specific code
}
```

## Deployment Examples

### Nginx Deployment

```nginx
server {
    listen 80;
    server_name your-frontend-domain.com;
    
    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
    }
    
    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://your-backend-server:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Docker Deployment

```dockerfile
# Multi-stage build
FROM node:18-alpine as builder

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .

# Build with environment variables
ARG VITE_API_BASE_URL
ARG VITE_PROXY_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_PROXY_BASE_URL=$VITE_PROXY_BASE_URL

RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
```

### CI/CD Pipeline (GitHub Actions)

```yaml
name: Deploy Frontend

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          
      - name: Install dependencies
        run: npm ci
        
      - name: Build
        env:
          VITE_API_BASE_URL: ${{ secrets.API_BASE_URL }}
          VITE_PROXY_BASE_URL: ${{ secrets.PROXY_BASE_URL }}
        run: npm run build
        
      - name: Deploy
        # Your deployment steps here
```

## Troubleshooting

### Common Issues

1. **Environment variables not loaded**
   - Ensure variables start with `VITE_`
   - Check file naming (`.env`, `.env.production`, etc.)
   - Restart development server after changes

2. **API calls failing**
   - Verify `VITE_API_BASE_URL` is correct
   - Check CORS settings on backend
   - Ensure backend is accessible from frontend

3. **Build issues**
   - Environment variables are embedded at build time
   - Rebuild after changing environment variables
   - Check for typos in variable names

### Debug Configuration

Enable debug mode to see configuration values:

```bash
VITE_DEBUG_MODE=true npm run dev
```

Check browser console for configuration output.

## Security Notes

- Never commit `.env` files containing sensitive data
- Use `.env.example` for documentation
- Environment variables are embedded in the build and visible to users
- Don't store secrets in frontend environment variables
- Use backend environment variables for sensitive configuration
