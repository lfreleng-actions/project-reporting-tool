# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Gerrit API Client

Client for interacting with Gerrit API to fetch project information
and repository metadata.

Extracted from generate_reports.py as part of Phase 2 refactoring.
"""

import logging
from urllib.parse import urlparse

from .client import GerritAPIClient
from .discovery import GerritAPIDiscovery
from .errors import GerritAPIError, GerritConnectionError


class GerritURLBuilder:
    """
    Centralized utility for constructing Gerrit Git repository URLs.

    This class provides a single source of truth for Gerrit URL construction,
    ensuring consistent handling of different Gerrit server configurations.

    Different Gerrit servers use different URL patterns:
    - ONAP, OpenDaylight: https://gerrit.example.org/r/{repo}
    - LF Broadband: https://gerrit.example.org/{repo}
    - Linux Foundation: https://gerrit.linuxfoundation.org/infra/{repo}

    This class uses the discovered API base URL to derive the correct Git URL pattern,
    avoiding hardcoded paths that break across different Gerrit installations.

    Usage:
        # From a GerritAPIClient instance
        builder = GerritURLBuilder.from_client(gerrit_client)
        git_url = builder.get_repo_url("ci-management")

        # From a known base URL
        builder = GerritURLBuilder("gerrit.example.org", "/r")
        git_url = builder.get_repo_url("my-project")

        # Auto-discover (standalone)
        builder = GerritURLBuilder.discover("gerrit.lfbroadband.org")
        git_url = builder.get_repo_url("ci-management")
    """

    def __init__(self, host: str, path_prefix: str = ""):
        """
        Initialize the URL builder.

        Args:
            host: Gerrit server hostname
            path_prefix: URL path prefix (e.g., "/r", "/gerrit", "")
        """
        self.host = host
        self.path_prefix = path_prefix.rstrip("/") if path_prefix else ""
        self._logger = logging.getLogger(__name__)

    @classmethod
    def from_client(cls, client: "GerritAPIClient") -> "GerritURLBuilder":
        """
        Create a URL builder from an existing GerritAPIClient.

        The client's discovered base_url is used to extract the correct path prefix.

        Args:
            client: An initialized GerritAPIClient

        Returns:
            GerritURLBuilder configured with the client's settings
        """
        parsed = urlparse(client.base_url)
        host = client.host
        path_prefix = parsed.path.rstrip("/") if parsed.path else ""
        return cls(host, path_prefix)

    @classmethod
    def from_base_url(cls, base_url: str) -> "GerritURLBuilder":
        """
        Create a URL builder from a base URL string.

        Args:
            base_url: Full base URL including scheme, host, and optional
                path prefix (for example, a Gerrit server root with a "/r"
                prefix)

        Returns:
            GerritURLBuilder configured from the URL
        """
        parsed = urlparse(base_url)
        host = parsed.netloc
        path_prefix = parsed.path.rstrip("/") if parsed.path else ""
        return cls(host, path_prefix)

    @classmethod
    def discover(cls, host: str, timeout: float = 30.0) -> "GerritURLBuilder":
        """
        Create a URL builder by discovering the correct path prefix.

        Uses GerritAPIDiscovery to find the working API endpoint,
        then extracts the path prefix.

        Args:
            host: Gerrit server hostname
            timeout: Discovery timeout in seconds

        Returns:
            GerritURLBuilder configured with discovered settings

        Raises:
            GerritAPIError: If discovery fails
        """
        with GerritAPIDiscovery(timeout) as discovery:
            base_url = discovery.discover_base_url(host)
            return cls.from_base_url(base_url)

    def get_repo_url(self, repo_name: str, scheme: str = "https") -> str:
        """
        Get the Git URL for a repository.

        Args:
            repo_name: Repository name (e.g., "ci-management", "aai/babel")
            scheme: URL scheme (default: "https")

        Returns:
            Full Git URL for the repository
        """
        if self.path_prefix:
            return f"{scheme}://{self.host}{self.path_prefix}/{repo_name}"
        else:
            return f"{scheme}://{self.host}/{repo_name}"

    def get_browse_url(self, repo_name: str, scheme: str = "https") -> str:
        """
        Get the web browse URL for a repository.

        This is typically the same as the Git URL for Gerrit servers.

        Args:
            repo_name: Repository name
            scheme: URL scheme (default: "https")

        Returns:
            Web URL for browsing the repository
        """
        return self.get_repo_url(repo_name, scheme)

    @property
    def base_url(self) -> str:
        """Get the base URL (without trailing slash)."""
        if self.path_prefix:
            # aislop-ignore-next-line hardcoded-url -- scheme prefix on dynamic host, not a fixed endpoint
            return f"https://{self.host}{self.path_prefix}"
        else:
            # aislop-ignore-next-line hardcoded-url -- scheme prefix on dynamic host, not a fixed endpoint
            return f"https://{self.host}"

    def __repr__(self) -> str:
        return f"GerritURLBuilder(host={self.host!r}, path_prefix={self.path_prefix!r})"


__all__ = [
    "GerritAPIClient",
    "GerritAPIDiscovery",
    "GerritAPIError",
    "GerritConnectionError",
    "GerritURLBuilder",
]
