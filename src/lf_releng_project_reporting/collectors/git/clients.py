# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Gerrit and Jenkins client integration for the Git collector."""

from pathlib import Path
from typing import Any

from .base import _CollectorState


class _ClientIntegrationMixin(_CollectorState):
    """Initialize external clients and resolve Gerrit repository metadata."""

    def _init_gerrit_client(self, gerrit_config: dict[str, Any]) -> None:
        """Initialize the Gerrit API client when Gerrit is enabled.

        Gerrit configuration is mandatory when enabled, so a missing host or a
        client failure is raised rather than swallowed.
        """
        if not gerrit_config.get("enabled", False):
            return

        host = gerrit_config.get("host")
        if not host:
            error_msg = "Gerrit is enabled in configuration but no host is specified"
            self.logger.error(error_msg)
            from lf_releng_project_reporting.exceptions import ConfigurationError

            raise ConfigurationError(error_msg)

        base_url = gerrit_config.get("base_url")
        timeout = gerrit_config.get("timeout", 30.0)
        try:
            self.gerrit_client = self._create_gerrit_client(host, base_url, timeout)
            self.logger.info(f"Initialized Gerrit API client for {host}")
            self._fetch_all_gerrit_projects()
        except Exception as e:
            self.logger.error(f"Failed to initialize Gerrit API client for {host}: {e}")
            # Re-raise to stop execution - Gerrit configuration is mandatory when enabled
            raise

    def _resolve_jjb_config(self, jenkins_config: dict[str, Any]) -> Any:
        """Resolve JJB attribution config from Jenkins or top-level configuration."""
        jjb_config = jenkins_config.get("jjb_attribution")
        if not jjb_config:
            # Check top-level config for jjb_attribution (or legacy ci_management)
            jjb_config = self.config.get("jjb_attribution") or self.config.get("ci_management")
        return jjb_config

    def _init_jenkins_client(
        self,
        jenkins_host: str | None,
        jenkins_config: dict[str, Any],
        gerrit_config: dict[str, Any],
    ) -> None:
        """Initialize the Jenkins API client from the environment or config.

        The ``JENKINS_HOST`` environment variable takes precedence over the
        config-file host. Client initialization failures are logged and
        re-raised. A config-enabled Jenkins with no host configured is logged
        as an error and skipped (no client is created, no exception raised),
        preserving the original behavior.
        """
        if jenkins_host:
            # Environment variable takes precedence - enables Jenkins integration
            try:
                self.jenkins_client = self._create_jenkins_client(
                    jenkins_host, jenkins_config, gerrit_config
                )
                self.logger.info(
                    f"Initialized Jenkins API client for {jenkins_host} (from environment)"
                )
                # Test the connection and cache all jobs upfront
                self._initialize_jenkins_cache()
            except Exception as e:
                self.logger.error(
                    f"Failed to initialize Jenkins API client for {jenkins_host}: {e}"
                )
                self.jenkins_client = None
                # Re-raise to stop execution - Jenkins is mandatory when JENKINS_HOST is set
                raise
            return

        if not jenkins_config.get("enabled", False):
            return

        # Fallback to config file (for backward compatibility)
        host = jenkins_config.get("host")
        if not host:
            self.logger.error("Jenkins enabled but no host configured")
            return

        try:
            self.jenkins_client = self._create_jenkins_client(host, jenkins_config, gerrit_config)
            self.logger.info(f"Initialized Jenkins API client for {host} (from config)")
            self._initialize_jenkins_cache()
        except Exception as e:
            self.logger.error(f"Failed to initialize Jenkins API client for {host}: {e}")
            # Re-raise to stop execution - Jenkins configuration is mandatory when enabled
            raise

    def _initialize_jenkins_cache(self):
        """Initialize Jenkins jobs cache at startup for better performance."""
        if not self.jenkins_client or self._jenkins_initialized:
            return

        try:
            self.logger.info("Caching all Jenkins jobs for efficient allocation...")
            all_jobs = self.jenkins_client.get_all_jobs()
            self.jenkins_allocation_context.set_all_jobs(all_jobs)
            job_count = len(all_jobs.get("jobs", []))

            # CRITICAL: If Jenkins is configured but returns 0 jobs, this is an ERROR
            if job_count == 0:
                jenkins_host = self.jenkins_client.host
                import os

                has_auth = bool(
                    os.environ.get("JENKINS_USER") and os.environ.get("JENKINS_API_TOKEN")
                )
                auth_hint = (
                    (
                        "\n  NOTE: No Jenkins authentication configured. If this server requires authentication,\n"
                        "        set JENKINS_USER and JENKINS_API_TOKEN environment variables."
                    )
                    if not has_auth
                    else ""
                )

                error_msg = (
                    f"FATAL: Jenkins server '{jenkins_host}' is configured and accessible, "
                    f"but returned 0 jobs. This indicates either:\n"
                    f"  1. The Jenkins server has no jobs configured (unlikely)\n"
                    f"  2. Authentication is required to view jobs (set JENKINS_USER and JENKINS_API_TOKEN)\n"
                    f"  3. The API endpoint is returning incomplete data\n"
                    f"Please verify Jenkins configuration and permissions.{auth_hint}"
                )
                self.logger.error(error_msg)
                # Raise exception to stop execution immediately
                from lf_releng_project_reporting.exceptions import JenkinsAPIError

                raise JenkinsAPIError(error_msg)

            self.logger.info(f"Jenkins cache initialized: {job_count} total jobs available")
            self._jenkins_initialized = True
        except Exception as e:
            self.logger.error(f"Failed to initialize Jenkins cache: {e}")
            self._jenkins_initialized = False
            # Re-raise to stop execution
            raise

    def _fetch_all_gerrit_projects(self) -> None:
        """Fetch all Gerrit project data upfront and cache it."""
        if not self.gerrit_client:
            return

        try:
            all_projects = self.gerrit_client.get_all_projects()

            if all_projects:
                self.gerrit_projects_cache = all_projects
                self.logger.info(f"Cached {len(all_projects)} projects from Gerrit")
            else:
                # CRITICAL: If Gerrit is configured but returns 0 projects, this is an ERROR
                gerrit_host = self.gerrit_client.host
                error_msg = (
                    f"FATAL: Gerrit server '{gerrit_host}' is configured and accessible, "
                    f"but returned 0 projects. This indicates either:\n"
                    f"  1. The Gerrit server has no projects configured (unlikely)\n"
                    f"  2. Authentication/permissions prevent viewing projects\n"
                    f"  3. The API endpoint is returning incomplete data\n"
                    f"Please verify Gerrit configuration and permissions."
                )
                self.logger.error(error_msg)
                from lf_releng_project_reporting.exceptions import GerritAPIError

                raise GerritAPIError(error_msg)

        except Exception as e:
            self.logger.error(f"Failed to fetch Gerrit projects: {e}")
            # Re-raise to stop execution
            raise

    def _extract_gerrit_project(self, repo_path: Path) -> str:
        """
        Extract the hierarchical Gerrit project name from the repository path.

        For paths containing hostname patterns like:
        /path/to/gerrit.o-ran-sc.org/aiml-fw/aihp/tps/kserve-adapter
        returns 'aiml-fw/aihp/tps/kserve-adapter' (the full Gerrit project hierarchy).

        Falls back to repository folder name if no hierarchical structure is detected.
        """
        try:
            path_parts = repo_path.parts

            # Strategy 1: Look for gerrit-repos-* directory pattern
            for i, part in enumerate(path_parts):
                if part.startswith("gerrit-repos-"):
                    if i < len(path_parts) - 1:
                        project_path_parts = path_parts[i + 1 :]
                        gerrit_project = "/".join(project_path_parts)
                        self.logger.debug(
                            f"Extracted Gerrit project from gerrit-repos pattern: {gerrit_project}"
                        )
                        return gerrit_project
                    break

            # Strategy 2: Look for hostname pattern (gerrit.domain.tld)
            for i, part in enumerate(path_parts):
                if "." in part and any(tld in part for tld in [".org", ".com", ".net", ".io"]):
                    if i < len(path_parts) - 1:
                        project_path_parts = path_parts[i + 1 :]
                        gerrit_project = "/".join(project_path_parts)
                        self.logger.debug(
                            f"Extracted Gerrit project from hostname pattern: {gerrit_project}"
                        )
                        return gerrit_project
                    break

            # Strategy 3: Look for organization root directories and extract relative path
            # Common organization names in paths
            org_names = ["onap", "o-ran-sc", "opendaylight", "fdio", "opnfv", "agl"]

            for i, part in enumerate(path_parts):
                if part.lower() in org_names:
                    # Found organization root, extract everything after it
                    if i < len(path_parts) - 1:
                        project_path_parts = path_parts[i + 1 :]
                        gerrit_project = "/".join(project_path_parts)
                        self.logger.debug(
                            f"Extracted Gerrit project from organization root '{part}': {gerrit_project}"
                        )
                        return gerrit_project
                    break

            # Strategy 4: Check if any parent directories suggest hierarchical structure
            # Look for common Gerrit project patterns (2+ levels deep)
            # Filter out root directory from path_parts
            meaningful_parts = [part for part in path_parts if part and part != "/"]
            if len(meaningful_parts) >= 3:
                # Take last 2-4 path components as potential project hierarchy
                for depth in range(4, 1, -1):  # Try 4, 3, 2 components
                    if len(meaningful_parts) >= depth:
                        "/".join(meaningful_parts[-depth:])
                        # Validate it looks_project

            # Fallback: use just the repository folder name
            self.logger.debug(
                f"No hierarchical structure detected, using folder name: {repo_path.name}"
            )
            return repo_path.name

        except Exception as e:
            self.logger.warning(f"Error extracting Gerrit project from {repo_path}: {e}")
            return repo_path.name

    def _extract_gerrit_path_prefix(self) -> str:
        """
        Extract the URL path prefix from the Gerrit API client's base URL.

        Returns:
            URL path prefix (e.g., "/r", "/gerrit", "") or empty string if no client
        """
        if not self.gerrit_client:
            return ""

        try:
            from urllib.parse import urlparse

            parsed = urlparse(self.gerrit_client.base_url)
            path = parsed.path.rstrip("/")
            return path if path else ""
        except Exception as e:
            self.logger.warning(f"Error extracting Gerrit path prefix: {e}")
            return ""

    def _derive_gerrit_url(self, repo_path: Path) -> str:
        """
        Derive the full Gerrit URL from the repository path.

        Extracts hostname and project path to create URL like:
        gerrit.o-ran-sc.org/aiml-fw/aihp/tps/kserve-adapter
        """
        try:
            path_parts = repo_path.parts

            # Look for hostname pattern and construct URL-style path
            for i, part in enumerate(path_parts):
                if "." in part and any(tld in part for tld in [".org", ".com", ".net", ".io"]):
                    hostname = part
                    if i < len(path_parts) - 1:
                        project_parts = path_parts[i + 1 :]
                        gerrit_url = f"{hostname}/{'/'.join(project_parts)}"
                        self.logger.debug(f"Derived Gerrit URL: {gerrit_url}")
                        return gerrit_url
                    else:
                        return hostname

            # Fallback: construct generic URL with repo name only (avoid recursive issues)
            repo_name = repo_path.name
            fallback_url = f"unknown-gerrit-host/{repo_name}"
            self.logger.warning(f"Could not detect Gerrit hostname, using fallback: {fallback_url}")
            return fallback_url

        except Exception as e:
            self.logger.warning(f"Error deriving Gerrit URL from {repo_path}: {e}")
            return str(repo_path)

    def _extract_gerrit_host(self, repo_path: Path) -> str:
        """Extract the Gerrit hostname from the repository path."""
        try:
            path_parts = repo_path.parts
            for part in path_parts:
                if "." in part and any(tld in part for tld in [".org", ".com", ".net", ".io"]):
                    return part
            return "unknown-gerrit-host"
        except Exception as e:
            self.logger.warning(f"Error extracting Gerrit host from {repo_path}: {e}")
            return "unknown-gerrit-host"
