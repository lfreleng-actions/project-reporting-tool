# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Contributor and organization leaderboard context builders.

Holds the ``RenderContext`` methods that rank individual contributors and
their organizations (by commit count and by lines of code) for the
leaderboard sections of a report.
"""

from typing import Any

from .shared import ContextMixinBase


class ContributorsContextMixin(ContextMixinBase):
    """Contributor and organization leaderboard sections of the render context."""

    def _build_contributors_context(self) -> dict[str, Any]:
        """Build contributors leaderboard context."""
        summaries = self.data.get("summaries", {})

        top_commits_raw = summaries.get("top_contributors_commits", [])
        top_loc_raw = summaries.get("top_contributors_loc", [])

        reporting_period = summaries.get("reporting_period", {})
        primary_window = reporting_period.get("window_name", "last_365")

        # Transform contributor data
        # Contributors use time-windowed metrics (dicts with last_30, last_90, etc.)
        top_commits = []
        for contrib in top_commits_raw:
            commits_dict = contrib.get("commits", {})
            # Handle both dict (new format) and int (old format)
            if isinstance(commits_dict, dict):
                total_commits = commits_dict.get(primary_window, 0)
            else:
                total_commits = commits_dict if isinstance(commits_dict, int) else 0

            repos_touched = contrib.get("repositories_touched", {})

            # Extract the count - repositories_touched values are sets stored as strings
            # We need to count the repos, not display the set
            repos_last_3y = repos_touched.get(primary_window, set())
            if isinstance(repos_last_3y, str):
                # If it's a string representation of a set, try to parse it
                # Count commas + 1, or use a safer method
                repos_count = repos_last_3y.count("'") // 2 if repos_last_3y != "set()" else 0
            elif isinstance(repos_last_3y, set):
                repos_count = len(repos_last_3y)
            else:
                repos_count = 0

            # Get LOC stats from time windows (needed for templates)
            lines_added_dict = contrib.get("lines_added", {})
            lines_removed_dict = contrib.get("lines_removed", {})
            lines_net_dict = contrib.get("lines_net", {})

            # Handle both dict (new format) and int (old format)
            if isinstance(lines_added_dict, dict):
                total_lines_added = lines_added_dict.get(primary_window, 0)
            else:
                total_lines_added = lines_added_dict if isinstance(lines_added_dict, int) else 0

            if isinstance(lines_removed_dict, dict):
                total_lines_removed = lines_removed_dict.get(primary_window, 0)
            else:
                total_lines_removed = (
                    lines_removed_dict if isinstance(lines_removed_dict, int) else 0
                )

            if isinstance(lines_net_dict, dict):
                net_lines = lines_net_dict.get(primary_window, 0)
            else:
                net_lines = lines_net_dict if isinstance(lines_net_dict, int) else 0

            # Calculate derived metrics
            delta_loc = total_lines_added + total_lines_removed
            avg_loc_per_commit = (net_lines / total_commits) if total_commits > 0 else 0

            transformed = {
                "name": contrib.get("name", "Unknown"),
                "email": contrib.get("email", ""),
                "total_commits": total_commits,
                "total_lines_added": total_lines_added,
                "total_lines_removed": total_lines_removed,
                "net_lines": net_lines,
                "delta_loc": delta_loc,
                "repositories_count": repos_count,
                "organization": contrib.get("domain", "N/A"),
                "avg_loc_per_commit": avg_loc_per_commit,
            }
            top_commits.append(transformed)

        top_loc = []
        for contrib in top_loc_raw:
            lines_added_dict = contrib.get("lines_added", {})
            lines_removed_dict = contrib.get("lines_removed", {})
            lines_net_dict = contrib.get("lines_net", {})

            total_lines_added = lines_added_dict.get(primary_window, 0)
            total_lines_removed = lines_removed_dict.get(primary_window, 0)
            net_lines = lines_net_dict.get(primary_window, 0)

            # Calculate derived metrics
            delta_loc = total_lines_added + total_lines_removed

            commits_dict = contrib.get("commits", {})
            total_commits = commits_dict.get(primary_window, 0)
            avg_loc_per_commit = (net_lines / total_commits) if total_commits > 0 else 0

            transformed = {
                "name": contrib.get("name", "Unknown"),
                "email": contrib.get("email", ""),
                "total_lines_added": total_lines_added,
                "total_lines_removed": total_lines_removed,
                "net_lines": net_lines,
                "delta_loc": delta_loc,
                "organization": contrib.get("domain", "N/A"),
                "avg_loc_per_commit": avg_loc_per_commit,
            }
            top_loc.append(transformed)

        # Limit to top N (from config or default 30)
        output_config = self.config.get("output", {})
        limit = output_config.get("top_contributors_limit", 30)

        return {
            "top_by_commits": top_commits[:limit],
            "top_by_commits_count": len(top_commits),
            "top_by_loc": top_loc[:limit],
            "top_by_loc_count": len(top_loc),
            "limit": limit,
            "has_contributors": len(top_commits) > 0 or len(top_loc) > 0,
        }

    def _build_organizations_context(self) -> dict[str, Any]:
        """Build organizations leaderboard context."""
        summaries = self.data.get("summaries", {})

        top_orgs_raw = summaries.get("top_organizations", [])

        reporting_period = summaries.get("reporting_period", {})
        primary_window = reporting_period.get("window_name", "last_365")

        # Transform organization data
        # Organizations use domain as the primary identifier
        # All metrics are time-windowed (dicts with last_30, last_90, etc.)
        top_orgs = []
        for org in top_orgs_raw:
            domain = org.get("domain", "Unknown")

            commits_dict = org.get("commits", {})
            # Handle both dict (new format) and int (old format)
            if isinstance(commits_dict, dict):
                total_commits = commits_dict.get(primary_window, 0)
            else:
                total_commits = commits_dict if isinstance(commits_dict, int) else 0

            contributor_count = org.get("contributor_count", 0)

            repos_dict = org.get("repositories_count", {})
            # Handle both dict (new format) and int (old format)
            if isinstance(repos_dict, dict):
                repos_count = repos_dict.get(primary_window, 0)
            else:
                repos_count = repos_dict if isinstance(repos_dict, int) else 0

            lines_added_dict = org.get("lines_added", {})
            lines_removed_dict = org.get("lines_removed", {})
            lines_net_dict = org.get("lines_net", {})

            # Handle both dict (new format) and int (old format)
            if isinstance(lines_added_dict, dict):
                total_lines_added = lines_added_dict.get(primary_window, 0)
            else:
                total_lines_added = lines_added_dict if isinstance(lines_added_dict, int) else 0

            if isinstance(lines_removed_dict, dict):
                total_lines_removed = lines_removed_dict.get(primary_window, 0)
            else:
                total_lines_removed = (
                    lines_removed_dict if isinstance(lines_removed_dict, int) else 0
                )

            if isinstance(lines_net_dict, dict):
                net_lines = lines_net_dict.get(primary_window, 0)
            else:
                net_lines = lines_net_dict if isinstance(lines_net_dict, int) else 0

            # Calculate derived metrics
            delta_loc = total_lines_added + total_lines_removed  # Total lines changed
            avg_loc_per_commit = (net_lines / total_commits) if total_commits > 0 else 0

            transformed = {
                "name": domain,  # Use domain as name
                "domain": domain,
                "unique_contributors": contributor_count,
                "total_commits": total_commits,
                "repositories_count": repos_count,
                "total_lines_added": total_lines_added,
                "total_lines_removed": total_lines_removed,
                "net_lines": net_lines,
                "delta_loc": delta_loc,
                "avg_loc_per_commit": avg_loc_per_commit,
            }
            top_orgs.append(transformed)

        # Limit to top N
        output_config = self.config.get("output", {})
        limit = output_config.get("top_organizations_limit", 30)

        return {
            "top": top_orgs[:limit],
            "total_count": len(top_orgs_raw),
            "limit": limit,
            "has_organizations": len(top_orgs_raw) > 0,
        }
