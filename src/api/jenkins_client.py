# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Jenkins API Client

Client for interacting with Jenkins API to fetch job information
and build status.

Extracted from generate_reports.py as part of Phase 2 refactoring.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from .base_client import BaseAPIClient
from .gerrit_client import GerritAPIError, GerritURLBuilder


# Optional JJB Attribution integration
try:
    from jjb_attribution import JJBAttribution, JJBRepoManager

    JJB_ATTRIBUTION_AVAILABLE = True
except ImportError:
    JJB_ATTRIBUTION_AVAILABLE = False  # pyright: ignore[reportConstantRedefinition]
    JJBAttribution = None
    JJBRepoManager = None


class JenkinsAPIClient(BaseAPIClient):
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

        # Check for Jenkins authentication from environment
        import os

        jenkins_user = os.environ.get("JENKINS_USER")
        jenkins_token = os.environ.get("JENKINS_API_TOKEN")

        # Create httpx client with optional authentication
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

    def _initialize_jjb_attribution(
        self, config: dict[str, Any], gerrit_host: str | None = None
    ) -> None:
        """
        Initialize JJB Attribution for authoritative job allocation.

        Automatically derives ci-management URL from Gerrit host if not explicitly provided.

        Args:
            config: JJB Attribution configuration dictionary
            gerrit_host: Gerrit hostname for auto-deriving ci-management URL
        """
        if not JJB_ATTRIBUTION_AVAILABLE:
            self.logger.warning(
                "JJB Attribution modules not available. Falling back to fuzzy matching."
            )
            return

        try:
            self.logger.debug("Initializing JJB Attribution...")

            # Setup repository manager
            cache_dir = Path(config.get("cache_dir", "/tmp"))
            if JJBRepoManager is None:
                return
            repo_mgr = JJBRepoManager(cache_dir)

            # Get ci-management URL (auto-derive from Gerrit host if not provided)
            ci_mgmt_url = config.get("url")
            if not ci_mgmt_url:
                if gerrit_host:
                    # Use centralized GerritURLBuilder to discover correct URL pattern
                    # This handles different Gerrit configurations (with/without /r/ prefix)
                    try:
                        url_builder = GerritURLBuilder.discover(gerrit_host)
                        ci_mgmt_url = url_builder.get_repo_url("ci-management")
                        self.logger.debug(
                            f"Auto-derived ci-management URL using GerritURLBuilder: {ci_mgmt_url}"
                        )
                    except GerritAPIError as e:
                        self.logger.debug(
                            f"Could not discover Gerrit URL pattern for {gerrit_host}: {e}. "
                            "Falling back to fuzzy matching."
                        )
                        return
                else:
                    self.logger.debug(
                        "ci-management URL not provided and Gerrit host unknown. "
                        "Falling back to fuzzy matching."
                    )
                    return

            branch = config.get("branch", "master")
            ci_mgmt_path, global_jjb_path = repo_mgr.ensure_repos(ci_mgmt_url, branch)

            # Initialize parser
            if JJBAttribution is None:
                return
            self.jjb_attribution = JJBAttribution(ci_mgmt_path, global_jjb_path)
            self.jjb_attribution.load_templates()

            # Get summary
            summary = self.jjb_attribution.get_project_summary()
            self.logger.info(
                f"JJB Attribution enabled: {summary['gerrit_projects']} projects, "
                f"{summary['total_jobs']} jobs from ci-management"
            )
            self.jjb_attribution_enabled = True

        except Exception as e:
            self.logger.warning(
                f"Failed to initialize JJB Attribution: {e}. Falling back to fuzzy matching."
            )
            self.jjb_attribution = None
            self.jjb_attribution_enabled = False

    def close(self):
        """Close the HTTP client."""
        if hasattr(self, "client"):
            self.client.close()

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
        ssl_error_occurred = False
        for pattern in api_patterns:
            try:
                test_url = f"{self.base_url}{pattern}?tree=jobs[name]"
                self.logger.debug(f"Testing Jenkins API path: {test_url}")

                response = self.client.get(test_url)
                if response.status_code == 200:
                    if self.stats:
                        self.stats.record_success("jenkins")
                    try:
                        data: dict[str, Any] = response.json()
                        if "jobs" in data and isinstance(data["jobs"], list):
                            self.api_base_path = pattern
                            job_count = len(data["jobs"])
                            self.logger.info(
                                f"Found working Jenkins API path: {pattern} ({job_count} jobs)"
                            )
                            return
                    except Exception as e:
                        self.logger.debug(f"Invalid JSON response from {pattern}: {e}")
                        continue
                else:
                    self.logger.debug(f"HTTP {response.status_code} for {pattern}")

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

        # If HTTPS failed with SSL error and fallback is allowed, try HTTP
        if ssl_error_occurred and self.allow_http_fallback:
            self.logger.warning(f"HTTPS certificate validation failure [{self.host}]")
            self.logger.warning(
                "Project configuration permits HTTP fallback (allow_http_fallback=True)"
            )

            # Switch to HTTP (preserve authentication if present)
            self.base_url = f"http://{self.host}"
            import os

            jenkins_user = os.environ.get("JENKINS_USER")
            jenkins_token = os.environ.get("JENKINS_API_TOKEN")

            if jenkins_user and jenkins_token:
                self.client = httpx.Client(timeout=self.timeout, auth=(jenkins_user, jenkins_token))
            else:
                self.client = httpx.Client(timeout=self.timeout)

            for pattern in api_patterns:
                try:
                    test_url = f"{self.base_url}{pattern}?tree=jobs[name]"
                    self.logger.debug(f"Testing Jenkins API path via HTTP: {test_url}")

                    response = self.client.get(test_url)
                    if response.status_code == 200:
                        if self.stats:
                            self.stats.record_success("jenkins")
                        try:
                            http_data = response.json()
                            if "jobs" in http_data and isinstance(http_data["jobs"], list):
                                self.api_base_path = pattern
                                job_count = len(http_data["jobs"])
                                self.logger.info(
                                    f"✅ HTTP fallback successful! Found working Jenkins API path: "
                                    f"{pattern} ({job_count} jobs)"
                                )
                                return
                        except Exception as e:
                            self.logger.debug(f"Invalid JSON response from {pattern}: {e}")
                            continue
                    else:
                        self.logger.debug(f"HTTP {response.status_code} for {pattern}")

                except Exception as e:
                    self.logger.debug(f"Error testing {pattern} via HTTP: {e}")
                    continue

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

    def get_all_jobs(self) -> dict[str, Any]:
        """
        Get all jobs from Jenkins with caching.

        Returns:
            Dictionary containing jobs array and metadata.
            Returns empty dict on error.

        Example:
            >>> client = JenkinsAPIClient("jenkins.example.com")
            >>> jobs_data = client.get_all_jobs()
            >>> for job in jobs_data.get('jobs', []):
            ...     print(job['name'])
        """
        # Return cached data if available
        if self._cache_populated and self._jobs_cache:
            self.logger.debug(
                f"Using cached Jenkins jobs data ({len(self._jobs_cache.get('jobs', []))} jobs)"
            )
            return self._jobs_cache

        if not self.api_base_path:
            self.logger.error(f"No valid API base path discovered for {self.host}")
            return {}

        try:
            url = (
                f"{self.base_url}{self.api_base_path}?tree=jobs[name,url,color,buildable,disabled]"
            )
            self.logger.debug(f"Fetching Jenkins jobs from: {url}")
            response = self.client.get(url)

            self.logger.debug(f"Jenkins API response: {response.status_code}")
            if response.status_code == 200:
                if self.stats:
                    self.stats.record_success("jenkins")
                data = response.json()
                job_count = len(data.get("jobs", []))
                self.logger.debug(f"Found {job_count} Jenkins jobs (cached for reuse)")

                # Cache the data
                self._jobs_cache = data
                self._cache_populated = True
                return dict(data)
            else:
                if self.stats:
                    self.stats.record_error("jenkins", response.status_code)
                self.logger.warning(
                    f"❌ Error: Jenkins API query returned error code: {response.status_code} for {url}"
                )
                self.logger.warning(f"Response text: {response.text[:500]}")
                return {}

        except Exception as e:
            if self.stats:
                self.stats.record_exception("jenkins")
            self.logger.error(f"❌ Error: Jenkins API query exception for {self.host}: {e}")
            return {}

    def get_jobs_for_project(
        self, project_name: str, allocated_jobs: set[str]
    ) -> list[dict[str, Any]]:
        """
        Get jobs related to a specific Gerrit project with duplicate prevention.

        Uses hybrid approach combining JJB Attribution (authoritative) and fuzzy
        matching (fallback) to maximize job attribution coverage.

        Strategy:
        1. Try JJB Attribution first (authoritative from ci-management)
        2. Also try fuzzy matching to catch legacy/manual jobs not in JJB
        3. Combine results, deduplicating by job name
        4. Return all matched jobs

        Args:
            project_name: Name of the Gerrit project (e.g., "foo/bar")
            allocated_jobs: Set of job names already allocated to other projects

        Returns:
            List of job detail dictionaries for matched jobs

        Example:
            >>> client = JenkinsAPIClient("jenkins.example.com")
            >>> allocated = set()
            >>> jobs = client.get_jobs_for_project("sdc/onap-sdc", allocated)
            >>> print(f"Found {len(jobs)} jobs")
        """
        self.logger.debug(f"Looking for Jenkins jobs for project: {project_name}")

        all_jobs = []
        job_names_found = set()  # Track to avoid duplicates

        # Try JJB Attribution first if enabled
        jjb_jobs = []
        if self.jjb_attribution_enabled and self.jjb_attribution:
            try:
                jjb_jobs = self._get_jobs_via_jjb_attribution(project_name, allocated_jobs)
                for job in jjb_jobs:
                    job_name = job.get("name")
                    if job_name and job_name not in job_names_found:
                        all_jobs.append(job)
                        job_names_found.add(job_name)

                if jjb_jobs:
                    self.logger.debug(
                        f"JJB Attribution found {len(jjb_jobs)} jobs for {project_name}"
                    )
            except Exception as e:
                self.logger.warning(
                    f"JJB Attribution lookup failed for {project_name}: {e}. "
                    f"Will rely on fuzzy matching only."
                )

        # Always try fuzzy matching to catch legacy/manual jobs not in JJB
        # This is especially important for projects with mixed job sources
        try:
            fuzzy_jobs = self._get_jobs_via_fuzzy_matching(project_name, allocated_jobs)

            # Add fuzzy matches that aren't already found via JJB
            fuzzy_added = 0
            for job in fuzzy_jobs:
                job_name = job.get("name")
                if job_name and job_name not in job_names_found:
                    all_jobs.append(job)
                    job_names_found.add(job_name)
                    fuzzy_added += 1

            if fuzzy_added > 0:
                self.logger.debug(
                    f"Fuzzy matching added {fuzzy_added} additional jobs for {project_name} "
                    f"(total: {len(all_jobs)})"
                )
        except Exception as e:
            self.logger.warning(f"Fuzzy matching failed for {project_name}: {e}")

        # Log summary of hybrid approach
        if all_jobs:
            sources = []
            if jjb_jobs:
                sources.append(f"{len(jjb_jobs)} JJB")
            if len(all_jobs) > len(jjb_jobs):
                sources.append(f"{len(all_jobs) - len(jjb_jobs)} fuzzy")

            self.logger.debug(
                f"Hybrid matching for {project_name}: {len(all_jobs)} jobs ({', '.join(sources)})"
            )

        return all_jobs

    def _get_jobs_via_jjb_attribution(
        self, project_name: str, allocated_jobs: set[str]
    ) -> list[dict[str, Any]]:
        """
        Get jobs using JJB Attribution authoritative definitions.

        Args:
            project_name: Name of the Gerrit project
            allocated_jobs: Set of job names already allocated

        Returns:
            List of job detail dictionaries
        """
        self.logger.debug(f"Using JJB Attribution for project: {project_name}")

        # Get expected job names from ci-management
        if self.jjb_attribution is None:
            self.logger.warning("JJB Attribution not available")
            return []

        expected_jobs = self.jjb_attribution.parse_project_jobs(project_name)

        # Filter out unresolved template variables
        resolved_jobs = [j for j in expected_jobs if "{" not in j]

        if not resolved_jobs:
            self.logger.debug(f"No resolved jobs found in JJB for {project_name}")
            return []

        self.logger.debug(f"JJB expects {len(resolved_jobs)} jobs for {project_name}")

        # Get all Jenkins jobs
        all_jobs = self.get_all_jobs()
        if "jobs" not in all_jobs:
            self.logger.debug(f"No 'jobs' key found in Jenkins API response for {project_name}")
            return []

        # Build a lookup map of available Jenkins jobs
        jenkins_jobs_map = {job.get("name", ""): job for job in all_jobs["jobs"]}

        # Match expected jobs against actual Jenkins jobs
        project_jobs: list[dict[str, Any]] = []
        matched_count = 0

        for expected_job in resolved_jobs:
            # Skip if already allocated
            if expected_job in allocated_jobs:
                self.logger.debug(f"Skipping already allocated job: {expected_job}")
                continue

            # Check if job exists in Jenkins
            if expected_job in jenkins_jobs_map:
                # Get detailed job info
                job_details = self.get_job_details(expected_job)
                if job_details:
                    project_jobs.append(job_details)
                    # NOTE: Do NOT add to allocated_jobs here - that's done by
                    # JenkinsAllocationContext.allocate_jobs() to avoid double-allocation
                    matched_count += 1
                    self.logger.debug(f"✓ Matched JJB job '{expected_job}' to {project_name}")
                else:
                    self.logger.warning(f"Failed to get details for Jenkins job: {expected_job}")
            else:
                self.logger.debug(f"Job '{expected_job}' defined in JJB but not found in Jenkins")

        accuracy = (matched_count / len(resolved_jobs) * 100) if resolved_jobs else 0
        self.logger.debug(
            f"JJB: {matched_count}/{len(resolved_jobs)} jobs ({accuracy:.1f}%) for {project_name}"
        )

        return project_jobs

    def _get_jobs_via_fuzzy_matching(
        self, project_name: str, allocated_jobs: set[str]
    ) -> list[dict[str, Any]]:
        """
        Get jobs using fuzzy matching algorithm (fallback method).

        Args:
            project_name: Name of the Gerrit project
            allocated_jobs: Set of job names already allocated

        Returns:
            List of job detail dictionaries
        """
        self.logger.debug(f"Using fuzzy matching for project: {project_name}")

        all_jobs = self.get_all_jobs()
        project_jobs: list[dict[str, Any]] = []

        if "jobs" not in all_jobs:
            self.logger.debug(f"No 'jobs' key found in Jenkins API response for {project_name}")
            return project_jobs

        # Convert project name to job name format (replace / with -)
        project_job_name = project_name.replace("/", "-")
        self.logger.debug(f"Searching for Jenkins jobs matching pattern: {project_job_name}")

        total_jobs = len(all_jobs["jobs"])
        self.logger.debug(f"Checking {total_jobs} total Jenkins jobs for matches")

        # Collect potential matches with scoring for better matching
        candidates: list[tuple[dict[str, Any], int]] = []

        for job in all_jobs["jobs"]:
            job_name = job.get("name", "")

            # Skip already allocated jobs
            if job_name in allocated_jobs:
                self.logger.debug(f"Skipping already allocated Jenkins job: {job_name}")
                continue

            # Calculate match score for better job attribution
            score = self._calculate_job_match_score(job_name, project_name, project_job_name)
            if score > 0:
                candidates.append((job, score))

        # Sort by score (highest first) to prioritize better matches
        candidates.sort(key=lambda x: x[1], reverse=True)

        for job, score in candidates:
            job_name = job.get("name", "")
            self.logger.debug(f"Processing Jenkins job: {job_name} (score: {score})")

            # Get detailed job info
            job_details = self.get_job_details(job_name)
            if job_details:
                project_jobs.append(job_details)
                # NOTE: Do NOT add to allocated_jobs here - that's done by
                # JenkinsAllocationContext.allocate_jobs() to avoid double-allocation
                self.logger.debug(
                    f"Matched Jenkins job '{job_name}' to project '{project_name}' (score: {score})"
                )
            else:
                self.logger.warning(f"Failed to get details for Jenkins job: {job_name}")

        self.logger.debug(
            f"Fuzzy matching: Found {len(project_jobs)} Jenkins jobs for project {project_name}"
        )
        return project_jobs

    def _calculate_job_match_score(
        self, job_name: str, project_name: str, project_job_name: str
    ) -> int:
        """
        Calculate a match score for Jenkins job attribution.

        Supports multiple job naming patterns used across LF projects:

        1. PREFIX PATTERN (ONAP, OpenDaylight style):
           {project-name}-{job-type}-{stream}
           Example: aai-babel-maven-verify-master -> aai/babel

        2. SUFFIX PATTERN (LF Broadband style):
           {job-type}_{project-name}
           Example: docker-publish_bbsim -> bbsim

        3. INFIX PATTERN (LF Broadband verify jobs):
           verify_{project-name}_{job-type}
           Example: verify_aaa_maven-test -> aaa

        This prevents duplicate allocation by ensuring jobs can only match one project.
        Higher scores indicate better matches. Returns 0 for no match.

        Args:
            job_name: Jenkins job name
            project_name: Original Gerrit project name (with slashes)
            project_job_name: Project name converted to job format (slashes -> dashes)

        Returns:
            Match score (0 = no match, higher = better match)
        """
        if not job_name or not project_job_name:
            return 0

        job_name_lower = job_name.lower()
        project_job_name_lower = project_job_name.lower()

        score = 0
        match_type = None

        # =================================================================
        # PATTERN 1: Exact match (highest priority)
        # =================================================================
        if job_name_lower == project_job_name_lower:
            match_type = "exact"
            score = 1000

        # =================================================================
        # PATTERN 2a: Prefix match - {project}-* (ONAP, ODL style)
        # Example: aai-babel-maven-verify-master matches aai/babel
        # =================================================================
        elif job_name_lower.startswith(project_job_name_lower + "-"):
            match_type = "prefix_hyphen"
            score = 500

        # =================================================================
        # PATTERN 2b: Prefix match - {project}_* (LF Broadband style)
        # Example: bbsim_scale_test matches bbsim
        # =================================================================
        elif job_name_lower.startswith(project_job_name_lower + "_"):
            match_type = "prefix_underscore"
            score = 490

        # =================================================================
        # PATTERN 3: Suffix match with underscore - *_{project}
        # Example: docker-publish_bbsim matches bbsim
        # Example: maven-publish_aaa matches aaa
        # Example: github-release_voltctl matches voltctl
        # =================================================================
        elif job_name_lower.endswith("_" + project_job_name_lower):
            match_type = "suffix_underscore"
            score = 450

        # =================================================================
        # PATTERN 4: Infix match - verify_{project}_* (LF Broadband verify)
        # Example: verify_aaa_licensed matches aaa
        # Example: verify_bbsim_unit-test matches bbsim
        # =================================================================
        elif (
            job_name_lower.startswith("verify_" + project_job_name_lower + "_")
            or job_name_lower == "verify_" + project_job_name_lower
        ):
            match_type = "infix_verify"
            score = 400

        # =================================================================
        # PATTERN 5: Prefix with common job type prefixes
        # Example: patchset-voltha-* matches voltha
        # Example: periodic-voltha-* matches voltha
        # Example: build-voltha-* matches voltha
        # =================================================================
        elif any(
            job_name_lower.startswith(prefix + project_job_name_lower + "-")
            or job_name_lower == prefix + project_job_name_lower
            for prefix in ["patchset-", "periodic-", "build-", "release-", "merge-"]
        ):
            match_type = "prefixed_project"
            score = 380

        # =================================================================
        # PATTERN 6: Infix with underscore delimiters - *_{project}_*
        # Example: build_berlin-community-pod-1-gpon_1T8GEM_DT_voltha_master matches voltha
        # Example: verify_berlin-community-pod-1-gpon-adtran_Default_DT_voltha_master_dmi matches voltha
        #
        # IMPORTANT: Avoid false positives where the project appears as part
        # of a parent-child pattern. Check that the prefix before the project
        # doesn't look like a parent project name with hyphen separator.
        # =================================================================
        elif "_" + project_job_name_lower + "_" in job_name_lower:
            # Find where the project name appears in the job name
            infix_pos = job_name_lower.find("_" + project_job_name_lower + "_")
            prefix_part = job_name_lower[:infix_pos]

            # Check if the prefix ends with a hyphenated version that suggests
            # this is actually a parent-child prefix pattern like "sdc-tosca"
            # being matched against standalone "tosca"
            if prefix_part.endswith("-" + project_job_name_lower):
                # This looks like parent-child, not a valid infix match
                pass
            else:
                match_type = "infix_underscore"
                score = 350

        # =================================================================
        # PATTERN 7: Infix with hyphen delimiters - *-{project}-*
        # Example: patchset-voltha-2.14-multiple-olts matches voltha
        # Example: periodic-voltha-dt-test-bbsim matches voltha
        #
        # IMPORTANT: Avoid false positives where the project appears as part
        # of a parent-child prefix pattern (e.g., "sdc-tosca-verify" should
        # NOT match standalone "tosca" because it's actually "sdc/tosca").
        # We check if the prefix before the project name looks like a known
        # job-type prefix rather than a parent project name.
        # =================================================================
        elif "-" + project_job_name_lower + "-" in job_name_lower:
            # Find where the project name appears in the job name
            infix_pos = job_name_lower.find("-" + project_job_name_lower + "-")
            prefix_part = job_name_lower[:infix_pos]

            # Known job-type prefixes that indicate this is a valid infix match
            known_job_prefixes = (
                "patchset",
                "periodic",
                "build",
                "release",
                "merge",
                "verify",
                "test",
                "deploy",
                "publish",
                "docker",
                "maven",
            )

            # Check if the prefix is a known job-type prefix or contains one
            # If not, this might be a parent-child pattern (e.g., sdc-tosca)
            is_valid_infix = False
            if (
                prefix_part in known_job_prefixes
                or any(prefix_part.startswith(p + "-") for p in known_job_prefixes)
                or any(prefix_part.endswith("-" + p) for p in known_job_prefixes)
            ):
                is_valid_infix = True
            elif "_" in prefix_part:
                # Underscore in prefix suggests it's a complex job name, not parent-child
                is_valid_infix = True

            if is_valid_infix:
                match_type = "infix_hyphen"
                score = 300

        # =================================================================
        # PATTERN 8: Suffix match with hyphen - *-{project}
        # Example: onos-app-release matches release (if release is a project)
        # Example: docker-build-voltha matches voltha
        # =================================================================
        elif job_name_lower.endswith("-" + project_job_name_lower):
            match_type = "suffix_hyphen"
            score = 250

        # =================================================================
        # No match found
        # =================================================================
        if match_type is None:
            return 0

        # =================================================================
        # Apply bonuses for more specific matches
        # =================================================================

        # Bonus for longer/more specific project paths (child projects get priority)
        path_parts = project_name.count("/") + 1
        score += path_parts * 50

        # For prefix matches, add bonus for consecutive component matches
        if match_type == "prefix":
            project_parts = project_job_name_lower.split("-")
            job_parts = job_name_lower.split("-")
            consecutive_matches = 0

            for i, project_part in enumerate(project_parts):
                if i < len(job_parts) and job_parts[i] == project_part:
                    consecutive_matches += 1
                else:
                    break

            score += consecutive_matches * 25

        return score

    def get_job_details(self, job_name: str) -> dict[str, Any]:
        """
        Get detailed information about a specific job.

        Args:
            job_name: Name of the Jenkins job

        Returns:
            Dictionary with job details including status, state, color, URLs, and last build info.
            Returns empty dict on error.

        Example:
            >>> client = JenkinsAPIClient("jenkins.example.com")
            >>> details = client.get_job_details("my-project-verify")
            >>> print(details['status'])  # e.g., "success"
        """
        try:
            # Extract base path without /api/json suffix for job URLs
            base_path = self.api_base_path.replace("/api/json", "") if self.api_base_path else ""
            url = f"{self.base_url}{base_path}/job/{job_name}/api/json"
            response = self.client.get(url)

            if response.status_code == 200:
                job_data = response.json()

                # Get last build info
                last_build_info = self.get_last_build_info(job_name)

                # Compute Jenkins job state from disabled field first
                disabled = job_data.get("disabled", False)
                buildable = job_data.get("buildable", True)
                state = self._compute_jenkins_job_state(disabled, buildable)

                # Get original color from Jenkins
                original_color = job_data.get("color", "")

                # Compute standardized status from color field, considering state
                status = self._compute_job_status_from_color(original_color)

                # Override color if job is disabled (regardless of last build result)
                if state == "disabled":
                    color = "grey"
                    if status not in ("disabled", "not_built"):
                        status = "disabled"
                else:
                    color = original_color

                # Build standardized job data structure
                job_url = job_data.get("url", "")
                if not job_url and base_path:
                    # Fallback: construct URL if not provided by API
                    job_url = f"{self.base_url}{base_path}/job/{job_name}/"

                return {
                    "name": job_name,
                    "status": status,
                    "state": state,
                    "color": color,
                    "urls": {
                        "job_page": job_url,
                        "source": None,
                        "api": url,
                    },
                    "buildable": buildable,
                    "disabled": disabled,
                    "description": job_data.get("description", ""),
                    "last_build": last_build_info,
                }
            else:
                self.logger.debug(f"Jenkins job API returned {response.status_code} for {job_name}")
                return {}

        except Exception as e:
            self.logger.debug(f"Exception fetching job details for {job_name}: {e}")
            return {}

    def _compute_jenkins_job_state(self, disabled: bool, buildable: bool) -> str:
        """
        Convert Jenkins disabled and buildable fields to standardized state.

        Jenkins job states:
        - disabled=True: Job is explicitly disabled
        - disabled=False + buildable=True: Job is active and can be built
        - disabled=False + buildable=False: Job exists but cannot be built (treat as disabled)

        Args:
            disabled: Whether the job is disabled in Jenkins
            buildable: Whether the job is buildable

        Returns:
            State string: "active" or "disabled"
        """
        if disabled:
            return "disabled"
        elif buildable:
            return "active"
        else:
            # If not disabled but not buildable, consider it effectively disabled
            return "disabled"

    def _compute_job_status_from_color(self, color: str) -> str:
        """
        Convert Jenkins color field to standardized status.

        Jenkins color meanings:
        - blue: success
        - red: failure
        - yellow: unstable
        - grey: not built/disabled
        - aborted: aborted
        - *_anime: building (animated versions)

        Args:
            color: Jenkins color code

        Returns:
            Standardized status string
        """
        if not color:
            return "unknown"

        color_lower = color.lower()

        # Handle animated colors (building states)
        if color_lower.endswith("_anime"):
            return "building"

        # Map standard colors
        color_map = {
            "blue": "success",
            "red": "failure",
            "yellow": "unstable",
            "grey": "disabled",
            "gray": "disabled",
            "aborted": "aborted",
            "notbuilt": "not_built",
            "disabled": "disabled",
        }

        return color_map.get(color_lower, "unknown")

    def get_last_build_info(self, job_name: str) -> dict[str, Any]:
        """
        Get information about the last build of a job.

        Args:
            job_name: Name of the Jenkins job

        Returns:
            Dictionary with last build information (result, duration, timestamp, etc.)
            Returns empty dict if no build exists or on error.
        """
        try:
            # Extract base path without /api/json suffix for job URLs
            base_path = self.api_base_path.replace("/api/json", "") if self.api_base_path else ""
            url = f"{self.base_url}{base_path}/job/{job_name}/lastBuild/api/json?tree=result,duration,timestamp,building,number"
            response = self.client.get(url)

            if response.status_code == 200:
                build_data = response.json()

                # Convert timestamp to readable format
                timestamp = build_data.get("timestamp", 0)
                if timestamp:
                    build_time = datetime.fromtimestamp(timestamp / 1000)
                    build_data["build_time"] = build_time.isoformat()

                # Convert duration to readable format
                duration_ms = build_data.get("duration", 0)
                if duration_ms:
                    duration_seconds = duration_ms / 1000
                    build_data["duration_seconds"] = duration_seconds

                return dict(build_data)
            else:
                return {}

        except Exception as e:
            self.logger.debug(f"Exception fetching last build info for {job_name}: {e}")
            return {}
