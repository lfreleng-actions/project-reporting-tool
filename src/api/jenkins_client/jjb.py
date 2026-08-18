# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
JJB Attribution integration for Jenkins.

Authoritative job-to-project attribution derived from a project's
ci-management repository, with graceful degradation when the optional
``jjb_attribution`` package or the ci-management URL is unavailable.
"""

from pathlib import Path
from typing import Any

from ..gerrit_client import GerritAPIError, GerritURLBuilder
from .builds import JenkinsBuildsMixin
from .catalog import JenkinsCatalogMixin


# Optional JJB Attribution integration
try:
    from jjb_attribution import JJBAttribution, JJBRepoManager

    JJB_ATTRIBUTION_AVAILABLE = True
except ImportError:
    JJB_ATTRIBUTION_AVAILABLE = False  # pyright: ignore[reportConstantRedefinition]
    JJBAttribution = None
    JJBRepoManager = None


class JenkinsJJBMixin(JenkinsCatalogMixin, JenkinsBuildsMixin):
    """Authoritative job attribution sourced from ci-management JJB definitions."""

    # Assigned by JenkinsAPIClient.__init__; declared here for type checking.
    jjb_attribution: Any | None
    jjb_attribution_enabled: bool

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

            if JJBAttribution is None:
                return
            self.jjb_attribution = JJBAttribution(ci_mgmt_path, global_jjb_path)
            self.jjb_attribution.load_templates()

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

        all_jobs = self.get_all_jobs()
        if "jobs" not in all_jobs:
            self.logger.debug(f"No 'jobs' key found in Jenkins API response for {project_name}")
            return []

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
