#!/bin/bash
# Run the React frontend locally

cd "$(dirname "$0")/frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing npm dependencies..."
    npm install
fi

# Resolve ports (allow override via env vars)
PORT="${FRONTEND_PORT:-5173}"
BACKEND="${BACKEND_PORT:-8000}"

# Pass backend port to Vite so the proxy target is dynamic
export VITE_BACKEND_PORT="$BACKEND"

# Run the dev server
echo "🚀 Starting React frontend on http://localhost:$PORT"
echo "   (proxying /api → http://localhost:$BACKEND)"
npx vite --port "$PORT"
