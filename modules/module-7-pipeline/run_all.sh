#!/bin/bash
# Run both backend and frontend (requires two terminals or background processes)

cd "$(dirname "$0")"

echo "🚀 Starting Module 7: Full RAG Pipeline"
echo "========================================"
echo ""
echo "This will start both backend and frontend."
echo "Press Ctrl+C to stop both services."
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend in background
echo "📦 Restarting backend..."
# Stop any existing backend on port 8000
if command -v lsof >/dev/null 2>&1; then
    lsof -ti :8000 | xargs kill -9 2>/dev/null
fi
./run_backend.sh &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 3

# Start frontend in background
echo "📦 Starting frontend..."
./run_frontend.sh &
FRONTEND_PID=$!

echo ""
echo "=========================================="
echo "✅ Services started!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "   API Docs: http://localhost:8000/docs"
echo "=========================================="
echo ""

# Wait for both processes
wait
