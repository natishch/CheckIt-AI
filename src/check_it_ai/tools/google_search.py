"""Google Custom Search API client with caching and fallback support."""

from typing import Any

import httpx
from pydantic import ValidationError

from check_it_ai.config import settings
from check_it_ai.types.schemas import SearchResult
from check_it_ai.utils.cache import SearchCache, search_cache
from check_it_ai.utils.logging import setup_logger

logger = setup_logger(__name__)

GOOGLE_SEARCH_API_URL = "https://www.googleapis.com/customsearch/v1"


class QuotaError(Exception):
    """Raised when Google API quota is exceeded."""

    pass


def google_search(
    query: str,
    num_results: int = 10,
    api_key: str | None = None,
    cse_id: str | None = None,
    cache: SearchCache | None = None,
    use_fallback: bool | None = None,
) -> list[SearchResult]:
    """Search using Google Custom Search API with caching.

    Args:
        query: Search query string
        num_results: Number of results to return (1-100)
        api_key: Google API key. If None, uses settings.google_api_key
        cse_id: Google Custom Search Engine ID. If None, uses settings.google_cse_id
        cache: SearchCache instance. If None, uses global search_cache
        use_fallback: Enable DuckDuckGo fallback. If None, uses settings.use_duckduckgo_backup

    Returns:
        List of SearchResult Pydantic models

    Raises:
        QuotaError: If Google API quota exceeded and no fallback enabled
        ValueError: If query is empty or num_results out of range
    """
    # Set defaults
    api_key = api_key or settings.google_api_key
    cse_id = cse_id or settings.google_cse_id
    cache = cache or search_cache
    use_fallback = (
        use_fallback if use_fallback is not None else settings.use_duckduckgo_backup
    )

    if not api_key or not cse_id:
        logger.warning(
            "Google API credentials not configured. "
            "Set GOOGLE_API_KEY and GOOGLE_CSE_ID in .env file"
        )

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
    try:
        logger.info(f"Fetching search results from Google API: {query}")
        results = _fetch_from_google(query, num_results, api_key, cse_id)

        # Step 3: Cache the results
        cache.set(query, results, num_results)

        # Step 4: Parse and return
        return _parse_results(results)

    except QuotaError as e:
        logger.warning(
            f"Google API quota exceeded for query: {query}",
            extra={"error": str(e)},
        )

        # Step 5: Try fallback if enabled
        if use_fallback:
            logger.info("Attempting DuckDuckGo fallback")
            return _fallback_search(query, num_results)
        else:
            raise


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
        QuotaError: If quota exceeded (429 or 403)
        httpx.HTTPError: For other HTTP errors
    """
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "num": min(num_results, 10),  # Google API max is 10 per request
    }

    try:
        with httpx.Client(timeout=settings.search_timeout) as client:
            response = client.get(GOOGLE_SEARCH_API_URL, params=params)

            # Check for quota errors
            if response.status_code in [403, 429]:
                error_detail = response.json().get("error", {})
                error_message = error_detail.get("message", "Quota exceeded")
                raise QuotaError(
                    f"Google API quota exceeded: {error_message} (status: {response.status_code})"
                )

            # Raise for other HTTP errors
            response.raise_for_status()

            # Parse response
            data = response.json()
            items = data.get("items", [])

            logger.info(
                f"Successfully fetched {len(items)} results from Google",
                extra={"query": query},
            )

            return items

    except httpx.TimeoutException:
        logger.error(f"Request timeout for query: {query}")
        raise
    except httpx.HTTPError as e:
        logger.error(
            "HTTP error during Google search",
            extra={"query": query, "error": str(e)},
        )
        raise


def _fallback_search(query: str, num_results: int) -> list[SearchResult]:
    """Fallback to DuckDuckGo search when Google quota exceeded.

    Args:
        query: Search query
        num_results: Number of results

    Returns:
        List of SearchResult models from DuckDuckGo

    Raises:
        ImportError: If duckduckgo-search is not installed
    """
    try:
        from urllib.parse import urlparse

        from duckduckgo_search import DDGS
    except ImportError:
        logger.error(
            "duckduckgo-search not installed. " "Install with: uv add duckduckgo-search"
        )
        return []

    try:
        logger.info(f"Using DuckDuckGo fallback for query: {query}")

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
            f"DuckDuckGo fallback completed: {len(parsed_results)} valid results",
            extra={"query": query},
        )

        return parsed_results

    except Exception as e:
        logger.error(
            f"DuckDuckGo fallback failed: {str(e)}",
            extra={"query": query, "error": str(e)},
        )
        return []


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

    logger.debug(
        f"Parsed {len(parsed_results)} valid results out of {len(raw_results)} total"
    )

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
        use_fallback: bool | None = None,
    ):
        """Initialize Google Search client.

        Args:
            api_key: Google API key. If None, uses settings.google_api_key
            cse_id: Google Custom Search Engine ID. If None, uses settings.google_cse_id
            cache: SearchCache instance. If None, uses global search_cache
            use_fallback: Enable DuckDuckGo fallback. If None, uses settings.use_duckduckgo_backup
        """
        self.api_key = api_key
        self.cse_id = cse_id
        self.cache = cache
        self.use_fallback = use_fallback

    def search(self, query: str, num_results: int = 10) -> list[SearchResult]:
        """Search using Google Custom Search API with caching.

        Args:
            query: Search query string
            num_results: Number of results to return (1-100)

        Returns:
            List of SearchResult Pydantic models

        Raises:
            QuotaError: If Google API quota exceeded and no fallback enabled
            ValueError: If query is empty or num_results out of range
        """
        return google_search(
            query=query,
            num_results=num_results,
            api_key=self.api_key,
            cse_id=self.cse_id,
            cache=self.cache,
            use_fallback=self.use_fallback,
        )
