# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Data model definitions for memory optimization.

Contains the memory size unit enum, the aggregate memory statistics and
the point-in-time memory snapshot record.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MemoryUnit(Enum):
    """Memory size units."""

    BYTES = 1
    KB = 1024
    MB = 1024 * 1024
    GB = 1024 * 1024 * 1024


@dataclass
class MemoryStats:
    """Memory usage statistics."""

    current_mb: float = 0.0
    peak_mb: float = 0.0
    allocated_mb: float = 0.0
    gc_collections: int = 0
    gc_collected: int = 0
    tracked_objects: int = 0
    lazy_loads: int = 0
    stream_reads: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "current_mb": self.current_mb,
            "peak_mb": self.peak_mb,
            "allocated_mb": self.allocated_mb,
            "gc_collections": self.gc_collections,
            "gc_collected": self.gc_collected,
            "tracked_objects": self.tracked_objects,
            "lazy_loads": self.lazy_loads,
            "stream_reads": self.stream_reads,
        }

    def format(self) -> str:
        """Format statistics as string."""
        return f"""Memory Statistics:
  Current: {self.current_mb:.1f} MB
  Peak: {self.peak_mb:.1f} MB
  Allocated: {self.allocated_mb:.1f} MB
  GC Collections: {self.gc_collections:,}
  GC Objects Collected: {self.gc_collected:,}
  Tracked Objects: {self.tracked_objects:,}
  Lazy Loads: {self.lazy_loads:,}
  Stream Reads: {self.stream_reads:,}"""


@dataclass
class MemorySnapshot:
    """Memory snapshot at a point in time."""

    timestamp: float
    memory_mb: float
    operation: str
    metadata: dict[str, Any] = field(default_factory=dict)
