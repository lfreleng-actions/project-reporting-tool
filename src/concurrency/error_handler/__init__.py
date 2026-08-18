# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Error Handling for Concurrent Operations.

Provides structured error collection, retry logic with exponential backoff,
and circuit breaker pattern for failing operations.

Phase 7: Concurrency Refinement
"""

from .circuit_breaker import CircuitBreaker, CircuitOpenError
from .handler import ConcurrentErrorHandler
from .records import ErrorRecord, ErrorSeverity
from .retry import with_retry


__all__ = [
    "CircuitBreaker",
    "CircuitOpenError",
    "ConcurrentErrorHandler",
    "ErrorRecord",
    "ErrorSeverity",
    "with_retry",
]
