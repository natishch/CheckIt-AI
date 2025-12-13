"""FastAPI server for Check-It AI.

Provides REST API endpoints for the React frontend to interact with the
LangGraph fact-checking pipeline.

Endpoints:
    POST /api/chat - Main chat endpoint (uses run_graph or mock based on settings)
    POST /api/check - Legacy endpoint (mock only)
    GET /health - Health check
"""

import logging
import sys
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.check_it_ai.config import settings
from src.check_it_ai.types.api import (
    ChatRequest,
    ChatResponse,
    CheckRequest,
    HealthResponse,
)
from src.check_it_ai.types.evidence import Citation, EvidenceBundle, EvidenceItem
from src.check_it_ai.types.output import FinalOutput

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# Backend Mode Detection (uses settings.use_mock)
# =============================================================================
_use_mock = settings.use_mock

# Try to import run_graph (real backend)
run_graph = None
if not _use_mock:
    try:
        from src.check_it_ai.graph.runner import run_graph

        logger.info("Real run_graph loaded successfully")
    except ImportError as e:
        logger.warning(f"Could not import run_graph: {e}. Falling back to mock.")
        _use_mock = True

# Try to import mock service (for development/testing)
mock_service = None
if _use_mock:
    # Add project root to sys.path to enable importing from tests/
    project_root = Path(__file__).parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    try:
        from tests.mocks import mock_service

        logger.info("Mock service loaded successfully")
    except ImportError as e:
        logger.warning(f"Could not import mock_service: {e}")
        mock_service = None


# =============================================================================
# FastAPI App
# =============================================================================
app = FastAPI(
    title="Check-It AI API",
    description="Backend API for the Check-It AI fact-checking system.",
    version="1.0.0",
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite React dev server
        "http://localhost:3000",  # Alternative React port
        "http://localhost:8501",  # Streamlit
        "*",  # Allow all for dev - tighten in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Endpoints
# =============================================================================


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Main chat endpoint for the React frontend.

    Accepts a query and returns a structured response with:
    - answer: The AI's response
    - citations: List of cited sources
    - evidence: Evidence bundle with items and verdict
    - metadata: Additional info (latency, confidence, route, etc.)

    Uses real run_graph() by default, or mock_service if settings.use_mock=true.
    """
    start_time = time.time()

    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        if _use_mock:
            return await _handle_mock_chat(request, start_time)
        else:
            return await _handle_real_chat(request, start_time)
    except Exception as e:
        logger.exception(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


async def _handle_real_chat(request: ChatRequest, start_time: float) -> ChatResponse:
    """Handle chat using real run_graph() pipeline."""
    if run_graph is None:
        raise HTTPException(status_code=500, detail="Graph runner not available")

    # Execute the graph
    result = run_graph(request.query)

    latency = time.time() - start_time

    # Map GraphResult to ChatResponse
    # Convert citations from dict to Citation objects
    citations = []
    for c in result.citations:
        if isinstance(c, dict):
            citations.append(
                Citation(
                    evidence_id=c.get("evidence_id", "E0"),
                    url=c.get("url", "https://example.com"),
                    title=c.get("title", ""),
                )
            )
        else:
            citations.append(c)

    # Build evidence bundle from GraphResult
    evidence = EvidenceBundle()
    if result.evidence_bundle:
        eb = result.evidence_bundle
        # Handle both dict and object forms
        if isinstance(eb, dict):
            evidence = EvidenceBundle(
                evidence_items=[
                    EvidenceItem(
                        id=item.get("id", f"E{i}"),
                        title=item.get("title", "Source"),
                        snippet=item.get("snippet", ""),
                        url=item.get("url", "https://example.com"),
                        display_domain=item.get("display_domain", ""),
                    )
                    for i, item in enumerate(eb.get("evidence_items", eb.get("items", [])))
                ],
                findings=eb.get("findings", []),
                overall_verdict=eb.get("overall_verdict", "insufficient"),
            )
        else:
            evidence = eb

    return ChatResponse(
        answer=result.final_answer,
        citations=citations,
        evidence=evidence,
        route=result.route,
        metadata={
            "mode": request.mode,
            "latency_ms": round(latency * 1000, 2),
            "confidence": result.confidence,
            "is_mock": False,
            "route": result.route,
            **result.metadata,
        },
    )


async def _handle_mock_chat(request: ChatRequest, start_time: float) -> ChatResponse:
    """Handle chat using mock service for UI development."""
    if mock_service is None:
        raise HTTPException(status_code=500, detail="Mock service not available")

    # Get mock response
    mock_response = mock_service.get_mock_response(request.query)

    # Build evidence bundle from citations
    evidence_items = []
    for citation in mock_response.citations:
        evidence_items.append(
            EvidenceItem(
                id=citation.evidence_id,
                title="Source",
                snippet=mock_response.answer[:200],
                url=citation.url,
                display_domain=str(citation.url).split("//")[1].split("/")[0],
            )
        )

    evidence = EvidenceBundle(
        evidence_items=evidence_items,
        findings=[],
        overall_verdict="supported" if mock_response.confidence > 0.7 else "insufficient",
    )

    latency = time.time() - start_time

    return ChatResponse(
        answer=mock_response.answer,
        citations=mock_response.citations,
        evidence=evidence,
        route="fact_check",
        metadata={
            "mode": request.mode,
            "latency_ms": round(latency * 1000, 2),
            "confidence": mock_response.confidence,
            "notes": mock_response.notes,
            "is_mock": True,
        },
    )


@app.post("/api/check", response_model=FinalOutput)
async def check_claim(request: CheckRequest) -> FinalOutput:
    """Legacy check endpoint (mock only).

    Use /api/chat for the full pipeline.
    """
    if mock_service is None:
        raise HTTPException(status_code=500, detail="Mock service not available")

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Claim text cannot be empty")

    return mock_service.get_mock_response(request.text)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        mode="mock" if _use_mock else "real",
        version="1.0.0",
    )
