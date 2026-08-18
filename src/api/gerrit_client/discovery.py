# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Gerrit API endpoint discovery.

Probes a Gerrit host for the path prefix under which its REST API is
served, so that neither the client nor the URL builder needs hardcoded
per-deployment paths.
"""

import json
import logging
from urllib.parse import urljoin, urlparse

import httpx

from .errors import GerritAPIError


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
            # aislop-ignore-next-line hardcoded-url -- scheme prefix on dynamic host, not a fixed endpoint
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
            # aislop-ignore-next-line hardcoded-url -- scheme prefix on dynamic host, not a fixed endpoint
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
