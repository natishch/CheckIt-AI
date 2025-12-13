"""Type definitions for check-it-ai.

This module re-exports all types from submodules for convenient imports.
"""

from src.check_it_ai.types.analyst import (
    ExtractedClaims,
    SingleEvaluation,
    VerdictResult,
)
from src.check_it_ai.types.api import (
    ChatRequest,
    ChatResponse,
    CheckRequest,
    HealthResponse,
)
from src.check_it_ai.types.evidence import (
    Citation,
    EvidenceBundle,
    EvidenceItem,
    EvidenceVerdict,
    Finding,
)
from src.check_it_ai.types.graph import (
    GraphCompleteEvent,
    GraphResult,
    NodeEndEvent,
    NodeStartEvent,
    StreamEvent,
)
from src.check_it_ai.types.output import FinalOutput
from src.check_it_ai.types.router import RouterDecision, RouterMetadata, RouterTrigger
from src.check_it_ai.types.search import SearchQuery, SearchResult
from src.check_it_ai.types.writer import WriterOutput

__all__ = [
    # Search
    "SearchQuery",
    "SearchResult",
    # Evidence
    "EvidenceItem",
    "EvidenceVerdict",
    "Finding",
    "EvidenceBundle",
    "Citation",
    # Analyst
    "ExtractedClaims",
    "SingleEvaluation",
    "VerdictResult",
    # Router
    "RouterTrigger",
    "RouterDecision",
    "RouterMetadata",
    # Output
    "FinalOutput",
    "WriterOutput",
    # Graph
    "GraphResult",
    "NodeStartEvent",
    "NodeEndEvent",
    "GraphCompleteEvent",
    "StreamEvent",
    # API
    "ChatRequest",
    "ChatResponse",
    "CheckRequest",
    "HealthResponse",
]
