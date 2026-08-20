# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Repository activity classification for the data aggregator.

Buckets repositories into current/active/inactive/no-commit groups, builds
the activity-distribution entries, and provides the commit-status diagnostic.
"""

import logging
from typing import Any


class AggregatorClassificationMixin:
    """Activity-status classification and commit-status diagnostics."""

    # Assigned by DataAggregator.__init__; declared here for type checking.
    logger: logging.Logger

    def _classify_repositories(
        self, repo_metrics: list[dict[str, Any]], primary_window: str
    ) -> dict[str, Any]:
        """Classify repositories by activity status and total commit/LOC counts.

        Returns a dict with the ``current``, ``active``, ``inactive``, and
        ``no_commit`` repository lists plus ``total_commits`` and
        ``total_lines_added`` for the primary window.
        """
        current_repos: list[dict[str, Any]] = []
        active_repos: list[dict[str, Any]] = []
        inactive_repos: list[dict[str, Any]] = []
        no_commit_repos: list[dict[str, Any]] = []

        total_commits = 0
        total_lines_added = 0

        for repo in repo_metrics:
            days_since_last = repo.get("days_since_last_commit")

            # Count total commits and lines of code
            commit_counts = repo.get("commit_counts", {})
            total_commits += commit_counts.get(primary_window, 0)
            loc_stats = repo.get("loc_stats", {})
            primary_loc_stats = loc_stats.get(primary_window, {})
            total_lines_added += primary_loc_stats.get("added", 0)

            # Repository with no commits at all - separate category
            if not repo.get("has_any_commits", False):
                no_commit_repos.append(repo)
                continue

            # Repository has commits but no days_since_last - treat as inactive
            if days_since_last is None:
                inactive_repos.append(repo)
                continue

            activity_status = repo.get("activity_status", "inactive")
            if activity_status == "current":
                current_repos.append(repo)
            elif activity_status == "active":
                active_repos.append(repo)
            else:
                inactive_repos.append(repo)

        return {
            "current": current_repos,
            "active": active_repos,
            "inactive": inactive_repos,
            "no_commit": no_commit_repos,
            "total_commits": total_commits,
            "total_lines_added": total_lines_added,
        }

    def _activity_distribution_entries(self, repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Build activity-distribution entries, defaulting missing ages to 999999."""
        return [
            {
                "gerrit_project": r.get("gerrit_project", "Unknown"),
                "days_since_last_commit": r.get("days_since_last_commit")
                if r.get("days_since_last_commit") is not None
                else 999999,
            }
            for r in repos
        ]

    def _analyze_repository_commit_status(self, repo_metrics: list[dict[str, Any]]) -> None:
        """Diagnostic function to analyze repository commit status."""
        self.logger.info("=== Repository Analysis ===")

        total_repos = len(repo_metrics)
        repos_with_commits = 0
        repos_no_commits = 0

        sample_no_commit_repos: list[dict[str, Any]] = []

        for repo in repo_metrics:
            repo_name = repo.get("gerrit_project", "Unknown")
            commit_counts = repo.get("commit_counts", {})

            # Check if repository has any commits across all time windows
            has_commits = any(count > 0 for count in commit_counts.values())

            if has_commits:
                repos_with_commits += 1
            else:
                repos_no_commits += 1
                if len(sample_no_commit_repos) < 3:  # Collect sample for detailed analysis
                    sample_no_commit_repos.append(
                        {"gerrit_project": repo_name, "commit_counts": commit_counts}
                    )

        self.logger.info(f"Total repositories: {total_repos}")
        self.logger.info(f"Repositories with commits: {repos_with_commits}")
        self.logger.info(f"Repositories with NO commits: {repos_no_commits}")

        if sample_no_commit_repos:
            self.logger.info("Sample repositories with NO commits:")
            for repo in sample_no_commit_repos:
                self.logger.info(f"  - {repo['gerrit_project']}")
