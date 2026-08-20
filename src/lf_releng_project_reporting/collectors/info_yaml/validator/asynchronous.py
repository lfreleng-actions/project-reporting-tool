# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Asynchronous URL validation.

Non-blocking HEAD-request validation with exponential backoff, and
semaphore-bounded concurrent bulk validation over a list of URLs.
"""

import asyncio
import logging
import time

import httpx


class URLValidatorAsyncMixin:
    """Concurrent HEAD-request validation with retry and backoff."""

    # Assigned by URLValidator.__init__; declared here for type checking.
    timeout: float
    retries: int
    cache_enabled: bool
    logger: logging.Logger
    _cache: dict[str, tuple[bool, str]]

    async def validate_async(self, url: str) -> tuple[bool, str]:
        """
        Validate a URL asynchronously by making an HTTP HEAD request.

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

        result = await self._validate_with_retry_async(url)

        # Cache the result
        if self.cache_enabled:
            self._cache[url] = result

        return result

    async def _validate_with_retry_async(self, url: str) -> tuple[bool, str]:
        """
        Validate URL asynchronously with retry logic and exponential backoff.

        Args:
            url: URL to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        last_error = "Unknown error"

        for attempt in range(self.retries + 1):  # +1 for initial attempt
            try:
                # Use httpx async client to check URL
                async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
                    # Use HEAD request for efficiency
                    response = await client.head(url)

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
                await asyncio.sleep(retry_delay)

        # All retries exhausted
        error_msg = f"{last_error} (after {self.retries + 1} attempts)"
        self.logger.debug(f"URL validation failed for {url}: {error_msg}")
        return (False, error_msg)

    async def validate_bulk_async(
        self, urls: list[str], max_concurrent: int = 10
    ) -> dict[str, tuple[bool, str]]:
        """
        Validate multiple URLs concurrently using async HTTP requests.

        This method provides significant performance improvements over sequential
        validation when checking many URLs.

        Args:
            urls: List of URLs to validate
            max_concurrent: Maximum number of concurrent requests (default: 10)

        Returns:
            Dictionary mapping URL to (is_valid, error_message) tuple
        """
        # Filter out empty URLs
        valid_urls = [url for url in urls if url]

        if not valid_urls:
            return {}

        semaphore = asyncio.Semaphore(max_concurrent)

        async def validate_with_semaphore(url: str) -> tuple[str, tuple[bool, str]]:
            """Validate a single URL with semaphore control."""
            async with semaphore:
                result = await self.validate_async(url)
                return (url, result)

        tasks = [validate_with_semaphore(url) for url in valid_urls]

        self.logger.info(
            f"Starting concurrent validation of {len(valid_urls)} URLs "
            f"(max_concurrent={max_concurrent})"
        )
        start_time = time.time()

        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = time.time() - start_time
        self.logger.info(
            f"Completed validation of {len(valid_urls)} URLs in {elapsed:.2f}s "
            f"({len(valid_urls) / elapsed:.1f} URLs/s)"
        )

        # Convert results to dictionary
        results = {}
        for item in results_list:
            if isinstance(item, Exception):
                self.logger.error(f"Task failed with exception: {item}")
                continue
            if isinstance(item, tuple) and len(item) == 2:
                url, result = item
                results[url] = result

        return results
