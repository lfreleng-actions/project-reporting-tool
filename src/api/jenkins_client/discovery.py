# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Jenkins API endpoint discovery.

Probes a Jenkins host for the path prefix under which its REST API is
served, including the optional plain-HTTP fallback for servers with
untrusted TLS certificates.
"""

from typing import Any

import httpx

from ..base_client import BaseAPIClient


class JenkinsDiscoveryMixin(BaseAPIClient):
    """API base-path discovery and protocol fallback for Jenkins servers."""

    # Assigned by JenkinsAPIClient.__init__; declared here for type checking.
    host: str
    base_url: str
    api_base_path: str | None
    allow_http_fallback: bool
    client: httpx.Client

    def _probe_api_patterns(
        self, api_patterns: list[str], *, via_http: bool = False
    ) -> tuple[bool, bool]:
        """Try each API pattern against the current base URL.

        Records the first pattern that returns a valid jobs listing on
        ``self.api_base_path``.

        Returns:
            Tuple of ``(found, ssl_error_occurred)`` where ``found`` is True
            when a working pattern was recorded, and ``ssl_error_occurred``
            indicates whether any attempt failed with a TLS/certificate error.
        """
        ssl_error_occurred = False
        for pattern in api_patterns:
            test_url = f"{self.base_url}{pattern}?tree=jobs[name]"
            self.logger.debug(f"Testing Jenkins API path: {test_url}")

            try:
                response = self.client.get(test_url)
            except httpx.ConnectError as e:
                error_str = str(e).lower()
                if "ssl" in error_str or "certificate" in error_str:
                    ssl_error_occurred = True
                    self.logger.debug(f"SSL error testing {pattern}: {e}")
                else:
                    self.logger.debug(f"Connection error testing {pattern}: {e}")
                continue
            except Exception as e:
                self.logger.debug(f"Error testing {pattern}: {e}")
                continue

            if response.status_code != 200:
                self.logger.debug(f"HTTP {response.status_code} for {pattern}")
                continue

            if self.stats:
                self.stats.record_success("jenkins")

            try:
                data: dict[str, Any] = response.json()
            except Exception as e:
                self.logger.debug(f"Invalid JSON response from {pattern}: {e}")
                continue

            if "jobs" in data and isinstance(data["jobs"], list):
                self.api_base_path = pattern
                job_count = len(data["jobs"])
                if via_http:
                    self.logger.info(
                        f"✅ HTTP fallback successful! Found working Jenkins API path: "
                        f"{pattern} ({job_count} jobs)"
                    )
                else:
                    self.logger.info(
                        f"Found working Jenkins API path: {pattern} ({job_count} jobs)"
                    )
                return True, ssl_error_occurred

        return False, ssl_error_occurred

    def _switch_to_http_fallback(self) -> None:
        """Reconfigure the client to talk to the host over plain HTTP.

        Preserves Jenkins authentication credentials when they are present in
        the environment.
        """
        self.logger.warning(f"HTTPS certificate validation failure [{self.host}]")
        self.logger.warning(
            "Project configuration permits HTTP fallback (allow_http_fallback=True)"
        )

        # Switch to HTTP (preserve authentication if present)
        # aislop-ignore-next-line hardcoded-url -- scheme prefix on dynamic host, not a fixed endpoint
        self.base_url = f"http://{self.host}"
        import os

        jenkins_user = os.environ.get("JENKINS_USER")
        jenkins_token = os.environ.get("JENKINS_API_TOKEN")

        # Close the existing HTTPS client before replacing it to avoid leaking
        # open connections during API base-path discovery.
        self.client.close()

        if jenkins_user and jenkins_token:
            self.client = httpx.Client(timeout=self.timeout, auth=(jenkins_user, jenkins_token))
        else:
            self.client = httpx.Client(timeout=self.timeout)

    def _discover_api_base_path(self):
        """
        Discover the correct API base path for this Jenkins server.

        Jenkins instances can be deployed with different path prefixes.
        This method tests common patterns to find the working API endpoint.
        If HTTPS fails and allow_http_fallback is enabled, will try HTTP.
        """
        # Common Jenkins API path patterns to try
        api_patterns = [
            "/api/json",
            "/releng/api/json",
            "/jenkins/api/json",
            "/ci/api/json",
            "/build/api/json",
        ]

        self.logger.info(f"Discovering Jenkins API base path for {self.host}")

        # Try HTTPS first
        found, ssl_error_occurred = self._probe_api_patterns(api_patterns)
        if found:
            return

        # If HTTPS failed with SSL error and fallback is allowed, try HTTP
        if ssl_error_occurred and self.allow_http_fallback:
            self._switch_to_http_fallback()
            found, _ = self._probe_api_patterns(api_patterns, via_http=True)
            if found:
                return

        # If no pattern worked, default to standard path
        self.api_base_path = "/api/json"
        if ssl_error_occurred and not self.allow_http_fallback:
            self.logger.error(
                f"❌ Could not connect to Jenkins at {self.host} due to SSL errors. "
                f"Consider setting 'allow_http_fallback: true' in Jenkins configuration "
                f"if this is a trusted internal server."
            )
        else:
            self.logger.warning(
                f"Could not discover Jenkins API path for {self.host}, using default: {self.api_base_path}"
            )
