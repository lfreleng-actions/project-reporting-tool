# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Multi-level cache composition and factory.

Chains the in-memory and persistent levels into a single interface that
promotes disk hits into memory, plus the INFO.yaml cache factory.
"""

import logging
from pathlib import Path
from typing import Any, Generic

from .memory import LRUCache
from .models import T
from .persistent import PersistentCache


class MultiLevelCache(Generic[T]):
    """
    Multi-level cache combining memory (LRU) and persistent storage.

    Provides a two-tier caching system:
    - Level 1: Fast in-memory LRU cache
    - Level 2: Persistent disk cache

    Data flows from L2 to L1 on cache hits, providing optimal performance
    for frequently accessed data while maintaining long-term persistence.
    """

    def __init__(
        self,
        memory_cache: LRUCache[T],
        disk_cache: PersistentCache | None = None,
    ):
        """
        Initialize the multi-level cache.

        Args:
            memory_cache: In-memory LRU cache (L1)
            disk_cache: Persistent disk cache (L2, optional)
        """
        self.memory_cache = memory_cache
        self.disk_cache = disk_cache

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(
            f"MultiLevelCache initialized: "
            f"memory={memory_cache is not None}, "
            f"disk={disk_cache is not None}"
        )

    def get(self, key: str, default: T | None = None) -> T | None:
        """
        Get a value from the cache.

        Checks L1 (memory) first, then L2 (disk) if not found.
        Promotes disk values to memory on hit.

        Args:
            key: Cache key
            default: Default value if not found

        Returns:
            Cached value or default
        """
        # Check L1 (memory)
        value = self.memory_cache.get(key)
        if value is not None:
            self.logger.debug(f"L1 cache hit: {key}")
            return value

        # Check L2 (disk)
        if self.disk_cache is not None:
            value = self.disk_cache.get(key)
            if value is not None:
                self.logger.debug(f"L2 cache hit: {key}, promoting to L1")
                # Promote to L1
                self.memory_cache.set(key, value)
                return value  # type: ignore[no-any-return]

        return default

    def set(self, key: str, value: T, ttl: float | None = None) -> None:
        """
        Set a value in the cache.

        Writes to both L1 (memory) and L2 (disk).

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        self.memory_cache.set(key, value, ttl=ttl)

        if self.disk_cache is not None:
            self.disk_cache.set(key, value)

    def delete(self, key: str) -> None:
        """
        Delete a value from the cache.

        Deletes from both L1 and L2.

        Args:
            key: Cache key
        """
        self.memory_cache.delete(key)

        if self.disk_cache is not None:
            self.disk_cache.delete(key)

    def clear(self) -> None:
        """Clear both L1 and L2 caches."""
        self.memory_cache.clear()

        if self.disk_cache is not None:
            self.disk_cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics for all cache levels.

        Returns:
            Dictionary with cache statistics
        """
        stats = {
            "memory": self.memory_cache.get_stats(),
        }

        if self.disk_cache is not None:
            cache_dir = self.disk_cache.cache_dir
            file_count = len(list(cache_dir.glob("*")))
            stats["disk"] = {
                "entries": file_count,
                "cache_dir": str(cache_dir),
            }

        return stats


def create_info_yaml_cache(
    cache_dir: Path | None = None,
    max_memory_entries: int = 1000,
    ttl: float | None = 3600,  # 1 hour default
    enable_disk_cache: bool = True,
) -> MultiLevelCache[Any]:
    """
    Factory function to create a configured multi-level cache for INFO.yaml data.

    Args:
        cache_dir: Directory for disk cache (None = use temp dir)
        max_memory_entries: Maximum entries in memory cache
        ttl: Default time-to-live in seconds
        enable_disk_cache: Enable persistent disk cache

    Returns:
        Configured MultiLevelCache instance
    """
    memory_cache: LRUCache[Any] = LRUCache(
        max_entries=max_memory_entries,
        max_size_bytes=100 * 1024 * 1024,  # 100MB
        default_ttl=ttl,
    )

    # Create disk cache if enabled
    disk_cache = None
    if enable_disk_cache:
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "lf-releng-project-reporting" / "info-yaml"
        disk_cache = PersistentCache(cache_dir, format="pickle")

    return MultiLevelCache(memory_cache, disk_cache)
