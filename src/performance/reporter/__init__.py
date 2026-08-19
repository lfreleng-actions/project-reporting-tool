# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Performance monitoring and reporting module.

This module provides utilities for generating performance reports, visualizing metrics,
tracking trends, and comparing performance against baselines.

Classes:
    PerformanceReporter: Main performance reporting coordinator
    MetricsCollector: Collects metrics from all performance components
    MetricsVisualizer: Visualizes performance metrics
    PerformanceReport: Performance report data structure
    MetricTrend: Trend analysis for metrics
    AlertRule: Performance alert rules

Example:
    >>> from src.performance.reporter import PerformanceReporter
    >>> reporter = PerformanceReporter()
    >>> reporter.collect_metrics()
    >>> report = reporter.generate_report()
    >>> print(report.format())
"""

from .collector import MetricsCollector
from .models import (
    Alert,
    AlertRule,
    AlertSeverity,
    Metric,
    MetricTrend,
    MetricType,
    PerformanceReport,
)
from .reporter import PerformanceReporter, create_performance_reporter
from .visualizer import MetricsVisualizer


__all__ = [
    "Alert",
    "AlertRule",
    "AlertSeverity",
    "Metric",
    "MetricTrend",
    "MetricType",
    "MetricsCollector",
    "MetricsVisualizer",
    "PerformanceReport",
    "PerformanceReporter",
    "create_performance_reporter",
]
