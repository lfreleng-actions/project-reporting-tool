# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Profiling session coordinator and report generation.

Contains the main profiler that records operations and aggregates their
metrics, and the report object that formats, exports and compares those
results against a stored baseline.
"""

import json
import os
import time
from contextlib import contextmanager
from typing import Any

from .models import AggregatedMetrics, OperationMetric
from .tracking import MemoryTracker, OperationTimer


class PerformanceProfiler:
    """
    Main performance profiler for tracking operations and generating reports.

    Example:
        >>> profiler = PerformanceProfiler()
        >>> with profiler.track_operation("analyze_repo", category="analysis"):
        ...     # Do analysis work
        ...     pass
        >>> report = profiler.get_report()
        >>> report.save("performance.json")
    """

    def __init__(self, name: str = "default"):
        """
        Initialize performance profiler.

        Args:
            name: Name for this profiler instance
        """
        self.name = name
        self.operations: list[OperationMetric] = []
        self.custom_metrics: dict[str, Any] = {}
        self.memory_tracker = MemoryTracker()
        self.start_time: float | None = None
        self.end_time: float | None = None

    def start(self):
        """Start profiling session."""
        self.start_time = time.perf_counter()
        self.memory_tracker.start()

    def stop(self):
        """Stop profiling session."""
        self.end_time = time.perf_counter()
        self.memory_tracker.stop()

    @contextmanager
    def track_operation(
        self, name: str, category: str = "other", metadata: dict[str, Any] | None = None
    ):
        """
        Context manager for tracking an operation.

        Args:
            name: Operation name
            category: Operation category
            metadata: Optional metadata to attach

        Yields:
            OperationTimer instance
        """
        timer = OperationTimer(name, category, self, metadata)
        with timer:
            yield timer

    def record_operation(self, metric: OperationMetric):
        """
        Record an operation metric.

        Args:
            metric: Operation metric to record
        """
        self.operations.append(metric)

    def record_metric(self, name: str, value: Any, unit: str = ""):
        """
        Record a custom metric.

        Args:
            name: Metric name
            value: Metric value
            unit: Optional unit of measurement
        """
        self.custom_metrics[name] = {"value": value, "unit": unit}

    def memory_snapshot(self, label: str):
        """
        Take a memory snapshot.

        Args:
            label: Snapshot label
        """
        self.memory_tracker.snapshot(label)

    def get_aggregated_metrics(self) -> dict[str, AggregatedMetrics]:
        """
        Get aggregated metrics by operation name.

        Returns:
            Dictionary mapping operation names to aggregated metrics
        """
        operation_groups: dict[str, list[OperationMetric]] = {}

        for op in self.operations:
            key = f"{op.category}:{op.name}"
            if key not in operation_groups:
                operation_groups[key] = []
            operation_groups[key].append(op)

        aggregated = {}
        for key, ops in operation_groups.items():
            durations = [op.duration for op in ops]
            memory_deltas = [op.memory_delta for op in ops]

            aggregated[key] = AggregatedMetrics(
                name=ops[0].name,
                category=ops[0].category,
                count=len(ops),
                total_duration=sum(durations),
                avg_duration=sum(durations) / len(durations),
                min_duration=min(durations),
                max_duration=max(durations),
                total_memory_delta=sum(memory_deltas),
                avg_memory_delta=sum(memory_deltas) / len(memory_deltas),
                success_count=sum(1 for op in ops if op.success),
                error_count=sum(1 for op in ops if not op.success),
            )

        return aggregated

    def get_report(self) -> "ProfileReport":
        """
        Generate performance report.

        Returns:
            ProfileReport instance
        """
        return ProfileReport(self)


class ProfileReport:
    """
    Performance profile report with formatting and export capabilities.
    """

    def __init__(self, profiler: PerformanceProfiler):
        """
        Initialize profile report.

        Args:
            profiler: PerformanceProfiler instance
        """
        self.profiler = profiler
        self.aggregated = profiler.get_aggregated_metrics()
        self.memory_stats = profiler.memory_tracker.get_stats()

    def format(self, detailed: bool = False) -> str:
        """
        Format report as human-readable text.

        Args:
            detailed: Include detailed operation list

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 70)
        lines.append(f"Performance Profile: {self.profiler.name}")
        lines.append("=" * 70)

        # Overall timing
        if self.profiler.start_time and self.profiler.end_time:
            total_duration = self.profiler.end_time - self.profiler.start_time
            lines.append(f"\nTotal Duration: {total_duration:.2f}s")

        # Memory stats
        if self.memory_stats.get("available"):
            lines.append("\nMemory Usage:")
            lines.append(f"  Start:  {self.memory_stats['start_mb']:.1f} MB")
            lines.append(f"  End:    {self.memory_stats['end_mb']:.1f} MB")
            lines.append(f"  Peak:   {self.memory_stats['peak_mb']:.1f} MB")
            lines.append(f"  Delta:  {self.memory_stats['delta_mb']:+.1f} MB")

        # Aggregated metrics by category
        if self.aggregated:
            lines.append("\nOperation Summary:")
            lines.append("-" * 70)

            by_category: dict[str, list[AggregatedMetrics]] = {}
            for metrics in self.aggregated.values():
                cat = metrics.category
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(metrics)

            for category in sorted(by_category.keys()):
                lines.append(f"\n{category.upper()}:")
                for metrics in sorted(
                    by_category[category], key=lambda m: m.total_duration, reverse=True
                ):
                    lines.append(f"  {metrics.name}:")
                    lines.append(f"    Count:        {metrics.count}")
                    lines.append(f"    Total Time:   {metrics.total_duration:.2f}s")
                    lines.append(f"    Avg Time:     {metrics.avg_duration_ms:.1f}ms")
                    lines.append(
                        f"    Min/Max:      {metrics.min_duration * 1000:.1f}ms / {metrics.max_duration * 1000:.1f}ms"
                    )
                    if metrics.avg_memory_delta != 0:
                        lines.append(f"    Avg Memory:   {metrics.avg_memory_mb:+.1f} MB")
                    lines.append(f"    Success Rate: {metrics.success_rate:.1f}%")

        # Custom metrics
        if self.profiler.custom_metrics:
            lines.append("\nCustom Metrics:")
            lines.append("-" * 70)
            for name, data in self.profiler.custom_metrics.items():
                value = data["value"]
                unit = data["unit"]
                lines.append(f"  {name}: {value} {unit}".strip())

        # Detailed operations
        if detailed and self.profiler.operations:
            lines.append("\nDetailed Operations:")
            lines.append("-" * 70)
            for op in self.profiler.operations:
                status = "✓" if op.success else "✗"
                lines.append(f"{status} {op.name} ({op.category}): {op.duration_ms:.1f}ms")
                if op.error:
                    lines.append(f"    Error: {op.error}")

        lines.append("=" * 70)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """
        Export report as dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "profiler_name": self.profiler.name,
            "start_time": self.profiler.start_time,
            "end_time": self.profiler.end_time,
            "total_duration": (
                self.profiler.end_time - self.profiler.start_time
                if self.profiler.start_time and self.profiler.end_time
                else None
            ),
            "memory_stats": self.memory_stats,
            "aggregated_metrics": {
                key: {
                    "name": m.name,
                    "category": m.category,
                    "count": m.count,
                    "total_duration": m.total_duration,
                    "avg_duration": m.avg_duration,
                    "min_duration": m.min_duration,
                    "max_duration": m.max_duration,
                    "avg_memory_mb": m.avg_memory_mb,
                    "success_rate": m.success_rate,
                }
                for key, m in self.aggregated.items()
            },
            "custom_metrics": self.profiler.custom_metrics,
            "operation_count": len(self.profiler.operations),
        }

    def to_json(self, indent: int = 2) -> str:
        """
        Export report as JSON.

        Args:
            indent: JSON indentation

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, filepath: str, format: str = "json"):
        """
        Save report to file.

        Args:
            filepath: Output file path
            format: Output format ('json' or 'text')
        """
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)

        with open(filepath, "w") as f:
            if format == "json":
                f.write(self.to_json())
            else:
                f.write(self.format(detailed=True))

    def compare_to_baseline(self, baseline_path: str) -> dict[str, Any]:
        """
        Compare this report to a baseline.

        Args:
            baseline_path: Path to baseline JSON report

        Returns:
            Comparison dictionary with improvements/regressions
        """
        with open(baseline_path) as f:
            baseline = json.load(f)

        current = self.to_dict()
        comparison: dict[str, Any] = {
            "baseline_duration": baseline.get("total_duration"),
            "current_duration": current.get("total_duration"),
            "duration_change_pct": None,
            "operation_comparisons": {},
        }

        # Overall duration comparison
        if baseline.get("total_duration") and current.get("total_duration"):
            baseline_dur = baseline["total_duration"]
            current_dur = current["total_duration"]
            change_pct = ((current_dur - baseline_dur) / baseline_dur) * 100
            comparison["duration_change_pct"] = change_pct
            comparison["improvement"] = change_pct < 0

        # Per-operation comparisons
        baseline_ops = baseline.get("aggregated_metrics", {})
        current_ops = current.get("aggregated_metrics", {})

        for op_key in set(baseline_ops.keys()) | set(current_ops.keys()):
            baseline_op = baseline_ops.get(op_key)
            current_op = current_ops.get(op_key)

            if baseline_op and current_op:
                baseline_avg = baseline_op["avg_duration"]
                current_avg = current_op["avg_duration"]
                change_pct = ((current_avg - baseline_avg) / baseline_avg) * 100

                comparison["operation_comparisons"][op_key] = {
                    "baseline_avg": baseline_avg,
                    "current_avg": current_avg,
                    "change_pct": change_pct,
                    "improved": change_pct < 0,
                }

        return comparison
