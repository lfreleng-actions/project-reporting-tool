# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Memory usage monitoring.

Samples process memory usage, records snapshots, tracks peak usage and
raises alerts when a configured threshold is exceeded.
"""

import logging
import threading
import time
from typing import Any

from .models import MemorySnapshot


logger = logging.getLogger(__name__)


class MemoryMonitor:
    """Memory usage monitoring and tracking."""

    def __init__(
        self,
        alert_threshold_mb: float = 1000,
        sample_interval: float = 1.0,
    ):
        """
        Initialize memory monitor.

        Args:
            alert_threshold_mb: Alert when memory exceeds this
            sample_interval: Sampling interval in seconds
        """
        self.alert_threshold_mb = alert_threshold_mb
        self.sample_interval = sample_interval

        self._snapshots: list[MemorySnapshot] = []
        self._peak_mb = 0.0
        self._monitoring = False
        self._monitor_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def get_current_memory(self) -> float:
        """
        Get current process memory usage in MB.

        Returns:
            Memory usage in MB
        """
        try:
            import psutil

            process = psutil.Process()
            return float(process.memory_info().rss / (1024 * 1024))
        except ImportError:
            # Fallback to gc stats if psutil not available
            import gc

            gc.collect()

            # Rough estimate from gc stats
            stats = gc.get_stats()
            if stats:
                # Very rough estimate
                collected = sum(s.get("collected", 0) for s in stats)
                return float(collected / 1000)  # Very approximate
            return 0.0

    def snapshot(
        self, operation: str = "", metadata: dict[str, Any] | None = None
    ) -> MemorySnapshot:
        """
        Take a memory snapshot.

        Args:
            operation: Current operation name
            metadata: Additional metadata

        Returns:
            Memory snapshot
        """
        current_mb = self.get_current_memory()

        snapshot = MemorySnapshot(
            timestamp=time.time(),
            memory_mb=current_mb,
            operation=operation,
            metadata=metadata or {},
        )

        with self._lock:
            self._snapshots.append(snapshot)
            if current_mb > self._peak_mb:
                self._peak_mb = current_mb

            # Alert if threshold exceeded
            if current_mb > self.alert_threshold_mb:
                logger.warning(
                    f"Memory alert: {current_mb:.1f} MB "
                    f"(threshold: {self.alert_threshold_mb:.1f} MB) "
                    f"during operation: {operation}"
                )

        return snapshot

    def start_monitoring(self) -> None:
        """Start continuous memory monitoring."""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

        logger.info(f"Started memory monitoring (interval: {self.sample_interval}s)")

    def stop_monitoring(self) -> None:
        """Stop continuous memory monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

        logger.info("Stopped memory monitoring")

    def _monitor_loop(self) -> None:
        """Monitoring loop (runs in thread)."""
        while self._monitoring:
            self.snapshot(operation="background_monitor")
            time.sleep(self.sample_interval)

    def get_snapshots(
        self,
        operation: str | None = None,
        since: float | None = None,
    ) -> list[MemorySnapshot]:
        """
        Get memory snapshots.

        Args:
            operation: Filter by operation name
            since: Filter by timestamp (Unix time)

        Returns:
            List of snapshots
        """
        with self._lock:
            snapshots = self._snapshots

            if operation:
                snapshots = [s for s in snapshots if s.operation == operation]

            if since:
                snapshots = [s for s in snapshots if s.timestamp >= since]

            return snapshots

    def get_peak_memory(self) -> float:
        """Get peak memory usage in MB."""
        return self._peak_mb

    def reset(self) -> None:
        """Reset monitoring data."""
        with self._lock:
            self._snapshots.clear()
            self._peak_mb = 0.0
