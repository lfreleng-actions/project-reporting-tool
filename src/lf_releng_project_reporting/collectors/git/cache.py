# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Filesystem cache support for collected Git metrics."""

import hashlib
import json
from pathlib import Path
from typing import Any

from .base import _CollectorState
from .commands import safe_git_command


class _CacheMixin(_CollectorState):
    """Load and save repository metrics using HEAD-based cache keys."""

    def _get_repo_cache_key(self, repo_path: Path) -> str | None:
        """Generate a cache key based on the repository's HEAD commit hash."""
        git_command = ["git", "rev-parse", "HEAD"]
        success, output = safe_git_command(git_command, repo_path, self.logger)

        if success and output.strip():
            head_hash = output.strip()
            # Include time windows in cache key to invalidate when windows change
            windows_key = hashlib.sha256(
                json.dumps(self.time_windows, sort_keys=True).encode()
            ).hexdigest()[:8]
            project_name = self._extract_gerrit_project(repo_path)
            # Replace path separators for cache key
            safe_project_name = project_name.replace("/", "_")
            return f"{safe_project_name}_{head_hash}_{windows_key}"

        return None

    def _get_cache_path(self, repo_path: Path) -> Path | None:
        """Get the cache file path for a repository."""
        if not self.cache_dir:
            return None

        cache_key = self._get_repo_cache_key(repo_path)
        if cache_key:
            return self.cache_dir / f"{cache_key}.json"

        return None

    def _load_from_cache(self, repo_path: Path) -> dict[str, Any] | None:
        """Load cached metrics for a repository if available and valid."""
        try:
            cache_path = self._get_cache_path(repo_path)
            if not cache_path or not cache_path.exists():
                return None

            with open(cache_path, encoding="utf-8") as f:
                cached_data = json.load(f)

            if not isinstance(cached_data, dict) or "repository" not in cached_data:
                project_name = self._extract_gerrit_project(repo_path)
                self.logger.warning(f"Invalid cache structure for {project_name}")
                return None

            # Check if cache is compatible with current time windows
            cached_repository = cached_data.get("repository", {})
            cached_windows = set(cached_repository.get("commit_counts", {}).keys())
            current_windows = set(self.time_windows.keys())

            if cached_windows != current_windows:
                self.logger.debug(f"Cache invalidated for {repo_path.name}: time windows changed")
                return None

            return cached_data

        except (OSError, json.JSONDecodeError, KeyError) as e:
            self.logger.debug(f"Failed to load cache for {repo_path.name}: {e}")
            return None

    def _save_cached_metrics(self, repo_path: Path, metrics: dict[str, Any]) -> None:
        """Save metrics to cache for future use."""
        try:
            cache_path = self._get_cache_path(repo_path)
            if not cache_path:
                return

            # Create a cache-friendly copy (convert sets to lists if any remain)
            cache_data = json.loads(json.dumps(metrics, default=str))

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, default=str)

            self.logger.debug(f"Saved cache for {repo_path.name}")

        except (OSError, TypeError) as e:
            self.logger.warning(f"Failed to save cache for {repo_path.name}: {e}")
