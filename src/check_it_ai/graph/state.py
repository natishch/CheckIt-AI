"""Pydantic state definitions for LangGraph workflow."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from check_it_ai.types.schemas import (
    Citation,
    EvidenceBundle,
    SearchQuery,
    SearchResult,
)


class AgentState(BaseModel):
    """Shared state for the agentic LangGraph workflow.

    This state is passed through all nodes in the graph and maintains
    the complete history and context of the fact-checking process.
    """

    # Pydantic configuration - allow arbitrary types for LangGraph compatibility
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # User input
    user_query: str = Field(default="", description="Original user query")

    # Router decision
    route: Literal["fact_check", "clarify", "out_of_scope"] = Field(
        default="fact_check", description="Routing decision from the router node"
    )

    # Search phase
    search_queries: list[SearchQuery] = Field(
        default_factory=list, description="Generated search queries for Google API"
    )
    search_results: list[SearchResult] = Field(
        default_factory=list, description="Raw search results from Google API"
    )

    # Analysis phase
    evidence_bundle: EvidenceBundle | None = Field(
        default=None, description="Processed evidence bundle from fact analyst"
    )

    # Output phase
    final_answer: str = Field(default="", description="Final generated answer")
    citations: list[Citation] = Field(
        default_factory=list, description="Citations used in the final answer"
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)"
    )

    # Metadata
    run_metadata: dict = Field(
        default_factory=dict,
        description="Runtime metadata (latency, token usage, API quota info)",
    )
