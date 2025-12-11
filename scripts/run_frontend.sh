#!/bin/bash
# Run the React frontend for Check-It AI

echo "🚀 Starting Check-It AI React Frontend..."
echo "📍 Make sure the FastAPI backend is running on http://localhost:8000"
echo "🌐 Frontend will be available at http://localhost:5173"
echo ""

cd frontend && npm run dev
