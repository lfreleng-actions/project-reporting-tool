# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Report rendering for the lf-releng-project-reporting package.

This package provides Jinja2 template-based rendering for reports in multiple
formats (Markdown, HTML). It separates data preparation from presentation
using a clean component-based architecture.

Architecture:
    - context: RenderContext for preparing data for templates
    - renderer.py: ModernReportRenderer orchestrator with TemplateRenderer
    - formatters: Reusable formatting utilities (Jinja2 filters)
    - info_yaml_renderer.py: Specialized renderer for INFO.yaml reports
    - assets.py: Pinned versions and hashes of third-party web assets

Usage:
    >>> from lf_releng_project_reporting.rendering.renderer import ModernReportRenderer
    >>> renderer = ModernReportRenderer(config, logger)
    >>> renderer.render_markdown_report(data, output_path)
    >>> renderer.render_html_report(data, output_path)
"""

from .context import RenderContext
from .formatters import (
    format_age,
    format_date,
    format_number,
    format_percentage,
    slugify,
)
from .renderer import ModernReportRenderer, TemplateRenderer


__all__ = [
    "RenderContext",
    "ModernReportRenderer",
    "TemplateRenderer",
    "format_number",
    "format_age",
    "format_percentage",
    "slugify",
    "format_date",
]

__version__ = "2.0.0"
