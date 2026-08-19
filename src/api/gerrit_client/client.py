# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Gerrit REST API client.

Project metadata queries against a Gerrit Code Review server, including
handling of Gerrit's XSSI magic prefix on JSON responses.
"""

import json
import logging
from typing import Any

import httpx

from ..base_client import BaseAPIClient
from .discovery import GerritAPIDiscovery


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
