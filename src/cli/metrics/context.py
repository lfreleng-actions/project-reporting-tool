# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Context manager that times an operation and records it on a collector."""

import time
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    # Imported for typing only: cli.metrics.collector imports this module at
    # runtime, so a runtime import here would be circular.
    from .collector import MetricsCollector


class _TimingContext:
    """Context manager for timing operations."""

    def __init__(self, collector: "MetricsCollector", name: str, metadata: dict[str, Any]):
        """Initialize timing context."""
        self.collector = collector
        self.name = name
        self.metadata = metadata
        self.start_time = 0.0

    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and record."""
        end_time = time.time()
        duration = end_time - self.start_time

        self.collector.record_timing(
            self.name, duration, self.start_time, end_time, **self.metadata
        )

        return False
