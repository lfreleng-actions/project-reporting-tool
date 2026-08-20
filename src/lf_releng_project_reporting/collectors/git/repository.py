# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Per-repository Git metric collection."""

import contextlib
from pathlib import Path
from typing import Any

from .base import _CollectorState
from .commands import safe_git_command


class _RepositoryMetricsMixin(_CollectorState):
    """Collect repository identity, size, commit, and Jenkins metrics."""

    def __del__(self):
        """Cleanup Gerrit client when GitDataCollector is destroyed."""
        if hasattr(self, "gerrit_client") and self.gerrit_client:
            with contextlib.suppress(Exception):
                self.gerrit_client.close()

    def _count_total_loc(self, repo_path: Path) -> int:
        """
        Count total lines of code in the current repository HEAD.

        Uses git diff --shortstat against the empty tree to efficiently count
        total lines. This is much faster than reading each file individually.

        Args:
            repo_path: Path to the git repository

        Returns:
            Total line count in current repository, or 0 if unable to count
        """
        try:
            # Use git diff against empty tree (4b825dc...) to get total lines
            # This is the hash of the empty tree in git
            # --shortstat gives us total files, insertions, deletions
            empty_tree = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

            # Get line count using git diff against empty tree
            # This shows all lines as insertions (since we're diffing from nothing)
            diff_cmd = ["git", "diff", "--shortstat", empty_tree, "HEAD"]
            success, output = safe_git_command(diff_cmd, repo_path, self.logger)

            if not success or not output:
                # Try alternative method: check if repo is empty
                rev_list_cmd = ["git", "rev-list", "-n", "1", "HEAD"]
                has_commits, _ = safe_git_command(rev_list_cmd, repo_path, self.logger)
                if not has_commits:
                    self.logger.debug(f"Repository {repo_path.name} has no commits")
                    return 0
                self.logger.debug(f"Could not count LOC for {repo_path.name}")
                return 0

            # Parse output like: "123 files changed, 45678 insertions(+)"
            # We want the insertions number
            total_lines = 0
            if "insertion" in output:
                parts = output.split(",")
                for part in parts:
                    if "insertion" in part:
                        num_str = part.strip().split()[0]
                        try:
                            total_lines = int(num_str)
                        except ValueError:
                            self.logger.debug(f"Could not parse line count from: {part}")
                            return 0
                        break

            self.logger.debug(f"Counted {total_lines} total lines in {repo_path.name}")
            return total_lines

        except Exception as e:
            self.logger.warning(f"Error counting total LOC for {repo_path.name}: {e}")
            return 0

    def _resolve_repository_identity(self, repo_path: Path) -> tuple[str, str, str, str]:
        """Resolve the repository identifier and Gerrit/GitHub URL metadata.

        Returns:
            Tuple of ``(repo_identifier, gerrit_host, gerrit_url,
            gerrit_path_prefix)``. GitHub-native projects derive the host from
            the org directory name and build a github.com URL.
        """
        gerrit_config = self.config.get("gerrit", {})
        gerrit_enabled = gerrit_config.get("enabled", False)

        # Extract repository information (Gerrit or GitHub)
        if self.repos_path:
            # Use relative path from repos_path as repository identifier
            repo_identifier = str(repo_path.relative_to(self.repos_path))
        else:
            repo_identifier = self._extract_gerrit_project(repo_path)

        if gerrit_enabled:
            # Gerrit project - extract Gerrit-specific information
            gerrit_host = self._extract_gerrit_host(repo_path)
            gerrit_url = self._derive_gerrit_url(repo_path)
            gerrit_path_prefix = self._extract_gerrit_path_prefix()
            self.logger.debug(f"Collecting Git metrics for Gerrit project: {repo_identifier}")
        else:
            # GitHub-native project - use org name and construct GitHub URL
            # For GitHub projects, repos_path is the org name (e.g., /tmp/opennetworkinglab)
            if self.repos_path:
                gerrit_host = self.repos_path.name  # org name
                repo_name = repo_path.name
                gerrit_url = f"https://github.com/{gerrit_host}/{repo_name}"
            else:
                gerrit_host = "unknown-github-org"
                gerrit_url = ""
            gerrit_path_prefix = ""  # GitHub doesn't use path prefix
            self.logger.debug(f"Collecting Git metrics for GitHub repository: {repo_identifier}")

        return repo_identifier, gerrit_host, gerrit_url, gerrit_path_prefix

    def _init_repo_metrics(
        self,
        repo_path: Path,
        gerrit_project: str,
        gerrit_host: str,
        gerrit_url: str,
        gerrit_path_prefix: str,
    ) -> dict[str, Any]:
        """Build the empty per-repository metrics structure for all time windows."""
        return {
            "repository": {
                "gerrit_project": gerrit_project,  # PRIMARY identifier
                "gerrit_host": gerrit_host,
                "gerrit_url": gerrit_url,
                "gerrit_path_prefix": gerrit_path_prefix,  # Discovered URL path (e.g., "/r")
                "local_path": str(repo_path),  # Secondary, for internal use
                "last_commit_timestamp": None,
                "days_since_last_commit": None,
                "activity_status": "inactive",  # "current", "active", or "inactive"
                "has_any_commits": False,  # Track if repo has ANY commits
                "total_commits_ever": 0,  # Total commits across all history
                "total_loc": 0,  # Total lines of code in current repository HEAD (all-time)
                "commit_counts": dict.fromkeys(self.time_windows, 0),
                "loc_stats": {
                    window: {"added": 0, "removed": 0, "net": 0} for window in self.time_windows
                },
                "unique_contributors": {window: set() for window in self.time_windows},
                "features": {},
            },
            "authors": {},  # email -> author metrics
            "errors": [],  # List[str]
        }

    def _attach_jenkins_jobs(self, repo_data: dict[str, Any], gerrit_project: str) -> None:
        """Attach enriched Jenkins job data to the repository metrics.

        Each job is normalized to include a ``status`` field for consistent
        downstream access.
        """
        jenkins_jobs = self._get_jenkins_jobs_for_repo(gerrit_project)

        # Store computed status for each job for consistent access
        enriched_jobs = []
        for job in jenkins_jobs:
            if isinstance(job, dict) and "status" in job:
                enriched_jobs.append(job)
            else:
                # Fallback for jobs missing status (shouldn't happen with new structure)
                enriched_job = dict(job) if isinstance(job, dict) else {"name": str(job)}
                enriched_job["status"] = "unknown"
                enriched_jobs.append(enriched_job)

        repo_data["jenkins"] = {
            "jobs": enriched_jobs,
            "job_count": len(enriched_jobs),
            "has_jobs": len(enriched_jobs) > 0,
        }

    def collect_repo_git_metrics(self, repo_path: Path) -> dict[str, Any]:
        """
        Extract Git metrics for a single repository across all time windows.

        Uses git log --numstat --date=iso --pretty=format for unified traversal.
        Single pass filtering commits into all time windows.
        Collects: timestamps, author name/email, added/removed lines.
        Returns structured metrics or error descriptor.
        """
        repo_identifier, gerrit_host, gerrit_url, gerrit_path_prefix = (
            self._resolve_repository_identity(repo_path)
        )

        # Use repo_identifier for gerrit_project field (works for both types)
        gerrit_project = repo_identifier

        metrics = self._init_repo_metrics(
            repo_path, gerrit_project, gerrit_host, gerrit_url, gerrit_path_prefix
        )

        try:
            # Check if this is actually a git repository
            if not (repo_path / ".git").exists():
                errors_list = metrics["errors"]
                assert isinstance(errors_list, list)
                errors_list.append(f"Not a git repository: {repo_path}")
                return metrics

            # Check cache if enabled
            if self.cache_enabled:
                cached_metrics = self._load_from_cache(repo_path)
                if cached_metrics:
                    self.logger.debug(f"Using cached metrics for {gerrit_project}")
                    return cached_metrics

            git_command = [
                "git",
                "log",
                "--numstat",
                "--date=iso",
                "--pretty=format:%H|%ad|%an|%ae|%s",
            ]

            # NOTE: Removed max_history_years filtering to ensure all commit data is captured
            # for accurate total_commits_ever, has_any_commits, and complete contributor data.
            # Time window filtering is applied separately during commit processing.

            success, output = safe_git_command(git_command, repo_path, self.logger)
            if not success:
                metrics["errors"].append(f"Git command failed: {output}")
                return metrics

            commits_data = self._parse_git_log_output(output, gerrit_project)

            metrics["repository"]["total_commits_ever"] = len(commits_data)
            metrics["repository"]["has_any_commits"] = len(commits_data) > 0

            # Count total lines of code in current repository HEAD
            metrics["repository"]["total_loc"] = self._count_total_loc(repo_path)

            for commit_data in commits_data:
                self._update_commit_metrics(commit_data, metrics)

            # Finalize repository metrics
            self._finalize_repo_metrics(metrics, gerrit_project)

            # Convert sets to counts for JSON serialization
            repo_data = metrics["repository"]

            # Add Jenkins job information if available
            if self.jenkins_client:
                self._attach_jenkins_jobs(repo_data, gerrit_project)

            unique_contributors = repo_data["unique_contributors"]
            for window in self.time_windows:
                contributor_set = unique_contributors[window]
                assert isinstance(contributor_set, set)
                unique_contributors[window] = len(contributor_set)

            self.logger.debug(f"Collected {len(commits_data)} commits for {gerrit_project}")

            # Save to cache if enabled
            if self.cache_enabled:
                self._save_cached_metrics(repo_path, metrics)

            return metrics

        except Exception as e:
            self.logger.error(f"Error collecting Git metrics for {gerrit_project}: {e}")
            errors_list = metrics["errors"]
            assert isinstance(errors_list, list)
            errors_list.append(f"Unexpected error: {str(e)}")
            return metrics
