#!/bin/bash
# One-time setup script for Module 7

echo "🔧 Setting up Module 7: Full RAG Pipeline"
echo "=========================================="

cd "$(dirname "$0")"

# Detect Python >=3.11 via pyenv (same logic as run_backend.sh)
PYTHON_CMD="python3"

if command -v pyenv &> /dev/null; then
    eval "$(pyenv init -)"
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
PYTHON_VERSION="$PY_MAJOR.$PY_MINOR"
echo "📌 Python version: $PYTHON_VERSION"

if [[ "$PY_MAJOR" -ne 3 ]] || [[ "$PY_MINOR" -lt 11 ]] || [[ "$PY_MINOR" -ge 14 ]]; then
    echo "❌ GraphRAG requires Python >=3.11, <3.14. Current: $PYTHON_VERSION"
    echo "   Install Python 3.11-3.13 via: pyenv install 3.11.0"
    exit 1
fi

# Check Node version
NODE_VERSION=$(node --version 2>&1)
echo "📌 Node version: $NODE_VERSION"

# Setup backend
echo ""
echo "📦 Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    echo "   ✅ Created virtual environment"
fi

./venv/bin/pip install --upgrade pip --quiet
./venv/bin/pip install -r requirements.txt --quiet
if [ $? -ne 0 ]; then
    echo "   ❌ Failed to install Python dependencies. Check errors above."
    exit 1
fi
echo "   ✅ Installed Python dependencies"

cd ..

# Setup frontend
echo ""
echo "📦 Setting up frontend..."
cd frontend
npm install --silent
echo "   ✅ Installed npm dependencies"

cd ..

# Check for .env file
echo ""
if [ -f "../.env" ] || [ -f "../../.env" ]; then
    echo "✅ Found .env file"
else
    echo "⚠️  No .env file found. Copy .env.example and fill in your Azure credentials:"
    echo "   cp .env.example ../.env"
fi

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo ""
echo "To run the application:"
echo "  Terminal 1: ./run_backend.sh"
echo "  Terminal 2: ./run_frontend.sh"
echo ""
echo "Or use the combined runner:"
echo "  ./run_all.sh"
