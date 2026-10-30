# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Data model definitions for the caching system.

Contains the cache type enum, the individual cache entry record with its
expiry and access bookkeeping, and the aggregate cache statistics.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CacheType(Enum):
    """Types of cached data."""

    REPOSITORY_METADATA = "repo_metadata"
    GIT_OPERATION = "git_operation"
    API_RESPONSE = "api_response"
    ANALYSIS_RESULT = "analysis_result"


@dataclass
class CacheEntry:
    """Individual cache entry with metadata."""

    key: str
    value: Any
    created_at: float
    ttl: float
    size_bytes: int
    cache_type: CacheType
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl <= 0:  # Never expires
            return False
        return time.time() - self.created_at > self.ttl

    def age_seconds(self) -> float:
        """Get age in seconds."""
        return time.time() - self.created_at

    def touch(self) -> None:
        """Update access time and count."""
        self.access_count += 1
        self.last_accessed = time.time()


@dataclass
class CacheStats:
    """Cache performance statistics."""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    invalidations: int = 0
    expirations: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0
    oldest_entry_age: float = 0.0
    newest_entry_age: float = 0.0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        return 1.0 - self.hit_rate

    @property
    def total_size_mb(self) -> float:
        """Get total size in megabytes."""
        return self.total_size_bytes / (1024 * 1024)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "invalidations": self.invalidations,
            "expirations": self.expirations,
            "evictions": self.evictions,
            "hit_rate": self.hit_rate,
            "miss_rate": self.miss_rate,
            "total_size_bytes": self.total_size_bytes,
            "total_size_mb": self.total_size_mb,
            "entry_count": self.entry_count,
            "oldest_entry_age": self.oldest_entry_age,
            "newest_entry_age": self.newest_entry_age,
        }

    def format(self) -> str:
        """Format statistics as string."""
        return f"""Cache Statistics:
  Requests: {self.hits + self.misses:,} ({self.hits:,} hits, {self.misses:,} misses)
  Hit Rate: {self.hit_rate:.1%}
  Sets: {self.sets:,}
  Invalidations: {self.invalidations:,}
  Expirations: {self.expirations:,}
  Evictions: {self.evictions:,}
  Size: {self.total_size_mb:.2f} MB ({self.entry_count:,} entries)
  Age Range: {self.newest_entry_age:.1f}s - {self.oldest_entry_age:.1f}s"""
