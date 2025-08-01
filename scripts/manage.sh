#!/bin/bash

# TestMCP Framework management script wrapper
# Simplifies calling the Python management tool, supporting all original features
# 
# Usage examples:
#   ./scripts/manage.sh up
#   ./scripts/manage.sh down
#   ./scripts/manage.sh ps
#   ./scripts/manage.sh up example

# Get absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Python management script path
PYTHON_MANAGER="$SCRIPT_DIR/manage.py"

# Check if Python management script exists
if [ ! -f "$PYTHON_MANAGER" ]; then
    echo "❌ Error: Python management script not found: $PYTHON_MANAGER"
    exit 1
fi

# Check Python environment
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python environment not found (requires python3 or python command)"
    echo "   Please install Python 3.12+ and ensure it's available in PATH"
    exit 1
fi

# Switch to project root directory
cd "$PROJECT_DIR"

# Check if using Poetry environment
if command -v poetry &> /dev/null && [ -f "$PROJECT_DIR/pyproject.toml" ]; then
    # Execute using Poetry environment
    exec poetry run "$PYTHON_CMD" "$PYTHON_MANAGER" "$@"
else
    # Execute directly with Python
    exec "$PYTHON_CMD" "$PYTHON_MANAGER" "$@"
fi