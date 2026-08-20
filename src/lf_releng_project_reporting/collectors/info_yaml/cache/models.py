# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Cache entry data structure.

Holds the per-entry metadata (creation/access timestamps, access count, TTL
and estimated size) shared by every cache level.
"""

import time
from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """
    Represents a single cache entry with metadata.

    Attributes:
        key: Cache key
        value: Cached value
        created_at: Unix timestamp when entry was created
        accessed_at: Unix timestamp when entry was last accessed
        access_count: Number of times entry has been accessed
        ttl: Time-to-live in seconds (None = no expiration)
        size_bytes: Approximate size in bytes
    """

    key: str
    value: T
    created_at: float
    accessed_at: float
    access_count: int = 0
    ttl: float | None = None
    size_bytes: int = 0

    def is_expired(self, current_time: float | None = None) -> bool:
        """
        Check if the cache entry has expired.

        Args:
            current_time: Current time (defaults to time.time())

        Returns:
            True if expired, False otherwise
        """
        if self.ttl is None:
            return False

        if current_time is None:
            current_time = time.time()

        return (current_time - self.created_at) > self.ttl

    def touch(self) -> None:
        """Update access time and increment access count."""
        self.accessed_at = time.time()
        self.access_count += 1
