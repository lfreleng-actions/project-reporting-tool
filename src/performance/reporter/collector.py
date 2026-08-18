# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Metric collection for performance monitoring.

Contains the collector that accumulates metrics from the performance
components and retains a bounded history per metric name.
"""

from collections import defaultdict, deque

from .models import Metric, MetricType


class MetricsCollector:
    """Collects metrics from all performance components."""

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: list[Metric] = []
        self._metric_history: dict[str, deque[Metric]] = defaultdict(lambda: deque(maxlen=100))

    def add_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        tags: dict[str, str] | None = None,
        unit: str = "",
    ) -> None:
        """
        Add a metric.

        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            tags: Metric tags
            unit: Unit of measurement
        """
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            tags=tags or {},
            unit=unit,
        )

        self.metrics.append(metric)
        self._metric_history[name].append(metric)

    def get_metric_history(self, name: str) -> list[Metric]:
        """Get metric history."""
        return list(self._metric_history.get(name, []))

    def get_latest_metric(self, name: str) -> Metric | None:
        """Get latest metric value."""
        history = list(self._metric_history.get(name, []))
        return history[-1] if history else None

    def clear(self) -> None:
        """Clear all metrics."""
        self.metrics.clear()
