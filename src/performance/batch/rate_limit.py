# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Smart rate limit tracking and optimization.

Tracks per-endpoint rate limit budgets, applies a reserve buffer, waits
for resets when required and adapts to limits reported by API responses.
"""

import logging
import threading
import time
from collections import defaultdict

from .models import RateLimitInfo


logger = logging.getLogger(__name__)


class RateLimitOptimizer:
    """Smart rate limit tracking and optimization."""

    def __init__(
        self,
        initial_limit: int = 5000,
        buffer_percentage: float = 0.1,
        adaptive: bool = True,
    ):
        """
        Initialize rate limit optimizer.

        Args:
            initial_limit: Initial rate limit
            buffer_percentage: Reserve buffer (0.1 = 10%)
            adaptive: Adapt to actual rate limits
        """
        self.rate_limits: dict[str, RateLimitInfo] = defaultdict(
            lambda: RateLimitInfo(limit=initial_limit, remaining=initial_limit)
        )
        self.buffer_percentage = buffer_percentage
        self.adaptive = adaptive
        self._lock = threading.Lock()

        logger.info(
            f"Rate limit optimizer initialized: limit={initial_limit}, buffer={buffer_percentage:.1%}"
        )

    def can_make_request(
        self,
        endpoint: str = "default",
        cost: int = 1,
    ) -> bool:
        """
        Check if request can be made.

        Args:
            endpoint: API endpoint
            cost: Request cost

        Returns:
            True if request can be made
        """
        with self._lock:
            rate_limit = self.rate_limits[endpoint]

            # Check if reset time has passed and reset if needed
            if rate_limit.remaining <= 0 and time.time() >= rate_limit.reset_time:
                rate_limit.remaining = rate_limit.limit

            # Apply buffer
            buffer_amount = int(rate_limit.limit * self.buffer_percentage)
            effective_remaining = rate_limit.remaining - buffer_amount

            # Check if we have enough remaining for this request
            return effective_remaining >= cost

    def wait_if_needed(
        self,
        endpoint: str = "default",
        cost: int = 1,
    ) -> float:
        """
        Wait if rate limit would be exceeded.

        Args:
            endpoint: API endpoint
            cost: Request cost

        Returns:
            Time waited in seconds
        """
        if self.can_make_request(endpoint, cost):
            return 0.0

        rate_limit = self.rate_limits[endpoint]
        wait_time = rate_limit.reset_in_seconds

        if wait_time > 0:
            logger.info(f"Rate limit approaching, waiting {wait_time:.1f}s for reset")
            time.sleep(wait_time)
            return wait_time

        return 0.0

    def record_request(
        self,
        endpoint: str = "default",
        cost: int = 1,
    ) -> None:
        """
        Record a request.

        Args:
            endpoint: API endpoint
            cost: Request cost
        """
        with self._lock:
            self.rate_limits[endpoint].consume(cost)

    def update_from_response(
        self,
        endpoint: str = "default",
        limit: int | None = None,
        remaining: int | None = None,
        reset_time: float | None = None,
    ) -> None:
        """
        Update rate limit from API response.

        Args:
            endpoint: API endpoint
            limit: Rate limit
            remaining: Remaining requests
            reset_time: Reset timestamp
        """
        if not self.adaptive:
            return

        with self._lock:
            rate_limit = self.rate_limits[endpoint]

            if limit is not None:
                rate_limit.limit = limit
            if remaining is not None:
                rate_limit.remaining = remaining
            if reset_time is not None:
                rate_limit.reset_time = reset_time

    def get_info(self, endpoint: str = "default") -> RateLimitInfo:
        """Get rate limit info for endpoint."""
        with self._lock:
            return self.rate_limits[endpoint]

    def get_all_info(self) -> dict[str, RateLimitInfo]:
        """Get all rate limit info."""
        with self._lock:
            return dict(self.rate_limits)
