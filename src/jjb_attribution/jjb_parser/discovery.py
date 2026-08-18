# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
JJB source loading and file discovery.

Registers the custom YAML tags used by Jenkins Job Builder, loads job-template
and job-group definitions from global-jjb and ci-management, and locates the
JJB YAML file that describes a given Gerrit project.
"""

import logging
from pathlib import Path
from typing import Any

import yaml


logger = logging.getLogger(__name__)


# Register JJB-specific YAML tags to prevent warnings
# These tags are used in JJB templates but we don't need to process them
def _jjb_tag_constructor(loader, node):
    """
    Constructor for JJB-specific YAML tags.

    Jenkins Job Builder uses custom YAML tags like !include-raw-escape: and !j2:
    for including shell scripts and Jinja2 templates. These tags cause warnings
    when parsed with standard yaml.safe_load() because they're not recognized.

    This constructor handles these tags gracefully by returning their values as-is.
    We don't need to process these tags for job name extraction - we only need
    the job-template definitions and project configurations.

    Supported tags:
    - !include-raw: - Include raw shell script
    - !include-raw-escape: - Include shell script with escaping
    - !include: - Generic include
    - !j2: - Jinja2 template processing
    - !j2-yaml: - Jinja2 with YAML output

    Args:
        loader: YAML loader instance
        node: YAML node to construct

    Returns:
        Constructed value based on node type
    """
    # Return the node value as-is (we don't need to process these)
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    elif isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    return None


# Register all JJB custom tags
yaml.SafeLoader.add_constructor("!include-raw:", _jjb_tag_constructor)
yaml.SafeLoader.add_constructor("!include-raw-escape:", _jjb_tag_constructor)
yaml.SafeLoader.add_constructor("!include-raw-escape", _jjb_tag_constructor)
yaml.SafeLoader.add_constructor("!include:", _jjb_tag_constructor)
yaml.SafeLoader.add_constructor("!include", _jjb_tag_constructor)
yaml.SafeLoader.add_constructor("!j2:", _jjb_tag_constructor)
yaml.SafeLoader.add_constructor("!j2", _jjb_tag_constructor)
yaml.SafeLoader.add_constructor("!j2-yaml:", _jjb_tag_constructor)
yaml.SafeLoader.add_constructor("!j2-yaml", _jjb_tag_constructor)


class JJBSourceDiscoveryMixin:
    """Template loading and JJB file lookup behaviour for ``JJBAttribution``.

    The attribute declarations below are type-only; the values are assigned by
    ``JJBAttribution.__init__``.
    """

    global_jjb_path: Path
    jjb_path: Path
    _templates: dict[str, dict[str, Any]]
    _job_groups: dict[str, list[str]]
    _gerrit_to_jjb_map: dict[str, Path]

    def load_templates(self) -> None:
        """
        Load JJB templates and job-groups from both global-jjb and ci-management.

        Parses all YAML files in global-jjb and ci-management to extract job-template
        definitions and job-group definitions for accurate job expansion.

        Templates from ci-management override those from global-jjb if they have the same name.
        """
        logger.info("Loading JJB templates and job-groups...")

        if self.global_jjb_path.exists():
            jjb_templates_path = self.global_jjb_path / "jjb"
            if jjb_templates_path.exists():
                template_files = list(jjb_templates_path.glob("*.yaml")) + list(
                    jjb_templates_path.glob("*.yml")
                )
                logger.info(f"Found {len(template_files)} template files in global-jjb")

                for template_file in template_files:
                    try:
                        self._load_template_file(template_file)
                    except Exception as e:
                        logger.warning(f"Failed to load template file {template_file}: {e}")
            else:
                logger.warning(f"JJB templates path does not exist: {jjb_templates_path}")
        else:
            logger.warning("Global-JJB path does not exist, skipping global-jjb templates")

        # Load from ci-management (these override global-jjb if same name)
        if self.jjb_path.exists():
            # Load top-level template files (e.g., global-templates-java.yaml)
            ci_template_files = list(self.jjb_path.glob("global-templates-*.yaml")) + list(
                self.jjb_path.glob("global-templates-*.yml")
            )
            logger.info(f"Found {len(ci_template_files)} global template files in ci-management")

            for template_file in ci_template_files:
                try:
                    self._load_template_file(template_file)
                except Exception as e:
                    logger.warning(f"Failed to load template file {template_file}: {e}")
        else:
            logger.warning(f"CI-Management JJB path does not exist: {self.jjb_path}")

        logger.info(
            f"Loaded {len(self._templates)} job templates and {len(self._job_groups)} job groups"
        )

    def _load_template_file(self, template_file: Path) -> None:
        """Load templates and job-groups from a single YAML file."""
        try:
            with open(template_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, list):
                return

            for item in data:
                if isinstance(item, dict):
                    if "job-template" in item:
                        template = item["job-template"]
                        template_id = template.get("id")
                        template_name = template.get("name")

                        # Store by id if available, otherwise by name
                        if template_id:
                            self._templates[template_id] = template
                            logger.debug(f"Loaded template by id: {template_id} -> {template_name}")
                        elif template_name:
                            self._templates[template_name] = template
                            logger.debug(f"Loaded template by name: {template_name}")

                    elif "job-group" in item:
                        job_group = item["job-group"]
                        group_name = job_group.get("name")
                        jobs_list = job_group.get("jobs", [])

                        if group_name and jobs_list:
                            # Store the list of job templates in this group
                            self._job_groups[group_name] = jobs_list
                            logger.debug(
                                f"Loaded job-group: {group_name} with {len(jobs_list)} jobs"
                            )

        except yaml.YAMLError as e:
            logger.warning(f"YAML error in {template_file}: {e}")
        except Exception as e:
            logger.warning(f"Error loading {template_file}: {e}")

    def find_jjb_file(self, gerrit_project: str) -> Path | None:
        """
        Find the JJB YAML file for a given Gerrit project.

        Mapping logic:
        - "aai/babel" → jjb/aai/aai-babel.yaml
        - "ccsdk/apps" → jjb/ccsdk/ccsdk-apps.yaml
        - "integration" → jjb/integration/integration.yaml

        Args:
            gerrit_project: Gerrit project name (e.g., "aai/babel")

        Returns:
            Path to the JJB file, or None if not found
        """
        if gerrit_project in self._gerrit_to_jjb_map:
            return self._gerrit_to_jjb_map[gerrit_project]

        if not self.jjb_path.exists():
            logger.warning(f"JJB path does not exist: {self.jjb_path}")
            return None

        # Try different mapping strategies
        jjb_file = self._find_jjb_file_strategies(gerrit_project)

        if jjb_file:
            self._gerrit_to_jjb_map[gerrit_project] = jjb_file
            logger.debug(f"Mapped {gerrit_project} -> {jjb_file}")

        return jjb_file

    def _find_jjb_file_strategies(self, gerrit_project: str) -> Path | None:
        """Try different strategies to find the JJB file."""
        # Strategy 1: Direct mapping with slashes to dashes
        # "aai/babel" -> "aai-babel.yaml"
        parts = gerrit_project.split("/")
        if len(parts) >= 2:
            parent_dir = self.jjb_path / parts[0]
            if parent_dir.exists() and parent_dir.is_dir():
                # Try exact match: aai/babel -> aai-babel.yaml
                jjb_name = "-".join(parts) + ".yaml"
                jjb_file = parent_dir / jjb_name
                if jjb_file.exists():
                    return jjb_file

                # Try with yml extension
                jjb_file = parent_dir / (jjb_name.replace(".yaml", ".yml"))
                if jjb_file.exists():
                    return jjb_file

                # Try without parent prefix: aai/babel -> babel.yaml
                jjb_name = "-".join(parts[1:]) + ".yaml"
                jjb_file = parent_dir / jjb_name
                if jjb_file.exists():
                    return jjb_file

        # Strategy 2: Single component project
        # "integration" -> "integration/integration.yaml"
        if "/" not in gerrit_project:
            project_dir = self.jjb_path / gerrit_project
            if project_dir.exists() and project_dir.is_dir():
                jjb_file = project_dir / f"{gerrit_project}.yaml"
                if jjb_file.exists():
                    return jjb_file

                jjb_file = project_dir / f"{gerrit_project}.yml"
                if jjb_file.exists():
                    return jjb_file

        # Strategy 3: Search by scanning files for matching project field
        return self._search_by_project_field(gerrit_project)

    def _search_by_project_field(self, gerrit_project: str) -> Path | None:
        """Search for JJB file by looking for 'project' field in YAML files."""
        if not self.jjb_path.exists():
            return None

        yaml_files = list(self.jjb_path.glob("**/*.yaml")) + list(self.jjb_path.glob("**/*.yml"))

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                if not isinstance(data, list):
                    continue

                for item in data:
                    if isinstance(item, dict) and "project" in item:
                        project_block = item["project"]
                        project_field = project_block.get("project")
                        if project_field == gerrit_project:
                            logger.debug(
                                f"Found {gerrit_project} in {yaml_file} via project field scan"
                            )
                            return yaml_file

            except Exception as e:
                logger.debug(f"Error scanning {yaml_file}: {e}")
                continue

        return None
