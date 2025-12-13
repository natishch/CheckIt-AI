"""Router node Pydantic schemas."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


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
