# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Memory optimization coordinator.

Ties together lazy loading, streaming, monitoring and garbage collection
tuning, and provides the memory tracking context manager and factory.
"""

import gc
import logging
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .loading import LazyLoader, LazyProxy, StreamProcessor
from .models import MemorySnapshot, MemoryStats
from .monitor import MemoryMonitor


logger = logging.getLogger(__name__)


class MemoryOptimizer:
    """Main memory optimizer coordinator."""

    def __init__(
        self,
        max_memory_mb: float = 500,
        lazy_loading: bool = True,
        stream_threshold_mb: float = 10,
        gc_interval: int = 10,
        auto_gc: bool = True,
    ):
        """
        Initialize memory optimizer.

        Args:
            max_memory_mb: Maximum memory per repository
            lazy_loading: Enable lazy loading
            stream_threshold_mb: Stream files larger than this
            gc_interval: Run GC every N operations
            auto_gc: Automatically run garbage collection
        """
        self.max_memory_mb = max_memory_mb
        self.lazy_loading = lazy_loading
        self.stream_threshold_mb = stream_threshold_mb
        self.gc_interval = gc_interval
        self.auto_gc = auto_gc

        # Components
        self.lazy_loader = LazyLoader()
        self.stream_processor = StreamProcessor()
        self.monitor = MemoryMonitor(alert_threshold_mb=max_memory_mb)

        # Statistics
        self._operations = 0
        self._gc_runs = 0
        self._gc_collected = 0

        # Environment optimized
        self._env_optimized = False

        logger.info(
            f"Memory optimizer initialized: max={max_memory_mb}MB, "
            f"lazy={lazy_loading}, stream_threshold={stream_threshold_mb}MB"
        )

    def optimize_environment(self) -> None:
        """Optimize Python environment for memory efficiency."""
        if self._env_optimized:
            return

        gc.set_threshold(700, 10, 10)  # More aggressive GC

        # Enable GC debug stats (development only)
        if logger.isEnabledFor(logging.DEBUG):
            gc.set_debug(gc.DEBUG_STATS)

        # Set recursion limit (prevent stack overflow)
        sys.setrecursionlimit(10000)

        self._env_optimized = True
        logger.info("Environment optimized for memory efficiency")

    def optimize_git_config(self) -> dict[str, str]:
        """
        Get git configuration for memory optimization.

        Returns:
            Git config dictionary
        """
        return {
            "core.packedGitLimit": "256m",
            "core.packedGitWindowSize": "256m",
            "pack.windowMemory": "256m",
            "pack.packSizeLimit": "256m",
            "pack.threads": "1",
            "core.preloadIndex": "true",
            "core.fscache": "true",
        }

    def create_lazy(
        self,
        loader: Callable[[], Any],
        name: str = "",
    ) -> LazyProxy | Any:
        """
        Create lazy-loaded object.

        Args:
            loader: Function to load data
            name: Name for debugging

        Returns:
            Lazy proxy if lazy loading enabled, else loaded object
        """
        if not self.lazy_loading:
            return loader()

        return self.lazy_loader.create_lazy(loader, name)

    def should_stream(self, file_path: str | Path) -> bool:
        """
        Check if file should be streamed.

        Args:
            file_path: Path to file

        Returns:
            True if file should be streamed
        """
        return self.stream_processor.should_stream(file_path, self.stream_threshold_mb)

    def stream_file(
        self,
        file_path: str | Path,
        processor: Callable[[str], Any],
        line_mode: bool = True,
    ) -> list[Any]:
        """
        Stream and process large file.

        Args:
            file_path: Path to file
            processor: Function to process each line/chunk
            line_mode: Process line-by-line

        Returns:
            List of processed results
        """
        return self.stream_processor.process_large_file(
            file_path,
            processor,
            line_mode=line_mode,
        )

    def track_memory(self, operation: str) -> "MemoryContext":
        """
        Context manager for tracking memory during operation.

        Args:
            operation: Operation name

        Returns:
            Memory tracking context manager
        """
        return MemoryContext(self, operation)

    def run_gc(self, force: bool = False) -> int:
        """
        Run garbage collection.

        Args:
            force: Force GC even if not at interval

        Returns:
            Number of objects collected
        """
        if not force and not self.auto_gc:
            return 0

        if not force:
            self._operations += 1
            if self._operations % self.gc_interval != 0:
                return 0

        logger.debug("Running garbage collection")
        collected = gc.collect()

        self._gc_runs += 1
        self._gc_collected += collected

        if collected > 0:
            logger.debug(f"GC collected {collected} objects")

        return collected

    def get_stats(self) -> MemoryStats:
        """Get memory statistics."""
        current_mb = self.monitor.get_current_memory()
        peak_mb = self.monitor.get_peak_memory()

        lazy_stats = self.lazy_loader.get_stats()
        stream_stats = self.stream_processor.get_stats()

        return MemoryStats(
            current_mb=current_mb,
            peak_mb=peak_mb,
            allocated_mb=current_mb,  # Approximate
            gc_collections=self._gc_runs,
            gc_collected=self._gc_collected,
            tracked_objects=lazy_stats["total_proxies"],
            lazy_loads=lazy_stats["loaded_proxies"],
            stream_reads=stream_stats["read_count"],
        )

    def reset(self) -> None:
        """Reset optimizer state."""
        self.lazy_loader.clear()
        self.monitor.reset()
        self._operations = 0
        self._gc_runs = 0
        self._gc_collected = 0


class MemoryContext:
    """Context manager for memory tracking."""

    def __init__(self, optimizer: MemoryOptimizer, operation: str):
        """
        Initialize memory context.

        Args:
            optimizer: Memory optimizer
            operation: Operation name
        """
        self.optimizer = optimizer
        self.operation = operation
        self._start_snapshot: MemorySnapshot | None = None
        self._end_snapshot: MemorySnapshot | None = None

    def __enter__(self) -> "MemoryContext":
        """Enter context."""
        self._start_snapshot = self.optimizer.monitor.snapshot(operation=f"{self.operation}_start")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context."""
        self._end_snapshot = self.optimizer.monitor.snapshot(operation=f"{self.operation}_end")

        # Run GC if needed
        self.optimizer.run_gc()

        if self._start_snapshot and self._end_snapshot:
            delta = self._end_snapshot.memory_mb - self._start_snapshot.memory_mb
            logger.debug(
                f"Memory for {self.operation}: "
                f"{self._start_snapshot.memory_mb:.1f} MB -> "
                f"{self._end_snapshot.memory_mb:.1f} MB "
                f"(delta: {delta:+.1f} MB)"
            )

    def get_delta(self) -> float:
        """Get memory delta in MB."""
        if self._start_snapshot and self._end_snapshot:
            return self._end_snapshot.memory_mb - self._start_snapshot.memory_mb
        return 0.0


def create_memory_optimizer(
    max_memory_mb: float = 500,
    lazy_loading: bool = True,
    stream_threshold_mb: float = 10,
    gc_interval: int = 10,
    auto_gc: bool = True,
) -> MemoryOptimizer:
    """
    Create memory optimizer with default settings.

    Args:
        max_memory_mb: Maximum memory per repository
        lazy_loading: Enable lazy loading
        stream_threshold_mb: Stream files larger than this
        gc_interval: Run GC every N operations
        auto_gc: Automatically run garbage collection

    Returns:
        Configured memory optimizer
    """
    optimizer = MemoryOptimizer(
        max_memory_mb=max_memory_mb,
        lazy_loading=lazy_loading,
        stream_threshold_mb=stream_threshold_mb,
        gc_interval=gc_interval,
        auto_gc=auto_gc,
    )
    optimizer.optimize_environment()
    return optimizer
