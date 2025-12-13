"""Type definitions for check-it-ai.

This module re-exports all types from submodules for convenient imports.
"""

from src.check_it_ai.types.evidence import (
    Citation,
    EvidenceBundle,
    EvidenceItem,
    EvidenceVerdict,
    Finding,
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
    # Router
    "RouterTrigger",
    "RouterDecision",
    "RouterMetadata",
    # Output
    "FinalOutput",
    "WriterOutput",
]
