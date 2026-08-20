# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Jenkins job allocation and audit support."""

from typing import Any

from .base import _CollectorState


class _JenkinsAllocationMixin(_CollectorState):
    """Allocate Jenkins jobs and report unallocated or orphaned jobs."""

    def _get_jenkins_jobs_for_repo(self, repo_name: str) -> list[dict[str, Any]]:
        """Get Jenkins jobs for a specific repository with duplicate prevention.

        Thread-safe: uses instance-level JenkinsAllocationContext.
        """
        if not self.jenkins_client or not self._jenkins_initialized:
            self.logger.debug(
                f"No Jenkins client available or cache not initialized for {repo_name}"
            )
            return []

        # Use cached data instead of making API calls
        cached = self.jenkins_allocation_context.get_cached_jobs(repo_name)
        if cached is not None:
            self.logger.debug(f"Using cached Jenkins jobs for {repo_name}")
            return list(cached)

        try:
            # Get jobs from Jenkins API (includes allocated jobs set for duplicate prevention)
            jobs = self.jenkins_client.get_jobs_for_project(
                repo_name, self.jenkins_allocation_context.allocated_jobs
            )

            if jobs:
                self.logger.debug(
                    f"Found {len(jobs)} Jenkins jobs for {repo_name}: {[job.get('name') for job in jobs]}"
                )
                # Allocate jobs (thread-safe, prevents duplicates)
                allocated = self.jenkins_allocation_context.allocate_jobs(repo_name, jobs)
                # Cache the allocated results
                self.jenkins_allocation_context.cache_jobs(repo_name, allocated)
                return list(allocated)
            else:
                # Cache empty result
                self.jenkins_allocation_context.cache_jobs(repo_name, [])
                return []
        except Exception as e:
            self.logger.warning(f"Error fetching Jenkins jobs for {repo_name}: {e}")
            self.jenkins_allocation_context.cache_jobs(repo_name, [])
            return []

    def reset_jenkins_allocation_state(self) -> None:
        """Reset Jenkins job allocation state for a fresh start.

        Thread-safe: uses instance-level JenkinsAllocationContext.
        """
        self.jenkins_allocation_context.reset()
        self.logger.info("Reset Jenkins job allocation state")

    def get_jenkins_job_allocation_summary(self) -> dict[str, Any]:
        """Get summary of Jenkins job allocation for auditing purposes.

        Thread-safe: uses instance-level JenkinsAllocationContext.
        """
        if not self.jenkins_client or not self._jenkins_initialized:
            return {"error": "No Jenkins client available or not initialized"}

        # Get summary from allocation context (thread-safe)
        summary = self.jenkins_allocation_context.get_allocation_summary()

        # Add percentage calculation
        total_jobs = summary["total_jobs"]
        allocated_count = summary["allocated_count"]
        unallocated_count = total_jobs - allocated_count
        allocated_names = self.jenkins_allocation_context.get_allocated_job_names()

        return {
            "total_jenkins_jobs": total_jobs,
            "allocated_jobs": allocated_count,
            "unallocated_jobs": unallocated_count,
            "allocated_job_names": sorted(allocated_names),
            "allocation_percentage": round((allocated_count / total_jobs * 100), 2)
            if total_jobs > 0
            else 0,
        }

    def validate_jenkins_job_allocation(self) -> list[str]:
        """Validate Jenkins job allocation and return any issues found."""
        issues: list[str] = []

        if not self.jenkins_client or not self._jenkins_initialized:
            return ["No Jenkins client available or not initialized for validation"]

        # Check for duplicate allocations (shouldn't happen with new system)
        allocation_summary = self.get_jenkins_job_allocation_summary()

        if "error" in allocation_summary:
            issues.append(allocation_summary["error"])
            return issues

        if allocation_summary["unallocated_jobs"] > 0:
            # Use cached data
            all_jobs = self.jenkins_allocation_context.get_all_jobs()
            all_job_names = {job.get("name", "") for job in all_jobs.get("jobs", [])}
            allocated_job_names = set(self.jenkins_allocation_context.get_allocated_job_names())
            unallocated_jobs = all_job_names - allocated_job_names

            # Try to match unallocated jobs to archived Gerrit projects
            self._allocate_orphaned_jobs_to_archived_projects(unallocated_jobs)

            # Identify infrastructure jobs that legitimately don't belong to projects
            infrastructure_patterns = [
                "lab-",
                "lf-",
                "openci-",
                "rtdv3-",
                "global-jjb-",
                "ci-management-",
                "releng-",
                "autorelease-",
                "docs-",
                "infra-",
            ]

            # After orphaned job detection, recalculate what's truly unallocated
            orphaned_jobs = self.jenkins_allocation_context.get_orphaned_jobs()
            orphaned_job_names = set(orphaned_jobs.keys())
            remaining_unallocated = unallocated_jobs - orphaned_job_names

            infrastructure_jobs = set()
            project_jobs = set()

            for job in remaining_unallocated:
                job_lower = job.lower()
                is_infrastructure = any(
                    job_lower.startswith(pattern) for pattern in infrastructure_patterns
                )
                if is_infrastructure:
                    infrastructure_jobs.add(job)
                else:
                    project_jobs.add(job)

            # Report orphaned jobs as informational (matched to archived projects)
            if orphaned_job_names:
                orphaned_jobs_list = sorted(orphaned_job_names)
                issues.append(
                    f"INFO: Found {len(orphaned_job_names)} Jenkins jobs matched to archived/read-only Gerrit projects"
                )
                issues.append(f"Orphaned jobs: {orphaned_jobs_list}")

                # Group by project state
                by_state: dict[str, list[str]] = {}
                orphaned_jobs = self.jenkins_allocation_context.get_orphaned_jobs()
                for job_name in orphaned_job_names:
                    job_info = orphaned_jobs[job_name]
                    state = job_info.get("state", "UNKNOWN")
                    if state not in by_state:
                        by_state[state] = []
                    by_state[state].append(job_name)

                for state, jobs in by_state.items():
                    issues.append(f"  - {len(jobs)} jobs for {state} projects: {sorted(jobs)}")

            # Only report remaining project jobs as critical errors
            if project_jobs:
                project_jobs_list = sorted(project_jobs)
                issues.append(
                    f"CRITICAL ERROR: Found {len(project_jobs)} unallocated project Jenkins jobs"
                )
                issues.append(f"Unallocated project jobs: {project_jobs_list}")

                # Analyze patterns in project jobs only
                patterns: dict[str, int] = {}
                for job in project_jobs:
                    parts = job.lower().split("-")
                    if parts:
                        first_part = parts[0]
                        patterns[first_part] = patterns.get(first_part, 0) + 1

                if patterns:
                    common_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:5]
                    issues.append(f"Common patterns in unallocated project jobs: {common_patterns}")

                # Generate detailed suggestions for fixing unallocated project jobs
                suggestions = []
                for job in sorted(project_jobs)[:20]:  # Analyze first 20
                    job_parts = job.lower().split("-")
                    if job_parts:
                        suggestions.append(
                            f"  - '{job}' might belong to project containing '{job_parts[0]}'"
                        )

                if suggestions:
                    issues.append("Suggestions for unallocated project jobs:")
                    issues.extend(suggestions)

            if infrastructure_jobs:
                infrastructure_jobs_list = sorted(infrastructure_jobs)
                issues.append(
                    f"INFO: Found {len(infrastructure_jobs)} infrastructure Jenkins jobs (not assigned to projects)"
                )
                issues.append(f"Infrastructure jobs: {infrastructure_jobs_list}")

        return issues

    def _allocate_orphaned_jobs_to_archived_projects(self, unallocated_jobs: set[str]) -> None:
        """Try to match unallocated Jenkins jobs to archived/read-only Gerrit projects."""
        if not self.gerrit_projects_cache or not unallocated_jobs:
            return

        self.logger.info(
            f"Attempting to match {len(unallocated_jobs)} unallocated Jenkins jobs to archived Gerrit projects"
        )

        # Get all archived/read-only projects
        archived_projects = {}
        for project_name, project_info in self.gerrit_projects_cache.items():
            state = project_info.get("state", "ACTIVE")
            if state in ["READ_ONLY", "HIDDEN"]:
                archived_projects[project_name] = project_info

        self.logger.debug(f"Found {len(archived_projects)} archived/read-only projects in Gerrit")

        # Try to match jobs to archived projects using same logic as active projects
        for job_name in list(unallocated_jobs):  # Use list() to avoid modification during iteration
            best_match = None
            best_score = 0

            for project_name, project_info in archived_projects.items():
                project_job_name = project_name.replace("/", "-")
                # Check if jenkins_client is available
                if self.jenkins_client:
                    score = self.jenkins_client._calculate_job_match_score(
                        job_name, project_name, project_job_name
                    )
                else:
                    # Fallback to simple matching if no Jenkins client
                    score = 100 if job_name.startswith(project_job_name) else 0

                if score > best_score:
                    best_score = score
                    best_match = (project_name, project_info)

            if best_match and best_score > 0:
                project_name, project_info = best_match
                orphaned = self.jenkins_allocation_context.get_orphaned_jobs()
                orphaned[job_name] = {
                    "project_name": project_name,
                    "state": project_info.get("state", "UNKNOWN"),
                    "score": best_score,
                }
                self.jenkins_allocation_context.set_orphaned_jobs(orphaned)
                self.logger.info(
                    f"Matched orphaned job '{job_name}' to archived project '{project_name}' (state: {project_info.get('state')}, score: {best_score})"
                )

    def get_orphaned_jenkins_jobs_summary(self) -> dict[str, Any]:
        """Get summary of Jenkins jobs matched to archived projects."""
        orphaned_jobs = self.jenkins_allocation_context.get_orphaned_jobs()
        if not orphaned_jobs:
            return {"total_orphaned_jobs": 0, "by_state": {}, "jobs": {}}

        by_state: dict[str, list[str]] = {}
        for job_name, job_info in orphaned_jobs.items():
            state = job_info.get("state", "UNKNOWN")
            if state not in by_state:
                by_state[state] = []
            by_state[state].append(job_name)

        return {
            "total_orphaned_jobs": len(orphaned_jobs),
            "by_state": {state: len(jobs) for state, jobs in by_state.items()},
            "jobs": dict(orphaned_jobs),
        }
