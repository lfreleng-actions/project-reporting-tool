# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Synchronous URL validation.

Blocking HEAD-request validation with exponential backoff between retries,
plus sequential bulk validation over a list of URLs.
"""

import logging
import time

import httpx


class URLValidatorSyncMixin:
    """Blocking HEAD-request validation with retry and backoff."""

    # Assigned by URLValidator.__init__; declared here for type checking.
    timeout: float
    retries: int
    cache_enabled: bool
    logger: logging.Logger
    _cache: dict[str, tuple[bool, str]]

    def validate(self, url: str) -> tuple[bool, str]:
        """
        Validate a URL by making an HTTP HEAD request.

        Args:
            url: URL to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if URL is accessible, False otherwise
            - error_message: Empty string if valid, error description if invalid
        """
        if not url:
            return (False, "No URL provided")

        if self.cache_enabled and url in self._cache:
            self.logger.debug(f"Cache hit for URL: {url}")
            return self._cache[url]

        result = self._validate_with_retry(url)

        # Cache the result
        if self.cache_enabled:
            self._cache[url] = result

        return result

    def _validate_with_retry(self, url: str) -> tuple[bool, str]:
        """
        Validate URL with retry logic and exponential backoff.

        Args:
            url: URL to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        last_error = "Unknown error"

        for attempt in range(self.retries + 1):  # +1 for initial attempt
            try:
                # Use httpx to check URL
                with httpx.Client(follow_redirects=True, timeout=self.timeout) as client:
                    # Use HEAD request for efficiency
                    response = client.head(url)

                    if response.status_code < 400:
                        self.logger.debug(
                            f"URL validation succeeded for {url}: HTTP {response.status_code}"
                        )
                        return (True, "")
                    else:
                        # HTTP error - don't retry
                        error_msg = f"HTTP {response.status_code}"
                        self.logger.debug(f"URL validation failed for {url}: {error_msg}")
                        return (False, error_msg)

            except httpx.ConnectError as e:
                last_error = "Connection failed"
                self.logger.debug(
                    f"Connection error for {url} (attempt {attempt + 1}/{self.retries + 1}): {e}"
                )

            except httpx.TimeoutException as e:
                last_error = f"Timeout after {self.timeout}s"
                self.logger.debug(
                    f"Timeout for {url} (attempt {attempt + 1}/{self.retries + 1}): {e}"
                )

            except httpx.UnsupportedProtocol as e:
                # Don't retry protocol errors
                last_error = "Unsupported protocol"
                self.logger.debug(f"Protocol error for {url}: {e}")
                return (False, last_error)

            except httpx.InvalidURL as e:
                # Don't retry invalid URL errors
                last_error = "Invalid URL"
                self.logger.debug(f"Invalid URL {url}: {e}")
                return (False, last_error)

            except Exception as e:
                # Unexpected error - don't retry
                last_error = f"Unexpected error: {type(e).__name__}"
                self.logger.warning(f"Unexpected error validating {url}: {e}")
                return (False, last_error)

            # If we haven't returned yet, we need to retry
            if attempt < self.retries:
                # Exponential backoff: 1s, 2s, 4s, etc.
                retry_delay = 1.0 * (2**attempt)
                self.logger.debug(
                    f"Retrying {url} in {retry_delay}s (attempt {attempt + 1}/{self.retries + 1})"
                )
                time.sleep(retry_delay)

        # All retries exhausted
        error_msg = f"{last_error} (after {self.retries + 1} attempts)"
        self.logger.debug(f"URL validation failed for {url}: {error_msg}")
        return (False, error_msg)

    def validate_bulk(self, urls: list[str]) -> dict[str, tuple[bool, str]]:
        """
        Validate multiple URLs sequentially.

        Args:
            urls: List of URLs to validate

        Returns:
            Dictionary mapping URL to (is_valid, error_message) tuple
        """
        results = {}

        for url in urls:
            if not url:
                continue

            results[url] = self.validate(url)

        return results
