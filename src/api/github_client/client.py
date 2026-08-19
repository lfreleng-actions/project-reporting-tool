# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
GitHub API client construction.

Owns the authenticated ``httpx`` session and composes the workflow and
status behaviour mixins into the public ``GitHubAPIClient``.
"""

import logging
from typing import Any


try:
    import httpx
except ImportError:
    from cli.errors import ConfigurationError

    raise ConfigurationError(
        "httpx package is required for GitHub API client",
        suggestion="Install with: pip install httpx",
    ) from None

from ..base_client import (
    BaseAPIClient,
)
from .workflows import GitHubWorkflowsMixin


class GitHubAPIClient(GitHubWorkflowsMixin, BaseAPIClient):
    """
    Client for interacting with GitHub API to fetch workflow run status.

    Provides methods to:
    - List workflows for a repository
    - Get workflow run status
    - Get comprehensive workflow status summaries

    Uses standardized response envelope pattern for consistent error handling.
    """

    def __init__(
        self,
        token: str,
        timeout: float = 30.0,
        stats: Any | None = None,
        use_envelope: bool = False,
    ):
        """
        Initialize GitHub API client with token.

        Args:
            token: GitHub Personal Access Token
            timeout: Request timeout in seconds
            stats: Statistics tracker object
            use_envelope: If True, use new envelope pattern; if False, use legacy dicts
        """
        super().__init__(timeout=timeout, stats=stats)

        self.token = token
        self.base_url = "https://api.github.com"
        self.use_envelope = use_envelope

        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "repository-reports/1.0.0",
            },
        )

        self.logger = logging.getLogger(__name__)

    def close(self):
        """Close the httpx client and clean up resources."""
        if hasattr(self, "client"):
            self.client.close()
