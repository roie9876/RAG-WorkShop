#!/bin/bash
# One-time setup script for Module 7

echo "🔧 Setting up Module 7: Full RAG Pipeline"
echo "=========================================="

cd "$(dirname "$0")"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "📌 Python version: $PYTHON_VERSION"

if [[ "$PYTHON_VERSION" < "3.11" ]]; then
    echo "⚠️  Warning: Python 3.11+ recommended. You have $PYTHON_VERSION"
fi

# Check Node version
NODE_VERSION=$(node --version 2>&1)
echo "📌 Node version: $NODE_VERSION"

# Setup backend
echo ""
echo "📦 Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "   ✅ Created virtual environment"
fi

source venv/bin/activate
pip install -r requirements.txt --quiet
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
