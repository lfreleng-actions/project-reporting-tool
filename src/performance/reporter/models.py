# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Data model definitions for performance monitoring and reporting.

Contains the metric and alert enums, the individual metric data point,
trend analysis and alert records, the alert rule definition, and the
aggregate performance report structure.
"""

import json
import operator
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# Comparison operators supported by AlertRule, mapped to their implementations
# so rule evaluation is table-driven rather than a branch per operator.
_ALERT_COMPARISONS: dict[str, Callable[[float, float], bool]] = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
}


class MetricType(Enum):
    """Metric types."""

    TIMING = "timing"
    COUNTER = "counter"
    GAUGE = "gauge"
    RATE = "rate"


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Metric:
    """Individual metric data point."""

    name: str
    value: float
    metric_type: MetricType
    timestamp: float = field(default_factory=time.time)
    tags: dict[str, str] = field(default_factory=dict)
    unit: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "unit": self.unit,
        }


@dataclass
class MetricTrend:
    """Trend analysis for a metric."""

    metric_name: str
    current_value: float
    previous_value: float
    change_percentage: float
    trend_direction: str  # "up", "down", "stable"
    is_improvement: bool

    def format(self) -> str:
        """Format trend as string."""
        arrow = (
            "↑" if self.trend_direction == "up" else "↓" if self.trend_direction == "down" else "→"
        )
        color = "✅" if self.is_improvement else "⚠️" if abs(self.change_percentage) > 5 else "ℹ️"

        return (
            f"{color} {self.metric_name}: {self.current_value:.2f} "
            f"({arrow} {self.change_percentage:+.1f}%)"
        )


@dataclass
class Alert:
    """Performance alert."""

    severity: AlertSeverity
    metric_name: str
    message: str
    value: float
    threshold: float
    timestamp: float = field(default_factory=time.time)

    def format(self) -> str:
        """Format alert as string."""
        severity_icons = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.ERROR: "❌",
            AlertSeverity.CRITICAL: "🚨",
        }
        icon = severity_icons.get(self.severity, "•")
        return f"{icon} [{self.severity.value.upper()}] {self.metric_name}: {self.message}"


@dataclass
class AlertRule:
    """Alert rule definition."""

    metric_name: str
    threshold: float
    comparison: str  # ">", "<", ">=", "<=", "=="
    severity: AlertSeverity
    message_template: str

    def evaluate(self, value: float) -> Alert | None:
        """Evaluate rule against value."""
        compare = _ALERT_COMPARISONS.get(self.comparison)
        triggered = compare(value, self.threshold) if compare is not None else False

        if triggered:
            message = self.message_template.format(
                value=value,
                threshold=self.threshold,
            )
            return Alert(
                severity=self.severity,
                metric_name=self.metric_name,
                message=message,
                value=value,
                threshold=self.threshold,
            )

        return None


@dataclass
class PerformanceReport:
    """Performance report data structure."""

    generated_at: float = field(default_factory=time.time)
    metrics: list[Metric] = field(default_factory=list)
    trends: list[MetricTrend] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "generated_at": self.generated_at,
            "generated_at_iso": datetime.fromtimestamp(self.generated_at).isoformat(),
            "metrics": [m.to_dict() for m in self.metrics],
            "trends": [
                {
                    "metric_name": t.metric_name,
                    "current_value": t.current_value,
                    "previous_value": t.previous_value,
                    "change_percentage": t.change_percentage,
                    "trend_direction": t.trend_direction,
                    "is_improvement": t.is_improvement,
                }
                for t in self.trends
            ],
            "alerts": [
                {
                    "severity": a.severity.value,
                    "metric_name": a.metric_name,
                    "message": a.message,
                    "value": a.value,
                    "threshold": a.threshold,
                }
                for a in self.alerts
            ],
            "summary": self.summary,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def format(self) -> str:
        """Format report as string."""
        lines = [
            "=" * 80,
            "PERFORMANCE REPORT",
            "=" * 80,
            f"Generated: {datetime.fromtimestamp(self.generated_at).strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # Summary section
        if self.summary:
            lines.append("SUMMARY")
            lines.append("-" * 80)
            for key, value in self.summary.items():
                lines.append(f"  {key}: {value}")
            lines.append("")

        # Alerts section
        if self.alerts:
            lines.append("ALERTS")
            lines.append("-" * 80)
            for alert in sorted(self.alerts, key=lambda a: a.severity.value, reverse=True):
                lines.append(f"  {alert.format()}")
            lines.append("")

        # Trends section
        if self.trends:
            lines.append("TRENDS")
            lines.append("-" * 80)
            for trend in self.trends:
                lines.append(f"  {trend.format()}")
            lines.append("")

        # Metrics section
        if self.metrics:
            lines.append("METRICS")
            lines.append("-" * 80)

            # Group by type
            metrics_by_type = defaultdict(list)
            for metric in self.metrics:
                metrics_by_type[metric.metric_type].append(metric)

            for metric_type, metrics in metrics_by_type.items():
                lines.append(f"  {metric_type.value.upper()}:")
                for metric in sorted(metrics, key=lambda m: m.name):
                    unit_str = f" {metric.unit}" if metric.unit else ""
                    lines.append(f"    {metric.name}: {metric.value:.2f}{unit_str}")
                lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)
