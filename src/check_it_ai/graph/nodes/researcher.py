"""Researcher agent for Google Search API integration."""

from src.check_it_ai.graph.state import AgentState
from src.check_it_ai.types.search import SearchResult


def researcher_node(state: AgentState) -> dict:
    """Execute Google Search and return results.

    Returns:
        Dict with search_results: list[SearchResult]
    """
    # TODO: Implement actual search logic
    # Placeholder returns empty list of SearchResult objects
    search_results: list[SearchResult] = []
    return {"search_results": search_results}
