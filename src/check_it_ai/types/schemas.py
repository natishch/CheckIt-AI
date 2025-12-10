"""Pydantic schemas for structured data with strict validation."""

import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class SearchQuery(BaseModel):
    """Search query schema."""

    query: str = Field(..., min_length=1, description="Search query string")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum number of results")


class SearchResult(BaseModel):
    """Search result schema from Google Custom Search API."""

    title: str = Field(..., description="Title of the search result")
    snippet: str = Field(..., description="Snippet/preview text from the result")
    url: HttpUrl = Field(..., description="URL of the search result")
    display_domain: str = Field(..., description="Display domain (e.g., 'wikipedia.org')")
    rank: int = Field(..., ge=1, description="Rank position in search results")


class EvidenceItem(BaseModel):
    """Individual evidence item with citation ID."""

    id: str = Field(..., description="Evidence ID in format 'E1', 'E2', etc.")
    title: str = Field(..., description="Source title")
    snippet: str = Field(..., description="Relevant snippet from the source")
    url: HttpUrl = Field(..., description="Source URL")
    display_domain: str = Field(..., description="Display domain of the source")

    @field_validator("id")
    @classmethod
    def validate_evidence_id(cls, v: str) -> str:
        """Validate evidence ID format: must be 'E' followed by digits."""
        if not re.match(r"^E\d+$", v):
            raise ValueError(f"Evidence ID must match pattern 'E<number>', got: {v}")
        return v



class EvidenceVerdict(str, Enum):
    """
    Normalized verdict for a historical claim based on the collected evidence.

    Values:
        SUPPORTED      – The evidence strongly supports the claim.
        NOT_SUPPORTED  – The evidence contradicts or fails to support the claim.
        CONTESTED      – The evidence is conflicting across sources.
        INSUFFICIENT   – There is not enough evidence to decide either way.
    """

    SUPPORTED = "supported"
    NOT_SUPPORTED = "not_supported"
    CONTESTED = "contested"
    INSUFFICIENT = "insufficient"

    @classmethod
    def from_str(cls, value: str) -> "EvidenceVerdict":
        """
        Lenient string-to-enum converter. Accepts common variants like:
        'Supported', 'NOT_SUPPORTED', 'contested', etc.
        Raises ValueError on unknown values.
        """
        normalized = value.strip().lower()

        mapping = {
            "supported": cls.SUPPORTED,
            "support": cls.SUPPORTED,
            "true": cls.SUPPORTED,
            "not_supported": cls.NOT_SUPPORTED,
            "not supported": cls.NOT_SUPPORTED,
            "false": cls.NOT_SUPPORTED,
            "contested": cls.CONTESTED,
            "mixed": cls.CONTESTED,
            "insufficient": cls.INSUFFICIENT,
            "unknown": cls.INSUFFICIENT,
        }

        try:
            return mapping[normalized]
        except KeyError:
            raise ValueError(f"Unknown EvidenceVerdict value: {value!r}") from None

class Finding(BaseModel):
    """A finding with a claim, verdict, and supporting evidence IDs."""

    claim: str = Field(..., description="The claim being evaluated")
    verdict: EvidenceVerdict

    evidence_ids: list[str] = Field(
        default_factory=list, description="List of evidence IDs supporting this finding"
    )

    @field_validator("evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, v: list[str]) -> list[str]:
        """Validate all evidence IDs in the list."""
        for evidence_id in v:
            if not re.match(r"^E\d+$", evidence_id):
                raise ValueError(f"Evidence ID must match pattern 'E<number>', got: {evidence_id}")
        return v


class EvidenceBundle(BaseModel):
    """Complete evidence bundle with items, findings, and overall verdict."""

    items: list[EvidenceItem] = Field(
        default_factory=list, description="List of evidence items"
    )
    findings: list[Finding] = Field(
        default_factory=list, description="List of findings with verdicts"
    )
    overall_verdict: EvidenceVerdict #Literal["supported", "not_supported", "contested", "insufficient"] = Field(
        #default="insufficient", description="Overall verdict based on all findings")


class Citation(BaseModel):
    """Citation linking evidence ID to URL."""

    evidence_id: str = Field(..., description="Evidence ID being cited")
    url: HttpUrl = Field(..., description="URL of the cited source")

    @field_validator("evidence_id")
    @classmethod
    def validate_evidence_id(cls, v: str) -> str:
        """Validate evidence ID format: must be 'E' followed by digits."""
        if not re.match(r"^E\d+$", v):
            raise ValueError(f"Evidence ID must match pattern 'E<number>', got: {v}")
        return v


class FinalOutput(BaseModel):
    """Final output schema with answer, citations, and confidence."""

    answer: str = Field(..., description="The final answer to the user query")
    citations: list[Citation] = Field(
        default_factory=list, description="Citations used in the answer"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0"
    )
    notes: str = Field(default="", description="Additional notes or limitations")
