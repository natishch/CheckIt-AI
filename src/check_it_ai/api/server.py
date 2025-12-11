# DEV ONLY: Import mock service for UI development
import sys
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from check_it_ai.types.schemas import (
    ChatRequest,
    ChatResponse,
    CheckRequest,
    EvidenceBundle,
    EvidenceItem,
    FinalOutput,
)

# Add project root to sys.path to enable importing from tests/
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from tests.mocks import mock_service
except ImportError:
    # In production/deployment where tests/ is not available, this should fail gracefully
    # or be replaced by real graph implementation
    mock_service = None

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
        "http://localhost:8501",  # Streamlit
        "*",  # Allow all for dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/check", response_model=FinalOutput)
async def check_claim(request: CheckRequest) -> FinalOutput:
    """
    Analyze a claim and return a verdict with evidence.

    Current Implementation: MOCK
    - Use 'mock:true' in text to get a TRUE verdict
    - Use 'mock:false' in text to get a FALSE verdict
    - Use 'mock:uncertain' in text to get an UNCERTAIN verdict
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Claim text cannot be empty")

    if mock_service is None:
        raise HTTPException(status_code=500, detail="Mock service not available")

    # Delegate to mock service (PLUG-IN POINT FOR REAL AI LATER)
    return mock_service.get_mock_response(request.text)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint for the React frontend.

    Accepts a query and returns a structured response with:
    - answer: The AI's response
    - citations: List of cited sources
    - evidence: Full evidence bundle with items
    - metadata: Additional info (latency, mode, etc.)

    Current Implementation: MOCK
    - Use 'mock:true' in query to get a TRUE verdict
    - Use 'mock:false' in query to get a FALSE verdict
    - Use 'mock:uncertain' in query to get an UNCERTAIN verdict
    """
    start_time = time.time()

    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

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
                title="Source",  # Mock data doesn't have full details
                snippet=mock_response.answer[:200],  # Use part of answer as snippet
                url=citation.url,
                display_domain=str(citation.url).split("//")[1].split("/")[0],
            )
        )

    evidence_bundle = EvidenceBundle(
        items=evidence_items,
        findings=[],  # Empty for now
        overall_verdict="supported" if mock_response.confidence > 0.7 else "insufficient",
    )

    # Calculate latency
    latency = time.time() - start_time

    return ChatResponse(
        answer=mock_response.answer,
        citations=mock_response.citations,
        evidence=evidence_bundle,
        metadata={
            "mode": request.mode,
            "latency_ms": round(latency * 1000, 2),
            "confidence": mock_response.confidence,
            "notes": mock_response.notes,
            "is_mock": True,
        },
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "mode": "mock"}
