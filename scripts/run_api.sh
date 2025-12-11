#!/bin/bash
# Run the FastAPI backend server for Check-It AI

echo "🚀 Starting Check-It AI FastAPI Backend..."
echo "📍 Server will be available at http://localhost:8000"
echo "📝 API docs at http://localhost:8000/docs"
echo ""

uv run uvicorn check_it_ai.api.server:app --reload --host 0.0.0.0 --port 8000
