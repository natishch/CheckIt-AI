"""Pydantic schemas for structured data with strict validation."""
#src.check_it_ai.types.schemas
import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


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
    # Optional in constructors; we can derive it from the URL later if needed.
    display_domain: str = Field(
        default="",
        description="Display domain of the source (e.g., 'wikipedia.org').",
    )

    @field_validator("id")
    @classmethod
    def validate_evidence_id(cls, v: str) -> str:
        """Validate evidence ID format: must be 'E' followed by digits."""
        if not re.match(r"^E\d+$", v):
            raise ValueError(f"Evidence ID must match pattern 'E<number>', got: {v}")
        return v



class EvidenceVerdict(StrEnum):
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
    """Complete evidence bundle with items, findings, and overall verdict.

    Notes
    -----
    - `evidence_items` is the canonical field used in new code.
    - `items` is kept as an alias for backward compatibility.
    """

    model_config = ConfigDict(populate_by_name=True)

    evidence_items: list[EvidenceItem] = Field(
        default_factory=list,
        description="List of evidence items",
        alias="items",
    )
    findings: list[Finding] = Field(
        default_factory=list,
        description="List of findings with verdicts",
    )
    overall_verdict: EvidenceVerdict = Field(
        default=EvidenceVerdict.INSUFFICIENT,
        description="Overall verdict based on all findings",
    )

    @property
    def items(self) -> list[EvidenceItem]:
        """Backward compatible attribute; returns `evidence_items`."""
        return self.evidence_items



class Citation(BaseModel):
    """Citation linking evidence ID to URL."""

    evidence_id: str = Field(..., description="Evidence ID being cited")
    url: HttpUrl = Field(..., description="URL of the cited source")
    title: str = Field(
        default="",
        description="Title of the cited source (for UI display).",
    )

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


# ============================================================================
# Router Node Schemas
# ============================================================================


class RouterTrigger(StrEnum):
    """
    All possible router trigger patterns.

    These represent the specific reason why a routing decision was made.
    Using StrEnum for type safety while maintaining string compatibility.
    """

    # Clarification triggers (query needs more info)
    EMPTY_QUERY = "empty_query"
    TOO_SHORT = "too_short"
    UNDERSPECIFIED_QUERY = "underspecified_query"
    UNRESOLVED_PRONOUN = "unresolved_pronoun"
    AMBIGUOUS_REFERENCE = "ambiguous_reference"
    OVERLY_BROAD = "overly_broad"
    UNSUPPORTED_LANGUAGE = "unsupported_language"

    # Out-of-scope triggers (not historical fact-checking)
    CREATIVE_WRITING = "creative_writing"
    CODING_REQUEST = "coding_request"
    CHAT_REQUEST = "chat_request"
    FUTURE_PREDICTION = "future_prediction"
    CURRENT_EVENTS = "current_events"
    OPINION_REQUEST = "opinion_request"
    NON_HISTORICAL_INTENT = "non_historical_intent"  # Generic out-of-scope

    # Fact-check triggers (proceed to fact-checking pipeline)
    DEFAULT_FACT_CHECK = "default_fact_check"
    EXPLICIT_VERIFICATION = "explicit_verification"


class RouterDecision(StrEnum):
    """
    Final routing decisions (where the query goes next).

    These are the three main paths through the system.
    """

    FACT_CHECK = "fact_check"
    CLARIFY = "clarify"
    OUT_OF_SCOPE = "out_of_scope"


class RouterMetadata(BaseModel):
    """
    Type-safe metadata for router node decisions.

    This model ensures all router decisions are properly structured and validated.
    Stored in state.run_metadata['router'] for UI display and debugging.

    Design notes:
    - Uses StrEnum for trigger/decision (type safety + string compatibility)
    - Includes both new fields (confidence, detected_language) and legacy fields (features)
    - Validates confidence is in [0.0, 1.0] range
    - Validates detected_language is 'he' or 'en'
    """

    trigger: RouterTrigger = Field(
        ..., description="Which pattern/rule triggered this routing decision"
    )

    decision: RouterDecision = Field(
        ..., description="Final routing decision (fact_check, clarify, out_of_scope)"
    )

    reasoning: str = Field(
        ..., min_length=1, description="Human-readable explanation of why this decision was made"
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in routing decision (0.0-1.0, higher = more certain)",
    )

    matched_patterns: list[str] = Field(
        default_factory=list, description="List of regex patterns that matched (for debugging)"
    )

    query_length_words: int = Field(..., ge=0, description="Number of words in the user query")

    has_historical_markers: bool = Field(
        default=False, description="Whether query contains historical entities, dates, or keywords"
    )

    detected_language: str = Field(
        default="en",
        pattern="^(he|en)$",
        description="Detected language: 'he' (Hebrew) or 'en' (English)",
    )

    # Backward compatibility: keep existing features dict
    features: dict[str, Any] = Field(
        default_factory=dict,
        description="Legacy features dict from existing router (num_tokens, num_chars, etc.)",
    )

    # Optional: intent_type for out_of_scope decisions
    intent_type: str | None = Field(
        default=None,
        description="Fine-grained intent category for out_of_scope (e.g., 'creative_request', 'coding_request')",
    )
