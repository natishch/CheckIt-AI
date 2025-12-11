"""DuckDuckGo search provider as a fallback option."""

from urllib.parse import urlparse

from pydantic import ValidationError

from src.check_it_ai.types.schemas import SearchResult
from src.check_it_ai.utils.logging import setup_logger

logger = setup_logger(__name__)


def duckduckgo_search(query: str, num_results: int = 10) -> list[SearchResult]:
    """Search using DuckDuckGo as a fallback search provider.

    This function is provided as a standalone search provider for use by the
    researcher node (AH-06) when Google Search or Fact Check API quota is exceeded.

    DuckDuckGo does not require API keys and has no quota limits, making it
    an ideal fallback option. However, results may be less comprehensive than
    Google Custom Search.

    Args:
        query: Search query string
        num_results: Number of results to return (default: 10)

    Returns:
        List of SearchResult models from DuckDuckGo
        Returns empty list on any error (graceful degradation)

    Note:
        Requires duckduckgo-search package: uv add duckduckgo-search
    """
    # Validate input
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    query = query.strip()

    try:
        from ddgs import DDGS
    except ImportError:
        logger.error(
            "ddgs package not installed. "
            "Install with: uv add ddgs"
        )
        return []

    try:
        logger.info(f"Using DuckDuckGo search for query: {query}")

        # Use DuckDuckGo search
        with DDGS() as ddgs:
            # Get text search results
            ddg_results = list(ddgs.text(query, max_results=num_results))

        logger.info(
            f"DuckDuckGo returned {len(ddg_results)} results",
            extra={"query": query},
        )

        # Convert DuckDuckGo results to SearchResult models
        parsed_results = []
        for i, item in enumerate(ddg_results, start=1):
            try:
                # Extract display domain from URL
                url = item.get("href", "")
                parsed_url = urlparse(url)
                display_domain = parsed_url.netloc or "unknown"

                result = SearchResult(
                    title=item.get("title", ""),
                    snippet=item.get("body", ""),
                    url=url,
                    display_domain=display_domain,
                    rank=i,
                )
                parsed_results.append(result)

            except ValidationError as e:
                logger.warning(
                    f"Failed to parse DuckDuckGo result at rank {i}",
                    extra={"error": str(e), "item": item},
                )
                # Skip invalid results
                continue

        logger.info(
            f"DuckDuckGo search completed: {len(parsed_results)} valid results",
            extra={"query": query},
        )

        return parsed_results

    except Exception as e:
        logger.error(
            f"DuckDuckGo search failed: {str(e)}",
            extra={"query": query, "error": str(e)},
        )
        return []
