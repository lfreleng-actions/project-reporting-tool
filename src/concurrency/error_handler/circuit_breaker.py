# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Circuit breaker pattern for concurrent operations.

Holds CircuitBreaker, which trips after a threshold of consecutive
failures, and CircuitOpenError, raised while the circuit is open.
"""

import logging
import threading
import time
from collections.abc import Callable
from typing import Any


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.

    Opens circuit after threshold failures, preventing further attempts
    until a timeout period expires.

    States:
        - CLOSED: Normal operation, requests pass through
        - OPEN: Too many failures, requests fail immediately
        - HALF_OPEN: Testing if service recovered

    Example:
        >>> breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        >>>
        >>> try:
        >>>     result = breaker.call(risky_operation)
        >>> except CircuitOpenError:
        >>>     # Circuit is open, don't retry
        >>>     return fallback_value
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: type[Exception] = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds before attempting to close circuit
            expected_exception: Exception type to count as failure
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._state = "CLOSED"
        self._lock = threading.Lock()

        # Logger
        self.logger = logging.getLogger(__name__)

    def call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Call function through circuit breaker.

        Args:
            fn: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result from function call

        Raises:
            CircuitOpenError: If circuit is open
            Exception: Any exception from fn
        """
        with self._lock:
            # Check if circuit should transition from OPEN to HALF_OPEN
            if self._state == "OPEN":
                if self._last_failure_time and time.time() - self._last_failure_time > self.timeout:
                    self._state = "HALF_OPEN"
                    self.logger.info("Circuit breaker transitioning to HALF_OPEN")
                else:
                    raise CircuitOpenError(
                        f"Circuit breaker is open. "
                        f"Failures: {self._failure_count}, "
                        f"Timeout: {self.timeout}s"
                    )

        try:
            result = fn(*args, **kwargs)

            # Success, reset circuit
            with self._lock:
                if self._state == "HALF_OPEN":
                    self._state = "CLOSED"
                    self.logger.info("Circuit breaker closed after successful test")
                self._failure_count = 0

            return result

        except self.expected_exception:
            with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.time()

                if self._failure_count >= self.failure_threshold and self._state != "OPEN":
                    self._state = "OPEN"
                    self.logger.warning(
                        f"Circuit breaker opened after {self._failure_count} failures"
                    )

            raise

    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        with self._lock:
            self._failure_count = 0
            self._last_failure_time = None
            self._state = "CLOSED"
            self.logger.info("Circuit breaker manually reset to CLOSED")

    def get_state(self) -> str:
        """
        Get current circuit state.

        Returns:
            Current state: "CLOSED", "OPEN", or "HALF_OPEN"
        """
        with self._lock:
            return self._state

    def get_failure_count(self) -> int:
        """
        Get current failure count.

        Returns:
            Number of consecutive failures
        """
        with self._lock:
            return self._failure_count


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""

    pass
