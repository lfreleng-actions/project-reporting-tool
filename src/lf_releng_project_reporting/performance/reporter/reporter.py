# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Performance reporting coordinator.

Contains the top-level reporter that gathers metrics from the performance
components, calculates trends against a baseline, evaluates alert rules,
and generates and saves reports.
"""

import logging
from pathlib import Path

from .collector import MetricsCollector
from .models import (
    Alert,
    AlertRule,
    AlertSeverity,
    MetricTrend,
    MetricType,
    PerformanceReport,
)
from .visualizer import MetricsVisualizer


logger = logging.getLogger(__name__)


class PerformanceReporter:
    """Main performance reporting coordinator."""

    def __init__(self):
        """Initialize performance reporter."""
        self.collector = MetricsCollector()
        self.visualizer = MetricsVisualizer()
        self.alert_rules: list[AlertRule] = []
        self._baseline_metrics: dict[str, float] = {}

        # Default alert rules
        self._add_default_rules()

        logger.info("Performance reporter initialized")

    def _add_default_rules(self) -> None:
        """Add default alert rules."""
        # Memory alerts
        self.add_alert_rule(
            "peak_memory_mb",
            threshold=1000,
            comparison=">",
            severity=AlertSeverity.WARNING,
            message_template="Peak memory usage ({value:.1f} MB) exceeds threshold ({threshold:.1f} MB)",
        )

        # Execution time alerts
        self.add_alert_rule(
            "execution_time",
            threshold=300,
            comparison=">",
            severity=AlertSeverity.WARNING,
            message_template="Execution time ({value:.1f}s) exceeds threshold ({threshold:.1f}s)",
        )

        # Cache hit rate alerts
        self.add_alert_rule(
            "cache_hit_rate",
            threshold=0.3,
            comparison="<",
            severity=AlertSeverity.INFO,
            message_template="Cache hit rate ({value:.1%}) is below target ({threshold:.1%})",
        )

    def add_alert_rule(
        self,
        metric_name: str,
        threshold: float,
        comparison: str,
        severity: AlertSeverity,
        message_template: str,
    ) -> None:
        """Add an alert rule."""
        rule = AlertRule(
            metric_name=metric_name,
            threshold=threshold,
            comparison=comparison,
            severity=severity,
            message_template=message_template,
        )
        self.alert_rules.append(rule)

    def collect_metrics(
        self,
        profiler=None,
        cache=None,
        memory_optimizer=None,
        batch_processor=None,
    ) -> None:
        """
        Collect metrics from performance components.

        Args:
            profiler: PerformanceProfiler instance
            cache: CacheManager instance
            memory_optimizer: MemoryOptimizer instance
            batch_processor: BatchProcessor instance
        """
        # Collect from profiler
        if profiler:
            try:
                report = profiler.get_report()

                if hasattr(report, "total_time"):
                    self.collector.add_metric(
                        "execution_time",
                        report.total_time,
                        MetricType.TIMING,
                        unit="s",
                    )

                if hasattr(report, "operation_count"):
                    self.collector.add_metric(
                        "total_operations",
                        report.operation_count,
                        MetricType.COUNTER,
                    )
            except Exception as e:
                logger.warning(f"Failed to collect profiler metrics: {e}")

        # Collect from cache
        if cache:
            try:
                stats = cache.get_stats()

                self.collector.add_metric(
                    "cache_hit_rate",
                    stats.hit_rate,
                    MetricType.GAUGE,
                )

                self.collector.add_metric(
                    "cache_size_mb",
                    stats.total_size_mb,
                    MetricType.GAUGE,
                    unit="MB",
                )

                self.collector.add_metric(
                    "cache_entries",
                    stats.entry_count,
                    MetricType.GAUGE,
                )
            except Exception as e:
                logger.warning(f"Failed to collect cache metrics: {e}")

        # Collect from memory optimizer
        if memory_optimizer:
            try:
                stats = memory_optimizer.get_stats()

                self.collector.add_metric(
                    "peak_memory_mb",
                    stats.peak_mb,
                    MetricType.GAUGE,
                    unit="MB",
                )

                self.collector.add_metric(
                    "current_memory_mb",
                    stats.current_mb,
                    MetricType.GAUGE,
                    unit="MB",
                )

                self.collector.add_metric(
                    "gc_collections",
                    stats.gc_collections,
                    MetricType.COUNTER,
                )
            except Exception as e:
                logger.warning(f"Failed to collect memory metrics: {e}")

        # Collect from batch processor
        if batch_processor:
            try:
                rate_limit_info = batch_processor.get_rate_limit_info()

                self.collector.add_metric(
                    "rate_limit_remaining",
                    rate_limit_info.remaining,
                    MetricType.GAUGE,
                )

                self.collector.add_metric(
                    "rate_limit_usage",
                    rate_limit_info.usage_percentage,
                    MetricType.GAUGE,
                )
            except Exception as e:
                logger.warning(f"Failed to collect batch processor metrics: {e}")

    def set_baseline(self, metrics: dict[str, float]) -> None:
        """Set baseline metrics for comparison."""
        self._baseline_metrics = metrics.copy()
        logger.info(f"Baseline set with {len(metrics)} metrics")

    def calculate_trends(self) -> list[MetricTrend]:
        """Calculate trends by comparing to baseline."""
        trends = []

        for metric in self.collector.metrics:
            if metric.name in self._baseline_metrics:
                baseline_value = self._baseline_metrics[metric.name]
                current_value = metric.value

                if baseline_value == 0:
                    change_percentage = 0.0
                else:
                    change_percentage = ((current_value - baseline_value) / baseline_value) * 100

                # Determine trend direction
                if abs(change_percentage) < 1:
                    trend_direction = "stable"
                elif change_percentage > 0:
                    trend_direction = "up"
                else:
                    trend_direction = "down"

                # Determine if improvement (depends on metric)
                improvement_metrics = {
                    "cache_hit_rate": "up",
                    "execution_time": "down",
                    "peak_memory_mb": "down",
                    "current_memory_mb": "down",
                }

                desired_direction = improvement_metrics.get(metric.name, "stable")
                is_improvement = trend_direction == desired_direction or trend_direction == "stable"

                trend = MetricTrend(
                    metric_name=metric.name,
                    current_value=current_value,
                    previous_value=baseline_value,
                    change_percentage=change_percentage,
                    trend_direction=trend_direction,
                    is_improvement=is_improvement,
                )

                trends.append(trend)

        return trends

    def evaluate_alerts(self) -> list[Alert]:
        """Evaluate alert rules against metrics."""
        alerts = []

        for metric in self.collector.metrics:
            for rule in self.alert_rules:
                if rule.metric_name == metric.name:
                    alert = rule.evaluate(metric.value)
                    if alert:
                        alerts.append(alert)

        return alerts

    def generate_report(self) -> PerformanceReport:
        """Generate performance report."""
        trends = self.calculate_trends()
        alerts = self.evaluate_alerts()

        # Generate summary
        summary = {}

        # Add key metrics to summary
        for metric in self.collector.metrics:
            if metric.name in ["execution_time", "peak_memory_mb", "cache_hit_rate"]:
                unit_str = f" {metric.unit}" if metric.unit else ""
                summary[metric.name] = f"{metric.value:.2f}{unit_str}"

        # Add alert count
        summary["total_alerts"] = str(len(alerts))
        summary["critical_alerts"] = str(
            sum(1 for a in alerts if a.severity == AlertSeverity.CRITICAL)
        )

        report = PerformanceReport(
            metrics=self.collector.metrics.copy(),
            trends=trends,
            alerts=alerts,
            summary=summary,
        )

        logger.info(
            f"Generated report with {len(report.metrics)} metrics, "
            f"{len(report.trends)} trends, {len(report.alerts)} alerts"
        )

        return report

    def save_report(
        self,
        report: PerformanceReport,
        output_path: str | Path,
        format: str = "json",
    ) -> None:
        """
        Save report to file.

        Args:
            report: Performance report
            output_path: Output file path
            format: Output format ("json", "html", "text")
        """
        output_path = Path(output_path)

        if format == "json":
            output_path.write_text(report.to_json())
        elif format == "html":
            self.visualizer.export_html(report, output_path)
        elif format == "text":
            output_path.write_text(report.format())
        else:
            raise ValueError(f"Unknown format: {format}")

        logger.info(f"Report saved to {output_path} ({format})")


def create_performance_reporter() -> PerformanceReporter:
    """
    Create performance reporter with default settings.

    Returns:
        Configured performance reporter
    """
    return PerformanceReporter()
