# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Git repository data collection interface."""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from api.gerrit_client import GerritAPIClient
from api.jenkins_client import JenkinsAPIClient
from concurrency.jenkins_allocation import JenkinsAllocationContext

from .cache import _CacheMixin
from .clients import _ClientIntegrationMixin
from .commands import (
    parse_git_iso_date as parse_git_iso_date,
)
from .commands import (
    safe_git_command as safe_git_command,
)
from .commits import _CommitMetricsMixin
from .jenkins import _JenkinsAllocationMixin
from .repository import _RepositoryMetricsMixin


class GitDataCollector(
    _ClientIntegrationMixin,
    _RepositoryMetricsMixin,
    _JenkinsAllocationMixin,
    _CommitMetricsMixin,
    _CacheMixin,
):
    """Handles Git repository analysis and metric collection.

    Thread Safety:
        This class is designed for concurrent use via ThreadPoolExecutor.
        Jenkins job allocation is protected by instance-level JenkinsAllocationContext.
    """

    def __init__(
        self,
        config: dict[str, Any],
        time_windows: dict[str, dict[str, Any]],
        logger: logging.Logger,
        jenkins_allocation_context: JenkinsAllocationContext | None = None,
        api_stats: Any | None = None,
    ) -> None:
        self.config = config
        self.time_windows = time_windows
        self.logger = logger
        self.api_stats = api_stats
        self._domain_config: dict[str, Any] | None = None
        performance_config = config.get("performance", {})
        self.cache_enabled = performance_config.get("cache", False)
        self.cache_dir = None
        self.repos_path: Path | None = None  # Will be set later for relative path calculation
        if self.cache_enabled:
            self.cache_dir = Path(tempfile.gettempdir()) / "repo_reporting_cache"
            self.cache_dir.mkdir(exist_ok=True)

        # Initialize Gerrit API client if configured
        self.gerrit_client: GerritAPIClient | None = None
        self.gerrit_projects_cache: dict[
            str, dict[str, Any]
        ] = {}  # Cache for all Gerrit project data
        gerrit_config = self.config.get("gerrit", {})

        # Initialize Jenkins API client if configured
        self.jenkins_client: JenkinsAPIClient | None = None
        # Jenkins allocation context for thread-safe job tracking (Phase 7)
        # If not provided, create a new instance (each collector gets its own context)
        self.jenkins_allocation_context = jenkins_allocation_context or JenkinsAllocationContext()
        self._jenkins_initialized = False

        jenkins_host = os.environ.get("JENKINS_HOST")
        jenkins_config = self.config.get("jenkins", {})

        self._init_gerrit_client(gerrit_config)
        self._init_jenkins_client(jenkins_host, jenkins_config, gerrit_config)

    def _create_gerrit_client(
        self, host: str, base_url: str | None, timeout: float
    ) -> GerritAPIClient:
        """Build a Gerrit API client through the public package patch point."""
        return GerritAPIClient(host, base_url, timeout, stats=self.api_stats)

    def _create_jenkins_client(
        self, host: str, jenkins_config: dict[str, Any], gerrit_config: dict[str, Any]
    ) -> JenkinsAPIClient:
        """Build a JenkinsAPIClient for the given host from configuration."""
        timeout = jenkins_config.get("timeout", 30.0)
        jjb_config = self._resolve_jjb_config(jenkins_config)
        gerrit_host = gerrit_config.get("host") if gerrit_config.get("enabled", False) else None
        allow_http_fallback = jenkins_config.get("allow_http_fallback", False)
        return JenkinsAPIClient(
            host,
            timeout,
            stats=self.api_stats,
            jjb_config=jjb_config,
            gerrit_host=gerrit_host,
            allow_http_fallback=allow_http_fallback,
        )
