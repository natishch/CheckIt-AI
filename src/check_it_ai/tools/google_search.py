"""Google Custom Search API client with caching support."""

from typing import Any

from pydantic import ValidationError

from src.check_it_ai.config import settings
from src.check_it_ai.tools._http_utils import QuotaExceededError, make_api_request
from src.check_it_ai.types.search import SearchResult
from src.check_it_ai.utils.cache import SearchCache, search_cache
from src.check_it_ai.utils.logging import setup_logger

logger = setup_logger(__name__)

GOOGLE_SEARCH_API_URL = "https://www.googleapis.com/customsearch/v1"


# Backwards compatibility: Keep QuotaError as alias for existing tests
QuotaError = QuotaExceededError


def google_search(
    query: str,
    num_results: int = 10,
    api_key: str | None = None,
    cse_id: str | None = None,
    cache: SearchCache | None = None,
) -> list[SearchResult]:
    """Search using Google Custom Search API with caching.

    Note: This function no longer handles DuckDuckGo fallback internally.
    Fallback logic should be implemented in the researcher node (AH-06) for
    better separation of concerns.

    Args:
        query: Search query string
        num_results: Number of results to return (1-100)
        api_key: Google API key. If None, uses settings.google_api_key
        cse_id: Google Custom Search Engine ID. If None, uses settings.google_cse_id
        cache: SearchCache instance. If None, uses global search_cache

    Returns:
        List of SearchResult Pydantic models

    Raises:
        QuotaExceededError: If Google API quota exceeded
        ValueError: If query is empty or num_results out of range
    """
    # Set defaults
    api_key = api_key or settings.google_api_key
    cse_id = cse_id or settings.google_cse_id
    cache = cache or search_cache

    if not api_key or not cse_id:
        logger.warning(
            "Google API credentials not configured. "
            "Set GOOGLE_API_KEY and GOOGLE_CSE_ID in .env file"
        )
        return []

    # Validate inputs
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    if not 1 <= num_results <= 100:
        raise ValueError("num_results must be between 1 and 100")

    query = query.strip()

    # Step 1: Check cache first
    cached_results = cache.get(query, num_results)
    if cached_results is not None:
        logger.info(
            f"Using cached results for query: {query}",
            extra={"num_results": len(cached_results)},
        )
        return _parse_results(cached_results)

    # Step 2: Make API request
    logger.info(f"Fetching search results from Google API: {query}")
    results = _fetch_from_google(query, num_results, api_key, cse_id)

    # Step 3: Cache the results
    cache.set(query, results, num_results)

    # Step 4: Parse and return
    return _parse_results(results)


def _fetch_from_google(
    query: str, num_results: int, api_key: str, cse_id: str
) -> list[dict[str, Any]]:
    """Fetch results from Google Custom Search API.

    Args:
        query: Search query
        num_results: Number of results
        api_key: Google API key
        cse_id: Google Custom Search Engine ID

    Returns:
        Raw API response items

    Raises:
        QuotaExceededError: If quota exceeded (429 or 403)
        httpx.HTTPError: For other HTTP errors
    """
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "num": min(num_results, 10),  # Google API max is 10 per request
    }

    # Use shared HTTP utility for consistent error handling
    data = make_api_request(GOOGLE_SEARCH_API_URL, params)
    items = data.get("items", [])

    logger.info(
        f"Successfully fetched {len(items)} results from Google",
        extra={"query": query},
    )

    return items


def _parse_results(raw_results: list[dict[str, Any]]) -> list[SearchResult]:
    """Parse raw API results into SearchResult Pydantic models.

    Args:
        raw_results: Raw search results from API or cache

    Returns:
        List of validated SearchResult models
    """
    parsed_results = []

    for i, item in enumerate(raw_results, start=1):
        try:
            # Extract fields from Google API response
            result = SearchResult(
                title=item.get("title", ""),
                snippet=item.get("snippet", ""),
                url=item.get("link", ""),
                display_domain=item.get("displayLink", ""),
                rank=i,
            )
            parsed_results.append(result)

        except ValidationError as e:
            logger.warning(
                f"Failed to parse search result at rank {i}",
                extra={"error": str(e), "item": item},
            )
            # Skip invalid results
            continue

    logger.debug(f"Parsed {len(parsed_results)} valid results out of {len(raw_results)} total")

    return parsed_results


# Backwards compatibility: Keep GoogleSearchClient as a wrapper
class GoogleSearchClient:
    """Wrapper class for backwards compatibility.

    Deprecated: Use google_search() function directly instead.
    """

    def __init__(
        self,
        api_key: str | None = None,
        cse_id: str | None = None,
        cache: SearchCache | None = None,
    ):
        """Initialize Google Search client.

        Args:
            api_key: Google API key. If None, uses settings.google_api_key
            cse_id: Google Custom Search Engine ID. If None, uses settings.google_cse_id
            cache: SearchCache instance. If None, uses global search_cache
        """
        self.api_key = api_key
        self.cse_id = cse_id
        self.cache = cache

    def search(self, query: str, num_results: int = 10) -> list[SearchResult]:
        """Search using Google Custom Search API with caching.

        Args:
            query: Search query string
            num_results: Number of results to return (1-100)

        Returns:
            List of SearchResult Pydantic models

        Raises:
            QuotaExceededError: If Google API quota exceeded
            ValueError: If query is empty or num_results out of range
        """
        return google_search(
            query=query,
            num_results=num_results,
            api_key=self.api_key,
            cse_id=self.cse_id,
            cache=self.cache,
        )
