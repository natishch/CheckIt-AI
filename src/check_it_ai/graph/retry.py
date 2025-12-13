"""Retry utilities for graph node execution."""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryableError(Exception):
    """Exception that indicates the operation should be retried."""

    pass


def with_retry(
    max_attempts: int = 2,
    delay_seconds: float = 1.0,
    retryable_exceptions: tuple[type[Exception], ...] = (RetryableError,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to add retry logic to a function.

    Args:
        max_attempts: Maximum number of attempts (including first try).
        delay_seconds: Delay between retries.
        retryable_exceptions: Exception types that trigger retry.

    Example:
        @with_retry(max_attempts=2)
        def call_api():
            response = httpx.get(url)
            if response.status_code == 429:
                raise RetryableError("Rate limited")
            return response
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            "%s failed (attempt %d/%d): %s. Retrying in %ss...",
                            func.__name__,
                            attempt,
                            max_attempts,
                            e,
                            delay_seconds,
                        )
                        time.sleep(delay_seconds)
                    else:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__,
                            max_attempts,
                            e,
                        )

            if last_exception is not None:
                raise last_exception
            raise RuntimeError("Unexpected state: no exception but no return value")

        return wrapper

    return decorator


def with_retry_async(
    max_attempts: int = 2,
    delay_seconds: float = 1.0,
    retryable_exceptions: tuple[type[Exception], ...] = (RetryableError,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Async version of retry decorator.

    Args:
        max_attempts: Maximum number of attempts (including first try).
        delay_seconds: Delay between retries.
        retryable_exceptions: Exception types that trigger retry.

    Example:
        @with_retry_async(max_attempts=2)
        async def call_api():
            response = await httpx.get(url)
            if response.status_code == 429:
                raise RetryableError("Rate limited")
            return response
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            "%s failed (attempt %d/%d): %s. Retrying in %ss...",
                            func.__name__,
                            attempt,
                            max_attempts,
                            e,
                            delay_seconds,
                        )
                        await asyncio.sleep(delay_seconds)
                    else:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__,
                            max_attempts,
                            e,
                        )

            if last_exception is not None:
                raise last_exception
            raise RuntimeError("Unexpected state: no exception but no return value")

        return wrapper  # type: ignore[return-value]

    return decorator
