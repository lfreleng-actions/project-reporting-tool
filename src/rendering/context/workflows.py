# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
CI/CD workflow and Jenkins job context builders.

Holds the ``RenderContext`` methods that describe deployed CI/CD jobs:
Jenkins jobs and GitHub workflows per repository, orphaned and
unattributed Jenkins jobs, and the job status/colour helpers they share.
"""

from typing import Any

from .shared import ContextMixinBase


class WorkflowsContextMixin(ContextMixinBase):
    """CI/CD workflow and Jenkins job sections of the render context."""

    def _build_workflows_context(self) -> dict[str, Any]:
        """Build CI/CD workflows context."""
        repositories = self.data.get("repositories", [])

        repos_with_cicd = []
        total_jenkins_jobs = 0
        total_github_workflows = 0

        for repo in repositories:
            gerrit_project = repo.get("gerrit_project", "Unknown")

            jenkins_data = repo.get("jenkins", {})
            jenkins_jobs = self._flatten_jenkins_jobs(jenkins_data.get("jobs", []))

            features = repo.get("features", {})
            workflows_data = features.get("workflows", {})
            github_workflows = self._build_github_workflows(workflows_data)

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
        all_jobs = self._collect_all_jenkins_jobs(repositories)

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

    def _flatten_jenkins_jobs(self, jenkins_jobs_raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Flatten Jenkins job records into the template-friendly shape.

        Collapses the nested ``urls.job_page`` structure to a flat ``url``.
        """
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
        return jenkins_jobs

    def _build_github_workflows(self, workflows_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Build the GitHub workflows list from API data or static files.

        Prefers GitHub API data (with runtime status, active workflows only)
        and falls back to the statically discovered workflow files.
        """
        workflow_files = workflows_data.get("files", [])

        # Extract GitHub API data if available for runtime status
        github_api_data = workflows_data.get("github_api_data", {})
        github_workflows_api = github_api_data.get("workflows", [])

        github_workflows: list[dict[str, Any]] = []

        # If we have GitHub API data with runtime status, use that
        if github_workflows_api:
            for gh_workflow in github_workflows_api:
                # Only include active workflows
                if gh_workflow.get("state") != "active":
                    continue
                # Extract filename from path for display (matching production)
                workflow_path = gh_workflow.get("path", "")
                workflow_filename = workflow_path.split("/")[-1] if workflow_path else "Unknown"

                gh_urls = gh_workflow.get("urls", {})
                github_workflows.append(
                    {
                        "name": workflow_filename,  # Use filename instead of title
                        "path": workflow_path,
                        "state": gh_workflow.get("state", "active"),
                        "status": gh_workflow.get("status", "unknown"),
                        "url": gh_urls.get("workflow_page", ""),
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

        return github_workflows

    def _collect_all_jenkins_jobs(self, repositories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Collect a flat list of all Jenkins jobs across repositories."""
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
        return all_jobs

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
