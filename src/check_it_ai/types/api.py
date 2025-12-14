"""API request/response schemas for FastAPI endpoints."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.check_it_ai.types.evidence import Citation, EvidenceBundle


class ChatRequest(BaseModel):
    """Request schema for POST /api/chat endpoint."""

    query: str = Field(..., min_length=1, description="The user's query/claim to verify")
    mode: Literal["standard", "animated"] = Field(
        default="standard", description="UI mode (standard or animated)"
    )


class ChatResponse(BaseModel):
    """Response schema for POST /api/chat endpoint.

    This schema maps GraphResult to frontend-expected format.
    """

    answer: str = Field(..., description="The AI's answer to the query")
    citations: list[Citation] = Field(
        default_factory=list, description="Citations used in the answer"
    )
    evidence: EvidenceBundle = Field(
        default_factory=EvidenceBundle, description="Evidence bundle with items and verdict"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (latency, confidence, route, etc.)",
    )
    route: str = Field(
        default="fact_check", description="Router decision (fact_check, clarify, out_of_scope)"
    )


class CheckRequest(BaseModel):
    """Legacy request schema for POST /api/check endpoint."""

    text: str = Field(..., min_length=1, description="The claim text to verify")


class HealthResponse(BaseModel):
    """Response schema for GET /health endpoint."""

    status: str = Field(default="ok")
    mode: str = Field(default="real", description="Backend mode (mock or real)")
    version: str = Field(default="1.0.0")
