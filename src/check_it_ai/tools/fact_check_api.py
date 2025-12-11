"""Google Fact Check Tools API client with caching support."""

from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError

from check_it_ai.config import settings
from check_it_ai.tools._http_utils import QuotaExceededError, make_api_request
from check_it_ai.types.schemas import SearchResult
from check_it_ai.utils.cache import SearchCache, search_cache
from check_it_ai.utils.logging import setup_logger

logger = setup_logger(__name__)

FACT_CHECK_API_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


# Backwards compatibility: Keep FactCheckQuotaError as alias for existing tests
FactCheckQuotaError = QuotaExceededError


def google_fact_check(
    query: str,
    num_results: int = 10,
    api_key: str | None = None,
    language_code: str = "en",
    cache: SearchCache | None = None,
) -> list[SearchResult]:
    """Search using Google Fact Check Tools API with caching.

    This API returns existing fact-checks from professional fact-checking organizations
    like PolitiFact, Snopes, FactCheck.org, etc.

    Args:
        query: Search query string
        num_results: Number of results to return (1-100)
        api_key: Google API key. If None, uses settings.google_api_key
        language_code: Language code (default: "en")
        cache: SearchCache instance. If None, uses global search_cache

    Returns:
        List of SearchResult Pydantic models with [FACT-CHECK] prefix in title

    Raises:
        QuotaExceededError: If API quota exceeded
        ValueError: If query is empty or num_results out of range
    """
    # Set defaults
    api_key = api_key or settings.google_api_key
    cache = cache or search_cache

    if not api_key:
        logger.warning(
            "Google API key not configured for Fact Check API. Set GOOGLE_API_KEY in .env file"
        )
        return []

    # Validate inputs
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    if not 1 <= num_results <= 100:
        raise ValueError("num_results must be between 1 and 100")

    query = query.strip()

    # Create cache key with "factcheck_" prefix to avoid collision with google_search cache
    cache_key = f"factcheck_{query}"

    # Step 1: Check cache first
    cached_results = cache.get(cache_key, num_results)
    if cached_results is not None:
        logger.info(
            f"Using cached fact-check results for query: {query}",
            extra={"num_results": len(cached_results)},
        )
        return _parse_fact_check_results(cached_results)

    # Step 2: Make API request
    try:
        logger.info(f"Fetching fact-check results from Google Fact Check API: {query}")
        raw_claims = _fetch_from_fact_check_api(query, num_results, api_key, language_code)

        # Step 3: Cache the raw results
        cache.set(cache_key, raw_claims, num_results)

        # Step 4: Parse and return
        parsed_results = _parse_fact_check_results(raw_claims)

        logger.info(
            f"Successfully fetched {len(parsed_results)} fact-check results",
            extra={"query": query},
        )

        return parsed_results

    except QuotaExceededError:
        # Re-raise quota errors for researcher node to handle
        logger.warning(f"Fact Check API quota exceeded for query: {query}")
        raise

    except Exception as e:
        logger.error(
            f"Fact Check API request failed: {str(e)}",
            extra={"query": query, "error": str(e)},
        )
        # Return empty list on failure to allow graceful degradation
        return []


def _fetch_from_fact_check_api(
    query: str, num_results: int, api_key: str, language_code: str
) -> list[dict[str, Any]]:
    """Fetch results from Google Fact Check Tools API.

    Args:
        query: Search query
        num_results: Number of results
        api_key: Google API key
        language_code: Language code (e.g., "en", "es", "fr")

    Returns:
        Raw API response claims

    Raises:
        QuotaExceededError: If quota exceeded (429 or 403)
        httpx.HTTPError: For other HTTP errors
    """
    params = {
        "key": api_key,
        "query": query,
        "languageCode": language_code,
        "pageSize": min(num_results, 100),  # API max is 100
    }

    # Use shared HTTP utility for consistent error handling
    data = make_api_request(FACT_CHECK_API_URL, params)
    claims = data.get("claims", [])

    logger.info(
        f"Successfully fetched {len(claims)} claims from Fact Check API",
        extra={"query": query},
    )

    return claims


