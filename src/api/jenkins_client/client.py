# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Jenkins API client construction.

Owns the ``httpx`` session, the discovered API base path and the JJB
Attribution state, and composes the per-surface behaviour mixins into the
public ``JenkinsAPIClient``.
"""

import logging
from typing import Any

import httpx

from ..base_client import BaseAPIClient
from .builds import JenkinsBuildsMixin
from .catalog import JenkinsCatalogMixin
from .discovery import JenkinsDiscoveryMixin
from .jjb import JenkinsJJBMixin
from .jobs import JenkinsJobsMixin
from .matching import JenkinsMatchingMixin


class JenkinsAPIClient(
    JenkinsJobsMixin,
    JenkinsJJBMixin,
    JenkinsMatchingMixin,
    JenkinsCatalogMixin,
    JenkinsBuildsMixin,
    JenkinsDiscoveryMixin,
    BaseAPIClient,
):
    """
    Client for interacting with Jenkins REST API.

    Provides methods to query job information from Jenkins CI/CD servers.
    Handles automatic API endpoint discovery, job matching, and caching.

    Features:
    - Auto-discovery of API base path
    - JJB Attribution for authoritative job-to-project mapping
    - Job-to-project matching with scoring algorithm (fallback)
    - Caching of all jobs data for performance
    - Build status and history retrieval
    - Duplicate job allocation prevention
    """

    def __init__(
        self,
        host: str,
        timeout: float = 30.0,
        stats: Any | None = None,
        jjb_config: dict[str, Any] | None = None,
        gerrit_host: str | None = None,
        allow_http_fallback: bool = False,
    ):
        """
        Initialize Jenkins API client.

        Args:
            host: Jenkins hostname
            timeout: Request timeout in seconds
            stats: Statistics tracker object
            jjb_config: Optional JJB Attribution configuration with keys:
                - url: Git URL for ci-management repository (auto-derived from gerrit_host if not provided)
                - branch: Branch to use (default: master)
                - cache_dir: Directory for caching repos (default: /tmp)
                - enabled: Enable JJB Attribution (default: True if config provided)
            gerrit_host: Gerrit hostname (used to auto-derive ci-management URL)
            allow_http_fallback: If True, fallback to HTTP if HTTPS fails due to SSL errors

        Environment Variables:
            JENKINS_USER: Username for Jenkins authentication (optional)
            JENKINS_API_TOKEN: API token for Jenkins authentication (optional)
        """
        super().__init__(timeout=timeout, stats=stats)
        self.host = host
        self.timeout = timeout
        self.allow_http_fallback = allow_http_fallback
        # aislop-ignore-next-line hardcoded-url -- scheme prefix on dynamic host, not a fixed endpoint
        self.base_url = f"https://{host}"
        self.api_base_path: str | None = None  # Will be discovered
        self._jobs_cache: dict[str, Any] = {}  # Cache for all jobs data
        self._cache_populated = False
        self.stats = stats
        self.logger = logging.getLogger(__name__)
        self.gerrit_host = gerrit_host

        # JJB Attribution integration
        self.jjb_attribution: Any | None = None
        self.jjb_attribution_enabled = False

        if jjb_config and jjb_config.get("enabled", True):
            self._initialize_jjb_attribution(jjb_config, gerrit_host)

        import os

        jenkins_user = os.environ.get("JENKINS_USER")
        jenkins_token = os.environ.get("JENKINS_API_TOKEN")

        if jenkins_user and jenkins_token:
            self.logger.info(f"Jenkins authentication enabled for user: {jenkins_user}")
            self.client = httpx.Client(timeout=timeout, auth=(jenkins_user, jenkins_token))
        else:
            self.logger.debug(
                "No Jenkins authentication configured (JENKINS_USER/JENKINS_API_TOKEN not set)"
            )
            self.client = httpx.Client(timeout=timeout)

        # Discover the correct API base path (and protocol)
        self._discover_api_base_path()

    def close(self):
        """Close the HTTP client."""
        if hasattr(self, "client"):
            self.client.close()
