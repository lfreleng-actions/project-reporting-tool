# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Batch processing coordination and factory helpers.

Wires the rate limit optimizer, request batcher and request queue into
the main batch processor, and provides the batching decorator and the
convenience constructor.
"""

import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from .batcher import RequestBatcher, RequestQueue
from .models import APIRequest, BatchResult, RateLimitInfo, RetryStrategy
from .rate_limit import RateLimitOptimizer


logger = logging.getLogger(__name__)


class BatchProcessor:
    """Main batch processing coordinator."""

    def __init__(
        self,
        batch_size: int = 10,
        parallel_requests: int = 5,
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        max_backoff: float = 60.0,
        rate_limit_buffer: float = 0.1,
    ):
        """
        Initialize batch processor.

        Args:
            batch_size: Number of requests per batch
            parallel_requests: Number of parallel requests
            retry_strategy: Retry strategy
            max_retries: Maximum retry attempts
            initial_backoff: Initial backoff time in seconds
            max_backoff: Maximum backoff time in seconds
            rate_limit_buffer: Rate limit buffer percentage
        """
        self.batch_size = batch_size
        self.parallel_requests = parallel_requests
        self.retry_strategy = retry_strategy
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff

        # Components
        self.rate_limiter = RateLimitOptimizer(buffer_percentage=rate_limit_buffer)
        self.batcher = RequestBatcher(batch_size=batch_size, parallel_requests=parallel_requests)
        self.queue = RequestQueue()

        logger.info(
            f"Batch processor initialized: batch_size={batch_size}, "
            f"parallel={parallel_requests}, retry={retry_strategy.value}"
        )

    def calculate_backoff(self, retry_count: int) -> float:
        """
        Calculate backoff time for retry.

        Args:
            retry_count: Number of retries already attempted

        Returns:
            Backoff time in seconds
        """
        if self.retry_strategy == RetryStrategy.EXPONENTIAL:
            backoff = self.initial_backoff * (2**retry_count)
        elif self.retry_strategy == RetryStrategy.LINEAR:
            backoff = self.initial_backoff * (retry_count + 1)
        else:  # FIXED
            backoff = self.initial_backoff

        return float(min(backoff, self.max_backoff))

    def execute_request(
        self,
        request: APIRequest,
        executor: Callable[[APIRequest], Any],
    ) -> tuple[Any | None, Exception | None]:
        """
        Execute a single request with retry logic.

        Args:
            request: API request
            executor: Function to execute request

        Returns:
            Tuple of (result, error)
        """
        cached = self.batcher.get_cached_result(request)
        if cached is not None:
            return cached, None

        last_error = None

        while request.can_retry():
            try:
                self.rate_limiter.wait_if_needed(request.endpoint, request.cost)

                result = executor(request)

                # Record success
                self.rate_limiter.record_request(request.endpoint, request.cost)

                # Cache result
                self.batcher.cache_result(request, result)

                return result, None

            except Exception as e:
                last_error = e
                request.retries += 1

                if request.can_retry():
                    backoff = self.calculate_backoff(request.retries)
                    logger.warning(
                        f"Request failed (attempt {request.retries}/{request.max_retries}), "
                        f"retrying in {backoff:.1f}s: {e}"
                    )
                    time.sleep(backoff)
                else:
                    logger.error(f"Request failed after {request.retries} retries: {e}")

        return None, last_error

    def process_batch(
        self,
        requests: list[APIRequest],
        executor: Callable[[APIRequest], Any],
    ) -> BatchResult:
        """
        Process a batch of requests.

        Args:
            requests: List of API requests
            executor: Function to execute requests

        Returns:
            Batch result
        """
        start_time = time.time()
        result = BatchResult(total_requests=len(requests))

        # Group into batches
        batches = self.batcher.batch_requests(requests)
        result.deduplicated = len(requests) - sum(len(b) for b in batches)

        for batch in batches:
            # Execute batch (limited parallelism)
            batch_results = []
            batch_errors = []

            # Simple parallel execution with thread pool
            from concurrent.futures import ThreadPoolExecutor, as_completed

            with ThreadPoolExecutor(max_workers=self.parallel_requests) as pool:
                futures = {pool.submit(self.execute_request, req, executor): req for req in batch}

                for future in as_completed(futures):
                    request = futures[future]
                    try:
                        res, err = future.result()

                        if err is None:
                            batch_results.append(res)
                            result.successful += 1
                        else:
                            batch_errors.append(err)
                            result.failed += 1

                        if request.retries > 0:
                            result.retried += 1

                    except Exception as e:
                        batch_errors.append(e)
                        result.failed += 1

            result.results.extend(batch_results)
            result.errors.extend(batch_errors)

        result.execution_time = time.time() - start_time

        logger.info(
            f"Processed {result.total_requests} requests: "
            f"{result.successful} successful, {result.failed} failed, "
            f"{result.retried} retried, {result.deduplicated} deduplicated "
            f"in {result.execution_time:.2f}s"
        )

        return result

    def update_rate_limit(
        self,
        endpoint: str = "default",
        limit: int | None = None,
        remaining: int | None = None,
        reset_time: float | None = None,
    ) -> None:
        """Update rate limit information from API response."""
        self.rate_limiter.update_from_response(endpoint, limit, remaining, reset_time)

    def get_rate_limit_info(self, endpoint: str = "default") -> RateLimitInfo:
        """Get rate limit info for endpoint."""
        return self.rate_limiter.get_info(endpoint)


def batch_api_calls(
    batch_size: int = 10,
    parallel_requests: int = 5,
    max_retries: int = 3,
):
    """
    Decorator for batching API calls.

    Args:
        batch_size: Number of requests per batch
        parallel_requests: Number of parallel requests
        max_retries: Maximum retry attempts

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        processor = BatchProcessor(
            batch_size=batch_size,
            parallel_requests=parallel_requests,
            max_retries=max_retries,
        )

        @wraps(func)
        def wrapper(requests: list[APIRequest], *args, **kwargs):
            def executor(request: APIRequest):
                return func(request, *args, **kwargs)

            return processor.process_batch(requests, executor)

        return wrapper

    return decorator


def create_batch_processor(
    batch_size: int = 10,
    parallel_requests: int = 5,
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    max_retries: int = 3,
    initial_backoff: float = 1.0,
    max_backoff: float = 60.0,
    rate_limit_buffer: float = 0.1,
) -> BatchProcessor:
    """
    Create batch processor with default settings.

    Args:
        batch_size: Number of requests per batch
        parallel_requests: Number of parallel requests
        retry_strategy: Retry strategy
        max_retries: Maximum retry attempts
        initial_backoff: Initial backoff time
        max_backoff: Maximum backoff time
        rate_limit_buffer: Rate limit buffer percentage

    Returns:
        Configured batch processor
    """
    return BatchProcessor(
        batch_size=batch_size,
        parallel_requests=parallel_requests,
        retry_strategy=retry_strategy,
        max_retries=max_retries,
        initial_backoff=initial_backoff,
        max_backoff=max_backoff,
        rate_limit_buffer=rate_limit_buffer,
    )
