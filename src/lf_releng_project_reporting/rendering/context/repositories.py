# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Repository table context builder.

Holds the ``RenderContext`` method that transforms per-repository records
into the rows rendered by the repositories section of a report.
"""

from typing import Any

from .shared import ContextMixinBase


class RepositoriesContextMixin(ContextMixinBase):
    """Repositories section of the render context."""

    def _build_repositories_context(self) -> dict[str, Any]:
        """Build repositories section context."""
        summaries = self.data.get("summaries", {})

        all_repos_raw = summaries.get("all_repositories", [])
        no_commit_repos = summaries.get("no_commit_repositories", [])

        # Transform repository data for templates
        all_repos = []
        for repo in all_repos_raw:
            summaries = self.data.get("summaries", {})
            reporting_period = summaries.get("reporting_period", {})
            primary_window = reporting_period.get("window_name", "last_365")

            unique_contributors_dict = repo.get("unique_contributors", {})
            if isinstance(unique_contributors_dict, dict):
                unique_contributors_value = unique_contributors_dict.get(primary_window, 0)
            else:
                # Fallback to authors list if unique_contributors is not time-windowed
                authors = repo.get("authors", [])
                unique_contributors_value = len(authors)

            # Extract LOC stats from time windows

            loc_stats = repo.get("loc_stats", {})
            loc_window = loc_stats.get(primary_window, {})
            total_lines_added = loc_window.get("added", 0)
            total_lines_removed = loc_window.get("removed", 0)
            net_lines = loc_window.get("net", 0)

            # Get all-time LOC from total_loc field (added in schema v1.3.0)
            total_loc = repo.get("total_loc", 0)

            last_commit_timestamp = repo.get("last_commit_timestamp", "")
            last_commit_date = "N/A"
            if last_commit_timestamp:
                try:
                    from datetime import datetime

                    dt = datetime.fromisoformat(last_commit_timestamp.replace("Z", "+00:00"))
                    last_commit_date = dt.strftime("%Y-%m-%d")
                except (ValueError, AttributeError):
                    last_commit_date = "N/A"

            # Map activity status to emoji for display
            activity_status_raw = repo.get("activity_status", "unknown")
            status_emoji_map = {"current": "✅", "active": "☑️", "inactive": "🛑", "unknown": "🛑"}
            activity_status_emoji = status_emoji_map.get(activity_status_raw, "🛑")

            gerrit_project_name = repo.get("gerrit_project", "Unknown")
            gerrit_host = repo.get("gerrit_host", "")
            gerrit_path_prefix = repo.get("gerrit_path_prefix", "")

            # Build repository URL based on project type
            # Detect if this is a GitHub-native project (no gerrit_path_prefix typically)
            project_type = self._detect_project_type()
            repo_url = self._build_repository_url(
                gerrit_project_name, gerrit_host, gerrit_path_prefix, project_type
            )

            jenkins_data = repo.get("jenkins", {})
            jenkins_jobs_count = len(jenkins_data.get("jobs", []))

            transformed = {
                "gerrit_project": gerrit_project_name,
                "name": gerrit_project_name,
                "gerrit_host": gerrit_host,
                "gerrit_url": repo_url,
                "activity_status": activity_status_emoji,  # Use emoji instead of text
                "activity_status_text": activity_status_raw,  # Preserve text for sorting/filtering
                "last_commit_age": repo.get("days_since_last_commit", 0),
                "days_inactive": repo.get("days_since_last_commit", 0),
                "last_commit_date": last_commit_date,
                "total_commits": repo.get("total_commits_ever", 0),
                "unique_contributors": unique_contributors_value,
                "jenkins_jobs_count": jenkins_jobs_count,
                "state": repo.get("state", "UNKNOWN"),
                "total_lines_added": total_lines_added,
                "total_lines_removed": total_lines_removed,
                "net_lines": net_lines,
                "total_loc": total_loc,
            }
            all_repos.append(transformed)

        # Sort repositories by commit count (descending)
        all_repos.sort(key=lambda x: x.get("total_commits", 0), reverse=True)

        # Sort repositories by activity (use text version for filtering)
        active_repos = [r for r in all_repos if r.get("activity_status_text") == "active"]
        inactive_repos = [r for r in all_repos if r.get("activity_status_text") == "inactive"]
        current_repos = [r for r in all_repos if r.get("activity_status_text") == "current"]

        return {
            "all": all_repos,
            "all_count": len(all_repos),
            "active": active_repos,
            "active_count": len(active_repos),
            "current": current_repos,
            "current_count": len(current_repos),
            "inactive": inactive_repos,
            "inactive_count": len(inactive_repos),
            "no_commits": no_commit_repos,
            "no_commits_count": len(no_commit_repos),
            "has_repositories": len(all_repos) > 0,
        }
