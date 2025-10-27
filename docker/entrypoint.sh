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

# Configure China mirror sources for runtime (if not already set)
if [ -z "$UV_INDEX_URL" ]; then
    export UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
    export UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
    export UV_EXTRA_INDEX_URL=https://pypi.org/simple
    export UV_CACHE_DIR=/root/.cache/uv
    export UV_LINK_MODE=copy
    echo "🇨🇳 Configured China mirror sources for better connectivity"
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
        echo "⏱️ Trying offline mode first..."
        UV_INDEX_URL="$UV_INDEX_URL" uv sync --no-dev --offline 2>&1 && echo "✅ Offline sync successful" || {
            echo "⏱️ Trying online mode with timeout (120s)..."
            # Correct way to use timeout with environment variables
            timeout 120 sh -c "UV_INDEX_URL='$UV_INDEX_URL' uv sync --no-dev" 2>&1 && echo "✅ Online sync successful" || {
                echo "⚠️ uv sync failed or timed out, trying alternative installation methods..."
                echo "🔍 Debug info: Checking current directory and pyproject.toml"
                ls -la
                head -20 pyproject.toml

                # Try to install with editable mode as fallback
                echo "🔧 Trying pip install -e . as alternative method..."
                UV_INDEX_URL="$UV_INDEX_URL" pip install -e . 2>&1 && {
                    echo "✅ Alternative installation successful"
                    export USE_UV_PIP_FALLBACK=1
                } || {
                    echo "❌ All dependency installation methods failed"
                    echo "💡 This indicates a configuration issue with pyproject.toml or network connectivity problems"
                    echo "💡 Please check pyproject.toml dependencies and network connectivity"
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

# Add proxy configuration if specified
if [ -n "$PROXY_HOST" ] && [ "$PROXY_HOST" != "0.0.0.0" ]; then
    CMD="$CMD --proxy-host $PROXY_HOST"
fi

if [ -n "$PROXY_PORT" ] && [ "$PROXY_PORT" != "1888" ]; then
    CMD="$CMD --proxy-port $PROXY_PORT"
fi

# Add API configuration if specified
if [ -n "$API_HOST" ] && [ "$API_HOST" != "0.0.0.0" ]; then
    CMD="$CMD --api-host $API_HOST"
fi

if [ -n "$API_PORT" ] && [ "$API_PORT" != "9000" ]; then
    CMD="$CMD --api-port $API_PORT"
fi

# Add any additional arguments
if [ -n "$MANAGE_ARGS" ]; then
    CMD="$CMD $MANAGE_ARGS"
fi

echo "🔧 Executing: $CMD"

# Execute the command
exec $CMD