#!/bin/bash
# Run the Streamlit UI for Check-It AI

echo "🚀 Starting Check-It AI Streamlit UI..."
echo "📍 Make sure the FastAPI backend is running on http://localhost:8000"
echo "🌐 UI will be available at http://localhost:8501"
echo ""

uv run streamlit run src/check_it_ai/web/streamlit_app.py \
    --server.port 8501 \
    --server.headless true \
    --browser.gatherUsageStats false
