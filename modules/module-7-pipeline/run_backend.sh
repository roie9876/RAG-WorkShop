#!/bin/bash
# Run the FastAPI backend locally

cd "$(dirname "$0")/backend"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt --quiet

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
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
