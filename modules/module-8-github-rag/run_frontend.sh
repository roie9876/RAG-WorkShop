#!/bin/bash
# Run the React frontend

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR/frontend"

echo "🎨 Starting GitHub RAG Frontend on http://localhost:5173"
npm run dev
