# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Memory optimization module for repository analysis.

This module provides utilities for reducing memory usage, lazy loading,
streaming large files, and monitoring memory consumption.

Classes:
    MemoryOptimizer: Main memory optimization coordinator
    LazyLoader: Lazy loading for deferred data access
    StreamProcessor: Stream processing for large files
    MemoryMonitor: Memory usage tracking and alerting
    MemoryStats: Memory usage statistics
    LazyProxy: Proxy for lazy-loaded objects

Example:
    >>> from src.performance.memory import MemoryOptimizer
    >>> optimizer = MemoryOptimizer(max_memory_mb=500)
    >>> optimizer.optimize_environment()
    >>> with optimizer.track_memory("analyze_repo"):
    ...     # Analysis code
    ...     pass
    >>> stats = optimizer.get_stats()
    >>> print(f"Peak memory: {stats.peak_mb:.1f} MB")
"""

from .loading import LazyLoader, LazyProxy, StreamProcessor
from .models import MemorySnapshot, MemoryStats, MemoryUnit
from .monitor import MemoryMonitor
from .optimizer import MemoryContext, MemoryOptimizer, create_memory_optimizer


__all__ = [
    "LazyLoader",
    "LazyProxy",
    "MemoryContext",
    "MemoryMonitor",
    "MemoryOptimizer",
    "MemorySnapshot",
    "MemoryStats",
    "MemoryUnit",
    "StreamProcessor",
    "create_memory_optimizer",
]
