# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Retry logic for concurrent operations.

Holds the with_retry decorator, which wraps a callable in exponential
backoff retries and optionally records each failure with a
ConcurrentErrorHandler.
"""

import time
from collections.abc import Callable
from typing import Any

from .handler import ConcurrentErrorHandler


def with_retry(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    error_handler: ConcurrentErrorHandler | None = None,
    context: str = "unknown",
    retry_on: tuple[type[Exception], ...] = (Exception,),
):
    """
    Decorator to add retry logic with exponential backoff to a function.

    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for delay between retries
        initial_delay: Initial delay in seconds before first retry
        error_handler: Error handler to record failures
        context: Context for error reporting
        retry_on: Tuple of exception types to retry on

    Returns:
        Decorator function

    Example:
        >>> @with_retry(max_retries=3, backoff_factor=2.0)
        >>> def fetch_data(endpoint_url):
        >>>     return requests.get(endpoint_url)
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args, **kwargs):
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except retry_on as e:
                    last_exception = e

                    # Record error if handler provided
                    if error_handler:
                        error_handler.record_error(
                            context=context,
                            error=e,
                            retry_count=attempt,
                            metadata={"max_retries": max_retries},
                        )

                    # Don't sleep after last attempt
                    if attempt < max_retries:
                        delay = initial_delay * (backoff_factor**attempt)
                        time.sleep(delay)

            # All retries exhausted, raise last exception
            if last_exception is not None:
                raise last_exception
            # Should never reach here, but satisfy type checker
            raise RuntimeError("Retry loop completed without exception or return")

        return wrapper

    return decorator
