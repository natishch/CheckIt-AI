"""Shared HTTP utilities for search tools to reduce code duplication."""

import httpx

from check_it_ai.config import settings
from check_it_ai.utils.logging import setup_logger

logger = setup_logger(__name__)


class QuotaExceededError(Exception):
    """Base exception for API quota errors across all search providers.

    This exception is raised when any search API (Google Search, Fact Check, etc.)
    returns a quota exceeded error (typically HTTP 403 or 429).
    """

    pass


def make_api_request(
    url: str,
    params: dict,
    timeout: int | None = None,
    quota_statuses: tuple[int, ...] = (403, 429),
) -> dict:
    """Make HTTP GET request with standardized quota error handling.

    This utility function provides consistent error handling across all search tools.
    It automatically detects quota exceeded errors and raises QuotaExceededError.

    Args:
        url: API endpoint URL
        params: Query parameters for the GET request
        timeout: Request timeout in seconds. If None, uses settings.search_timeout
        quota_statuses: HTTP status codes that indicate quota exceeded (default: 403, 429)

    Returns:
        Parsed JSON response as dictionary

    Raises:
        QuotaExceededError: If response status code is in quota_statuses
        httpx.TimeoutException: If request times out
        httpx.HTTPError: For other HTTP errors
    """
    timeout = timeout or settings.search_timeout

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, params=params)

            # Check for quota errors first
            if response.status_code in quota_statuses:
                error_detail = response.json().get("error", {})
                error_message = error_detail.get("message", "Quota exceeded")
                raise QuotaExceededError(
                    f"API quota exceeded: {error_message} (status: {response.status_code})"
                )

            # Raise for other HTTP errors
            response.raise_for_status()

            # Parse and return JSON
            return response.json()

    except httpx.TimeoutException:
        logger.error(f"Request timeout for URL: {url}")
        raise
    except httpx.HTTPError as e:
        logger.error(
            "HTTP error during API request",
            extra={"url": url, "error": str(e)},
        )
        raise
