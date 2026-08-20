# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Repository analysis workflow.

Drives the end-to-end analysis pass: the report skeleton and its time
windows, parallel repository analysis, INFO.yaml collection and the
Jenkins job allocation summary.
"""

import datetime
import os
from pathlib import Path
from typing import Any, cast

from lf_releng_project_reporting.exceptions import NoRepositoriesError

from .discovery import ReporterDiscoveryMixin
from .info_master import ReporterInfoMasterMixin


class ReporterAnalysisMixin(ReporterDiscoveryMixin, ReporterInfoMasterMixin):
    """Analysis orchestration for the reporter."""

    # Assigned by RepositoryReporter.__init__; declared here for type checking.
    aggregator: Any
    info_yaml_collector: Any
    _info_master_path: Path | None

    def analyze_repositories(self, repos_path: Path, allow_empty: bool = False) -> dict[str, Any]:
        """
        Main analysis workflow.

        Coordinates all phases of repository analysis:
        1. Discover all repositories (fails fast if none are found, before
           any network work, unless ``allow_empty`` is set)
        2. Clone info-master for additional context
        3. Initialize report data structure
        4. Analyze repositories in parallel
        5. Aggregate data across repositories
        6. Generate Jenkins allocation summary

        Args:
            repos_path: Path to directory containing repositories to analyze
            allow_empty: When ``False`` (the default), a hard error is raised
                if no repositories are discovered under ``repos_path``. This
                guards against generating an empty, misleading report when an
                upstream clone step failed transiently. Set to ``True`` only
                when an empty result is genuinely acceptable.

        Returns:
            Complete report data dictionary with all analysis results

        Raises:
            NoRepositoriesError: If no repositories are discovered and
                ``allow_empty`` is ``False``.
        """
        # Resolve to absolute path for consistent handling
        repos_path_abs = repos_path.resolve()
        self.logger.info(f"Starting repository analysis in {repos_path_abs}")

        # Determine Gerrit server from repos_path (e.g., "gerrit.onap.org")
        # This is used to filter INFO.yaml data to only the relevant server
        gerrit_server = self._determine_gerrit_server(repos_path_abs)
        self.logger.info(f"Detected Gerrit server: {gerrit_server}")

        # Discover repositories up front and fail fast when the working
        # directory is empty. An empty result almost always means an upstream
        # clone step produced no repositories (for example, a transient Gerrit
        # discovery/clone failure). Continuing would generate an empty report
        # that could overwrite previously good output, so raise a retryable
        # error before doing any further (network) work, unless the caller
        # explicitly opts in via allow_empty.
        repo_dirs = self._discover_repositories(repos_path_abs)
        self.logger.info(f"Found {len(repo_dirs)} repositories to analyze")
        if not repo_dirs and not allow_empty:
            raise NoRepositoriesError(
                f"No repositories found to analyze under '{repos_path_abs}'. "
                "This usually indicates an upstream clone failure (for example, "
                "a transient Gerrit discovery/clone problem). Re-run the clone "
                "and report generation, or explicitly allow an empty result "
                "(pass --allow-empty on the CLI, or allow_empty=True via the "
                "Python API)."
            )

        # Clone info-master repository for additional context
        # This is cloned to a temporary directory to avoid it appearing in the report
        info_master_path = self._clone_info_master_repo()
        if info_master_path:
            self.logger.debug(f"Info-master repository available at: {info_master_path}")
        else:
            self.logger.warning("Info-master repository not available - continuing without it")

        # Store info_master_path for INFO.yaml collection
        self._info_master_path = info_master_path

        report_data = self._build_initial_report_data()

        self.git_collector.time_windows = cast(
            dict[str, dict[str, Any]], report_data["time_windows"]
        )

        # Update git collector with repos_path for relative path calculation
        self.git_collector.repos_path = repos_path_abs

        # Analyze repositories (with concurrency)
        repo_metrics = self._analyze_repositories_parallel(repo_dirs)

        successful_repos = []
        for metrics in repo_metrics:
            if "error" in metrics:
                cast(list[dict[str, Any]], report_data["errors"]).append(metrics)
            else:
                successful_repos.append(metrics["repository"])

        report_data["repositories"] = successful_repos

        # Aggregate data (pass repository records directly)
        report_data["authors"] = self.aggregator.compute_author_rollups(successful_repos)
        report_data["organizations"] = self.aggregator.compute_org_rollups(report_data["authors"])
        report_data["summaries"] = self.aggregator.aggregate_global_data(successful_repos)

        # Collect INFO.yaml data if info-master is available
        self._collect_info_yaml_data(report_data, info_master_path, gerrit_server, repo_metrics)

        # Log comprehensive Jenkins job allocation summary for auditing
        self._record_jenkins_allocation(report_data)

        self.logger.info(
            f"Analysis complete: {len(report_data['repositories'])} repositories, {len(report_data['errors'])} errors"
        )

        return report_data

    def _build_initial_report_data(self) -> dict[str, Any]:
        """Create the report skeleton and attach Jenkins metadata when configured."""
        report_data: dict[str, Any] = {
            "schema_version": self.config.get("_schema_version", "1.0.0"),
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "project": self.config["project"],
            "config_digest": self._compute_config_digest(self.config),
            "script_version": self.config.get("_script_version", "1.0.0"),
            "time_windows": self._setup_time_windows(self.config),
            "repositories": [],
            "authors": [],
            "organizations": [],
            "summaries": {},
            "errors": [],
        }

        # Add Jenkins metadata if Jenkins is configured
        jenkins_config = self.config.get("jenkins", {})
        jenkins_host = os.environ.get("JENKINS_HOST") or jenkins_config.get("host", "")
        if jenkins_host or jenkins_config.get("enabled"):
            report_data["jenkins_metadata"] = {
                "host": jenkins_host,
                "requires_auth": bool(
                    os.environ.get("JENKINS_USER") and os.environ.get("JENKINS_API_TOKEN")
                ),
            }

        return report_data

    def _collect_info_yaml_data(
        self,
        report_data: dict[str, Any],
        info_master_path: Path | None,
        gerrit_server: str,
        repo_metrics: list[dict[str, Any]],
    ) -> None:
        """Collect INFO.yaml data for the current Gerrit server, if available.

        Filters to only the current Gerrit server to avoid cross-project
        contamination. Skips collection (with a debug note) when info-master is
        unavailable or the collector is disabled.
        """
        if not (info_master_path and self.info_yaml_collector.is_enabled()):
            if not info_master_path:
                self.logger.debug("INFO.yaml collection skipped: info-master not available")
            else:
                self.logger.debug("INFO.yaml collection skipped: disabled in configuration")
            return

        try:
            self.logger.info(f"Collecting INFO.yaml project data for {gerrit_server}...")
            info_yaml_data = self.info_yaml_collector.collect(
                info_master_path,
                git_metrics=repo_metrics,
                gerrit_server=gerrit_server,  # Filter by server
            )
            report_data["info_yaml"] = info_yaml_data
            self.logger.info(
                f"✅ Collected {info_yaml_data.get('total_projects', 0)} INFO.yaml projects for {gerrit_server}"
            )
        except Exception as e:
            self.logger.error(f"❌ Failed to collect INFO.yaml data: {e}")
            report_data["info_yaml"] = {
                "projects": [],
                "lifecycle_summary": [],
                "total_projects": 0,
                "servers": [],
                "error": str(e),
            }

    def _record_jenkins_allocation(self, report_data: dict[str, Any]) -> None:
        """Log the Jenkins job allocation summary and attach it to the report."""
        if not (self.git_collector.jenkins_client and self.git_collector._jenkins_initialized):
            return

        allocation_summary = self.git_collector.get_jenkins_job_allocation_summary()

        self.logger.info("Jenkins job allocation summary:")
        self.logger.info(f"  Total jobs: {allocation_summary['total_jenkins_jobs']}")
        self.logger.info(f"  Allocated: {allocation_summary['allocated_jobs']}")
        self.logger.info(f"  Unallocated: {allocation_summary['unallocated_jobs']}")
        self.logger.info(f"  Allocation rate: {allocation_summary['allocation_percentage']}%")

        validation_issues = self.git_collector.validate_jenkins_job_allocation()
        if validation_issues:
            self.logger.warning("Jenkins job allocation information:")
            for issue in validation_issues:
                self.logger.debug(f"  - {issue}")

            allocation_summary = self.git_collector.get_jenkins_job_allocation_summary()
            orphaned_summary = self.git_collector.get_orphaned_jenkins_jobs_summary()

            total_jobs = allocation_summary.get("total_jenkins_jobs", 0)
            allocated_jobs = allocation_summary.get("allocated_jobs", 0)
            orphaned_jobs = orphaned_summary.get("total_orphaned_jobs", 0)

            self.logger.info(
                f"Final Jenkins job allocation: {allocated_jobs}/{total_jobs} active, {orphaned_jobs} orphaned"
            )
        else:
            self.logger.info("Jenkins job allocation validation: No issues found")

        # Add allocation data to report for debugging
        report_data["jenkins_allocation"] = allocation_summary

        if allocation_summary.get("unallocated_jobs", 0) > 0:
            all_jobs = self.git_collector.jenkins_allocation_context.get_all_jobs()
            all_jobs_list = all_jobs.get("jobs", [])
            all_job_names = {job.get("name", "") for job in all_jobs_list}
            allocated_job_names = set(allocation_summary.get("allocated_job_names", []))
            unallocated_job_names = sorted(all_job_names - allocated_job_names)
            report_data["jenkins_allocation"]["unallocated_job_names"] = unallocated_job_names

            # Store basic job data for unallocated jobs (same structure as cache)
            # This includes: name, url, color, buildable, disabled
            unallocated_job_details = [
                job for job in all_jobs_list if job.get("name", "") in unallocated_job_names
            ]
            report_data["jenkins_allocation"]["unallocated_job_details"] = unallocated_job_details

        # Add orphaned jobs data to report
        orphaned_summary = self.git_collector.get_orphaned_jenkins_jobs_summary()
        report_data["orphaned_jenkins_jobs"] = orphaned_summary
        if orphaned_summary["total_orphaned_jobs"] > 0:
            self.logger.info(
                f"Found {orphaned_summary['total_orphaned_jobs']} Jenkins jobs belonging to archived Gerrit projects"
            )
            for state, count in orphaned_summary["by_state"].items():
                self.logger.info(f"  - {count} jobs for {state} projects")

    def _compute_config_digest(self, config: dict[str, Any]) -> str:
        """
        Compute SHA256 digest of configuration for reproducibility tracking.

        Args:
            config: Configuration dictionary

        Returns:
            Hexadecimal SHA256 digest string
        """
        import hashlib
        import json

        config_json = json.dumps(config, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(config_json.encode("utf-8")).hexdigest()

    def _setup_time_windows(self, config: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """
        Compute time window boundaries based on configuration.

        Args:
            config: Configuration dictionary with time_windows settings

        Returns:
            Dictionary with window definitions including start/end timestamps
        """
        from datetime import timedelta

        now = datetime.datetime.now(datetime.UTC)
        windows = {}

        # Default time windows if not specified
        default_windows = {
            "last_30": 30,
            "last_90": 90,
            "last_365": 365,
            "last_3_years": 1095,
        }

        time_window_config = config.get("time_windows", default_windows)

        for window_name, window_config in time_window_config.items():
            # Support both simple integer format and dictionary format
            if isinstance(window_config, int):
                # Simple format: last_30: 30
                days = window_config
            elif isinstance(window_config, dict) and "days" in window_config:
                # Dictionary format: last_30: {days: 30}
                days = window_config["days"]
            else:
                self.logger.warning(f"Time window '{window_name}' has invalid format, skipping")
                continue

            start_date = now - timedelta(days=days)
            windows[window_name] = {
                "days": days,
                "start": start_date.isoformat(),
                "end": now.isoformat(),
                "start_timestamp": start_date.timestamp(),
                "end_timestamp": now.timestamp(),
            }

        return windows
