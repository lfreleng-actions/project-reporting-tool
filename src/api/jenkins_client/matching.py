# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Jenkins fuzzy job matching.

Fallback attribution for jobs that have no JJB definition, using the
naming-pattern scoring algorithm that covers the job naming conventions
in use across LF projects.
"""

from typing import Any

from .builds import JenkinsBuildsMixin
from .catalog import JenkinsCatalogMixin


class JenkinsMatchingMixin(JenkinsCatalogMixin, JenkinsBuildsMixin):
    """Name-pattern scoring used to attribute Jenkins jobs to projects."""

    def _get_jobs_via_fuzzy_matching(
        self, project_name: str, allocated_jobs: set[str]
    ) -> list[dict[str, Any]]:
        """
        Get jobs using fuzzy matching algorithm (fallback method).

        Args:
            project_name: Name of the Gerrit project
            allocated_jobs: Set of job names already allocated

        Returns:
            List of job detail dictionaries
        """
        self.logger.debug(f"Using fuzzy matching for project: {project_name}")

        all_jobs = self.get_all_jobs()
        project_jobs: list[dict[str, Any]] = []

        if "jobs" not in all_jobs:
            self.logger.debug(f"No 'jobs' key found in Jenkins API response for {project_name}")
            return project_jobs

        # Convert project name to job name format (replace / with -)
        project_job_name = project_name.replace("/", "-")
        self.logger.debug(f"Searching for Jenkins jobs matching pattern: {project_job_name}")

        total_jobs = len(all_jobs["jobs"])
        self.logger.debug(f"Checking {total_jobs} total Jenkins jobs for matches")

        # Collect potential matches with scoring for better matching
        candidates: list[tuple[dict[str, Any], int]] = []

        for job in all_jobs["jobs"]:
            job_name = job.get("name", "")

            # Skip already allocated jobs
            if job_name in allocated_jobs:
                self.logger.debug(f"Skipping already allocated Jenkins job: {job_name}")
                continue

            # Calculate match score for better job attribution
            score = self._calculate_job_match_score(job_name, project_name, project_job_name)
            if score > 0:
                candidates.append((job, score))

        # Sort by score (highest first) to prioritize better matches
        candidates.sort(key=lambda x: x[1], reverse=True)

        for job, score in candidates:
            job_name = job.get("name", "")
            self.logger.debug(f"Processing Jenkins job: {job_name} (score: {score})")

            job_details = self.get_job_details(job_name)
            if job_details:
                project_jobs.append(job_details)
                # NOTE: Do NOT add to allocated_jobs here - that's done by
                # JenkinsAllocationContext.allocate_jobs() to avoid double-allocation
                self.logger.debug(
                    f"Matched Jenkins job '{job_name}' to project '{project_name}' (score: {score})"
                )
            else:
                self.logger.warning(f"Failed to get details for Jenkins job: {job_name}")

        self.logger.debug(
            f"Fuzzy matching: Found {len(project_jobs)} Jenkins jobs for project {project_name}"
        )
        return project_jobs

    def _calculate_job_match_score(
        self, job_name: str, project_name: str, project_job_name: str
    ) -> int:
        """
        Calculate a match score for Jenkins job attribution.

        Supports multiple job naming patterns used across LF projects:

        1. PREFIX PATTERN (ONAP, OpenDaylight style):
           {project-name}-{job-type}-{stream}
           Example: aai-babel-maven-verify-master -> aai/babel

        2. SUFFIX PATTERN (LF Broadband style):
           {job-type}_{project-name}
           Example: docker-publish_bbsim -> bbsim

        3. INFIX PATTERN (LF Broadband verify jobs):
           verify_{project-name}_{job-type}
           Example: verify_aaa_maven-test -> aaa

        This prevents duplicate allocation by ensuring jobs can only match one project.
        Higher scores indicate better matches. Returns 0 for no match.

        Args:
            job_name: Jenkins job name
            project_name: Original Gerrit project name (with slashes)
            project_job_name: Project name converted to job format (slashes -> dashes)

        Returns:
            Match score (0 = no match, higher = better match)
        """
        if not job_name or not project_job_name:
            return 0

        job_name_lower = job_name.lower()
        project_job_name_lower = project_job_name.lower()

        score = 0
        match_type = None

        # Pattern 1: exact match (highest priority).
        if job_name_lower == project_job_name_lower:
            match_type = "exact"
            score = 1000

        # Pattern 2a: {project}-* prefix (ONAP, ODL style),
        # e.g. aai-babel-maven-verify-master matches aai/babel.
        elif job_name_lower.startswith(project_job_name_lower + "-"):
            match_type = "prefix_hyphen"
            score = 500

        # Pattern 2b: {project}_* prefix (LF Broadband style),
        # e.g. bbsim_scale_test matches bbsim.
        elif job_name_lower.startswith(project_job_name_lower + "_"):
            match_type = "prefix_underscore"
            score = 490

        # Pattern 3: *_{project} suffix with underscore, e.g.
        # docker-publish_bbsim matches bbsim, maven-publish_aaa matches aaa,
        # github-release_voltctl matches voltctl.
        elif job_name_lower.endswith("_" + project_job_name_lower):
            match_type = "suffix_underscore"
            score = 450

        # Pattern 4: verify_{project}_* infix (LF Broadband verify), e.g.
        # verify_aaa_licensed matches aaa, verify_bbsim_unit-test matches bbsim.
        elif (
            job_name_lower.startswith("verify_" + project_job_name_lower + "_")
            or job_name_lower == "verify_" + project_job_name_lower
        ):
            match_type = "infix_verify"
            score = 400

        # Pattern 5: common job-type prefixes before {project}, e.g.
        # patchset-voltha-*, periodic-voltha-*, build-voltha-* match voltha.
        elif any(
            job_name_lower.startswith(prefix + project_job_name_lower + "-")
            or job_name_lower == prefix + project_job_name_lower
            for prefix in ["patchset-", "periodic-", "build-", "release-", "merge-"]
        ):
            match_type = "prefixed_project"
            score = 380

        # Pattern 6: *_{project}_* infix with underscore delimiters, e.g.
        # build_berlin-community-pod-1-gpon_1T8GEM_DT_voltha_master matches
        # voltha. Guard against false positives where the project is really a
        # child in a parent-child pattern (prefix ending in "-{project}").
        elif "_" + project_job_name_lower + "_" in job_name_lower:
            # Find where the project name appears in the job name
            infix_pos = job_name_lower.find("_" + project_job_name_lower + "_")
            prefix_part = job_name_lower[:infix_pos]

            # Check if the prefix ends with a hyphenated version that suggests
            # this is actually a parent-child prefix pattern like "sdc-tosca"
            # being matched against standalone "tosca"
            if prefix_part.endswith("-" + project_job_name_lower):
                # This looks like parent-child, not a valid infix match
                pass
            else:
                match_type = "infix_underscore"
                score = 350

        # Pattern 7: *-{project}-* infix with hyphen delimiters, e.g.
        # patchset-voltha-2.14-multiple-olts matches voltha,
        # periodic-voltha-dt-test-bbsim matches voltha. Guard against
        # parent-child prefixes (e.g. "sdc-tosca-verify" must not match
        # standalone "tosca") by requiring the prefix to look like a known
        # job-type prefix rather than a parent project name.
        elif "-" + project_job_name_lower + "-" in job_name_lower:
            # Find where the project name appears in the job name
            infix_pos = job_name_lower.find("-" + project_job_name_lower + "-")
            prefix_part = job_name_lower[:infix_pos]

            # Known job-type prefixes that indicate this is a valid infix match
            known_job_prefixes = (
                "patchset",
                "periodic",
                "build",
                "release",
                "merge",
                "verify",
                "test",
                "deploy",
                "publish",
                "docker",
                "maven",
            )

            # Check if the prefix is a known job-type prefix or contains one
            # If not, this might be a parent-child pattern (e.g., sdc-tosca)
            is_valid_infix = False
            if (
                prefix_part in known_job_prefixes
                or any(prefix_part.startswith(p + "-") for p in known_job_prefixes)
                or any(prefix_part.endswith("-" + p) for p in known_job_prefixes)
            ):
                is_valid_infix = True
            elif "_" in prefix_part:
                # Underscore in prefix suggests it's a complex job name, not parent-child
                is_valid_infix = True

            if is_valid_infix:
                match_type = "infix_hyphen"
                score = 300

        # Pattern 8: *-{project} suffix with hyphen, e.g.
        # onos-app-release matches release (when release is a project),
        # docker-build-voltha matches voltha.
        elif job_name_lower.endswith("-" + project_job_name_lower):
            match_type = "suffix_hyphen"
            score = 250

        if match_type is None:
            return 0

        # Apply bonuses for more specific matches.

        # Bonus for longer/more specific project paths (child projects get priority)
        path_parts = project_name.count("/") + 1
        score += path_parts * 50

        # For prefix matches, add bonus for consecutive component matches
        if match_type == "prefix":
            project_parts = project_job_name_lower.split("-")
            job_parts = job_name_lower.split("-")
            consecutive_matches = 0

            for i, project_part in enumerate(project_parts):
                if i < len(job_parts) and job_parts[i] == project_part:
                    consecutive_matches += 1
                else:
                    break

            score += consecutive_matches * 25

        return score
