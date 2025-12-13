"""Graph execution types for runner and streaming."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# Graph Result
# =============================================================================


class GraphResult(BaseModel):
    """Structured result from graph execution."""

    model_config = {"arbitrary_types_allowed": True}

    # Core outputs
    final_answer: str
    confidence: float
    route: str

    # Citations (empty for clarify/out_of_scope)
    citations: list[dict[str, Any]] = Field(default_factory=list)

    # Evidence (None for clarify/out_of_scope)
    evidence_bundle: dict[str, Any] | None = None

    # Execution metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    # For clarify route
    clarify_request: dict[str, Any] | None = None

    # Full state (for debugging) - excluded from serialization
    # Using Any to avoid circular import with AgentState
    internal_state: Any = Field(default=None, exclude=True, repr=False)

    @property
    def is_fact_check(self) -> bool:
        """Check if this result is from a fact_check route."""
        return self.route == "fact_check"

    @property
    def is_clarify(self) -> bool:
        """Check if this result is from a clarify route."""
        return self.route == "clarify"

    @property
    def is_out_of_scope(self) -> bool:
        """Check if this result is from an out_of_scope route."""
        return self.route == "out_of_scope"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Note: This is provided for backwards compatibility.
        Prefer using model_dump() directly.
        """
        return self.model_dump()


# =============================================================================
# Streaming Event Types
# =============================================================================


class NodeStartEvent(BaseModel):
    """Event emitted when a node starts execution."""

    model_config = {"frozen": True}

    node_name: str
    timestamp: float


class NodeEndEvent(BaseModel):
    """Event emitted when a node completes execution."""

    model_config = {"frozen": True}

    node_name: str
    timestamp: float
    duration_ms: float
    output_keys: list[str] = Field(default_factory=list)


class GraphCompleteEvent(BaseModel):
    """Event emitted when graph execution completes."""

    model_config = {"frozen": True}

    result: GraphResult
    total_duration_ms: float


# Type alias for streaming events
StreamEvent = NodeStartEvent | NodeEndEvent | GraphCompleteEvent
