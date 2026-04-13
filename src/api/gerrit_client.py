# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Gerrit API Client

Client for interacting with Gerrit API to fetch project information
and repository metadata.

Extracted from generate_reports.py as part of Phase 2 refactoring.
"""

import json
import logging
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from .base_client import BaseAPIClient


class GerritAPIError(Exception):
    """Base exception for Gerrit API errors."""

    pass


class GerritConnectionError(Exception):
    """Raised when connection to Gerrit server fails."""

    pass


class GerritAPIDiscovery:
    """
    Discovers the correct Gerrit API base URL for a given host.

    Gerrit instances can be deployed with different path prefixes.
    This class tests common patterns to find the working API endpoint.
    """

    # Common Gerrit API path patterns to test
    COMMON_PATHS = [
        "",  # Direct: https://host/
        "/r",  # Standard: https://host/r/
        "/gerrit",  # OpenDaylight style: https://host/gerrit/
        "/infra",  # Linux Foundation style: https://host/infra/
        "/a",  # Authenticated API: https://host/a/
    ]

    def __init__(self, timeout: float = 30.0):
        """
        Initialize discovery client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.client = httpx.Client(
            timeout=httpx.Timeout(timeout, connect=10.0),
            follow_redirects=True,
            headers={
                "User-Agent": "repository-reports/1.0.0",
                "Accept": "application/json",
            },
        )

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, *args):
        """Exit context manager and cleanup."""
        self.close()

    def close(self):
        """Close HTTP client."""
        if hasattr(self, "client"):
            self.client.close()

    def discover_base_url(self, host: str) -> str:
        """
        Discover the correct API base URL for a Gerrit host.

        Tries to follow redirects first, then tests common path patterns.

        Args:
            host: Gerrit hostname

        Returns:
            Working API base URL

        Raises:
            GerritAPIError: If no working endpoint is found
        """
        logging.debug(f"Starting API discovery for host: {host}")

        # First, try to follow redirects from the base URL
        redirect_path = self._discover_via_redirect(host)
        if redirect_path:
            test_paths = [redirect_path] + [p for p in self.COMMON_PATHS if p != redirect_path]
        else:
            test_paths = self.COMMON_PATHS

        # Test each potential path
        for path in test_paths:
            base_url = f"https://{host}{path}"
            logging.debug(f"Testing API endpoint: {base_url}")

            if self._test_projects_api(base_url):
                logging.debug(f"Discovered working API base URL: {base_url}")
                return base_url

        # If all paths fail, raise an error
        raise GerritAPIError(
            f"Could not discover Gerrit API endpoint for {host}. Tested paths: {test_paths}"
        )

    def _discover_via_redirect(self, host: str) -> str | None:
        """
        Attempt to discover the API path by following redirects.

        Args:
            host: Gerrit hostname

        Returns:
            Redirect path if found, None otherwise
        """
        try:
            response = self.client.get(f"https://{host}", follow_redirects=False)
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if location:
                    parsed = urlparse(location)
                    if parsed.netloc == host or not parsed.netloc:
                        path = parsed.path.rstrip("/")
                        if path and path != "/":
                            return str(path)
        except Exception as e:
            logging.debug(f"Error checking redirects for {host}: {e}")
        return None

    def _test_projects_api(self, base_url: str) -> bool:
        """
        Test if the projects API is available at the given base URL.

        Args:
            base_url: Base URL to test

        Returns:
            True if projects API responds correctly
        """
        try:
            projects_url = urljoin(base_url.rstrip("/") + "/", "projects/?d")
            response = self.client.get(projects_url)

            if response.status_code == 200:
                return self._validate_projects_response(response.text)
            return False
        except Exception as e:
            logging.debug(f"Error testing projects API at {base_url}: {e}")
            return False

    def _validate_projects_response(self, response_text: str) -> bool:
        """
        Validate that the response looks like a valid Gerrit projects API response.

        Args:
            response_text: Raw response text

        Returns:
            True if response is valid Gerrit projects data
        """
        try:
            # Strip Gerrit's security prefix
            json_text = response_text[4:] if response_text.startswith(")]}'") else response_text

            data = json.loads(json_text)
            return isinstance(data, dict)
        except Exception:
            return False


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
            base_url: Full base URL (e.g., "https://gerrit.onap.org/r")

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
            return f"https://{self.host}{self.path_prefix}"
        else:
            return f"https://{self.host}"

    def __repr__(self) -> str:
        return f"GerritURLBuilder(host={self.host!r}, path_prefix={self.path_prefix!r})"


