# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Metric data structures and human-readable formatting helpers."""

from dataclasses import dataclass, field
from typing import Any


# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass
class TimingMetric:
    """Individual timing measurement."""

    name: str
    duration: float
    start_time: float
    end_time: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """Format timing for display."""
        return f"{self.name}: {format_duration(self.duration)}"


@dataclass
class APIStatistics:
    """API call statistics."""

    api_name: str
    total_calls: int = 0
    cached_calls: int = 0
    failed_calls: int = 0
    total_duration: float = 0.0

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_calls == 0:
            return 0.0
        return (self.cached_calls / self.total_calls) * 100

    @property
    def average_duration(self) -> float:
        """Calculate average call duration."""
        if self.total_calls == 0:
            return 0.0
        return self.total_duration / self.total_calls

    @property
    def calls_per_second(self) -> float:
        """Calculate calls per second."""
        if self.total_duration == 0:
            return 0.0
        return self.total_calls / self.total_duration


@dataclass
class ResourceUsage:
    """Resource usage statistics."""

    peak_memory_mb: float = 0.0
    avg_memory_mb: float = 0.0
    cpu_time_seconds: float = 0.0
    cpu_utilization: float = 0.0
    disk_read_mb: float = 0.0
    disk_write_mb: float = 0.0


@dataclass
class OperationMetrics:
    """Metrics for a specific operation (e.g., repository analysis)."""

    operation_name: str
    duration: float
    success: bool = True
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# FORMATTING HELPERS
# =============================================================================


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "2m 15s", "1h 23m 45s")
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"

    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes = int(seconds // 60)
    secs = int(seconds % 60)

    if minutes < 60:
        return f"{minutes}m {secs}s"

    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}h {minutes}m {secs}s"


def format_bytes(bytes_count: float) -> str:
    """
    Format bytes in human-readable format.

    Args:
        bytes_count: Number of bytes

    Returns:
        Formatted string (e.g., "1.2 GB", "345 MB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"


def format_percentage(value: float, total: float) -> str:
    """
    Format percentage with value.

    Args:
        value: Partial value
        total: Total value

    Returns:
        Formatted string (e.g., "45s (33%)")
    """
    if total == 0:
        return f"{format_duration(value)} (0%)"

    percentage = (value / total) * 100
    return f"{format_duration(value)} ({percentage:.0f}%)"
