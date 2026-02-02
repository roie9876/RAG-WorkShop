#!/bin/bash
# Reset all indexes and data for a fresh start
# Usage: ./reset_all.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
GRAPHRAG_DIR="$BACKEND_DIR/graphrag-index"

echo "🧹 Resetting RAG Pipeline..."

# 1. Stop any running backend processes
echo "1️⃣  Stopping backend processes..."
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
sleep 1

# 2. Clear GraphRAG data
echo "2️⃣  Clearing GraphRAG index..."
find "$GRAPHRAG_DIR/input" -type f -delete 2>/dev/null || true
find "$GRAPHRAG_DIR/output" -type f -delete 2>/dev/null || true
find "$GRAPHRAG_DIR/cache" -type f -delete 2>/dev/null || true
rm -f "$GRAPHRAG_DIR/.indexing_in_progress" "$GRAPHRAG_DIR/indexing.log" 2>/dev/null || true
echo "   ✅ GraphRAG data cleared"

# 3. Clear Azure AI Search index
echo "3️⃣  Clearing Azure AI Search index..."
cd "$BACKEND_DIR"
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    python3 -c "
import sys
import asyncio
sys.path.insert(0, '.')
from services.search_service import SearchService

async def main():
    s = SearchService()
    await s.delete_index()
    print('   ✅ Azure AI Search index deleted')

asyncio.run(main())
" 2>/dev/null || echo "   ⚠️  Could not delete search index (may already be empty)"
else
    echo "   ⚠️  Backend venv not found, skipping search index deletion"
fi

echo ""
echo "✅ Reset complete! You can now start fresh:"
echo "   cd $SCRIPT_DIR"
echo "   ./run_all.sh"
