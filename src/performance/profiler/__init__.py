# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Performance profiling utilities for the Repository Reporting System.

This module provides tools for tracking execution time, memory usage, and
operation metrics to identify bottlenecks and measure optimization impact.

Classes:
    PerformanceProfiler: Main profiling coordinator
    OperationTimer: Context manager for timing operations
    MemoryTracker: Memory usage monitoring
    ProfileReport: Performance report generation

Example:
    >>> profiler = PerformanceProfiler()
    >>> with profiler.track_operation("analyze_repo", category="analysis"):
    ...     # Do analysis work
    ...     pass
    >>> report = profiler.get_report()
    >>> print(report.format())
"""

from .models import AggregatedMetrics, OperationCategory, OperationMetric
from .profiler import PerformanceProfiler, ProfileReport
from .tracking import MemoryTracker, OperationTimer, profile_operation


__all__ = [
    "AggregatedMetrics",
    "MemoryTracker",
    "OperationCategory",
    "OperationMetric",
    "OperationTimer",
    "PerformanceProfiler",
    "ProfileReport",
    "profile_operation",
]
