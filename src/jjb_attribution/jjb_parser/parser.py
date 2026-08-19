# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
JJB attribution parser.

Holds the ``JJBAttribution`` entry point that parses JJB project blocks from
ci-management YAML files and maps the resulting jobs to Gerrit projects.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from .discovery import JJBSourceDiscoveryMixin
from .expansion import JJBJobExpansionMixin
from .models import JJBJobDefinition, JJBProject


logger = logging.getLogger(__name__)


class JJBAttribution(JJBSourceDiscoveryMixin, JJBJobExpansionMixin):
    """
    Parser for Jenkins Job Builder (JJB) attribution.

    This class parses JJB YAML files to extract job definitions and map them
    to Gerrit projects, enabling accurate Jenkins job attribution based on
    authoritative JJB configuration files from ci-management repositories.
    """

    def __init__(self, ci_management_path: Path, global_jjb_path: Path):
        """
        Initialize the CI-Management parser.

        Args:
            ci_management_path: Path to the ci-management repository
            global_jjb_path: Path to the global-jjb repository
        """
        self.ci_management_path = Path(ci_management_path)
        self.global_jjb_path = Path(global_jjb_path)
        self.jjb_path = self.ci_management_path / "jjb"

        # Cache for parsed data
        self._templates: dict[str, dict[str, Any]] = {}
        self._job_groups: dict[str, list[str]] = {}
        self._project_cache: dict[str, list[JJBProject]] = {}
        self._gerrit_to_jjb_map: dict[str, Path] = {}

        # Verify paths exist
        if not self.ci_management_path.exists():
            logger.warning(f"CI-Management path does not exist: {self.ci_management_path}")
        if not self.global_jjb_path.exists():
            logger.warning(f"Global-JJB path does not exist: {self.global_jjb_path}")

        logger.debug(f"Initialized JJBAttribution with ci-management: {self.ci_management_path}")

    def parse_project_jobs(self, gerrit_project: str) -> list[str]:
        """
        Parse JJB files to get expected job names for a project.

        Args:
            gerrit_project: Gerrit project name (e.g., "aai/babel")

        Returns:
            List of expected job name patterns/names
        """
        if gerrit_project in self._project_cache:
            projects = self._project_cache[gerrit_project]
            return self._extract_job_names(projects)

        jjb_file = self.find_jjb_file(gerrit_project)
        if not jjb_file:
            logger.debug(f"No JJB file found for project: {gerrit_project}")
            return []

        projects = self._parse_jjb_file(jjb_file, gerrit_project)
        self._project_cache[gerrit_project] = projects

        return self._extract_job_names(projects)

    def _parse_jjb_file(self, jjb_file: Path, gerrit_project: str) -> list[JJBProject]:
        """Parse a JJB YAML file and extract project blocks."""
        projects: list[JJBProject] = []

        try:
            with open(jjb_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, list):
                logger.warning(f"JJB file {jjb_file} does not contain a list")
                return projects

            for item in data:
                if isinstance(item, dict) and "project" in item:
                    project_block = item["project"]
                    project_field = project_block.get("project")

                    # Only process projects matching the Gerrit project
                    if project_field and project_field != gerrit_project:
                        continue

                    jjb_project = self._parse_project_block(project_block)
                    if jjb_project:
                        projects.append(jjb_project)

            logger.debug(f"Parsed {len(projects)} project blocks from {jjb_file}")

        except yaml.YAMLError as e:
            logger.error(f"YAML error parsing {jjb_file}: {e}")
        except Exception as e:
            logger.error(f"Error parsing {jjb_file}: {e}")

        return projects

    def _parse_project_block(self, project_block: dict[str, Any]) -> JJBProject | None:
        """Parse a single project block from JJB YAML."""
        try:
            name = project_block.get("name", "")
            gerrit_project = project_block.get("project")
            project_name = project_block.get("project-name", name)

            jjb_project = JJBProject(
                name=name, gerrit_project=gerrit_project, parameters=project_block
            )

            jobs_list = project_block.get("jobs", [])
            for job_item in jobs_list:
                if isinstance(job_item, str):
                    # Simple job or job-group reference: "gerrit-maven-verify"
                    self._append_jobs(jjb_project, job_item, project_name, project_block)
                elif isinstance(job_item, dict):
                    # Job with parameters: {"gerrit-maven-stage": {"sign-artifacts": true}}
                    for template_name, params in job_item.items():
                        merged_params = {**project_block}
                        if isinstance(params, dict):
                            merged_params.update(params)
                        self._append_jobs(jjb_project, template_name, project_name, merged_params)

            return jjb_project

        except Exception as e:
            logger.warning(f"Error parsing project block: {e}")
            return None

    def _append_jobs(
        self,
        jjb_project: JJBProject,
        template_name: str,
        project_name: str,
        params: dict[str, Any],
    ) -> None:
        """Append job definitions for a template, expanding job-groups when present.

        When ``template_name`` names a job-group it is expanded to its member
        templates; otherwise the template is added as a single job.
        """
        expanded_jobs = self._expand_job_group(template_name, project_name, params)
        templates = expanded_jobs if expanded_jobs else [template_name]
        for template in templates:
            jjb_project.jobs.append(
                JJBJobDefinition(
                    template_name=template,
                    project_name=project_name,
                    parameters=params,
                )
            )

    def get_all_projects(self) -> dict[str, list[JJBProject]]:
        """
        Get all projects from all JJB files.

        Returns:
            Dictionary mapping Gerrit project names to their JJB project definitions
        """
        all_projects: dict[str, list[JJBProject]] = {}

        if not self.jjb_path.exists():
            logger.warning(f"JJB path does not exist: {self.jjb_path}")
            return all_projects

        # Find all YAML files
        yaml_files = list(self.jjb_path.glob("**/*.yaml")) + list(self.jjb_path.glob("**/*.yml"))

        logger.info(f"Scanning {len(yaml_files)} JJB files...")

        for yaml_file in yaml_files:
            # Skip global files
            if yaml_file.name.startswith("global-"):
                continue

            self._scan_jjb_file(yaml_file, all_projects)

        logger.info(f"Found {len(all_projects)} Gerrit projects with JJB definitions")
        return all_projects

    def _scan_jjb_file(self, yaml_file: Path, all_projects: dict[str, list[JJBProject]]) -> None:
        """Parse one JJB YAML file and merge its projects into ``all_projects``."""
        try:
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, list):
                return

            for item in data:
                if not (isinstance(item, dict) and "project" in item):
                    continue

                project_block = item["project"]
                gerrit_project = project_block.get("project")
                if not gerrit_project:
                    continue

                jjb_project = self._parse_project_block(project_block)
                if jjb_project:
                    all_projects.setdefault(gerrit_project, []).append(jjb_project)

        except Exception as e:
            logger.debug(f"Error scanning {yaml_file}: {e}")

    def get_project_summary(self) -> dict[str, int]:
        """
        Get a summary of projects and job counts.

        Returns:
            Dictionary with statistics about parsed projects
        """
        all_projects = self.get_all_projects()

        total_jobs = 0
        for projects in all_projects.values():
            for project in projects:
                total_jobs += len(project.jobs)

        return {
            "gerrit_projects": len(all_projects),
            "jjb_project_blocks": sum(len(p) for p in all_projects.values()),
            "total_jobs": total_jobs,
            "templates_loaded": len(self._templates),
        }
