# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Job name expansion for JJB definitions.

Turns parsed JJB job definitions into concrete Jenkins job names by expanding
job-groups, applying job-template name patterns and substituting template
variables.
"""

import logging
import re
from typing import Any

from .models import JJBJobDefinition, JJBProject


logger = logging.getLogger(__name__)


class JJBJobExpansionMixin:
    """Job name expansion behaviour for ``JJBAttribution``.

    The attribute declarations below are type-only; the values are assigned by
    ``JJBAttribution.__init__``.
    """

    _templates: dict[str, dict[str, Any]]
    _job_groups: dict[str, list[str]]

    def _extract_job_names(self, projects: list[JJBProject]) -> list[str]:
        """Extract all job names from parsed projects."""
        job_names = []

        for project in projects:
            for job_def in project.jobs:
                # Try to expand the job template to actual names
                expanded = self._expand_job_template(job_def)
                job_names.extend(expanded)

        return job_names

    def _expand_job_group(
        self, job_name: str, _project_name: str, _params: dict[str, Any]
    ) -> list[str]:
        """
        Expand a job-group reference to its component job templates.

        Job groups in JJB are defined like:
        - job-group:
            name: "{project-name}-gerrit-docker-jobs"
            jobs:
              - gerrit-docker-verify
              - gerrit-docker-merge

        When a project references "{project-name}-gerrit-docker-jobs", we need to:
        1. Check if the job_name (with template variables) matches a job-group name
        2. Return the list of job templates in that group

        Args:
            job_name: Job name that might be a job-group reference (e.g., "{project-name}-gerrit-docker-jobs")
            project_name: Project name to substitute into the pattern
            params: Parameters for variable substitution

        Returns:
            List of job template names if this is a job-group, empty list otherwise
        """
        # Check if this job name (potentially with template variables) matches a job-group
        # Job-groups are stored with their template names like "{project-name}-gerrit-docker-jobs"
        if job_name in self._job_groups:
            logger.debug(f"Expanding job-group: {job_name} -> {self._job_groups[job_name]}")
            return self._job_groups[job_name]

        # Not a job-group
        return []

    def _expand_job_template(self, job_def: JJBJobDefinition) -> list[str]:
        """
        Expand a job template to actual job names.

        This is a simplified expansion that handles common cases.
        For full expansion, we would need to integrate with JJB library.
        """
        template_name = job_def.template_name
        params = job_def.parameters
        project_name = job_def.project_name

        # Check if we have a template definition
        template = self._templates.get(template_name)

        if template:
            # Use the template's name pattern
            name_pattern = template.get("name", "")
            return self._expand_name_pattern(name_pattern, params)

        # Fallback: Generate common job name patterns
        # This handles cases where templates aren't loaded
        return self._generate_common_job_patterns(template_name, project_name, params)

    def _expand_name_pattern(self, pattern: str, params: dict[str, Any]) -> list[str]:
        """Expand a JJB name pattern with parameters."""
        job_names = []

        streams = params.get("stream", [])
        if streams:
            for stream_item in streams:
                if isinstance(stream_item, str):
                    stream_name = stream_item
                    stream_vars: dict[str, Any] = {}
                elif isinstance(stream_item, dict):
                    stream_name = list(stream_item.keys())[0]
                    stream_vars = (
                        stream_item[stream_name]
                        if isinstance(stream_item[stream_name], dict)
                        else {}
                    )
                else:
                    continue

                # Create a copy of params with stream value and merge nested stream variables
                stream_params = {**params, "stream": stream_name, **stream_vars}
                expanded = self._substitute_variables(pattern, stream_params)
                job_names.append(expanded)
        else:
            # No stream, just expand with params
            expanded = self._substitute_variables(pattern, params)
            job_names.append(expanded)

        return job_names

    def _substitute_variables(self, pattern: str, params: dict[str, Any]) -> str:
        """Substitute {variable} placeholders in a pattern."""
        result = pattern

        # Find all {variable} patterns
        variables = re.findall(r"\{([^}]+)\}", pattern)

        for var in variables:
            value = params.get(var, f"{{{var}}}")  # Keep placeholder if not found

            # Skip list/dict values - they need stream expansion
            if isinstance(value, (list, dict)):
                continue

            if isinstance(value, str):
                result = result.replace(f"{{{var}}}", value)
            elif isinstance(value, (int, float, bool)):
                result = result.replace(f"{{{var}}}", str(value))

        return result

    def _generate_common_job_patterns(
        self, template_name: str, project_name: str, params: dict[str, Any]
    ) -> list[str]:
        """
        Generate common job name patterns when template isn't available.

        This provides reasonable job names based on common LF conventions.
        """
        job_names = []

        mvn_version = params.get("mvn-version", "mvn36")
        java_version = params.get("java-version", "openjdk11")
        streams = params.get("stream", [{"master": {"branch": "master"}}])

        stream_names = []
        if streams:
            for stream_item in streams:
                if isinstance(stream_item, str):
                    stream_names.append(stream_item)
                elif isinstance(stream_item, dict):
                    stream_names.extend(stream_item.keys())

        if not stream_names:
            stream_names = ["master"]

        # Common template patterns
        patterns = {
            "gerrit-maven-verify": f"{project_name}-maven-verify-{{stream}}-{mvn_version}-{java_version}",
            "gerrit-maven-merge": f"{project_name}-maven-merge-{{stream}}-{mvn_version}-{java_version}",
            "gerrit-maven-stage": f"{project_name}-maven-stage-{{stream}}-{mvn_version}-{java_version}",
            "gerrit-maven-docker-stage": f"{project_name}-maven-docker-stage-{{stream}}",
            "gerrit-maven-sonar": f"{project_name}-sonar",
            "gerrit-maven-clm": f"{project_name}-clm",
            "github-maven-verify": f"{project_name}-maven-verify-{{stream}}-{mvn_version}-{java_version}",
            "github-maven-merge": f"{project_name}-maven-merge-{{stream}}-{mvn_version}-{java_version}",
        }

        pattern = patterns.get(template_name)

        if pattern:
            if "{stream}" in pattern:
                # Expand for each stream
                for stream in stream_names:
                    job_name = pattern.replace("{stream}", stream)
                    job_names.append(job_name)
            else:
                job_names.append(pattern)
        else:
            # Unknown template, create a generic name
            job_names.append(f"{project_name}-{template_name}")

        return job_names
