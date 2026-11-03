# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Time window, INFO.yaml, configuration and table-of-contents builders.

Holds the remaining ``RenderContext`` sections: the time window table,
the INFO.yaml report section, the rendering configuration exposed to
templates, and the table of contents derived from that configuration.
"""

from collections.abc import Callable
from typing import Any

from .shared import ContextMixinBase


class SectionsContextMixin(ContextMixinBase):
    """Time window, INFO.yaml, configuration and TOC render context sections."""

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

        include_sections = config["include_sections"]

        # Ordered TOC section specs: (config key, title, anchor, presence check).
        # A section is listed when its include flag is enabled and the presence
        # check (evaluated lazily) reports content is available.
        section_specs: list[tuple[str, str, str, Callable[[], bool]]] = [
            ("summary", "Global Summary", "summary", lambda: True),
            (
                "repositories",
                "Gerrit Projects",
                "repositories",
                lambda: self._build_repositories_context()["has_repositories"],
            ),
            (
                "contributors",
                "Top Contributors",
                "contributors",
                lambda: self._build_contributors_context()["has_contributors"],
            ),
            (
                "organizations",
                "Top Organizations",
                "organizations",
                lambda: self._build_organizations_context()["has_organizations"],
            ),
            (
                "features",
                "Repository Feature Matrix",
                "features",
                lambda: self._build_features_context()["has_features"],
            ),
            (
                "workflows",
                "Deployed CI/CD Jobs",
                "workflows",
                lambda: self._build_workflows_context()["has_workflows"],
            ),
            (
                "orphaned_jobs",
                "Orphaned Jenkins Jobs",
                "orphaned-jobs",
                lambda: self._build_orphaned_jobs_context()["has_orphaned_jobs"],
            ),
            (
                "unattributed_jobs",
                "Unattributed Jenkins Jobs",
                "unattributed-jobs",
                lambda: self._build_unattributed_jobs_context()["has_unattributed_jobs"],
            ),
            (
                "time_windows",
                "Time Windows",
                "time-windows",
                lambda: len(self._build_time_windows_context()) > 0,
            ),
        ]

        sections = []
        for config_key, title, anchor, is_present in section_specs:
            if include_sections.get(config_key, True) and is_present():
                sections.append({"title": title, "anchor": anchor, "level": 1})

        return {
            "sections": sections,
            "has_sections": len(sections) > 0,
        }
