# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Module-level URL validation convenience functions.

One-shot wrappers around ``URLValidator`` for single URLs, sequential
batches, concurrent batches, and automatic async/sync selection.
"""

import asyncio
import logging


logger = logging.getLogger(__name__)


def validate_url(url: str, timeout: float = 10.0, retries: int = 2) -> tuple[bool, str]:
    """
    Convenience function to validate a single URL.

    Args:
        url: URL to validate
        timeout: Request timeout in seconds
        retries: Number of retry attempts

    Returns:
        Tuple of (is_valid, error_message)
    """
    from . import URLValidator

    validator = URLValidator(timeout=timeout, retries=retries, cache_enabled=False)
    return validator.validate(url)


def validate_urls(
    urls: list[str], timeout: float = 10.0, retries: int = 2
) -> dict[str, tuple[bool, str]]:
    """
    Convenience function to validate multiple URLs sequentially.

    Args:
        urls: List of URLs to validate
        timeout: Request timeout in seconds
        retries: Number of retry attempts

    Returns:
        Dictionary mapping URL to (is_valid, error_message) tuple
    """
    from . import URLValidator

    validator = URLValidator(timeout=timeout, retries=retries, cache_enabled=True)
    return validator.validate_bulk(urls)


async def validate_urls_async(
    urls: list[str],
    timeout: float = 10.0,
    retries: int = 2,
    max_concurrent: int = 10,
) -> dict[str, tuple[bool, str]]:
    """
    Convenience function to validate multiple URLs concurrently.

    This async function provides significant performance improvements when
    validating many URLs by making concurrent HTTP requests.

    Args:
        urls: List of URLs to validate
        timeout: Request timeout in seconds
        retries: Number of retry attempts
        max_concurrent: Maximum number of concurrent requests (default: 10)

    Returns:
        Dictionary mapping URL to (is_valid, error_message) tuple

    Example:
        >>> urls = ["https://example.com", "https://github.com"]
        >>> results = await validate_urls_async(urls, max_concurrent=5)
        >>> print(results)
        {'https://example.com': (True, ''), 'https://github.com': (True, '')}
    """
    from . import URLValidator

    validator = URLValidator(timeout=timeout, retries=retries, cache_enabled=True)
    return await validator.validate_bulk_async(urls, max_concurrent=max_concurrent)


def validate_urls_sync(
    urls: list[str],
    timeout: float = 10.0,
    retries: int = 2,
    max_concurrent: int = 10,
    use_async: bool = True,
) -> dict[str, tuple[bool, str]]:
    """
    Convenience function to validate multiple URLs with automatic async/sync selection.

    This function automatically uses async validation for better performance when
    validating multiple URLs, but can fall back to synchronous validation if needed.

    Args:
        urls: List of URLs to validate
        timeout: Request timeout in seconds
        retries: Number of retry attempts
        max_concurrent: Maximum number of concurrent requests (default: 10)
        use_async: Use async validation for better performance (default: True)

    Returns:
        Dictionary mapping URL to (is_valid, error_message) tuple

    Example:
        >>> urls = ["https://example.com", "https://github.com"]
        >>> results = validate_urls_sync(urls, max_concurrent=5)
        >>> print(results)
        {'https://example.com': (True, ''), 'https://github.com': (True, '')}
    """
    if use_async and len(urls) > 1:
        # Use async validation for multiple URLs
        try:
            # Try to get existing event loop
            try:
                asyncio.get_running_loop()
                # We're already in an async context, can't use asyncio.run()
                # Fall back to sync validation
                logger.debug("Event loop already running, falling back to sync validation")
                return validate_urls(urls, timeout=timeout, retries=retries)
            except RuntimeError:
                # No event loop exists, create one with asyncio.run()
                pass

            # Use asyncio.run() which properly cleans up the event loop
            return asyncio.run(
                validate_urls_async(
                    urls, timeout=timeout, retries=retries, max_concurrent=max_concurrent
                )
            )
        except Exception as e:
            # If async fails for any reason, fall back to sync
            logger.warning(f"Async validation failed, falling back to sync: {e}")
            return validate_urls(urls, timeout=timeout, retries=retries)
    else:
        # Use synchronous validation for single URL or when async is disabled
        return validate_urls(urls, timeout=timeout, retries=retries)
