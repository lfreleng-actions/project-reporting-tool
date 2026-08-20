# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
URL validator construction and result cache.

Owns the timeout/retry settings and the in-process result cache, and
composes the synchronous and asynchronous validation mixins.
"""

import logging

from .asynchronous import URLValidatorAsyncMixin
from .synchronous import URLValidatorSyncMixin


class URLValidator(URLValidatorSyncMixin, URLValidatorAsyncMixin):
    """
    Validates HTTP/HTTPS URLs with caching and retry logic.

    Features:
    - Caching to avoid repeated requests to the same URL
    - Configurable timeout and retry count
    - Exponential backoff for transient failures
    - Follows redirects
    - HEAD requests for efficiency
    """

    def __init__(
        self,
        timeout: float = 10.0,
        retries: int = 2,
        cache_enabled: bool = True,
    ):
        """
        Initialize the URL validator.

        Args:
            timeout: Request timeout in seconds (default: 10.0)
            retries: Number of retry attempts (default: 2)
            cache_enabled: Enable response caching (default: True)
        """
        self.timeout = timeout
        self.retries = retries
        self.cache_enabled = cache_enabled

        # Cache for validation results: {url: (is_valid, error_message)}
        self._cache: dict[str, tuple[bool, str]] = {}

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(
            f"URLValidator initialized: timeout={timeout}s, retries={retries}, "
            f"cache={cache_enabled}"
        )

    def clear_cache(self) -> None:
        """Clear the validation cache."""
        self._cache.clear()
        self.logger.debug("Validation cache cleared")

    def get_cache_stats(self) -> dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics:
            - total_entries: Total number of cached entries
            - valid_entries: Number of valid URLs in cache
            - invalid_entries: Number of invalid URLs in cache
        """
        stats = {
            "total_entries": len(self._cache),
            "valid_entries": sum(1 for is_valid, _ in self._cache.values() if is_valid),
            "invalid_entries": sum(1 for is_valid, _ in self._cache.values() if not is_valid),
        }
        return stats

    def get_cached_result(self, url: str) -> tuple[bool, str] | None:
        """
        Get cached validation result for a URL.

        Args:
            url: URL to look up

        Returns:
            Cached result tuple or None if not in cache
        """
        return self._cache.get(url)

    def is_url_cached(self, url: str) -> bool:
        """
        Check if a URL is in the cache.

        Args:
            url: URL to check

        Returns:
            True if URL is cached, False otherwise
        """
        return url in self._cache
