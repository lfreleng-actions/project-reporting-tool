#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Repository Reporter - Main Orchestration Module

This module contains the RepositoryReporter class which orchestrates the entire
repository analysis workflow, including:
- Repository discovery and scanning
- Git data collection coordination
- Feature detection coordination
- Data aggregation
- Report rendering and output generation

The RepositoryReporter acts as the main controller that ties together all the
subsystems (collectors, aggregators, renderers) to produce comprehensive
repository analysis reports.
"""

import atexit
import concurrent.futures
import datetime
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, cast

from lf_releng_project_reporting.aggregators import DataAggregator
from lf_releng_project_reporting.collectors import GitDataCollector, INFOYamlCollector
from lf_releng_project_reporting.config import save_resolved_config
from lf_releng_project_reporting.exceptions import NoRepositoriesError
from lf_releng_project_reporting.features import FeatureRegistry
from rendering.renderer import ModernReportRenderer
from util.git import safe_git_command
from util.zip_bundle import create_report_bundle


# Global API statistics (imported from main module)


class RepositoryReporter:
    """Main orchestrator for repository reporting."""

    def __init__(
        self, config: dict[str, Any], logger: logging.Logger, api_stats: Any | None = None
    ) -> None:
        """
        Initialize the repository reporter.

        Args:
            config: Merged configuration dictionary
            logger: Logger instance for reporting progress and issues
            api_stats: Optional API statistics tracker for monitoring external API calls
        """
        self.config = config
        self.logger = logger
        self.api_stats = api_stats
        self.git_collector = GitDataCollector(config, {}, logger, api_stats=api_stats)
        self.feature_registry = FeatureRegistry(config, logger, api_stats=api_stats)
        self.aggregator = DataAggregator(config, logger)
        self.renderer = ModernReportRenderer(config, logger)
        self.info_yaml_collector = INFOYamlCollector(config)
        self.info_master_temp_dir: str | None = None
        self._info_master_path: Path | None = None

    def _cleanup_info_master_repo(self) -> None:
        """Clean up the temporary info-master repository directory."""
        if self.info_master_temp_dir and os.path.exists(self.info_master_temp_dir):
            try:
                self.logger.info(
                    f"Cleaning up info-master repository at {self.info_master_temp_dir}"
                )
                shutil.rmtree(self.info_master_temp_dir)
                self.logger.info("Successfully cleaned up info-master repository")
            except Exception as e:
                self.logger.warning(f"Failed to clean up info-master repository: {e}")

    def _clone_info_master_repo(self) -> Path | None:
        """
        Clone the info-master repository for additional context data.

        Returns the path to the cloned repository in a temporary directory,
        or None if cloning failed.
        """
        self.info_master_temp_dir = tempfile.mkdtemp(prefix="info-master-")
        info_master_path = Path(self.info_master_temp_dir) / "info-master"
        info_master_url = "https://gerrit.linuxfoundation.org/infra/releng/info-master"

        self.logger.info(
            f"Cloning info-master repository to temporary location: {info_master_path}"
        )
        success, output = safe_git_command(
            ["git", "clone", info_master_url, str(info_master_path)],
            Path(self.info_master_temp_dir),
            self.logger,
        )

        if success:
            if self.api_stats:
                self.api_stats.record_info_master(True)
            self.logger.debug("✅ Successfully cloned info-master repository")
            # Register cleanup handler
            atexit.register(self._cleanup_info_master_repo)
            return info_master_path
        else:
            error_msg = f"Clone failed: {output[:200]}" if output else "Clone failed"
            if self.api_stats:
                self.api_stats.record_info_master(False, error_msg)
            self.logger.error(f"❌ Failed to clone info-master repository: {output}")
            # Clean up the temp directory if clone failed
            if os.path.exists(self.info_master_temp_dir):
                shutil.rmtree(self.info_master_temp_dir)
            self.info_master_temp_dir = None
            return None

    def analyze_repositories(self, repos_path: Path, allow_empty: bool = False) -> dict[str, Any]:
        """
        Main analysis workflow.

        Coordinates all phases of repository analysis:
        1. Clone info-master for additional context
        2. Initialize report data structure
        3. Discover all repositories
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
                "and report generation, or pass allow_empty=True if an empty "
                "result is expected."
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

    def generate_reports(self, repos_path: Path, output_dir: Path) -> dict[str, Path]:
        """
        Generate complete reports (JSON, Markdown, HTML, ZIP).

        This is a convenience method that combines analysis and rendering into
        a single call. It:
        1. Analyzes all repositories
        2. Generates JSON report
        3. Generates Markdown report
        4. Generates HTML report (if enabled)
        5. Saves resolved configuration
        6. Creates ZIP bundle (if enabled)

        Args:
            repos_path: Path to directory containing repositories
            output_dir: Path to output directory for generated reports

        Returns:
            Dictionary mapping output type to file path for all generated files
        """
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Analyze repositories
        report_data = self.analyze_repositories(repos_path)

        project = self.config["project"]
        json_path = output_dir / "report_raw.json"
        markdown_path = output_dir / "report.md"
        html_path = output_dir / "report.html"
        config_path = output_dir / "config_resolved.json"

        generated_files = {}

        # Generate JSON report
        self.renderer.render_json_report(report_data, json_path)
        generated_files["json"] = json_path

        # Generate Markdown report
        self.renderer.render_markdown_report(report_data, markdown_path)
        generated_files["markdown"] = markdown_path

        # Generate HTML report (if not disabled)
        html_output_config = self.config.get("output", {})
        if not html_output_config.get("no_html", False):
            self.renderer.render_html_report(report_data, html_path)
            generated_files["html"] = html_path

        save_resolved_config(self.config, config_path)
        generated_files["config"] = config_path

        # Create ZIP bundle (if not disabled)
        zip_output_config = self.config.get("output", {})
        if not zip_output_config.get("no_zip", False):
            zip_path = create_report_bundle(output_dir, project, self.logger)
            generated_files["zip"] = zip_path

        return generated_files

    def _determine_gerrit_server(self, repos_path: Path) -> str:
        """
        Determine the Gerrit server name from the repositories path.

        The repos_path is typically the Gerrit server hostname (e.g., gerrit.onap.org)
        or contains it as the directory name.

        Args:
            repos_path: Path to the repositories directory

        Returns:
            Gerrit server name (e.g., "gerrit.onap.org", "git.opendaylight.org")
        """
        # Check if the directory name itself is a Gerrit server
        dir_name = repos_path.name

        # Common Gerrit server patterns
        if dir_name.startswith("gerrit.") or dir_name.startswith("git."):
            self.logger.debug(f"Gerrit server determined from directory name: {dir_name}")
            return dir_name

        # Check if there's a gerrit configuration or .gitreview file
        # that might indicate the server
        gitreview_path = repos_path / ".gitreview"
        if gitreview_path.exists():
            try:
                with open(gitreview_path) as f:
                    for line in f:
                        if line.startswith("host="):
                            server = line.split("=", 1)[1].strip()
                            self.logger.debug(f"Gerrit server from .gitreview: {server}")
                            return server
            except Exception as e:
                self.logger.debug(f"Could not read .gitreview: {e}")

        # Fallback: use the directory name
        self.logger.warning(
            f"Could not determine Gerrit server from {repos_path}, using directory name: {dir_name}"
        )
        return dir_name

    def _discover_repositories(self, repos_path: Path) -> list[Path]:
        """
        Find all repository directories recursively with no artificial depth limit.

        Args:
            repos_path: Root path to search for repositories

        Returns:
            List of paths to discovered Git repositories, sorted by depth
            (deepest first) to ensure child projects get processed before parents

        Raises:
            FileNotFoundError: If repos_path does not exist
        """
        if not repos_path.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repos_path}")

        self.logger.debug(f"Discovering repositories recursively under: {repos_path}")

        repo_dirs: list[Path] = []
        access_errors = 0

        # Use rglob to discover all .git directories without a depth limit
        try:
            for git_dir in repos_path.rglob(".git"):
                try:
                    repo_dir = self._validate_discovered_repo(git_dir, repos_path)
                    if repo_dir is not None:
                        repo_dirs.append(repo_dir)
                except (PermissionError, OSError) as e:
                    access_errors += 1
                    self.logger.debug(f"Cannot access potential repository at {git_dir}: {e}")
        except (PermissionError, OSError) as e:
            self.logger.warning(f"Error during repository discovery: {e}")

        # Deduplicate and sort results by path depth (deepest first) to ensure
        # child projects get processed before parent projects for Jenkins job allocation
        unique_repos = list({p.resolve() for p in repo_dirs})
        unique_repos.sort(key=lambda p: (-len(p.parts), str(p)))

        self.logger.info(f"Discovered {len(unique_repos)} git repositories")
        if access_errors:
            self.logger.debug(f"Encountered {access_errors} access errors during discovery")

        return unique_repos

    def _validate_discovered_repo(self, git_dir: Path, repos_path: Path) -> Path | None:
        """Resolve a discovered ``.git`` entry to its repository directory.

        Logs the discovery and, when a Gerrit projects cache is available,
        notes whether the repository is present in it.

        Returns:
            The repository directory, or None if the ``.git`` entry no longer
            exists.
        """
        if not git_dir.exists():
            return None

        repo_dir = git_dir.parent

        # Use relative path from repos_path for clean logging (fallback to absolute)
        try:
            rel_path = str(repo_dir.relative_to(repos_path))
        except ValueError:
            rel_path = str(repo_dir)

        self.logger.debug(f"Found git repository: {rel_path}")

        # Validate against Gerrit API cache if available
        cache = getattr(self.git_collector, "gerrit_projects_cache", None)
        if cache and rel_path in cache:
            self.logger.debug(f"Verified {rel_path} exists in Gerrit")
        elif cache:
            self.logger.warning(f"Repository {rel_path} not found in Gerrit API cache")

        return repo_dir

    def _analyze_repositories_parallel(self, repo_dirs: list[Path]) -> list[dict[str, Any]]:
        """
        Analyze repositories with optional concurrency.

        Args:
            repo_dirs: List of repository paths to analyze

        Returns:
            List of analysis results (metrics or error records)
        """
        performance_config = self.config.get("performance", {})
        max_workers = performance_config.get("max_workers", 8)

        if max_workers == 1:
            # Sequential processing
            return [self._analyze_single_repository(repo_dir) for repo_dir in repo_dirs]

        # Concurrent processing
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_repo = {
                executor.submit(self._analyze_single_repository, repo_dir): repo_dir
                for repo_dir in repo_dirs
            }

            for future in concurrent.futures.as_completed(future_to_repo):
                repo_dir = future_to_repo[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Failed to analyze {repo_dir.name}: {e}")
                    results.append(
                        {
                            "error": str(e),
                            "repo": repo_dir.name,
                            "category": "analysis_failure",
                        }
                    )

        return results

    def _analyze_single_repository(self, repo_path: Path) -> dict[str, Any]:
        """
        Analyze a single repository.

        Args:
            repo_path: Path to repository to analyze

        Returns:
            Repository metrics dictionary or error record
        """
        try:
            self.logger.debug(f"Analyzing repository: {repo_path.name}")

            # Collect Git metrics
            repo_metrics = self.git_collector.collect_repo_git_metrics(repo_path)

            # Scan features
            repo_features = self.feature_registry.detect_features(repo_path)
            repo_metrics["repository"]["features"] = repo_features

            return dict(repo_metrics)

        except Exception as e:
            self.logger.error(f"Error analyzing {repo_path.name}: {e}")
            return {
                "error": str(e),
                "repo": repo_path.name,
                "category": "repository_analysis",
            }

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
