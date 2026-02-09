#!/bin/bash
# Run the FastAPI backend

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR/backend"

echo "🚀 Starting GitHub RAG Backend on http://localhost:8000"
echo "📖 API docs: http://localhost:8000/docs"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --loop asyncio
