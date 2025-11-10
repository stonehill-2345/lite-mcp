# LiteMCP Backend Docker Configuration
# Use nikolaik/python-nodejs image (full version with build tools)
# This includes Python 3.12, Node.js 24, and gcc for compiling native extensions
FROM nikolaik/python-nodejs:python3.12-nodejs24

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
# Note: uv is already included in nikolaik/python-nodejs:python3.12-nodejs24
COPY pyproject.toml README.md ./

# Configure Python package sources (Aliyun primary, PyPI fallback)
# Note: Tsinghua mirror currently returns 403, using official PyPI as backup
ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    UV_EXTRA_INDEX_URL=https://pypi.org/simple \
    UV_CACHE_DIR=/root/.cache/uv \
    UV_LINK_MODE=copy \
    UV_HTTP_TIMEOUT=120 \
    UV_CONCURRENT_DOWNLOADS=10 \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    PIP_EXTRA_INDEX_URL=https://pypi.org/simple \
    PIP_TRUSTED_HOST=mirrors.aliyun.com \
    PIP_TIMEOUT=120 \
    PIP_RETRIES=5

# Install dependencies using uv with fallback
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    echo "📦 Installing dependencies using uv..." && \
    echo "🔍 System info:" && \
    python --version && \
    node --version && \
    uv --version && \
    echo "" && \
    echo "🔍 Environment: UV_INDEX_URL=$UV_INDEX_URL" && \
    echo "" && \
    echo "⏱️  Attempt 1: Using Aliyun mirror" && \
    ( \
        set -x && \
        uv sync --no-dev --verbose 2>&1 && \
        set +x && \
        echo "" && \
        echo "✅ SUCCESS: Dependencies installed from Aliyun mirror" \
    ) || ( \
        echo "" && \
        echo "⚠️  Aliyun mirror failed, trying Official PyPI..." && \
        echo "⏱️  Attempt 2: Using Official PyPI" && \
        set -x && \
        UV_INDEX_URL=https://pypi.org/simple uv sync --no-dev --verbose 2>&1 && \
        set +x && \
        echo "" && \
        echo "✅ SUCCESS: Dependencies installed from Official PyPI" \
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