def _parse_fact_check_results(raw_claims: list[dict[str, Any]]) -> list[SearchResult]:
    """Parse raw Fact Check API claims into SearchResult Pydantic models.

    The Fact Check API returns ClaimReview structured data. We normalize it to
    SearchResult format for consistency with Google Search results.

    Args:
        raw_claims: Raw claims from Fact Check API or cache

    Returns:
        List of validated SearchResult models with [FACT-CHECK] prefix
    """
    parsed_results = []

    for i, claim in enumerate(raw_claims, start=1):
        try:
            # Extract claim text
            claim_text = claim.get("text", "")
            if not claim_text:
                logger.warning(f"Claim at rank {i} has no text, skipping")
                continue

            # Get claimReview array (may have multiple fact-checkers for same claim)
            claim_reviews = claim.get("claimReview", [])
            if not claim_reviews:
                logger.warning(f"Claim at rank {i} has no reviews, skipping")
                continue

            # Use the first review (typically most authoritative)
            review = claim_reviews[0]

            # Extract review details
            publisher = review.get("publisher", {})
            publisher_name = publisher.get("name", "Fact Checker")
            publisher_site = publisher.get("site", "")

            review_url = review.get("url", "")
            if not review_url:
                logger.warning(f"Claim at rank {i} has no review URL, skipping")
                continue

            review_title = review.get("title", "")
            textual_rating = review.get("textualRating", "Unknown")

            # Build snippet with rating and review title
            snippet_parts = [f"Rating: {textual_rating}"]
            if review_title:
                snippet_parts.append(review_title)
            else:
                snippet_parts.append(claim_text[:200])  # Fallback to claim text

            snippet = " | ".join(snippet_parts)

            # Parse display domain from URL
            try:
                parsed_url = urlparse(review_url)
                display_domain = publisher_site or parsed_url.netloc or publisher_name
            except Exception:
                display_domain = publisher_name

            # Create SearchResult with [FACT-CHECK] prefix
            result = SearchResult(
                title=f"[FACT-CHECK] {claim_text[:100]}",  # Truncate long claims
                snippet=snippet,
                url=review_url,
                display_domain=display_domain,
                rank=i,
            )
            parsed_results.append(result)

        except ValidationError as e:
            logger.warning(
                f"Failed to parse fact-check claim at rank {i}",
                extra={"error": str(e), "claim": claim},
            )
            # Skip invalid results
            continue

        except Exception as e:
            logger.warning(
                f"Unexpected error parsing fact-check claim at rank {i}: {str(e)}",
                extra={"claim": claim},
            )
            continue

    logger.debug(
        f"Parsed {len(parsed_results)} valid fact-check results out of {len(raw_claims)} total"
    )

    return parsed_results


# Backwards compatibility: Keep FactCheckClient as a wrapper
class FactCheckClient:
    """Wrapper class for backwards compatibility.

    Deprecated: Use google_fact_check() function directly instead.
    """

    def __init__(
        self,
        api_key: str | None = None,
        language_code: str = "en",
        cache: SearchCache | None = None,
    ):
        """Initialize Fact Check API client.

        Args:
            api_key: Google API key. If None, uses settings.google_api_key
            language_code: Language code (default: "en")
            cache: SearchCache instance. If None, uses global search_cache
        """
        self.api_key = api_key
        self.language_code = language_code
        self.cache = cache

    def search(self, query: str, num_results: int = 10) -> list[SearchResult]:
        """Search using Google Fact Check Tools API with caching.

        Args:
            query: Search query string
            num_results: Number of results to return (1-100)

        Returns:
            List of SearchResult Pydantic models

        Raises:
            QuotaExceededError: If API quota exceeded
            ValueError: If query is empty or num_results out of range
        """
        return google_fact_check(
            query=query,
            num_results=num_results,
            api_key=self.api_key,
            language_code=self.language_code,
            cache=self.cache,
        )
