# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Modern template-based rendering system for repository reports.

This package provides Jinja2 template-based rendering for reports in multiple
formats (Markdown, HTML). It separates data preparation from presentation
using a clean component-based architecture.

Architecture:
    - context.py: RenderContext for preparing data for templates
    - renderer.py: ModernReportRenderer orchestrator with TemplateRenderer
    - formatters.py: Reusable formatting utilities (Jinja2 filters)
    - info_yaml_renderer.py: Specialized renderer for INFO.yaml reports

Usage:
    >>> from rendering.renderer import ModernReportRenderer
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
