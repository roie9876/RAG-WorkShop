#!/bin/bash
# Run the FastAPI backend locally

cd "$(dirname "$0")/backend"

# GraphRAG requires Python >=3.11, <3.14
# Use pyenv to get the right version
PYTHON_CMD="python3"

if command -v pyenv &> /dev/null; then
    eval "$(pyenv init -)"
    # Try to use Python 3.11 or 3.12 or 3.13 from pyenv
    for ver in 3.11.0 3.11 3.12.0 3.12 3.13.0 3.13; do
        if pyenv versions --bare | grep -q "^${ver}"; then
            export PYENV_VERSION="$ver"
            PYTHON_CMD="$(pyenv which python)"
            echo "✅ Using Python $ver via pyenv: $PYTHON_CMD"
            break
        fi
    done
fi

# Verify Python version is in valid range
PY_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')
if [[ "$PY_MAJOR" -ne 3 ]] || [[ "$PY_MINOR" -lt 11 ]] || [[ "$PY_MINOR" -ge 14 ]]; then
    echo "❌ GraphRAG requires Python >=3.11, <3.14. Current: $PY_MAJOR.$PY_MINOR"
    echo "   Install Python 3.11-3.13 via: pyenv install 3.11.0"
    exit 1
fi

# Check if virtual environment exists and has correct Python version
if [ -d "venv" ]; then
    VENV_MINOR=$(./venv/bin/python -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo "0")
    if [[ "$VENV_MINOR" -lt 11 ]] || [[ "$VENV_MINOR" -ge 14 ]]; then
        echo "⚠️  Existing venv uses Python 3.$VENV_MINOR, recreating..."
        rm -rf venv
    fi
fi

if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment with Python 3.$PY_MINOR..."
    $PYTHON_CMD -m venv venv
fi

# Upgrade pip for better dependency resolution
./venv/bin/pip install --upgrade pip --quiet

# Install dependencies
echo "📥 Installing dependencies..."
./venv/bin/pip install -r requirements.txt --quiet

# Load environment variables from root .env
if [ -f "../../.env" ]; then
    export $(grep -v '^#' ../../.env | xargs)
    echo "✅ Loaded environment from ../../.env"
elif [ -f "../.env" ]; then
    export $(grep -v '^#' ../.env | xargs)
    echo "✅ Loaded environment from ../.env"
fi

# Run the server
echo "🚀 Starting FastAPI backend on http://localhost:8000"
echo "📚 API docs at http://localhost:8000/docs"
echo "🔗 GraphRAG endpoints at http://localhost:8000/api/graphrag"
# Use --loop asyncio to avoid conflict between uvloop and graphrag's nest_asyncio2
./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload --loop asyncio
