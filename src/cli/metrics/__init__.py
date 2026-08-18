#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Performance Metrics Module

Collects and reports performance metrics for repository analysis operations.
Provides execution summaries, timing breakdowns, resource usage statistics,
and debug-level profiling information.

Features:
- Execution timing and breakdown
- Resource usage tracking (memory, CPU, disk I/O)
- API call statistics
- Operation profiling
- Debug mode detailed metrics
- Beautiful formatted output

Phase 13: CLI & UX Improvements - Step 6
"""

from .collector import MetricsCollector
from .models import (
    APIStatistics,
    OperationMetrics,
    ResourceUsage,
    TimingMetric,
    format_bytes,
    format_duration,
    format_percentage,
)
from .session import (
    get_metrics_collector,
    print_debug_metrics,
    print_performance_summary,
    record_api_call,
    reset_metrics_collector,
    time_operation,
)


__all__ = [
    # Data structures
    "TimingMetric",
    "APIStatistics",
    "ResourceUsage",
    "OperationMetrics",
    # Main class
    "MetricsCollector",
    # Global instance
    "get_metrics_collector",
    "reset_metrics_collector",
    # Convenience functions
    "time_operation",
    "record_api_call",
    "print_performance_summary",
    "print_debug_metrics",
    # Formatting
    "format_duration",
    "format_bytes",
    "format_percentage",
]
