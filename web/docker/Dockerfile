# Multi-stage build for LiteMCP Frontend
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Copy source code first
COPY . .

# Install dependencies with cache mount
# Try Taobao npm mirror first, fallback to official registry
RUN --mount=type=cache,target=/tmp/npm-cache \
    ( \
        # Try Taobao npm mirror for faster downloads in China \
        npm config set registry https://registry.npmmirror.com && \
        npm ci --cache /tmp/npm-cache && \
        echo "✅ Installed dependencies (npm mirror)" \
    ) || ( \
        # Fallback to official npm registry for international users \
        echo "⚠️ npm mirror failed, using official npm registry" && \
        npm config set registry https://registry.npmjs.org && \
        npm ci --cache /tmp/npm-cache && \
        echo "✅ Installed dependencies (Official registry)" \
    )

# Build arguments for environment variables
ARG VITE_API_BASE_URL
ARG VITE_PROXY_BASE_URL
ARG VITE_DEBUG_MODE=false
ARG VITE_LOG_LEVEL=error

# Set environment variables for build
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_PROXY_BASE_URL=$VITE_PROXY_BASE_URL
ENV VITE_DEBUG_MODE=$VITE_DEBUG_MODE
ENV VITE_LOG_LEVEL=$VITE_LOG_LEVEL

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY docker/nginx.conf /etc/nginx/nginx.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
