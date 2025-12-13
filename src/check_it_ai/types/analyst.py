"""Analyst-related Pydantic schemas for the Fact Analyst node."""

from typing import Literal

from pydantic import BaseModel, Field


class ExtractedClaims(BaseModel):
    """Output from the claim extraction LLM call."""

    claims: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="List of atomic, verifiable claims extracted from user query",
    )


class SingleEvaluation(BaseModel):
    """Output from evaluating one (claim, snippet) pair."""

    verdict: Literal["SUPPORTED", "NOT_SUPPORTED", "IRRELEVANT"] = Field(
        ...,
        description="Whether the snippet supports, contradicts, or is irrelevant to the claim",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in this verdict (0.0-1.0)",
    )
    reasoning: str = Field(
        ...,
        max_length=200,
        description="Brief explanation for the verdict",
    )


class VerdictResult(BaseModel):
    """Legacy model for whole-query verdict evaluation."""

    verdict: Literal["supported", "not_supported", "contested", "insufficient"]
    reasoning: str
    confidence: float
