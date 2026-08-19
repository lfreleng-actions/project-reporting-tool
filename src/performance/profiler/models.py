# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Data model definitions for performance profiling.

Contains the operation category enum, the per-execution operation metric
record, and the aggregated statistics for an operation type.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OperationCategory(Enum):
    """Categories for organizing operations in profiling."""

    GIT = "git"
    API = "api"
    ANALYSIS = "analysis"
    RENDERING = "rendering"
    IO = "io"
    CACHE = "cache"
    VALIDATION = "validation"
    OTHER = "other"


@dataclass
class OperationMetric:
    """Metrics for a single operation execution."""

    name: str
    category: str
    start_time: float
    end_time: float
    duration: float
    memory_start: int  # bytes
    memory_end: int  # bytes
    memory_delta: int  # bytes
    success: bool = True
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        return self.duration * 1000

    @property
    def memory_mb(self) -> float:
        """Memory delta in megabytes."""
        return self.memory_delta / (1024 * 1024)


@dataclass
class AggregatedMetrics:
    """Aggregated statistics for an operation type."""

    name: str
    category: str
    count: int
    total_duration: float
    avg_duration: float
    min_duration: float
    max_duration: float
    total_memory_delta: int
    avg_memory_delta: float
    success_count: int
    error_count: int

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        return (self.success_count / self.count * 100) if self.count > 0 else 0.0

    @property
    def avg_duration_ms(self) -> float:
        """Average duration in milliseconds."""
        return self.avg_duration * 1000

    @property
    def avg_memory_mb(self) -> float:
        """Average memory delta in megabytes."""
        return self.avg_memory_delta / (1024 * 1024)
