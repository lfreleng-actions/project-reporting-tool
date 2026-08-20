# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Enrichment result statistics.

Summarises a batch of enriched projects: Git-data coverage, committer
activity status/colour counts and URL validation outcomes.
"""

from typing import Any

from domain.info_yaml import ProjectInfo


class EnricherStatisticsMixin:
    """Aggregate reporting over enriched project batches."""

    def get_enrichment_statistics(self, projects: list[ProjectInfo]) -> dict[str, Any]:
        """
        Get statistics about enrichment results.

        Args:
            projects: List of enriched ProjectInfo objects

        Returns:
            Dictionary with enrichment statistics
        """
        stats: dict[str, Any] = {
            "total_projects": len(projects),
            "with_git_data": 0,
            "without_git_data": 0,
            "status_counts": {
                "current": 0,
                "active": 0,
                "inactive": 0,
                "unknown": 0,
            },
            "color_counts": {
                "green": 0,
                "orange": 0,
                "red": 0,
                "gray": 0,
            },
            "url_validation": {
                "total_urls": 0,
                "valid_urls": 0,
                "invalid_urls": 0,
                "no_url": 0,
            },
        }

        for project in projects:
            # Git data
            if project.has_git_data:
                stats["with_git_data"] += 1
            else:
                stats["without_git_data"] += 1

            # Count committer statuses
            for committer in project.committers:
                status = committer.activity_status
                color = committer.activity_color
                stats["status_counts"][status] = stats["status_counts"].get(status, 0) + 1
                stats["color_counts"][color] = stats["color_counts"].get(color, 0) + 1

            # URL validation
            if project.issue_tracking.url:
                stats["url_validation"]["total_urls"] += 1
                if project.issue_tracking.is_valid:
                    stats["url_validation"]["valid_urls"] += 1
                else:
                    stats["url_validation"]["invalid_urls"] += 1
            else:
                stats["url_validation"]["no_url"] += 1

        return stats
