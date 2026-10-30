# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Error data model for concurrent operations.

Holds the severity classification enum and the record structure used to
capture a single error raised by a concurrent worker.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    TRANSIENT = "transient"  # Temporary error, retry may succeed
    PERMANENT = "permanent"  # Permanent error, retry will fail
    UNKNOWN = "unknown"  # Unknown error type


@dataclass
class ErrorRecord:
    """Record of an error that occurred during concurrent execution."""

    context: str  # Context where error occurred (e.g., repo name)
    error_type: str  # Error class name
    error_message: str  # Error message
    severity: ErrorSeverity  # Error severity
    timestamp: datetime = field(default_factory=datetime.now)
    traceback: str | None = None
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
