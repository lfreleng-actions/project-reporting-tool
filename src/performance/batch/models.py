# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Data model definitions for batch processing and API optimization.

Contains the enums and dataclasses shared by the batch processing
components: priorities, retry strategies, rate limit state, request
metadata and batch execution results.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RequestPriority(Enum):
    """Request priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class RetryStrategy(Enum):
    """Retry strategies."""

    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"


@dataclass
class RateLimitInfo:
    """Rate limit information."""

    limit: int = 5000
    remaining: int = 5000
    reset_time: float = 0.0

    @property
    def reset_in_seconds(self) -> float:
        """Time until rate limit resets."""
        return max(0, self.reset_time - time.time())

    @property
    def usage_percentage(self) -> float:
        """Percentage of rate limit used."""
        if self.limit == 0:
            return 0.0
        return (self.limit - self.remaining) / self.limit

    def can_make_request(self, cost: int = 1) -> bool:
        """Check if request can be made."""
        if self.remaining <= 0:
            return time.time() >= self.reset_time
        return self.remaining >= cost

    def consume(self, cost: int = 1) -> None:
        """Consume rate limit budget."""
        self.remaining = max(0, self.remaining - cost)

    def update(self, limit: int, remaining: int, reset_time: float) -> None:
        """Update rate limit info."""
        self.limit = limit
        self.remaining = remaining
        self.reset_time = reset_time


@dataclass
class APIRequest:
    """API request metadata."""

    id: str
    endpoint: str
    method: str = "GET"
    params: dict[str, Any] = field(default_factory=dict)
    priority: RequestPriority = RequestPriority.NORMAL
    cost: int = 1
    created_at: float = field(default_factory=time.time)
    retries: int = 0
    max_retries: int = 3

    def get_cache_key(self) -> str:
        """Generate cache key for request."""
        key_parts = [self.method, self.endpoint]
        if self.params:
            param_str = json.dumps(self.params, sort_keys=True)
            key_parts.append(param_str)
        key_str = ":".join(key_parts)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def can_retry(self) -> bool:
        """Check if request can be retried."""
        return self.retries < self.max_retries


@dataclass
class BatchResult:
    """Batch execution result."""

    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    retried: int = 0
    deduplicated: int = 0
    execution_time: float = 0.0
    results: list[Any] = field(default_factory=list)
    errors: list[Exception] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful / self.total_requests

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        return 1.0 - self.success_rate

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_requests": self.total_requests,
            "successful": self.successful,
            "failed": self.failed,
            "retried": self.retried,
            "deduplicated": self.deduplicated,
            "execution_time": self.execution_time,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
        }

    def format(self) -> str:
        """Format result as string."""
        return f"""Batch Result:
  Total Requests: {self.total_requests:,}
  Successful: {self.successful:,} ({self.success_rate:.1%})
  Failed: {self.failed:,} ({self.failure_rate:.1%})
  Retried: {self.retried:,}
  Deduplicated: {self.deduplicated:,}
  Execution Time: {self.execution_time:.2f}s
  Throughput: {self.total_requests / self.execution_time if self.execution_time > 0 else 0:.1f} req/s"""
