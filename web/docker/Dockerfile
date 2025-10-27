# Multi-stage build for LiteMCP Frontend
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Copy source code first
COPY . .

# Install dependencies with cache mount (much faster rebuilds)
# Use /tmp for cache to work across different systems and users
RUN --mount=type=cache,target=/tmp/npm-cache \
    npm ci --cache /tmp/npm-cache

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
