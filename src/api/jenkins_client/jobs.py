# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Jenkins job attribution for a Gerrit project.

Combines the authoritative JJB Attribution results with fuzzy matching so
that legacy or manually created jobs are still attributed.
"""

from typing import Any

from .jjb import JenkinsJJBMixin
from .matching import JenkinsMatchingMixin


class JenkinsJobsMixin(JenkinsJJBMixin, JenkinsMatchingMixin):
    """Hybrid per-project job lookup across the available attribution sources."""

    def get_jobs_for_project(
        self, project_name: str, allocated_jobs: set[str]
    ) -> list[dict[str, Any]]:
        """
        Get jobs related to a specific Gerrit project with duplicate prevention.

        Uses hybrid approach combining JJB Attribution (authoritative) and fuzzy
        matching (fallback) to maximize job attribution coverage.

        Strategy:
        1. Try JJB Attribution first (authoritative from ci-management)
        2. Also try fuzzy matching to catch legacy/manual jobs not in JJB
        3. Combine results, deduplicating by job name
        4. Return all matched jobs

        Args:
            project_name: Name of the Gerrit project (e.g., "foo/bar")
            allocated_jobs: Set of job names already allocated to other projects

        Returns:
            List of job detail dictionaries for matched jobs

        Example:
            >>> client = JenkinsAPIClient("jenkins.example.com")
            >>> allocated = set()
            >>> jobs = client.get_jobs_for_project("sdc/onap-sdc", allocated)
            >>> print(f"Found {len(jobs)} jobs")
        """
        self.logger.debug(f"Looking for Jenkins jobs for project: {project_name}")

        all_jobs = []
        job_names_found = set()  # Track to avoid duplicates

        # Try JJB Attribution first if enabled
        jjb_jobs = []
        if self.jjb_attribution_enabled and self.jjb_attribution:
            try:
                jjb_jobs = self._get_jobs_via_jjb_attribution(project_name, allocated_jobs)
                for job in jjb_jobs:
                    job_name = job.get("name")
                    if job_name and job_name not in job_names_found:
                        all_jobs.append(job)
                        job_names_found.add(job_name)

                if jjb_jobs:
                    self.logger.debug(
                        f"JJB Attribution found {len(jjb_jobs)} jobs for {project_name}"
                    )
            except Exception as e:
                self.logger.warning(
                    f"JJB Attribution lookup failed for {project_name}: {e}. "
                    f"Will rely on fuzzy matching only."
                )

        # Always try fuzzy matching to catch legacy/manual jobs not in JJB
        # This is especially important for projects with mixed job sources
        try:
            fuzzy_jobs = self._get_jobs_via_fuzzy_matching(project_name, allocated_jobs)

            # Add fuzzy matches that aren't already found via JJB
            fuzzy_added = 0
            for job in fuzzy_jobs:
                job_name = job.get("name")
                if job_name and job_name not in job_names_found:
                    all_jobs.append(job)
                    job_names_found.add(job_name)
                    fuzzy_added += 1

            if fuzzy_added > 0:
                self.logger.debug(
                    f"Fuzzy matching added {fuzzy_added} additional jobs for {project_name} "
                    f"(total: {len(all_jobs)})"
                )
        except Exception as e:
            self.logger.warning(f"Fuzzy matching failed for {project_name}: {e}")

        if all_jobs:
            sources = []
            if jjb_jobs:
                sources.append(f"{len(jjb_jobs)} JJB")
            if len(all_jobs) > len(jjb_jobs):
                sources.append(f"{len(all_jobs) - len(jjb_jobs)} fuzzy")

            self.logger.debug(
                f"Hybrid matching for {project_name}: {len(all_jobs)} jobs ({', '.join(sources)})"
            )

        return all_jobs
