# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Render context builder for preparing data for template rendering.

This module provides the RenderContext class which transforms raw report data
into a structured context suitable for Jinja2 templates. It handles data
extraction, formatting, and organization.

Phase: 8 - Renderer Modernization (Fixed for actual data schema)
"""

import logging
from datetime import datetime
from typing import Any

from .formatters import (
    format_number,
    get_template_filters,
)


logger = logging.getLogger(__name__)


class RenderContext:
    """
    Builds rendering context from report data.

    This class prepares data for template rendering by:
    - Extracting relevant data from raw report structure
    - Formatting values for display
    - Organizing data into logical sections
    - Providing template-friendly data structures

    Thread Safety:
        This class is stateless and thread-safe. Each render operation
        creates a new context instance.

    Example:
        >>> data = load_report_data()
        >>> config = load_config()
        >>> context = RenderContext(data, config)
        >>> template_vars = context.build()
        >>> # Use template_vars in Jinja2 templates
    """

    def __init__(self, data: dict[str, Any], config: dict[str, Any]):
        """
        Initialize context builder.

        Args:
            data: Raw report data dictionary (from JSON report)
            config: Rendering configuration
        """
        self.data = data
        self.config = config

    def build(self) -> dict[str, Any]:
        """
        Build complete template context.

        Returns:
            Dictionary containing all template variables organized by section.
        """
        context = {
            "project": self._build_project_context(),
            "summary": self._build_summary_context(),
            "repositories": self._build_repositories_context(),
            "contributors": self._build_contributors_context(),
            "organizations": self._build_organizations_context(),
            "features": self._build_features_context(),
            "workflows": self._build_workflows_context(),
            "orphaned_jobs": self._build_orphaned_jobs_context(),
            "unattributed_jobs": self._build_unattributed_jobs_context(),
            "time_windows": self._build_time_windows_context(),
            "info_yaml": self._build_info_yaml_context(),
            "config": self._build_config_context(),
            "toc": self._build_toc_context(),
        }

        # Add Jinja2 filters under 'filters' key for backward compatibility with tests
        # Note: Filters are already registered on the Jinja2 environment in TemplateRenderer
        context["filters"] = get_template_filters()

        return context

    def _build_project_context(self) -> dict[str, Any]:
        """Build project metadata context."""
        project_name = self.data.get("project", "Repository Analysis")

        # Handle both string and dict formats
        if isinstance(project_name, dict):
            project_name = project_name.get("name", "Repository Analysis")

        # Check for generated_at in root or metadata
        generated_at = self.data.get("generated_at", "")
        if not generated_at:
            metadata = self.data.get("metadata", {})
            generated_at = metadata.get("generated_at", "")

        # Format the generated_at timestamp
        generated_at_formatted = "Unknown"
        if generated_at:
            try:
                dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
                generated_at_formatted = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
            except (ValueError, AttributeError):
                generated_at_formatted = str(generated_at)

        # Check for report_version in metadata
        metadata = self.data.get("metadata", {})
        report_version = metadata.get("report_version", "")

        # Detect project type from configuration
        # Priority: gerrit.host exists -> "gerrit", otherwise -> "github"
        project_type = self._detect_project_type()

        # Build terminology based on project type
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

        # Calculate totals from actual repository data
        # Handle both old format (direct fields) and new format (time-windowed)
        total_commits = 0
        total_lines_added = 0
        total_lines_removed = 0

        for repo in repositories:
            # Handle commits - try new format first (total_commits_ever), fall back to old (total_commits)
            total_commits += repo.get("total_commits_ever", repo.get("total_commits", 0))

            # Handle LOC - try new format (loc_stats dict), fall back to old (direct fields)
            loc_stats = repo.get("loc_stats", {})
            if loc_stats and isinstance(loc_stats, dict):
                # New format: sum across all time windows
                for window_data in loc_stats.values():
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

    def _build_repositories_context(self) -> dict[str, Any]:
        """Build repositories section context."""
        summaries = self.data.get("summaries", {})

        all_repos_raw = summaries.get("all_repositories", [])
        no_commit_repos = summaries.get("no_commit_repositories", [])

        # Transform repository data for templates
        all_repos = []
        for repo in all_repos_raw:
            # Get primary reporting window from summaries
            summaries = self.data.get("summaries", {})
            reporting_period = summaries.get("reporting_period", {})
            primary_window = reporting_period.get("window_name", "last_365")

            # Get unique contributors from time window
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

            # Extract last commit date
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

            # Build Gerrit admin URL
            gerrit_project_name = repo.get("gerrit_project", "Unknown")
            gerrit_host = repo.get("gerrit_host", "")
            gerrit_path_prefix = repo.get("gerrit_path_prefix", "")

            # Build repository URL based on project type
            # Detect if this is a GitHub-native project (no gerrit_path_prefix typically)
            project_type = self._detect_project_type()
            repo_url = self._build_repository_url(
                gerrit_project_name, gerrit_host, gerrit_path_prefix, project_type
            )

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
                "jenkins_jobs_count": len(repo.get("jenkins", {}).get("jobs", [])),
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

    def _build_contributors_context(self) -> dict[str, Any]:
        """Build contributors leaderboard context."""
        summaries = self.data.get("summaries", {})

        top_commits_raw = summaries.get("top_contributors_commits", [])
        top_loc_raw = summaries.get("top_contributors_loc", [])

        # Get primary reporting window from data
        reporting_period = summaries.get("reporting_period", {})
        primary_window = reporting_period.get("window_name", "last_365")

        # Transform contributor data
        # Contributors use time-windowed metrics (dicts with last_30, last_90, etc.)
        top_commits = []
        for contrib in top_commits_raw:
            # Get commits from time windows
            commits_dict = contrib.get("commits", {})
            # Handle both dict (new format) and int (old format)
            if isinstance(commits_dict, dict):
                total_commits = commits_dict.get(primary_window, 0)
            else:
                total_commits = commits_dict if isinstance(commits_dict, int) else 0

            # Get repository counts from repositories_touched
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
            # Get LOC stats from time windows using primary window
            lines_added_dict = contrib.get("lines_added", {})
            lines_removed_dict = contrib.get("lines_removed", {})
            lines_net_dict = contrib.get("lines_net", {})

            total_lines_added = lines_added_dict.get(primary_window, 0)
            total_lines_removed = lines_removed_dict.get(primary_window, 0)
            net_lines = lines_net_dict.get(primary_window, 0)

            # Calculate derived metrics
            delta_loc = total_lines_added + total_lines_removed

            # Get commits for avg calculation
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
        limit = self.config.get("output", {}).get("top_contributors_limit", 30)

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

        # Get primary reporting window from data
        reporting_period = summaries.get("reporting_period", {})
        primary_window = reporting_period.get("window_name", "last_365")

        # Transform organization data
        # Organizations use domain as the primary identifier
        # All metrics are time-windowed (dicts with last_30, last_90, etc.)
        top_orgs = []
        for org in top_orgs_raw:
            domain = org.get("domain", "Unknown")

            # Get commits from time windows using primary window
            commits_dict = org.get("commits", {})
            # Handle both dict (new format) and int (old format)
            if isinstance(commits_dict, dict):
                total_commits = commits_dict.get(primary_window, 0)
            else:
                total_commits = commits_dict if isinstance(commits_dict, int) else 0

            # Get contributor count
            contributor_count = org.get("contributor_count", 0)

            # Get repository counts from time windows
            repos_dict = org.get("repositories_count", {})
            # Handle both dict (new format) and int (old format)
            if isinstance(repos_dict, dict):
                repos_count = repos_dict.get(primary_window, 0)
            else:
                repos_count = repos_dict if isinstance(repos_dict, int) else 0

            # Get LOC data from time windows
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
        limit = self.config.get("output", {}).get("top_organizations_limit", 30)

        return {
            "top": top_orgs[:limit],
            "total_count": len(top_orgs_raw),
            "limit": limit,
            "has_organizations": len(top_orgs_raw) > 0,
        }

    def _build_features_context(self) -> dict[str, Any]:
        """Build features detection context."""
        repositories = self.data.get("repositories", [])

        if not repositories:
            return {
                "has_features": False,
                "features_list": [],
                "matrix": [],
                "feature_count": 0,
                "repositories_count": 0,
            }

        # Extract unique features across all repos
        features_set = set()
        for repo in repositories:
            repo_features = repo.get("features", {})
            features_set.update(repo_features.keys())

        features_list = sorted(features_set)

        # Build feature matrix
        matrix = []
        for repo in repositories:
            repo_features = repo.get("features", {})

            # Extract project types
            project_types = repo_features.get("project_types", {})
            if isinstance(project_types, dict):
                primary_type = project_types.get("primary_type")
                detected_types = project_types.get("detected_types", project_types.get("types", []))
            else:
                primary_type = None
                detected_types = []

            # Separate primary type from other types
            if primary_type and detected_types:
                # Remove primary type from detected_types to get other types
                other_types = [t for t in detected_types if t != primary_type]
            else:
                other_types = []

            # Display values
            primary_type_display = primary_type if primary_type else "N/A"
            other_types_display = other_types if other_types else []

            # Determine status based on activity
            activity_status = repo.get("activity_status", "unknown")
            if activity_status == "current":
                status = "✅"
            elif activity_status == "active":
                status = "☑️"
            else:
                status = "🛑"

            # Normalize feature names for template (strip has_ prefix)
            normalized_features = {}
            for feature in features_list:
                # Get the feature value
                if isinstance(repo_features.get(feature), dict):
                    feature_value = repo_features.get(feature, {}).get("present", False)
                else:
                    feature_value = bool(repo_features.get(feature, False))

                # Normalize the feature name (strip has_ prefix if present)
                normalized_name = (
                    feature.replace("has_", "") if feature.startswith("has_") else feature
                )
                normalized_features[normalized_name] = feature_value

            matrix.append(
                {
                    "repo_name": repo.get("gerrit_project", "Unknown"),
                    "primary_type": primary_type_display,
                    "other_types": other_types_display,
                    "status": status,
                    "features": normalized_features,
                }
            )

        return {
            "has_features": len(features_list) > 0,
            "features_list": features_list,
            "matrix": matrix,
            "feature_count": len(features_list),
            "repositories_count": len(repositories),
        }

    def _build_workflows_context(self) -> dict[str, Any]:
        """Build CI/CD workflows context."""
        repositories = self.data.get("repositories", [])

        # Build repositories with CI/CD jobs grouped by project
        repos_with_cicd = []
        total_jenkins_jobs = 0
        total_github_workflows = 0

        for repo in repositories:
            gerrit_project = repo.get("gerrit_project", "Unknown")

            # Get Jenkins jobs for this repo and flatten URL structure
            jenkins_data = repo.get("jenkins", {})
            jenkins_jobs_raw = jenkins_data.get("jobs", [])

            # Transform Jenkins jobs to flatten URL structure for template
            jenkins_jobs = []
            for job in jenkins_jobs_raw:
                job_dict = {
                    "name": job.get("name", "Unknown"),
                    "status": job.get("status", "unknown"),
                    "color": job.get("color", "notbuilt"),
                    "state": job.get("state", "active"),
                }
                # Flatten nested URL structure: urls.job_page -> url
                urls = job.get("urls", {})
                if isinstance(urls, dict):
                    job_dict["url"] = urls.get("job_page", "")
                else:
                    job_dict["url"] = job.get("url", "")
                jenkins_jobs.append(job_dict)

            # Get GitHub workflows for this repo from features.workflows
            features = repo.get("features", {})
            workflows_data = features.get("workflows", {})
            workflow_files = workflows_data.get("files", [])

            # Extract GitHub API data if available for runtime status
            github_api_data = workflows_data.get("github_api_data", {})
            github_workflows_api = github_api_data.get("workflows", [])

            # Build github_workflows list with proper structure for template
            github_workflows = []

            # If we have GitHub API data with runtime status, use that
            if github_workflows_api:
                for gh_workflow in github_workflows_api:
                    # Only include active workflows
                    if gh_workflow.get("state") == "active":
                        # Extract filename from path for display (matching production)
                        workflow_path = gh_workflow.get("path", "")
                        workflow_filename = (
                            workflow_path.split("/")[-1] if workflow_path else "Unknown"
                        )

                        github_workflows.append(
                            {
                                "name": workflow_filename,  # Use filename instead of title
                                "path": workflow_path,
                                "state": gh_workflow.get("state", "active"),
                                "status": gh_workflow.get("status", "unknown"),
                                "url": gh_workflow.get("urls", {}).get("workflow_page", ""),
                            }
                        )
            # Otherwise use the static workflow files data
            elif workflow_files:
                for workflow_file in workflow_files:
                    github_workflows.append(
                        {
                            "name": workflow_file.get("name", "Unknown"),
                            "path": workflow_file.get("name", ""),
                            "state": "active",  # Assume active if found locally
                            "status": "unknown",  # No runtime status available
                            "url": "",  # No URL without GitHub API data
                        }
                    )

            # Only include repos that have at least one job or workflow
            if jenkins_jobs or github_workflows:
                repos_with_cicd.append(
                    {
                        "gerrit_project": gerrit_project,
                        "jenkins_jobs": jenkins_jobs,
                        "jenkins_job_count": len(jenkins_jobs),
                        "github_workflows": github_workflows,
                        "github_workflow_count": len(github_workflows),
                    }
                )

                total_jenkins_jobs += len(jenkins_jobs)
                total_github_workflows += len(github_workflows)

        # Collect all Jenkins jobs (flat list for status counts)
        all_jobs = []
        for repo in repositories:
            jenkins_data = repo.get("jenkins", {})
            jobs = jenkins_data.get("jobs", [])
            repo_name = repo.get("gerrit_project", "Unknown")

            for job in jobs:
                jenkins_color = job.get("color", "notbuilt")
                all_jobs.append(
                    {
                        "name": job.get("name", "Unknown"),
                        "repo": repo_name,
                        "status": job.get("status", "UNKNOWN"),
                        "color": self._get_status_color(jenkins_color),
                        "url": job.get("url", ""),
                    }
                )

        # Count by status
        status_counts: dict[str, int] = {}
        for job in all_jobs:
            status = job.get("status", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "repositories": repos_with_cicd,
            "total_jenkins_jobs": total_jenkins_jobs,
            "total_github_workflows": total_github_workflows,
            "total_repositories": len(repos_with_cicd),
            "status_counts": status_counts,
            "has_workflows": len(repos_with_cicd) > 0,
            # Legacy flat list for backward compatibility if needed
            "all": all_jobs,
            "total_count": len(all_jobs),
        }

    def _build_orphaned_jobs_context(self) -> dict[str, Any]:
        """Build orphaned jobs context."""
        orphaned_data = self.data.get("orphaned_jenkins_jobs", {})

        jobs_dict = orphaned_data.get("jobs", {})
        by_state = orphaned_data.get("by_state", {})

        # Transform jobs dict to list
        jobs_list = []
        for job_name, job_data in jobs_dict.items():
            jobs_list.append(
                {
                    "name": job_name,
                    "project": job_data.get("project_name", "Unknown"),
                    "state": job_data.get("state", "UNKNOWN"),
                    "score": job_data.get("score", 0),
                }
            )

        # Sort by score descending
        jobs_list.sort(key=lambda x: x.get("score", 0), reverse=True)

        return {
            "jobs": jobs_list,
            "total_count": len(jobs_list),
            "by_state": by_state,
            "has_orphaned_jobs": len(jobs_list) > 0,
        }

    def _build_unattributed_jobs_context(self) -> dict[str, Any]:
        """Build unattributed jobs context."""
        jenkins_allocation = self.data.get("jenkins_allocation", {})

        # Get unallocated job details (basic structure from cache: name, url, color, buildable, disabled)
        unallocated_job_details = jenkins_allocation.get("unallocated_job_details", [])

        # Fallback to job names only if details not available
        if not unallocated_job_details:
            unallocated_job_names = jenkins_allocation.get("unallocated_job_names", [])
            # Convert to basic job list format
            unallocated_job_details = []
            for job_name in unallocated_job_names:
                unallocated_job_details.append(
                    {
                        "name": job_name,
                        "url": "",
                        "color": "",
                        "buildable": True,
                        "disabled": False,
                    }
                )

        # Build jobs list with computed status
        jobs_list = []
        for job_data in unallocated_job_details:
            job_name = job_data.get("name", "")

            # Get URL from job data (already provided by Jenkins API)
            url = job_data.get("url", "")

            # Determine status from Jenkins color code
            color = job_data.get("color", "")
            status = self._jenkins_color_to_status(color)

            # Check if disabled
            if job_data.get("disabled", False):
                status = "Disabled"

            jobs_list.append(
                {
                    "name": job_name,
                    "status": status,
                    "color": color,
                    "url": url,
                }
            )

        # Sort alphabetically by name
        jobs_list.sort(key=lambda x: x.get("name", "").lower())

        # Determine description and authentication info
        description = ""
        auth_warning = ""
        jenkins_url = ""

        if len(jobs_list) > 0:
            # Check if this is a GitHub-only or Gerrit project
            # Note: project_metadata may not be available, so we check config
            self.config.get("jenkins", {})
            gerrit_config = self.config.get("gerrit", {})
            has_gerrit = bool(gerrit_config.get("host"))

            if has_gerrit:
                description = "These jobs could not be matched to any active or archived repository. They may be infrastructure jobs, release jobs, build pipelines, or jobs that use naming conventions different from the repository names. Consider reviewing the job names and repository naming patterns to improve attribution."
            else:
                description = "These jobs could not be matched to any repository. They may be infrastructure jobs, release jobs, build pipelines, or jobs that use naming conventions different from the repository names. Consider reviewing the job names and repository naming patterns to improve attribution."

            # Check if Jenkins authentication is required (from report metadata)
            jenkins_metadata = self.data.get("jenkins_metadata", {})
            requires_auth = jenkins_metadata.get("requires_auth", False)
            jenkins_host = jenkins_metadata.get("host", "")

            if requires_auth and jenkins_host:
                # Authentication is configured, add warning about login requirement
                jenkins_url = f"https://{jenkins_host}"
                auth_warning = f"This project requires authentication to view configured jobs; you can use the URL below to login:\n\n{jenkins_url}"

        return {
            "jobs": jobs_list,
            "total_count": len(jobs_list),
            "has_unattributed_jobs": len(jobs_list) > 0,
            "description": description,
            "auth_warning": auth_warning,
            "jenkins_url": jenkins_url,
        }

    def _jenkins_color_to_status(self, color: str) -> str:
        """Convert Jenkins color code to human-readable status."""
        if not color:
            return "Unknown"

        # Jenkins color codes: blue (success), red (failure), yellow (unstable),
        # grey (not built), disabled, aborted, notbuilt
        # Suffix _anime indicates job is building
        color_base = color.replace("_anime", "")

        status_map = {
            "blue": "Success",
            "green": "Success",
            "red": "Failed",
            "yellow": "Unstable",
            "grey": "Not Built",
            "disabled": "Disabled",
            "aborted": "Aborted",
            "notbuilt": "Not Built",
        }

        return status_map.get(color_base, "Unknown")

    def _build_time_windows_context(self) -> list[dict[str, Any]]:
        """Build time windows context."""
        time_windows = self.data.get("time_windows", [])

        if not isinstance(time_windows, list):
            return []

        # Transform time window data
        transformed = []
        for window in time_windows:
            if isinstance(window, dict):
                transformed.append(
                    {
                        "name": window.get("name", "Unknown"),
                        "days": window.get("days", 0),
                        "description": window.get("description", ""),
                        "start_date": window.get("start_date", "N/A"),
                        "end_date": window.get("end_date", "N/A"),
                        "commits": window.get("commits", 0),
                        "contributors": window.get("contributors", 0),
                        "lines_added": window.get("lines_added", 0),
                        "lines_removed": window.get("lines_removed", 0),
                        "net_lines": window.get("net_lines", 0),
                    }
                )

        return transformed

    def _build_info_yaml_context(self) -> dict[str, Any]:
        """Build INFO.yaml report context."""
        info_yaml = self.data.get("info_yaml", {})

        projects = info_yaml.get("projects", [])
        lifecycle_summary = info_yaml.get("lifecycle_summary", [])
        total_projects = info_yaml.get("total_projects", 0)
        servers = info_yaml.get("servers", [])
        error = info_yaml.get("error")

        return {
            "projects": projects,
            "lifecycle_summary": lifecycle_summary,
            "total_projects": total_projects,
            "servers": servers,
            "has_projects": len(projects) > 0
            or error is not None,  # Show section if there's data or error
            "has_lifecycle_summary": len(lifecycle_summary) > 0,
            "error": error,
            "has_error": error is not None,
        }

    def _build_config_context(self) -> dict[str, Any]:
        """Build configuration context."""
        # Get project name from config
        project_config = self.config.get("project", "Repository Analysis")
        if isinstance(project_config, dict):
            project_name = project_config.get("name", "Repository Analysis")
        else:
            project_name = project_config

        # Get output config (check both 'output' and 'render' for backwards compatibility)
        output_config = self.config.get("output", {})
        render_config = self.config.get("render", {})

        # Merge configs with render taking precedence for theme
        if "theme" in render_config:
            output_config = {**output_config, "theme": render_config["theme"]}

        # Build include_sections dict
        # Define all known sections with defaults
        all_sections = [
            "title",
            "summary",
            "repositories",
            "contributors",
            "organizations",
            "features",
            "workflows",
            "orphaned_jobs",
            "unattributed_jobs",
            "time_windows",
            "info_yaml",
        ]

        # Start with all sections enabled by default
        include_sections = dict.fromkeys(all_sections, True)

        # Check if output.include_sections is a dict (new style config)
        if "include_sections" in output_config and isinstance(
            output_config["include_sections"], dict
        ):
            # Merge provided sections with defaults
            include_sections.update(output_config["include_sections"])
        else:
            # Otherwise check for individual include_* flags (old style)
            for section in all_sections:
                if f"include_{section}" in output_config:
                    include_sections[section] = output_config[f"include_{section}"]

        # Get html_tables config for DataTables support
        html_tables_config = self.config.get("html_tables", {})
        html_tables = {
            "sortable": html_tables_config.get("sortable", True),
            "searchable": html_tables_config.get("searchable", True),
            "pagination": html_tables_config.get("pagination", True),
            "entries_per_page": html_tables_config.get("entries_per_page", 20),
            "page_size_options": html_tables_config.get("page_size_options", [20, 50, 100, 200]),
            "min_rows_for_sorting": html_tables_config.get("min_rows_for_sorting", 3),
        }

        # Get table_of_contents setting - check render config first, then output config
        table_of_contents = render_config.get(
            "table_of_contents", output_config.get("table_of_contents", True)
        )

        return {
            "project_name": project_name,
            "theme": output_config.get("theme", "default"),
            "include_sections": include_sections,
            "table_of_contents": table_of_contents,
            "top_contributors_limit": output_config.get("top_contributors_limit", 30),
            "top_organizations_limit": output_config.get("top_organizations_limit", 30),
            "html_tables": html_tables,
        }

    def _build_toc_context(self) -> dict[str, Any]:
        """Build table of contents context."""
        config = self._build_config_context()

        # Don't build TOC if disabled in config (check explicitly for False)
        toc_enabled = config.get("table_of_contents", True)
        if toc_enabled is False:
            return {"sections": [], "has_sections": False}

        sections = []

        # Summary (always included if enabled)
        if config["include_sections"].get("summary", True):
            sections.append(
                {
                    "title": "Global Summary",
                    "anchor": "summary",
                    "level": 1,
                }
            )

        # Repositories (comes before contributors to match expected order)
        repositories = self._build_repositories_context()
        if (
            config["include_sections"].get("repositories", True)
            and repositories["has_repositories"]
        ):
            sections.append(
                {
                    "title": "Gerrit Projects",
                    "anchor": "repositories",
                    "level": 1,
                }
            )

        # Contributors
        contributors = self._build_contributors_context()
        if (
            config["include_sections"].get("contributors", True)
            and contributors["has_contributors"]
        ):
            sections.append(
                {
                    "title": "Top Contributors",
                    "anchor": "contributors",
                    "level": 1,
                }
            )

        # Organizations
        organizations = self._build_organizations_context()
        if (
            config["include_sections"].get("organizations", True)
            and organizations["has_organizations"]
        ):
            sections.append(
                {
                    "title": "Top Organizations",
                    "anchor": "organizations",
                    "level": 1,
                }
            )

        # Features
        features = self._build_features_context()
        if config["include_sections"].get("features", True) and features["has_features"]:
            sections.append(
                {
                    "title": "Repository Feature Matrix",
                    "anchor": "features",
                    "level": 1,
                }
            )

        # Workflows (use "Deployed CI/CD Jobs" to match test expectations)
        workflows = self._build_workflows_context()
        if config["include_sections"].get("workflows", True) and workflows["has_workflows"]:
            sections.append(
                {
                    "title": "Deployed CI/CD Jobs",
                    "anchor": "workflows",
                    "level": 1,
                }
            )

        # Orphaned Jobs
        orphaned = self._build_orphaned_jobs_context()
        if config["include_sections"].get("orphaned_jobs", True) and orphaned["has_orphaned_jobs"]:
            sections.append(
                {
                    "title": "Orphaned Jenkins Jobs",
                    "anchor": "orphaned-jobs",
                    "level": 1,
                }
            )

        # Unattributed Jobs
        unattributed = self._build_unattributed_jobs_context()
        if (
            config["include_sections"].get("unattributed_jobs", True)
            and unattributed["has_unattributed_jobs"]
        ):
            sections.append(
                {
                    "title": "Unattributed Jenkins Jobs",
                    "anchor": "unattributed-jobs",
                    "level": 1,
                }
            )

        # Time Windows
        time_windows = self._build_time_windows_context()
        if config["include_sections"].get("time_windows", True) and len(time_windows) > 0:
            sections.append(
                {
                    "title": "Time Windows",
                    "anchor": "time-windows",
                    "level": 1,
                }
            )

        return {
            "sections": sections,
            "has_sections": len(sections) > 0,
        }

    def _get_status_color_from_github(self, status: str) -> str:
        """
        Get workflow status color based on GitHub workflow status.

        Args:
            status: GitHub workflow status string

        Returns:
            Color code for rendering
        """
        status_lower = str(status).lower()

        if status_lower in ["success", "completed", "active"]:
            return "green"
        elif status_lower in ["failure", "failing"]:
            return "red"
        elif status_lower in ["pending", "in_progress", "queued"]:
            return "yellow"
        elif status_lower in ["disabled", "skipped"]:
            return "gray"
        else:
            return "gray"

    def _get_status_color(self, jenkins_color: str) -> str:
        """
        Get status color based on Jenkins ball color.

        Args:
            jenkins_color: Jenkins ball color string

        Returns:
            Semantic status name for rendering (success, failure, warning, disabled, unknown)
        """
        color_lower = str(jenkins_color).lower()

        if color_lower in ["blue", "blue_anime", "green"]:
            return "success"
        elif color_lower in ["red", "red_anime"]:
            return "failure"
        elif color_lower in ["yellow", "yellow_anime", "aborted"]:
            return "warning"
        elif color_lower in ["disabled", "grey", "gray"]:
            return "disabled"
        elif color_lower in ["notbuilt"]:
            return "unknown"
        else:
            return "unknown"
