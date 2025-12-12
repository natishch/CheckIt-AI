"""JSON file-based cache for search results to save API quota."""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.check_it_ai.config import settings
from src.check_it_ai.utils.logging import setup_logger

logger = setup_logger(__name__)


class SearchCache:
    """File-based cache for storing search results.

    Uses JSON files keyed by query hash to cache Google Search API results.
    Critical for saving API quota during development and demos.
    """

    def __init__(self, cache_dir: Path | None = None, ttl_hours: int | None = None):
        """Initialize the search cache.

        Args:
            cache_dir: Directory to store cache files. If None, uses settings.cache_dir
            ttl_hours: Time-to-live for cache entries in hours. If None, uses settings.cache_ttl_hours
        """
        self.cache_dir = cache_dir or settings.cache_dir
        self.ttl_hours = ttl_hours or settings.cache_ttl_hours

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "SearchCache initialized",
            extra={"cache_dir": str(self.cache_dir), "ttl_hours": self.ttl_hours},
        )

    def _get_cache_key(self, query: str, num_results: int = 10) -> str:
        """Generate a cache key from query parameters.

        Args:
            query: Search query string
            num_results: Number of results requested

        Returns:
            Hash string to use as cache key
        """
        # Create a unique key from query + num_results
        cache_input = f"{query.lower().strip()}:{num_results}"
        return hashlib.sha256(cache_input.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key.

        Args:
            cache_key: Cache key hash

        Returns:
            Path to cache file
        """
        return self.cache_dir / f"{cache_key}.json"

    def get(self, query: str, num_results: int = 10) -> list[dict[str, Any]] | None:
        """Retrieve cached search results.

        Args:
            query: Search query string
            num_results: Number of results requested

        Returns:
            Cached search results if valid cache hit, None otherwise
        """
        cache_key = self._get_cache_key(query, num_results)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            logger.debug(f"Cache miss: {query}", extra={"cache_key": cache_key})
            return None

        try:
            with cache_path.open("r") as f:
                cache_data = json.load(f)

            # Check if cache is expired
            cached_time = datetime.fromisoformat(cache_data["timestamp"])
            expiry_time = cached_time + timedelta(hours=self.ttl_hours)

            if datetime.now() > expiry_time:
                logger.debug(
                    f"Cache expired: {query}",
                    extra={
                        "cache_key": cache_key,
                        "cached_time": cached_time.isoformat(),
                    },
                )
                # Remove expired cache file
                cache_path.unlink()
                return None

            logger.info(
                f"Cache hit: {query}",
                extra={
                    "cache_key": cache_key,
                    "num_results": len(cache_data["results"]),
                },
            )
            return cache_data["results"]

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(
                f"Invalid cache file: {cache_path}",
                extra={"error": str(e)},
            )
            # Remove corrupted cache file
            cache_path.unlink(missing_ok=True)
            return None

    def set(self, query: str, results: list[dict[str, Any]], num_results: int = 10) -> None:
        """Store search results in cache.

        Args:
            query: Search query string
            results: Search results to cache
            num_results: Number of results requested
        """
        cache_key = self._get_cache_key(query, num_results)
        cache_path = self._get_cache_path(cache_key)

        cache_data = {
            "query": query,
            "num_results": num_results,
            "timestamp": datetime.now().isoformat(),
            "results": results,
        }

        try:
            with cache_path.open("w") as f:
                json.dump(cache_data, f, indent=2)

            logger.info(
                f"Cached search results: {query}",
                extra={
                    "cache_key": cache_key,
                    "num_results": len(results),
                },
            )
        except (OSError, TypeError) as e:
            logger.error(
                f"Failed to write cache: {cache_path}",
                extra={"error": str(e)},
            )

    def clear(self) -> int:
        """Clear all cache files.

        Returns:
            Number of cache files deleted
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except OSError as e:
                logger.warning(
                    f"Failed to delete cache file: {cache_file}",
                    extra={"error": str(e)},
                )

        logger.info("Cleared cache", extra={"files_deleted": count})
        return count

    def clear_expired(self) -> int:
        """Clear only expired cache files.

        Returns:
            Number of expired cache files deleted
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with cache_file.open("r") as f:
                    cache_data = json.load(f)

                cached_time = datetime.fromisoformat(cache_data["timestamp"])
                expiry_time = cached_time + timedelta(hours=self.ttl_hours)

                if datetime.now() > expiry_time:
                    cache_file.unlink()
                    count += 1
            except (json.JSONDecodeError, KeyError, ValueError, OSError) as e:
                logger.warning(
                    f"Error processing cache file: {cache_file}",
                    extra={"error": str(e)},
                )
                # Delete corrupted files
                cache_file.unlink(missing_ok=True)
                count += 1

        logger.info("Cleared expired cache", extra={"files_deleted": count})
        return count


# Global cache instance
search_cache = SearchCache()
