#!/bin/bash
# Module 8 - GitHub RAG Setup
# Installs dependencies for both backend and frontend

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 Setting up Module 8 - GitHub Repository RAG..."
echo ""

# Backend
echo "📦 Installing backend dependencies..."
cd "$SCRIPT_DIR/backend"
pip install -r requirements.txt
echo "✅ Backend dependencies installed"
echo ""

# Frontend
echo "📦 Installing frontend dependencies..."
cd "$SCRIPT_DIR/frontend"
npm install
echo "✅ Frontend dependencies installed"
echo ""

echo "🎉 Setup complete! Run ./run_all.sh to start."
