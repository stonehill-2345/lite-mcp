# LiteMCP Backend Docker Configuration
# Use official uv image with Python
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Install system dependencies and minimal Python packages for fallback
RUN apt-get update && apt-get install -y \
    curl \
    procps \
    git \
    python3-pip \
    python3-yaml \
    python3-requests \
    && rm -rf /var/lib/apt/lists/* \
    && echo "✅ Installed system dependencies and minimal Python packages for fallback"

# Install Node.js for external MCP services that use npx
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && echo "✅ Installed Node.js $(node --version) and npm $(npm --version) for external MCP services" \
    && echo "🔧 Node.js and npm are ready for external MCP services"

# Copy dependency files first for better caching
COPY pyproject.toml README.md ./

# Configure China mirror sources for better connectivity in China
# Set uv index URL to use Tsinghua mirror (using correct environment variable)
ENV UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV UV_EXTRA_INDEX_URL=https://pypi.org/simple
ENV UV_CACHE_DIR=/root/.cache/uv
ENV UV_LINK_MODE=copy

# Configure pip mirror as fallback (for uv pip install)
RUN mkdir -p /root/.pip && \
    echo "[global]" > /root/.pip/pip.conf && \
    echo "index-url = https://pypi.tuna.tsinghua.edu.cn/simple" >> /root/.pip/pip.conf && \
    echo "extra-index-url = https://pypi.org/simple" >> /root/.pip/pip.conf && \
    echo "trusted-host = pypi.tuna.tsinghua.edu.cn" >> /root/.pip/pip.conf && \
    echo "timeout = 120" >> /root/.pip/pip.conf && \
    echo "✅ Configured China mirror sources (Tsinghua University)"

# Install dependencies using uv with enhanced retry mechanism
# Only copy source code after dependencies are installed for better caching
RUN --mount=type=cache,target=/tmp/uv-cache \
    echo "📦 Installing dependencies using uv..." && \
    uv --version && echo "✅ uv is available" && \
    ( \
        echo "⏱️ Attempt 1: Trying offline sync first..." && \
        UV_CACHE_DIR=/tmp/uv-cache uv sync --frozen --no-dev --offline 2>/dev/null && \
        echo "✅ Offline sync successful" \
    ) || ( \
        echo "⏱️ Attempt 2: Trying online sync with extended timeout..." && \
        timeout 120 sh -c "UV_CACHE_DIR=/tmp/uv-cache uv sync --no-dev --retry 3" 2>/dev/null && \
        echo "✅ Online sync successful" \
    ) || ( \
        echo "⏱️ Attempt 3: Trying with different resolver strategy..." && \
        timeout 90 sh -c "UV_CACHE_DIR=/tmp/uv-cache uv sync --no-dev --resolution lowest-direct" 2>/dev/null && \
        echo "✅ Alternative sync successful" \
    ) || ( \
        echo "⚠️ All sync attempts failed, dependencies will be installed at runtime" && \
        echo "💡 This is usually due to network connectivity issues during build" && \
        echo "🔧 The entrypoint script will handle dependency installation" \
    )

# Now copy the rest of the application code
COPY . .

# Create necessary directories
RUN mkdir -p runtime/logs runtime/pids

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose ports
EXPOSE 1888 9000 8000-8100

# Health check with extended timeouts for slower startup
HEALTHCHECK --interval=30s --timeout=15s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:9000/api/v1/health || exit 1

# Copy and set entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Default command
ENTRYPOINT ["/entrypoint.sh"]