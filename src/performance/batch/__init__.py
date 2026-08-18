# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Batch processing and API optimization module.

This module provides utilities for batching API requests, intelligent rate limiting,
request deduplication, and retry logic with exponential backoff.

Classes:
    BatchProcessor: Main batch processing coordinator
    RateLimitOptimizer: Smart rate limit tracking and optimization
    RequestBatcher: Request grouping and parallel execution
    RequestQueue: Priority queue for API requests
    RateLimitInfo: Rate limit information tracking
    BatchResult: Batch execution results

Example:
    >>> from src.performance.batch import BatchProcessor
    >>> processor = BatchProcessor(batch_size=10, parallel_requests=5)
    >>> results = processor.batch_requests(api_calls)
    >>> print(f"Success rate: {results.success_rate:.1%}")
"""

from .batcher import RequestBatcher, RequestQueue
from .models import (
    APIRequest,
    BatchResult,
    RateLimitInfo,
    RequestPriority,
    RetryStrategy,
)
from .processor import BatchProcessor, batch_api_calls, create_batch_processor
from .rate_limit import RateLimitOptimizer


__all__ = [
    "APIRequest",
    "BatchProcessor",
    "BatchResult",
    "RateLimitInfo",
    "RateLimitOptimizer",
    "RequestBatcher",
    "RequestPriority",
    "RequestQueue",
    "RetryStrategy",
    "batch_api_calls",
    "create_batch_processor",
]