class GerritAPIClient(BaseAPIClient):
    """
    Client for interacting with Gerrit REST API.

    Provides methods to query project information from Gerrit Code Review.
    Handles automatic API endpoint discovery and Gerrit's JSON response format.

    Features:
    - Auto-discovery of API base URL
    - Gerrit magic prefix handling (")]}'")
    - URL encoding for project names with slashes
    - Error tracking and statistics
    """

    def __init__(
        self,
        host: str,
        base_url: str | None = None,
        timeout: float = 30.0,
        stats: Any | None = None,
    ):
        """
        Initialize Gerrit API client.

        Args:
            host: Gerrit hostname
            base_url: Optional base URL (auto-discovered if not provided)
            timeout: Request timeout in seconds
            stats: Statistics tracker object
        """
        super().__init__(timeout=timeout, stats=stats)
        self.host = host
        self.logger = logging.getLogger(__name__)

        if base_url:
            self.base_url = base_url
        else:
            # Auto-discover the base URL
            with GerritAPIDiscovery(timeout) as discovery:
                self.base_url = discovery.discover_base_url(host)

        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout, connect=10.0),
            follow_redirects=True,
            headers={
                "User-Agent": "repository-reports/1.0.0",
                "Accept": "application/json",
            },
        )

    def __enter__(self):
        """Enter context manager."""
        super().__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and cleanup."""
        self.close()
        return super().__exit__(exc_type, exc_val, exc_tb)

    def close(self):
        """Close HTTP client."""
        if hasattr(self, "client"):
            self.client.close()

    def get_project_info(self, project_name: str) -> dict[str, Any] | None:
        """
        Get detailed information about a specific project.

        Args:
            project_name: Name of the Gerrit project (can contain slashes)

        Returns:
            Project information dict, or None if not found

        Example:
            >>> client = GerritAPIClient("gerrit.example.com")
            >>> info = client.get_project_info("foo/bar")
            >>> if info:
            ...     print(f"Project: {info['name']}")
        """
        try:
            # URL-encode the project name and use the projects API with detailed information
            encoded_name = project_name.replace("/", "%2F")
            url = f"/projects/{encoded_name}?d"

            response = self.client.get(url)

            if response.status_code == 200:
                if self.stats:
                    self.stats.record_success("gerrit")
                result = self._parse_json_response(response.text)
                return result
            elif response.status_code == 404:
                if self.stats:
                    self.stats.record_error("gerrit", 404)
                self.logger.debug(f"Project not found in Gerrit: {project_name}")
                return None
            else:
                if self.stats:
                    self.stats.record_error("gerrit", response.status_code)
                self.logger.warning(
                    f"❌ Error: Gerrit API query returned error code: {response.status_code} "
                    f"for project {project_name}"
                )
                return None

        except Exception as e:
            if self.stats:
                self.stats.record_exception("gerrit")
            self.logger.error(f"❌ Error: Gerrit API query exception for {project_name}: {e}")
            return None

    def get_all_projects(self) -> dict[str, Any]:
        """
        Get all projects with detailed information.

        Returns:
            Dictionary mapping project names to project information.
            Returns empty dict on error.

        Example:
            >>> client = GerritAPIClient("gerrit.example.com")
            >>> projects = client.get_all_projects()
            >>> print(f"Found {len(projects)} projects")
        """
        try:
            response = self.client.get("/projects/?d")

            if response.status_code == 200:
                if self.stats:
                    self.stats.record_success("gerrit")
                result = self._parse_json_response(response.text)
                self.logger.info(f"Fetched {len(result)} projects from Gerrit")
                return result if isinstance(result, dict) else {}
            else:
                if self.stats:
                    self.stats.record_error("gerrit", response.status_code)
                self.logger.error(
                    f"❌ Error: Gerrit API query returned error code: {response.status_code}"
                )
                return {}

        except Exception as e:
            if self.stats:
                self.stats.record_exception("gerrit")
            self.logger.error(f"❌ Error: Gerrit API query exception: {e}")
            return {}

    def _parse_json_response(self, response_text: str) -> dict[str, Any]:
        """
        Parse Gerrit JSON response, handling magic prefix.

        Gerrit prepends ")]}" to JSON responses as a security measure
        to prevent XSSI attacks. This method strips it before parsing.

        Args:
            response_text: Raw response text from Gerrit API

        Returns:
            Parsed JSON as dictionary
        """
        # Remove Gerrit's magic prefix if present
        if response_text.startswith(")]}'"):
            clean_text = response_text[4:].lstrip()
        else:
            clean_text = response_text

        try:
            result = json.loads(clean_text)
            return result if isinstance(result, dict) else {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON response: {e}")
            return {}
