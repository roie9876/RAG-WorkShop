#!/bin/bash
# Run both backend and frontend

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Starting Module 8 - GitHub Repository RAG"
echo ""

# Start backend in background
cd "$SCRIPT_DIR"
bash run_backend.sh &
BACKEND_PID=$!

# Wait for backend to be ready
echo "⏳ Waiting for backend..."
for i in {1..30}; do
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is ready"
    break
  fi
  sleep 1
done

# Start frontend
bash run_frontend.sh &
FRONTEND_PID=$!

echo ""
echo "🎉 GitHub RAG is running!"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait and cleanup
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
