# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Core cache manager.

Coordinates the in-memory cache and its on-disk backing store, including
loading, persistence, expiration, invalidation, eviction and statistics.
"""

import logging
import pickle
import shutil
import threading
import time
from pathlib import Path
from typing import Any

from .models import CacheEntry, CacheStats, CacheType


logger = logging.getLogger(__name__)


class CacheManager:
    """Main cache manager for repository analysis."""

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        ttl: float = 3600,
        max_size_mb: float = 1000,
        auto_cleanup: bool = True,
    ):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory for cache storage. Defaults to a per-user
                cache location rather than a working-directory-relative path,
                so the tool never unpickles cache files that happen to live
                inside an analyzed (and potentially untrusted) repository.
            ttl: Default time-to-live in seconds (0 = never expire)
            max_size_mb: Maximum cache size in megabytes
            auto_cleanup: Automatically clean expired entries
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "lf-releng-project-reporting" / "report-cache"
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.max_size_mb = max_size_mb
        self.auto_cleanup = auto_cleanup

        # In-memory cache
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

        # Statistics
        self._stats = CacheStats()

        self._init_cache_dir()

        self._load_cache()

        logger.info(
            f"Cache initialized: dir={self.cache_dir}, ttl={self.ttl}s, "
            f"max_size={self.max_size_mb}MB"
        )

    def _init_cache_dir(self) -> None:
        """Initialize cache directory structure."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        for cache_type in CacheType:
            (self.cache_dir / cache_type.value).mkdir(exist_ok=True)

    def _get_cache_file(self, key: str, cache_type: CacheType) -> Path:
        """Get cache file path for key."""
        # Use first 2 chars of key for subdirectory (sharding)
        subdir = key[:2] if len(key) >= 2 else "00"
        cache_subdir = self.cache_dir / cache_type.value / subdir
        cache_subdir.mkdir(parents=True, exist_ok=True)
        return cache_subdir / f"{key}.pkl"

    def _load_cache(self) -> None:
        """Load cache entries from disk."""
        loaded = 0
        expired = 0

        for cache_type in CacheType:
            type_dir = self.cache_dir / cache_type.value
            if not type_dir.exists():
                continue

            cache_root = self.cache_dir.resolve()
            for cache_file in type_dir.rglob("*.pkl"):
                try:
                    # Defense in depth: never unpickle a file that resolves
                    # outside the cache directory (e.g. via a symlink).
                    resolved = cache_file.resolve()
                    if cache_root not in resolved.parents:
                        # Skip without unlinking: the path may resolve
                        # outside the cache because a parent directory is a
                        # symlink, and unlinking would delete the external
                        # target rather than the cache entry.
                        logger.warning(
                            "Skipping cache file outside cache directory: %s", cache_file
                        )
                        continue
                    with open(resolved, "rb") as f:
                        # aislop-ignore-next-line pickle-load -- path-contained cache file written by this tool
                        entry: CacheEntry = pickle.load(f)

                    if entry.is_expired():
                        cache_file.unlink()
                        expired += 1
                    else:
                        self._cache[entry.key] = entry
                        loaded += 1
                except Exception as e:
                    logger.warning(f"Failed to load cache entry {cache_file}: {e}")
                    cache_file.unlink(missing_ok=True)

        if loaded > 0:
            logger.info(f"Loaded {loaded} cache entries from disk ({expired} expired)")

        self._update_stats()

    def get(self, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                logger.debug(f"Cache miss: {key}")
                return None

            if entry.is_expired():
                self._invalidate_entry(key, entry)
                self._stats.misses += 1
                self._stats.expirations += 1
                logger.debug(f"Cache expired: {key}")
                return None

            entry.touch()
            self._stats.hits += 1
            logger.debug(f"Cache hit: {key} (age={entry.age_seconds():.1f}s)")
            return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: float | None = None,
        cache_type: CacheType = CacheType.REPOSITORY_METADATA,
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = use default)
            cache_type: Type of cache entry

        Returns:
            True if cached successfully
        """
        if ttl is None:
            ttl = self.ttl

        with self._lock:
            # Serialize to get size
            try:
                serialized = pickle.dumps(value)
                size_bytes = len(serialized)
            except Exception as e:
                logger.error(f"Failed to serialize value for {key}: {e}")
                return False

            # Check if we need to evict
            if self.auto_cleanup:
                self._maybe_evict(size_bytes)

            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                ttl=ttl,
                size_bytes=size_bytes,
                cache_type=cache_type,
            )

            # Store in memory
            self._cache[key] = entry
            self._stats.sets += 1

            # Persist to disk
            try:
                cache_file = self._get_cache_file(key, cache_type)
                with open(cache_file, "wb") as f:
                    pickle.dump(entry, f)
                logger.debug(f"Cached: {key} (size={size_bytes / 1024:.1f}KB, ttl={ttl}s)")
            except Exception as e:
                logger.error(f"Failed to persist cache entry {key}: {e}")
                # Keep in memory even if disk write fails

            self._update_stats()
            return True

    def invalidate(self, key: str) -> bool:
        """
        Invalidate a cache entry.

        Args:
            key: Cache key to invalidate

        Returns:
            True if entry was invalidated
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False

            self._invalidate_entry(key, entry)
            self._stats.invalidations += 1
            self._update_stats()
            return True

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all entries matching pattern.

        Args:
            pattern: Pattern to match (supports * wildcard)

        Returns:
            Number of entries invalidated
        """
        import fnmatch

        with self._lock:
            keys_to_invalidate = [key for key in self._cache if fnmatch.fnmatch(key, pattern)]

            for key in keys_to_invalidate:
                entry = self._cache[key]
                self._invalidate_entry(key, entry)

            self._stats.invalidations += len(keys_to_invalidate)
            self._update_stats()

            logger.info(f"Invalidated {len(keys_to_invalidate)} entries matching '{pattern}'")
            return len(keys_to_invalidate)

    def _invalidate_entry(self, key: str, entry: CacheEntry) -> None:
        """Remove entry from cache."""
        del self._cache[key]

        cache_file = self._get_cache_file(key, entry.cache_type)
        cache_file.unlink(missing_ok=True)

        logger.debug(f"Invalidated: {key}")

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()

            # Clear disk cache
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self._init_cache_dir()

            # Reset statistics
            old_stats = self._stats
            self._stats = CacheStats()
            self._stats.invalidations = old_stats.invalidations + count

            logger.info(f"Cleared {count} cache entries")
            return count

    def cleanup(self) -> int:
        """
        Remove expired entries.

        Returns:
            Number of entries cleaned up
        """
        with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]

            for key in expired_keys:
                entry = self._cache[key]
                self._invalidate_entry(key, entry)

            self._stats.expirations += len(expired_keys)
            self._update_stats()

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired entries")

            return len(expired_keys)

    def _maybe_evict(self, needed_bytes: int) -> None:
        """Evict entries if cache is too full."""
        max_bytes = int(self.max_size_mb * 1024 * 1024)
        current_bytes = sum(entry.size_bytes for entry in self._cache.values())

        if current_bytes + needed_bytes <= max_bytes:
            return

        # Need to evict - use LRU strategy
        entries = sorted(self._cache.items(), key=lambda x: x[1].last_accessed)

        evicted = 0
        for key, entry in entries:
            if current_bytes + needed_bytes <= max_bytes:
                break

            self._invalidate_entry(key, entry)
            current_bytes -= entry.size_bytes
            evicted += 1

        self._stats.evictions += evicted
        logger.info(f"Evicted {evicted} entries to make space")

    def _update_stats(self) -> None:
        """Update cache statistics."""
        if not self._cache:
            self._stats.entry_count = 0
            self._stats.total_size_bytes = 0
            self._stats.oldest_entry_age = 0.0
            self._stats.newest_entry_age = 0.0
            return

        self._stats.entry_count = len(self._cache)
        self._stats.total_size_bytes = sum(entry.size_bytes for entry in self._cache.values())

        ages = [entry.age_seconds() for entry in self._cache.values()]
        self._stats.oldest_entry_age = max(ages)
        self._stats.newest_entry_age = min(ages)

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            self._update_stats()
            return self._stats

    def get_entries(self, cache_type: CacheType | None = None) -> list[CacheEntry]:
        """
        Get all cache entries.

        Args:
            cache_type: Filter by cache type (None = all)

        Returns:
            List of cache entries
        """
        with self._lock:
            if cache_type is None:
                return list(self._cache.values())
            return [entry for entry in self._cache.values() if entry.cache_type == cache_type]
