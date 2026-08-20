# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
In-memory LRU cache level.

Level 1 of the cache stack: bounded by entry count and total estimated size,
with TTL expiry, least-recently-used eviction and hit/miss statistics.
"""

import logging
import pickle
import time
from typing import Any, Generic

from .models import CacheEntry, T


class LRUCache(Generic[T]):
    """
    LRU (Least Recently Used) cache with TTL support.

    Features:
    - Automatic eviction based on size or entry count
    - Time-to-live (TTL) expiration
    - Access tracking for statistics
    - Thread-safe operations
    """

    def __init__(
        self,
        max_entries: int = 1000,
        max_size_bytes: int | None = None,
        default_ttl: float | None = None,
    ):
        """
        Initialize the LRU cache.

        Args:
            max_entries: Maximum number of entries (default: 1000)
            max_size_bytes: Maximum total size in bytes (None = unlimited)
            default_ttl: Default time-to-live in seconds (None = no expiration)
        """
        self.max_entries = max_entries
        self.max_size_bytes = max_size_bytes
        self.default_ttl = default_ttl

        self._cache: dict[str, CacheEntry[T]] = {}
        self._total_size_bytes = 0

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(
            f"LRUCache initialized: max_entries={max_entries}, "
            f"max_size_bytes={max_size_bytes}, default_ttl={default_ttl}"
        )

    def get(self, key: str, default: T | None = None) -> T | None:
        """
        Get a value from the cache.

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return default

        # Check if expired
        if entry.is_expired():
            self._misses += 1
            self._evict_entry(key)
            return default

        entry.touch()
        self._hits += 1

        return entry.value

    def set(
        self,
        key: str,
        value: T,
        ttl: float | None = None,
    ) -> None:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = use default)
        """
        # Calculate size
        size_bytes = self._estimate_size(value)

        # Check if we need to evict existing entry
        if key in self._cache:
            self._evict_entry(key)

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            accessed_at=time.time(),
            access_count=0,
            ttl=ttl if ttl is not None else self.default_ttl,
            size_bytes=size_bytes,
        )

        # Evict if necessary
        self._evict_if_necessary(size_bytes)

        # Add to cache
        self._cache[key] = entry
        self._total_size_bytes += size_bytes

        self.logger.debug(
            f"Cached entry: key={key}, size={size_bytes}B, total_entries={len(self._cache)}"
        )

    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: Cache key

        Returns:
            True if entry was deleted, False if not found
        """
        if key in self._cache:
            self._evict_entry(key)
            return True
        return False

    def clear(self) -> None:
        """Clear all entries from the cache."""
        count = len(self._cache)
        self._cache.clear()
        self._total_size_bytes = 0
        self.logger.info(f"Cleared {count} entries from cache")

    def _evict_entry(self, key: str) -> None:
        """Evict a specific entry from the cache."""
        entry = self._cache.pop(key, None)
        if entry:
            self._total_size_bytes -= entry.size_bytes
            self._evictions += 1

    def _evict_if_necessary(self, incoming_size: int) -> None:
        """
        Evict entries if necessary to make room for new entry.

        Args:
            incoming_size: Size of entry being added
        """
        while len(self._cache) >= self.max_entries:
            self._evict_lru()

        if self.max_size_bytes is not None:
            while self._total_size_bytes + incoming_size > self.max_size_bytes and self._cache:
                self._evict_lru()

    def _evict_lru(self) -> None:
        """Evict the least recently used entry."""
        if not self._cache:
            return

        # Find entry with oldest access time
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].accessed_at,
        )

        self._evict_entry(lru_key)
        self.logger.debug(f"Evicted LRU entry: {lru_key}")

    def _estimate_size(self, value: T) -> int:
        """
        Estimate the size of a value in bytes.

        Args:
            value: Value to estimate

        Returns:
            Estimated size in bytes
        """
        try:
            # Use pickle to estimate size
            return len(pickle.dumps(value))
        except Exception:
            # Fallback estimate
            return 1024  # 1KB default

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "entries": len(self._cache),
            "max_entries": self.max_entries,
            "size_bytes": self._total_size_bytes,
            "max_size_bytes": self.max_size_bytes,
            "size_mb": round(self._total_size_bytes / (1024 * 1024), 2),
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate": round(hit_rate, 2),
        }

    def prune_expired(self) -> int:
        """
        Remove all expired entries from the cache.

        Returns:
            Number of entries pruned
        """
        current_time = time.time()
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired(current_time)]

        for key in expired_keys:
            self._evict_entry(key)

        if expired_keys:
            self.logger.info(f"Pruned {len(expired_keys)} expired entries")

        return len(expired_keys)
