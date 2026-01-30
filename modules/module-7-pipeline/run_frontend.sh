#!/bin/bash
# Run the React frontend locally

cd "$(dirname "$0")/frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing npm dependencies..."
    npm install
fi

# Run the dev server
echo "🚀 Starting React frontend on http://localhost:5173"
npm run dev
