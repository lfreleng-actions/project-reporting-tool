# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Global aggregation orchestration.

Owns the aggregator configuration and drives classification, rollups and
ranking to produce the global summary block consumed by the reporter.
"""

import logging
from typing import Any

from .classification import AggregatorClassificationMixin
from .ranking import AggregatorRankingMixin
from .rollups import AggregatorRollupsMixin


class DataAggregator(
    AggregatorClassificationMixin,
    AggregatorRollupsMixin,
    AggregatorRankingMixin,
):
    """Handles aggregation of repository data into global summaries."""

    def __init__(self, config: dict[str, Any], logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger

    def aggregate_global_data(self, repo_metrics: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Aggregate all repository metrics into global summaries.

        Performs comprehensive aggregation including:
        - Active/inactive classification
        - Author and organization rollups
        - Top/least active repository identification
        - Contributor leaderboards
        - Age distribution analysis
        """
        self.logger.info("Starting global data aggregation")

        # Debug: Analyze repository commit status
        self._analyze_repository_commit_status(repo_metrics)

        # Primary time window for rankings (configurable, defaults to last_365)
        primary_window = self.config.get("primary_reporting_window", "last_365")
        primary_window_days = self._resolve_primary_window_days(primary_window)

        # Classify repositories by unified activity status
        classification = self._classify_repositories(repo_metrics, primary_window)
        current_repos = classification["current"]
        active_repos = classification["active"]
        inactive_repos = classification["inactive"]
        no_commit_repos = classification["no_commit"]
        total_commits = classification["total_commits"]
        total_lines_added = classification["total_lines_added"]

        # Aggregate author and organization data
        self.logger.info("Computing author rollups")
        authors = self.compute_author_rollups(repo_metrics)

        self.logger.info("Computing organization rollups")
        organizations = self.compute_org_rollups(authors)

        # Build complete repository list (all repositories sorted by activity)
        # Combine all activity status repositories for comprehensive view
        all_repos = current_repos + active_repos + inactive_repos

        # Sort all repositories by commits in primary window (descending)
        all_repositories_by_activity = self.rank_entities(
            all_repos,
            f"commit_counts.{primary_window}",
            reverse=True,
            limit=None,  # No limit - show all repositories
        )

        # Keep separate lists for different activity statuses
        top_current = self.rank_entities(
            current_repos, f"commit_counts.{primary_window}", reverse=True, limit=None
        )

        top_active = self.rank_entities(
            active_repos, f"commit_counts.{primary_window}", reverse=True, limit=None
        )

        least_active = self.rank_entities(
            inactive_repos, "days_since_last_commit", reverse=True, limit=None
        )

        top_contributors_commits = self.rank_entities(
            authors, f"commits.{primary_window}", reverse=True, limit=None
        )

        top_contributors_loc = self.rank_entities(
            authors, f"lines_net.{primary_window}", reverse=True, limit=None
        )

        top_organizations = self.rank_entities(
            organizations, f"commits.{primary_window}", reverse=True, limit=None
        )

        summaries = {
            "reporting_period": {
                "window_name": primary_window,
                "days": primary_window_days,
            },
            "counts": {
                "total_repositories": len(repo_metrics),
                "current_repositories": len(current_repos),
                "active_repositories": len(active_repos),
                "inactive_repositories": len(inactive_repos),
                "no_commit_repositories": len(no_commit_repos),
                "total_commits": total_commits,
                "total_lines_added": total_lines_added,
                "total_authors": len(authors),
                "total_organizations": len(organizations),
            },
            "activity_status_distribution": {
                "current": self._activity_distribution_entries(current_repos),
                "active": self._activity_distribution_entries(active_repos),
                "inactive": self._activity_distribution_entries(inactive_repos),
            },
            "top_current_repositories": top_current,
            "top_active_repositories": top_active,
            "least_active_repositories": least_active,
            "all_repositories": all_repositories_by_activity,
            "no_commit_repositories": no_commit_repos,
            "top_contributors_commits": top_contributors_commits,
            "top_contributors_loc": top_contributors_loc,
            "top_organizations": top_organizations,
        }

        self.logger.info(
            f"Aggregation complete: {len(current_repos)} current, {len(active_repos)} active, {len(inactive_repos)} inactive, {len(no_commit_repos)} no-commit repositories"
        )
        self.logger.info(f"Found {len(authors)} authors across {len(organizations)} organizations")

        return summaries

    def _resolve_primary_window_days(self, primary_window: str) -> int:
        """Resolve the day count for the configured primary reporting window.

        Falls back to 365 days (with a warning) when the window is missing or
        malformed in the configuration.
        """
        time_windows = self.config.get("time_windows", {})
        window_config = time_windows.get(primary_window, {})

        if isinstance(window_config, dict) and "days" in window_config:
            return int(window_config["days"])
        if isinstance(window_config, int):
            return window_config

        # Fallback to 365 if window not found
        self.logger.warning(
            f"Primary reporting window '{primary_window}' not found in time_windows, "
            "defaulting to 365 days"
        )
        return 365
