#!/bin/bash
# LiteMCP Backend Docker Entrypoint Script

set -e

# Default values
PROXY_HOST=${PROXY_HOST:-"0.0.0.0"}
PROXY_PORT=${PROXY_PORT:-1888}
API_HOST=${API_HOST:-"0.0.0.0"}
API_PORT=${API_PORT:-9000}
MANAGE_ARGS=${MANAGE_ARGS:-""}

echo "🚀 Starting LiteMCP Backend Services..."
echo "📋 Configuration:"
echo "   - Proxy: ${PROXY_HOST}:${PROXY_PORT}"
echo "   - API: ${API_HOST}:${API_PORT}"
echo "   - Additional args: ${MANAGE_ARGS}"

# Configure Python package sources for runtime
if [ -z "$UV_INDEX_URL" ]; then
    export UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
    export UV_EXTRA_INDEX_URL=https://pypi.org/simple
    export UV_CACHE_DIR=/root/.cache/uv
    export UV_LINK_MODE=copy
    export UV_HTTP_TIMEOUT=120
    export UV_CONCURRENT_DOWNLOADS=10
    echo "🌐 Configured Python package sources"
fi

# Create runtime directories if they don't exist
mkdir -p runtime/logs runtime/pids

# Check and install dependencies if needed
if command -v uv >/dev/null 2>&1; then
    echo "🔧 Checking Python dependencies..."
    echo "🔍 uv version: $(uv --version)"

    # Check if we have a valid virtual environment from volume mount
    if [ -d ".venv" ] && [ -f ".venv/pyvenv.cfg" ]; then
        echo "✅ Found existing virtual environment from volume mount"
        echo "🔍 Virtual environment contents:"
        ls -la .venv | head -10

        # Verify that the virtual environment is functional
        echo "🔍 Verifying virtual environment integrity..."
        if timeout 30 uv run python -c "import sys; print('Python OK')" 2>/dev/null; then
            # Additional check: verify critical packages are installed
            if timeout 30 uv run python -c "import psutil; print('psutil OK')" 2>/dev/null; then
                echo "✅ Virtual environment is fully functional"
                USE_EXISTING_VENV=1
            else
                echo "⚠️ Virtual environment missing critical packages, will reinstall dependencies"
            fi
        else
            echo "⚠️ Virtual environment verification failed, will reinstall dependencies"
        fi

        # Only remove if we need to reinstall and can do so safely
        if [ "$USE_EXISTING_VENV" != "1" ]; then
            echo "🧹 Cleaning up existing virtual environment..."
            # Check if .venv is a mount point
            if mountpoint -q .venv 2>/dev/null || [ -d "/.dockerenv" ] && [ ! -w ".venv" ]; then
                echo "⚠️ .venv appears to be mounted, will create new venv in temporary location"
                export UV_PROJECT_ENVIRONMENT="/tmp/venv"
            else
                # Try to remove safely
                if rm -rf .venv 2>/dev/null; then
                    echo "✅ Successfully removed existing virtual environment"
                else
                    echo "⚠️ Cannot remove .venv directory, will create new venv in temporary location"
                    export UV_PROJECT_ENVIRONMENT="/tmp/venv"
                fi
            fi
        fi
    else
        echo "⚠️ No existing virtual environment found"
    fi

    # Only sync dependencies if we don't have a valid virtual environment
    if [ "$USE_EXISTING_VENV" != "1" ]; then
        echo "📦 Installing dependencies using uv..."
        echo "================================================"
        echo "⏱️  Attempt 1: Using Aliyun mirror"
        echo "================================================"

        set -x  # Enable command tracing
        UV_CONCURRENT_DOWNLOADS=10 uv sync --no-dev --retry 5 --verbose --no-progress 2>&1 && {
            set +x
            echo ""
            echo "✅ SUCCESS: Dependencies installed from Aliyun mirror"
            echo "================================================"
        } || {
            set +x
            echo ""
            echo "⚠️  Aliyun mirror failed, trying Official PyPI..."
            echo ""
            echo "⏱️  Attempt 2: Using Official PyPI"
            echo "================================================"

            set -x
            UV_INDEX_URL="https://pypi.org/simple" uv sync --no-dev --retry 3 --verbose --no-progress 2>&1 && {
                set +x
                echo ""
                echo "✅ SUCCESS: Dependencies installed from Official PyPI"
                echo "================================================"
            } || {
                set +x
                echo ""
                echo "❌ All uv sync attempts failed"
                echo "🔧 Trying pip install -e . as fallback..."
                echo "================================================"

                # Ensure build dependencies are installed first
                echo "🔧 Installing build dependencies first..."
                pip install --no-cache-dir hatchling wheel setuptools -q 2>&1 || echo "Build deps may already exist"
                echo ""

                echo "🔍 Debug info:"
                ls -la
                echo ""
                echo "🔍 pyproject.toml (first 20 lines):"
                head -20 pyproject.toml
                echo "================================================"
                echo "🔧 Installing project dependencies..."
                echo ""

                set -x
                pip install -e . -v 2>&1 && {
                    set +x
                    echo ""
                    echo "✅ SUCCESS: Dependencies installed via pip install -e ."
                    echo "================================================"
                    export USE_UV_PIP_FALLBACK=1
                } || {
                    set +x
                    echo ""
                    echo "❌ FATAL: All dependency installation methods failed"
                    echo "💡 Possible causes:"
                    echo "   1. Network connectivity issues"
                    echo "   2. Invalid pyproject.toml configuration"
                    echo "   3. Incompatible package versions"
                    echo "💡 Please check:"
                    echo "   - Network connection to PyPI mirrors"
                    echo "   - pyproject.toml dependencies section"
                    echo "   - Build logs above for specific errors"
                    echo "================================================"
                    exit 1
                }
            }
        }
    fi

    # Build the command
    if [ "$USE_UV_PIP_FALLBACK" = "1" ]; then
        echo "⚠️ Running with pip installed dependencies"
        CMD="python3 scripts/manage.py up --foreground"
    else
        echo "🚀 Using uv virtual environment"
        CMD="uv run python scripts/manage.py up --foreground"
    fi
else
    echo "❌ uv not found, cannot proceed"
    exit 1
fi

# Add proxy URL if MCP_SERVER_HOST is set
if [ -n "$MCP_SERVER_HOST" ] && [ "$MCP_SERVER_HOST" != "http://127.0.0.1:1888" ]; then
    echo "🔗 Configuring proxy URL: $MCP_SERVER_HOST"
    CMD="$CMD --proxy-url $MCP_SERVER_HOST"
fi

# Add any additional arguments
if [ -n "$MANAGE_ARGS" ]; then
    CMD="$CMD $MANAGE_ARGS"
fi

echo "🔧 Executing: $CMD"

# Execute the command
exec $CMD