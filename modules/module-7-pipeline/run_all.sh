#!/bin/bash
# Run both backend and frontend (requires two terminals or background processes)

cd "$(dirname "$0")"

echo "🚀 Starting Module 7: Full RAG Pipeline"
echo "========================================"
echo ""
echo "This will start both backend and frontend."
echo "Press Ctrl+C to stop both services."
echo ""

# ──────────────────────────────────────────────
# Port detection: find an available port starting
# from the preferred one, skipping ports already
# in use by OTHER processes.
# ──────────────────────────────────────────────
find_available_port() {
    local preferred=$1
    local max_tries=${2:-20}   # search up to 20 ports ahead
    local port=$preferred

    for (( i=0; i<max_tries; i++ )); do
        # Check if anything is listening on this port
        if command -v lsof >/dev/null 2>&1; then
            if ! lsof -iTCP:"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
                echo "$port"
                return 0
            fi
        elif command -v ss >/dev/null 2>&1; then
            if ! ss -tlnH "sport = :$port" | grep -q .; then
                echo "$port"
                return 0
            fi
        elif command -v netstat >/dev/null 2>&1; then
            if ! netstat -tln 2>/dev/null | grep -q ":$port "; then
                echo "$port"
                return 0
            fi
        else
            # No tool available – just use the preferred port
            echo "$port"
            return 0
        fi

        if (( i == 0 )); then
            echo "⚠️  Port $port is already in use, looking for an alternative..." >&2
        fi
        (( port++ ))
    done

    echo "❌ Could not find a free port in range $preferred-$port" >&2
    return 1
}

# Resolve backend port (default 8000)
export BACKEND_PORT
BACKEND_PORT=$(find_available_port "${BACKEND_PORT:-8000}") || exit 1
if [[ "$BACKEND_PORT" != "8000" ]]; then
    echo "ℹ️  Backend will use port $BACKEND_PORT (8000 was busy)"
fi

# Resolve frontend port (default 5173)
export FRONTEND_PORT
FRONTEND_PORT=$(find_available_port "${FRONTEND_PORT:-5173}") || exit 1
if [[ "$FRONTEND_PORT" != "5173" ]]; then
    echo "ℹ️  Frontend will use port $FRONTEND_PORT (5173 was busy)"
fi

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
# Stop any existing backend on BACKEND_PORT that WE may have left behind
if command -v lsof >/dev/null 2>&1; then
    lsof -ti :"$BACKEND_PORT" | xargs kill -9 2>/dev/null
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
echo "   Backend:  http://localhost:$BACKEND_PORT"
echo "   Frontend: http://localhost:$FRONTEND_PORT"
echo "   API Docs: http://localhost:$BACKEND_PORT/docs"
echo "=========================================="
echo ""

# Monitor and auto-restart backend if it dies
while true; do
    # Check if backend is still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo ""
        echo "🔄 Backend stopped. Restarting..."
        ./run_backend.sh &
        BACKEND_PID=$!
        sleep 2
    fi
    
    # Check if frontend is still running
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo ""
        echo "⚠️  Frontend stopped. Exiting..."
        cleanup
    fi
    
    sleep 2
done
