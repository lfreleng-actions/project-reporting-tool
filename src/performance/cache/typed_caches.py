# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Typed cache facades over the cache manager.

Provides purpose-specific wrappers for repository metadata, git operation
results, API responses and analysis results, plus the cache manager factory.
"""

from pathlib import Path
from typing import Any

from .keys import CacheKey
from .manager import CacheManager
from .models import CacheType


class RepositoryCache:
    """Cache for repository metadata."""

    def __init__(self, cache_manager: CacheManager):
        """
        Initialize repository cache.

        Args:
            cache_manager: Underlying cache manager
        """
        self.cache = cache_manager

    def get_metadata(self, repo_url: str, ref: str | None = None) -> dict[str, Any] | None:
        """
        Get cached repository metadata.

        Args:
            repo_url: Repository URL
            ref: Git reference (branch/tag/commit)

        Returns:
            Cached metadata or None
        """
        key = CacheKey.repository(repo_url, ref)
        return self.cache.get(key)

    def set_metadata(
        self,
        repo_url: str,
        metadata: dict[str, Any],
        ref: str | None = None,
        ttl: float | None = None,
    ) -> bool:
        """
        Cache repository metadata.

        Args:
            repo_url: Repository URL
            metadata: Metadata to cache
            ref: Git reference
            ttl: Time-to-live in seconds

        Returns:
            True if cached successfully
        """
        key = CacheKey.repository(repo_url, ref)
        return self.cache.set(key, metadata, ttl, CacheType.REPOSITORY_METADATA)

    def invalidate_repository(self, repo_url: str) -> int:
        """
        Invalidate all cache entries for a repository.

        Args:
            repo_url: Repository URL

        Returns:
            Number of entries invalidated
        """
        # Hash the repo URL to match cache keys
        pattern = f"repo:{repo_url}:*"
        hashed_pattern = CacheKey._hash(pattern).replace("*", "*")
        return self.cache.invalidate_pattern(hashed_pattern)


class GitOperationCache:
    """Cache for git operation results."""

    def __init__(self, cache_manager: CacheManager):
        """
        Initialize git operation cache.

        Args:
            cache_manager: Underlying cache manager
        """
        self.cache = cache_manager

    def get_operation(
        self,
        repo_url: str,
        operation: str,
        params: dict[str, Any] | None = None,
    ) -> Any | None:
        """
        Get cached git operation result.

        Args:
            repo_url: Repository URL
            operation: Operation name (e.g., 'log', 'diff', 'blame')
            params: Operation parameters

        Returns:
            Cached result or None
        """
        key = CacheKey.git_operation(repo_url, operation, params)
        return self.cache.get(key)

    def set_operation(
        self,
        repo_url: str,
        operation: str,
        result: Any,
        params: dict[str, Any] | None = None,
        ttl: float | None = None,
    ) -> bool:
        """
        Cache git operation result.

        Args:
            repo_url: Repository URL
            operation: Operation name
            result: Operation result
            params: Operation parameters
            ttl: Time-to-live in seconds

        Returns:
            True if cached successfully
        """
        key = CacheKey.git_operation(repo_url, operation, params)
        return self.cache.set(key, result, ttl, CacheType.GIT_OPERATION)

    def invalidate_repository(self, repo_url: str) -> int:
        """
        Invalidate all git operation cache entries for a repository.

        Args:
            repo_url: Repository URL

        Returns:
            Number of entries invalidated
        """
        pattern = f"git:{repo_url}:*"
        hashed_pattern = CacheKey._hash(pattern).replace("*", "*")
        return self.cache.invalidate_pattern(hashed_pattern)


class APIResponseCache:
    """Cache for API responses."""

    def __init__(self, cache_manager: CacheManager):
        """
        Initialize API response cache.

        Args:
            cache_manager: Underlying cache manager
        """
        self.cache = cache_manager

    def get_response(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> Any | None:
        """
        Get cached API response.

        Args:
            endpoint: API endpoint
            params: Request parameters

        Returns:
            Cached response or None
        """
        key = CacheKey.api_response(endpoint, params)
        return self.cache.get(key)

    def set_response(
        self,
        endpoint: str,
        response: Any,
        params: dict[str, Any] | None = None,
        ttl: float | None = None,
    ) -> bool:
        """
        Cache API response.

        Args:
            endpoint: API endpoint
            response: API response
            params: Request parameters
            ttl: Time-to-live in seconds

        Returns:
            True if cached successfully
        """
        key = CacheKey.api_response(endpoint, params)
        return self.cache.set(key, response, ttl, CacheType.API_RESPONSE)


class AnalysisResultCache:
    """Cache for analysis results."""

    def __init__(self, cache_manager: CacheManager):
        """
        Initialize analysis result cache.

        Args:
            cache_manager: Underlying cache manager
        """
        self.cache = cache_manager

    def get_result(
        self,
        repo_url: str,
        analysis_type: str,
        config: dict[str, Any] | None = None,
    ) -> Any | None:
        """
        Get cached analysis result.

        Args:
            repo_url: Repository URL
            analysis_type: Type of analysis
            config: Analysis configuration

        Returns:
            Cached result or None
        """
        key = CacheKey.analysis_result(repo_url, analysis_type, config)
        return self.cache.get(key)

    def set_result(
        self,
        repo_url: str,
        analysis_type: str,
        result: Any,
        config: dict[str, Any] | None = None,
        ttl: float | None = None,
    ) -> bool:
        """
        Cache analysis result.

        Args:
            repo_url: Repository URL
            analysis_type: Type of analysis
            result: Analysis result
            config: Analysis configuration
            ttl: Time-to-live in seconds

        Returns:
            True if cached successfully
        """
        key = CacheKey.analysis_result(repo_url, analysis_type, config)
        return self.cache.set(key, result, ttl, CacheType.ANALYSIS_RESULT)

    def invalidate_repository(self, repo_url: str) -> int:
        """
        Invalidate all analysis results for a repository.

        Args:
            repo_url: Repository URL

        Returns:
            Number of entries invalidated
        """
        pattern = f"analysis:{repo_url}:*"
        hashed_pattern = CacheKey._hash(pattern).replace("*", "*")
        return self.cache.invalidate_pattern(hashed_pattern)


def create_cache_manager(
    cache_dir: str | Path | None = None,
    ttl: float = 3600,
    max_size_mb: float = 1000,
    auto_cleanup: bool = True,
) -> CacheManager:
    """
    Create a cache manager with default settings.

    Args:
        cache_dir: Directory for cache storage
        ttl: Default time-to-live in seconds
        max_size_mb: Maximum cache size in megabytes
        auto_cleanup: Automatically clean expired entries

    Returns:
        Configured cache manager
    """
    return CacheManager(
        cache_dir=cache_dir,
        ttl=ttl,
        max_size_mb=max_size_mb,
        auto_cleanup=auto_cleanup,
    )
