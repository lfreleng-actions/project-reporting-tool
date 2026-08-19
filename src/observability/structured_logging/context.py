# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Logging context primitives and log entry records.

Holds the phase and level enumerations, the propagated logging context and
the structured log entry used for aggregation and analysis.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LogPhase(Enum):
    """Enumeration of processing phases for context tracking."""

    INITIALIZATION = "initialization"
    DISCOVERY = "discovery"
    COLLECTION = "collection"
    AGGREGATION = "aggregation"
    RENDERING = "rendering"
    FINALIZATION = "finalization"
    API_CALL = "api_call"
    GIT_OPERATION = "git_operation"
    VALIDATION = "validation"


class LogLevel(Enum):
    """Log level enumeration for aggregation."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogContext:
    """
    Context information for structured logging.

    Attributes:
        repository: Current repository being processed
        phase: Current processing phase
        operation: Specific operation being performed
        window: Time window being processed
        extra: Additional context fields
    """

    repository: str | None = None
    phase: LogPhase | None = None
    operation: str | None = None
    window: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for logging."""
        context = {}

        if self.repository:
            context["repository"] = self.repository
        if self.phase:
            context["phase"] = self.phase.value
        if self.operation:
            context["operation"] = self.operation
        if self.window:
            context["window"] = self.window
        if self.extra:
            context.update(self.extra)

        return context

    def merge(self, other: "LogContext") -> "LogContext":
        """Merge with another context, preferring other's non-None values."""
        return LogContext(
            repository=other.repository or self.repository,
            phase=other.phase or self.phase,
            operation=other.operation or self.operation,
            window=other.window or self.window,
            extra={**self.extra, **other.extra},
        )


@dataclass
class LogEntry:
    """
    Structured log entry for aggregation and analysis.

    Attributes:
        level: Log level
        message: Log message
        context: Logging context
        timestamp: When the log was created
        duration_ms: Optional duration for performance tracking
    """

    level: LogLevel
    message: str
    context: LogContext
    timestamp: float = field(default_factory=time.time)
    duration_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert log entry to dictionary."""
        entry: dict[str, Any] = {
            "level": self.level.value,
            "message": self.message,
            "timestamp": self.timestamp,
        }

        if self.duration_ms is not None:
            entry["duration_ms"] = self.duration_ms

        context = self.context.to_dict()
        if context:
            entry["context"] = context

        return entry
