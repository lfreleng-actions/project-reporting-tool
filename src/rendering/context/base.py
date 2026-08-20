# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Public RenderContext class composed from the section mixins.

``RenderContext`` owns the raw data/config it is constructed with and the
``build()`` entry point. Every ``_build_*`` section builder lives in a
sibling mixin module and is composed here, so ``self.<method>`` calls
resolve through the MRO exactly as they did when this was one module.
"""

from typing import Any

from ..formatters import get_template_filters
from .contributors import ContributorsContextMixin
from .features import FeaturesContextMixin
from .project import ProjectContextMixin
from .repositories import RepositoriesContextMixin
from .sections import SectionsContextMixin
from .workflows import WorkflowsContextMixin


class RenderContext(
    ProjectContextMixin,
    RepositoriesContextMixin,
    ContributorsContextMixin,
    FeaturesContextMixin,
    WorkflowsContextMixin,
    SectionsContextMixin,
):
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
