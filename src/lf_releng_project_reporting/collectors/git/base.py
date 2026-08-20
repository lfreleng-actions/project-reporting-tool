# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Shared state contract for Git collector implementation modules."""

import logging
from pathlib import Path
from typing import Any


class _CollectorState:
    """Describe state and cross-module methods supplied by the collector."""

    config: dict[str, Any]
    time_windows: dict[str, dict[str, Any]]
    logger: logging.Logger
    api_stats: Any | None
    _domain_config: dict[str, Any] | None
    cache_enabled: bool
    cache_dir: Path | None
    repos_path: Path | None
    gerrit_client: Any | None
    gerrit_projects_cache: dict[str, dict[str, Any]]
    jenkins_client: Any | None
    jenkins_allocation_context: Any
    _jenkins_initialized: bool

    def _create_gerrit_client(self, host: str, base_url: str | None, timeout: float) -> Any:
        """Create the configured Gerrit client."""
        raise NotImplementedError

    def _create_jenkins_client(
        self,
        host: str,
        jenkins_config: dict[str, Any],
        gerrit_config: dict[str, Any],
    ) -> Any:
        """Create the configured Jenkins client."""
        raise NotImplementedError

    def _extract_gerrit_project(self, repo_path: Path) -> str:
        """Resolve a Gerrit project name from a repository path."""
        raise NotImplementedError

    def _extract_gerrit_host(self, repo_path: Path) -> str:
        """Resolve a Gerrit host from a repository path."""
        raise NotImplementedError

    def _derive_gerrit_url(self, repo_path: Path) -> str:
        """Resolve a Gerrit URL from a repository path."""
        raise NotImplementedError

    def _extract_gerrit_path_prefix(self) -> str:
        """Resolve the configured Gerrit URL path prefix."""
        raise NotImplementedError

    def _get_jenkins_jobs_for_repo(self, repo_name: str) -> list[dict[str, Any]]:
        """Return Jenkins jobs allocated to a repository."""
        raise NotImplementedError

    def _load_from_cache(self, repo_path: Path) -> dict[str, Any] | None:
        """Load cached repository metrics."""
        raise NotImplementedError

    def _save_cached_metrics(self, repo_path: Path, metrics: dict[str, Any]) -> None:
        """Save repository metrics to the cache."""
        raise NotImplementedError

    def _parse_git_log_output(self, git_output: str, repo_name: str) -> list[dict[str, Any]]:
        """Parse Git log output into commit records."""
        raise NotImplementedError

    def _update_commit_metrics(self, commit: dict[str, Any], metrics: dict[str, Any]) -> None:
        """Add one commit to repository metrics."""
        raise NotImplementedError

    def _finalize_repo_metrics(self, metrics: dict[str, Any], repo_name: str) -> None:
        """Finalize collected repository metrics."""
        raise NotImplementedError
