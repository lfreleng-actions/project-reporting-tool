# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Project metadata, terminology and global summary context builders.

Holds the ``RenderContext`` methods that describe the project itself
(name, generation timestamp, project type, terminology, repository URLs)
and the aggregate summary statistics shown at the top of a report.
"""

from datetime import datetime
from typing import Any

from ..formatters import format_number
from .shared import ContextMixinBase


class ProjectContextMixin(ContextMixinBase):
    """Project metadata and global summary sections of the render context."""

    def _build_project_context(self) -> dict[str, Any]:
        """Build project metadata context."""
        project_name = self.data.get("project", "Repository Analysis")

        if isinstance(project_name, dict):
            project_name = project_name.get("name", "Repository Analysis")

        generated_at = self.data.get("generated_at", "")
        if not generated_at:
            metadata = self.data.get("metadata", {})
            generated_at = metadata.get("generated_at", "")

        generated_at_formatted = "Unknown"
        if generated_at:
            try:
                dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
                generated_at_formatted = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except (ValueError, AttributeError):
                generated_at_formatted = str(generated_at)

        metadata = self.data.get("metadata", {})
        report_version = metadata.get("report_version", "")

        # Detect project type from configuration
        # Priority: gerrit.host exists -> "gerrit", otherwise -> "github"
        project_type = self._detect_project_type()

        terminology = self._build_terminology(project_type)

        result = {
            "name": project_name,
            "schema_version": self.data.get("schema_version", "1.0.0"),
            "generated_at": generated_at,
            "generated_at_formatted": generated_at_formatted,
            "report_version": report_version,
            "project_type": project_type,
            "terminology": terminology,
        }

        return result

    def _detect_project_type(self) -> str:
        """
        Detect project type from configuration.

        Returns:
            "gerrit" if gerrit.host is configured, "github" otherwise
        """
        gerrit_config = self.config.get("gerrit", {})
        gerrit_host = gerrit_config.get("host", "")

        # If gerrit.host exists and is non-empty, it's a Gerrit project
        if gerrit_host:
            return "gerrit"

        # Otherwise, it's a GitHub-native project
        return "github"

    def _build_terminology(self, project_type: str) -> dict[str, str]:
        """
        Build terminology dictionary based on project type.

        Args:
            project_type: "gerrit" or "github"

        Returns:
            Dictionary with terminology strings for templates
        """
        if project_type == "gerrit":
            return {
                "repository": "Gerrit Project",
                "repositories": "Gerrit Projects",
                "source_system": "Gerrit",
            }
        else:  # github
            return {
                "repository": "Repository",
                "repositories": "Repositories",
                "source_system": "GitHub",
            }

    def _build_repository_url(
        self, project_name: str, host: str, path_prefix: str, project_type: str
    ) -> str:
        """
        Build URL to repository based on project type.

        Args:
            project_name: Repository/project name
            host: Host (Gerrit server or GitHub org)
            path_prefix: Path prefix for Gerrit (e.g., "/r", "/gerrit")
            project_type: "gerrit" or "github"

        Returns:
            Full URL to repository
        """
        if not host or project_name == "Unknown":
            return ""

        if project_type == "gerrit":
            # Gerrit admin URL format
            # Examples:
            #   https://gerrit.onap.org/r/admin/repos/oom,general
            #   https://git.opendaylight.org/gerrit/admin/repos/releng/autorelease,general
            # aislop-ignore-next-line hardcoded-url -- scheme prefix on dynamic host, not a fixed endpoint
            return f"https://{host}{path_prefix}/admin/repos/{project_name},general"
        else:  # github
            # GitHub repository URL format
            # For GitHub-native projects:
            #   - gerrit_host contains the GitHub org name
            #   - gerrit_project contains the repo name
            # Example: https://github.com/opennetworkinglab/aether
            return f"https://github.com/{host}/{project_name}"

    def _build_summary_context(self) -> dict[str, Any]:
        """Build summary statistics context."""
        summaries = self.data.get("summaries", {})
        counts = summaries.get("counts", {})
        repositories = self.data.get("repositories", [])

        # Calculate totals from actual repository data. Time windows overlap, so
        # only the configured reporting window contributes to LOC totals.
        reporting_period = summaries.get("reporting_period", {})
        primary_window = reporting_period.get(
            "window_name", self.config.get("primary_reporting_window", "last_365")
        )
        total_commits = 0
        total_lines_added = 0
        total_lines_removed = 0

        for repo in repositories:
            # Handle commits - try new format first (total_commits_ever), fall back to old (total_commits)
            total_commits += repo.get("total_commits_ever", repo.get("total_commits", 0))

            # Handle LOC - use the primary window in the new format, then fall
            # back to the old direct fields when no matching window exists.
            loc_stats = repo.get("loc_stats", {})
            window_data = loc_stats.get(primary_window) if isinstance(loc_stats, dict) else None
            if isinstance(window_data, dict):
                total_lines_added += window_data.get("added", 0)
                total_lines_removed += window_data.get("removed", 0)
            else:
                # Old format: direct fields on repository
                total_lines_added += repo.get("total_lines_added", 0)
                total_lines_removed += repo.get("total_lines_removed", 0)

        # Get counts from summaries
        # Handle both 'repositories_analyzed' (old) and 'total_repositories' (new)
        repositories_analyzed = counts.get(
            "repositories_analyzed", counts.get("total_repositories", 0)
        )
        total_repositories = counts.get(
            "total_repositories", counts.get("total_gerrit_projects", repositories_analyzed)
        )
        current_count = counts.get("current_repositories", 0)
        active_count = counts.get("active_repositories", 0)
        inactive_count = counts.get("inactive_repositories", 0)
        no_commit_count = counts.get("no_commit_repositories", 0)

        # Count unique authors - try summaries.counts first, then authors dict
        unique_authors = counts.get("unique_contributors", len(self.data.get("authors", {})))

        # Calculate percentages (avoid division by zero)
        def calc_percentage(part: int, total: int) -> float:
            return (part / total * 100) if total > 0 else 0.0

        current_pct = calc_percentage(current_count, repositories_analyzed)
        active_pct = calc_percentage(active_count, repositories_analyzed)
        inactive_pct = calc_percentage(inactive_count, repositories_analyzed)
        no_commit_pct = calc_percentage(no_commit_count, repositories_analyzed)

        return {
            "repositories_analyzed": repositories_analyzed,
            "total_repositories": total_repositories,
            "unique_contributors": unique_authors,
            "total_commits": total_commits,
            "total_commits_formatted": format_number(total_commits),
            "total_organizations": counts.get("total_organizations", 0),
            "current_count": current_count,
            "current_percentage": current_pct,
            "active_count": active_count,
            "active_percentage": active_pct,
            "inactive_count": inactive_count,
            "inactive_percentage": inactive_pct,
            "no_commit_count": no_commit_count,
            "no_commit_percentage": no_commit_pct,
            "total_lines_added": total_lines_added,
            "total_lines_added_formatted": format_number(total_lines_added),
            "total_lines_removed": total_lines_removed,
            "total_lines_removed_formatted": format_number(total_lines_removed),
            "net_lines": total_lines_added - total_lines_removed,
            "net_lines_formatted": format_number(total_lines_added - total_lines_removed),
        }
