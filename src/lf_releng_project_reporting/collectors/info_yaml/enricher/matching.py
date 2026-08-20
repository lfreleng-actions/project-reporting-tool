# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Repository matching and Git-data application for the enricher.

Builds the Gerrit-project lookup, matches INFO.yaml projects to Git
repositories, and derives committer activity status and colour from the
most recent commit across the matched repositories.
"""

import logging
from typing import Any

from domain.info_yaml import CommitterInfo, ProjectInfo


class EnricherMatchingMixin:
    """Git repository matching and activity-status derivation."""

    # Assigned by InfoYamlEnricher.__init__; declared here for type checking.
    logger: logging.Logger
    activity_windows: dict[str, int]

    def _build_repo_lookup(self, git_metrics: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """
        Build a lookup dictionary from Git metrics.

        Args:
            git_metrics: List of repository metrics

        Returns:
            Dictionary mapping Gerrit project path to metrics
        """
        lookup = {}

        for metrics in git_metrics:
            repo_info = metrics.get("repository", {})
            gerrit_project = repo_info.get("gerrit_project", "")

            if gerrit_project:
                lookup[gerrit_project] = metrics

        self.logger.debug(f"Built repo lookup with {len(lookup)} repositories")
        return lookup

    def _find_matching_repos(
        self,
        project: ProjectInfo,
        repo_lookup: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Find Git repositories matching a project.

        Tries:
        1. Exact match on project_path
        2. Match on listed repositories

        Args:
            project: ProjectInfo object
            repo_lookup: Repository lookup dictionary

        Returns:
            List of matching repository metrics
        """
        matched = []

        # Try exact match on project path
        if project.project_path in repo_lookup:
            matched.append(repo_lookup[project.project_path])
            self.logger.debug(f"Matched project '{project.project_name}' via project_path")

        # Try matching against listed repositories
        for repo_name in project.repositories:
            if repo_name in repo_lookup:
                # Avoid duplicates
                repo_metrics = repo_lookup[repo_name]
                if repo_metrics not in matched:
                    matched.append(repo_metrics)
                    self.logger.debug(
                        f"Matched project '{project.project_name}' via repository '{repo_name}'"
                    )

        return matched

    def _enrich_with_git_data(
        self,
        project: ProjectInfo,
        matched_repos: list[dict[str, Any]],
    ) -> ProjectInfo:
        """
        Enrich project with Git data from matched repositories.

        Args:
            project: ProjectInfo object
            matched_repos: List of matching repository metrics

        Returns:
            Enriched ProjectInfo object
        """
        # Find most recent activity across all repos
        most_recent_days = self._find_most_recent_activity(matched_repos)

        # Calculate activity status and color
        status, color = self._calculate_activity_status(most_recent_days)

        # Apply to all committers (project-level coloring)
        enriched_committers = []
        for committer in project.committers:
            enriched_committer = CommitterInfo(
                name=committer.name,
                email=committer.email,
                company=committer.company,
                id=committer.id,
                timezone=committer.timezone,
                activity_status=status,
                activity_color=color,
                days_since_last_commit=most_recent_days,
            )
            enriched_committers.append(enriched_committer)

        project.committers = enriched_committers
        project.has_git_data = True
        project.project_days_since_last_commit = most_recent_days

        self.logger.debug(
            f"Enriched project '{project.project_name}': "
            f"status={status}, color={color}, days={most_recent_days}"
        )

        return project

    def _mark_as_unknown(self, project: ProjectInfo) -> ProjectInfo:
        """
        Mark project committers as unknown activity.

        Args:
            project: ProjectInfo object

        Returns:
            ProjectInfo with committers marked as unknown
        """
        enriched_committers = []
        for committer in project.committers:
            enriched_committer = CommitterInfo(
                name=committer.name,
                email=committer.email,
                company=committer.company,
                id=committer.id,
                timezone=committer.timezone,
                activity_status="unknown",
                activity_color="gray",
                days_since_last_commit=None,
            )
            enriched_committers.append(enriched_committer)

        project.committers = enriched_committers
        project.has_git_data = False
        project.project_days_since_last_commit = None

        self.logger.debug(f"No Git data for project '{project.project_name}', marked as unknown")

        return project

    def _find_most_recent_activity(self, matched_repos: list[dict[str, Any]]) -> int | None:
        """
        Find the most recent activity across multiple repositories.

        Args:
            matched_repos: List of repository metrics

        Returns:
            Days since most recent commit, or None if no data
        """
        most_recent = None

        for repo_metrics in matched_repos:
            repo_info = repo_metrics.get("repository", {})
            days_since = repo_info.get("days_since_last_commit")

            if days_since is not None and (most_recent is None or days_since < most_recent):
                most_recent = days_since

        return most_recent

    def _calculate_activity_status(self, days_since_commit: int | None) -> tuple[str, str]:
        """
        Calculate activity status and color based on days since last commit.

        Args:
            days_since_commit: Days since last commit (None if no data)

        Returns:
            Tuple of (status, color):
            - ("current", "green"): Active within current window
            - ("active", "orange"): Active within active window
            - ("inactive", "red"): No activity beyond active window
            - ("unknown", "gray"): No Git data available
        """
        if days_since_commit is None:
            return ("unknown", "gray")

        current_window = self.activity_windows.get("current", 365)
        active_window = self.activity_windows.get("active", 1095)

        if days_since_commit <= current_window:
            return ("current", "green")
        elif days_since_commit <= active_window:
            return ("active", "orange")
        else:
            return ("inactive", "red")
