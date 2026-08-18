# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Timing and memory tracking primitives for performance profiling.

Contains the operation timer context manager, the memory usage tracker,
and the convenience decorator built on top of the timer.
"""

import time
from typing import TYPE_CHECKING, Any, Optional

import psutil

from .models import OperationMetric


if TYPE_CHECKING:
    # Imported for type checking only; importing at runtime would create a
    # cycle because profiler.py imports OperationTimer from this module.
    from .profiler import PerformanceProfiler


class OperationTimer:
    """
    Context manager for timing operations and tracking memory usage.

    Example:
        >>> timer = OperationTimer("process_repo", category="analysis")
        >>> with timer:
        ...     # Do work
        ...     pass
        >>> print(f"Duration: {timer.duration:.2f}s")
    """

    def __init__(
        self,
        name: str,
        category: str = "other",
        profiler: Optional["PerformanceProfiler"] = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize operation timer.

        Args:
            name: Operation name
            category: Operation category
            profiler: Optional profiler to register with
            metadata: Optional metadata to attach
        """
        self.name = name
        self.category = category
        self.profiler = profiler
        self.metadata = metadata or {}

        self.start_time: float | None = None
        self.end_time: float | None = None
        self.duration: float | None = None
        self.memory_start: int | None = None
        self.memory_end: int | None = None
        self.memory_delta: int | None = None
        self.success = True
        self.error: str | None = None

    def __enter__(self) -> "OperationTimer":
        """Start timing and memory tracking."""
        self.start_time = time.perf_counter()

        try:
            process = psutil.Process()
            self.memory_start = process.memory_info().rss
        except (ImportError, Exception):
            # Fallback if psutil not available
            self.memory_start = 0

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record metrics."""
        self.end_time = time.perf_counter()
        if self.start_time is not None:
            self.duration = self.end_time - self.start_time

        try:
            process = psutil.Process()
            mem_end = process.memory_info().rss
            self.memory_end = mem_end
            if self.memory_start is not None:
                self.memory_delta = mem_end - self.memory_start
        except (ImportError, Exception):
            self.memory_end = self.memory_start if self.memory_start is not None else 0
            self.memory_delta = 0

        # Track success/failure
        if exc_type is not None:
            self.success = False
            self.error = f"{exc_type.__name__}: {exc_val}"

        # Register with profiler if provided
        if (
            self.profiler
            and self.start_time is not None
            and self.end_time is not None
            and self.duration is not None
        ):
            metric = OperationMetric(
                name=self.name,
                category=self.category,
                start_time=self.start_time,
                end_time=self.end_time,
                duration=self.duration,
                memory_start=self.memory_start or 0,
                memory_end=self.memory_end or 0,
                memory_delta=self.memory_delta or 0,
                success=self.success,
                error=self.error,
                metadata=self.metadata,
            )
            self.profiler.record_operation(metric)

        # Don't suppress exceptions
        return False


class MemoryTracker:
    """
    Track memory usage over time to identify leaks and spikes.

    Example:
        >>> tracker = MemoryTracker()
        >>> tracker.start()
        >>> # Do work
        >>> tracker.snapshot("after_analysis")
        >>> stats = tracker.get_stats()
    """

    def __init__(self):
        """Initialize memory tracker."""
        self.snapshots: list[tuple[str, int, float]] = []
        self.start_memory: int | None = None
        self.start_time: float | None = None
        self.tracking = False

    def start(self):
        """Start memory tracking."""
        self.tracking = True
        self.start_time = time.perf_counter()
        try:
            process = psutil.Process()
            start_mem = process.memory_info().rss
            self.start_memory = start_mem
            self.snapshots = [("start", start_mem, 0.0)]
        except (ImportError, Exception):
            self.start_memory = 0
            self.snapshots = []

    def snapshot(self, label: str):
        """
        Take a memory snapshot with a label.

        Args:
            label: Description of this snapshot point
        """
        if not self.tracking:
            return

        try:
            process = psutil.Process()
            current_memory = process.memory_info().rss
            if self.start_time is not None:
                elapsed = time.perf_counter() - self.start_time
                self.snapshots.append((label, current_memory, elapsed))
        except (ImportError, Exception):
            pass

    def stop(self):
        """Stop memory tracking and take final snapshot."""
        self.snapshot("end")
        self.tracking = False

    def get_stats(self) -> dict[str, Any]:
        """
        Get memory usage statistics.

        Returns:
            Dictionary with memory statistics
        """
        if not self.snapshots:
            return {"available": False, "reason": "psutil not available or no snapshots taken"}

        memories = [mem for _, mem, _ in self.snapshots]
        start_mem = memories[0]
        end_mem = memories[-1]
        peak_mem = max(memories)

        return {
            "available": True,
            "start_mb": start_mem / (1024 * 1024),
            "end_mb": end_mem / (1024 * 1024),
            "peak_mb": peak_mem / (1024 * 1024),
            "delta_mb": (end_mem - start_mem) / (1024 * 1024),
            "snapshots": [
                {"label": label, "memory_mb": mem / (1024 * 1024), "elapsed_seconds": elapsed}
                for label, mem, elapsed in self.snapshots
            ],
        }


# Convenience function for simple profiling
def profile_operation(name: str, category: str = "other"):
    """
    Decorator for profiling a function.

    Args:
        name: Operation name
        category: Operation category

    Example:
        >>> @profile_operation("process_data", category="analysis")
        ... def process():
        ...     pass
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            timer = OperationTimer(name, category)
            with timer:
                return func(*args, **kwargs)

        return wrapper

    return decorator
