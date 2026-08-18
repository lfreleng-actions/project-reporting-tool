# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Enhanced caching system for repository analysis.

This module provides intelligent caching for repository metadata and git operations
to significantly improve performance on repeated analyses.

Classes:
    CacheManager: Main cache coordinator
    RepositoryCache: Repository metadata caching
    GitOperationCache: Git command result caching
    CacheStats: Cache performance statistics
    CacheEntry: Individual cache entry
    CacheKey: Cache key generation

Example:
    >>> from src.performance.cache import CacheManager
    >>> cache = CacheManager(cache_dir=".cache", ttl=3600)
    >>> cache.set("repo:owner/name:metadata", metadata)
    >>> cached = cache.get("repo:owner/name:metadata")
    >>> stats = cache.get_stats()
    >>> print(f"Hit rate: {stats.hit_rate:.1%}")
"""

from .keys import CacheKey
from .manager import CacheManager
from .models import CacheEntry, CacheStats, CacheType
from .typed_caches import (
    AnalysisResultCache,
    APIResponseCache,
    GitOperationCache,
    RepositoryCache,
    create_cache_manager,
)


__all__ = [
    "APIResponseCache",
    "AnalysisResultCache",
    "CacheEntry",
    "CacheKey",
    "CacheManager",
    "CacheStats",
    "CacheType",
    "GitOperationCache",
    "RepositoryCache",
    "create_cache_manager",
]
