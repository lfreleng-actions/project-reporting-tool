# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Log aggregation and summarisation.

Holds the aggregator that collects log entries and derives counts by level,
errors and warnings by repository, and performance metrics by phase.
"""

from collections import defaultdict
from typing import Any

from .context import LogEntry, LogLevel


class LogAggregator:
    """
    Aggregates log entries for summary reporting.

    Tracks counts by level, errors by repository, and performance metrics.
    """

    def __init__(self) -> None:
        self.entries: list[LogEntry] = []
        self.counts_by_level: dict[str, int] = defaultdict(int)
        self.errors_by_repo: dict[str, list[str]] = defaultdict(list)
        self.warnings_by_repo: dict[str, list[str]] = defaultdict(list)
        self.performance_by_phase: dict[str, list[float]] = defaultdict(list)

    def add_entry(self, entry: LogEntry) -> None:
        """Add a log entry to the aggregator."""
        self.entries.append(entry)
        self.counts_by_level[entry.level.value] += 1

        # Track errors and warnings by repository
        if entry.context.repository:
            if entry.level == LogLevel.ERROR:
                self.errors_by_repo[entry.context.repository].append(entry.message)
            elif entry.level == LogLevel.WARNING:
                self.warnings_by_repo[entry.context.repository].append(entry.message)

        # Track performance by phase
        if entry.duration_ms is not None and entry.context.phase:
            self.performance_by_phase[entry.context.phase.value].append(entry.duration_ms)

    def get_summary(self) -> dict[str, Any]:
        """
        Get summary of aggregated logs.

        Returns:
            Dictionary with log counts, errors, and performance metrics.
        """
        summary: dict[str, Any] = {
            "log_summary": dict(self.counts_by_level),
            "total_entries": len(self.entries),
        }

        # Add error details if present
        if self.errors_by_repo:
            summary["errors_by_repository"] = {
                repo: {
                    "count": len(errors),
                    "messages": errors[:5],  # First 5 errors
                }
                for repo, errors in self.errors_by_repo.items()
            }

        # Add warning details if present
        if self.warnings_by_repo:
            summary["warnings_by_repository"] = {
                repo: {
                    "count": len(warnings),
                    "messages": warnings[:5],  # First 5 warnings
                }
                for repo, warnings in self.warnings_by_repo.items()
            }

        # Add performance metrics if present
        if self.performance_by_phase:
            summary["performance_by_phase"] = {
                phase: {
                    "count": len(durations),
                    "total_ms": sum(durations),
                    "avg_ms": sum(durations) / len(durations),
                    "min_ms": min(durations),
                    "max_ms": max(durations),
                }
                for phase, durations in self.performance_by_phase.items()
            }

        return summary

    def get_partial_failures(self) -> list[dict[str, Any]]:
        """
        Get list of repositories with partial failures (warnings but not errors).

        Returns:
            List of repositories with warning counts.
        """
        partial_failures = []

        for repo, warnings in self.warnings_by_repo.items():
            if repo not in self.errors_by_repo:  # No errors, only warnings
                partial_failures.append(
                    {
                        "repository": repo,
                        "warning_count": len(warnings),
                        "sample_warnings": warnings[:3],
                    }
                )

        return partial_failures
