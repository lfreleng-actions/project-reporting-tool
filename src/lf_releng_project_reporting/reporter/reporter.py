#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Repository reporter construction and report generation.

Owns the collaborator objects (Git collector, feature registry,
aggregator, renderer, INFO.yaml collector) and the report rendering
entry point, composing the analysis and discovery behaviour mixins into
the public ``RepositoryReporter``.
"""

import logging
from pathlib import Path
from typing import Any

from lf_releng_project_reporting.config import save_resolved_config
from util.zip_bundle import create_report_bundle

from .analysis import ReporterAnalysisMixin


class RepositoryReporter(ReporterAnalysisMixin):
    """Main orchestrator for repository reporting."""

    def __init__(
        self, config: dict[str, Any], logger: logging.Logger, api_stats: Any | None = None
    ) -> None:
        """
        Initialize the repository reporter.

        Args:
            config: Merged configuration dictionary
            logger: Logger instance for reporting progress and issues
            api_stats: Optional API statistics tracker for monitoring external API calls
        """
        # Resolve collaborators through the package facade so historical mock
        # patch points such as ``lf_releng_project_reporting.reporter.GitDataCollector``
        # continue to intercept construction.
        from . import (
            DataAggregator,
            FeatureRegistry,
            GitDataCollector,
            INFOYamlCollector,
            ModernReportRenderer,
        )

        self.config = config
        self.logger = logger
        self.api_stats = api_stats
        self.git_collector = GitDataCollector(config, {}, logger, api_stats=api_stats)
        self.feature_registry = FeatureRegistry(config, logger, api_stats=api_stats)
        self.aggregator = DataAggregator(config, logger)
        self.renderer = ModernReportRenderer(config, logger)
        self.info_yaml_collector = INFOYamlCollector(config)
        self.info_master_temp_dir: str | None = None
        self._info_master_path: Path | None = None

    def generate_reports(
        self, repos_path: Path, output_dir: Path, allow_empty: bool = False
    ) -> dict[str, Path]:
        """
        Generate complete reports (JSON, Markdown, HTML, ZIP).

        This is a convenience method that combines analysis and rendering into
        a single call. It:
        1. Analyzes all repositories
        2. Generates JSON report
        3. Generates Markdown report
        4. Generates HTML report (if enabled)
        5. Saves resolved configuration
        6. Creates ZIP bundle (if enabled)

        Args:
            repos_path: Path to directory containing repositories
            output_dir: Path to output directory for generated reports
            allow_empty: Forwarded to :meth:`analyze_repositories`. When
                ``False`` (the default), a hard error is raised if no
                repositories are discovered under ``repos_path``.

        Returns:
            Dictionary mapping output type to file path for all generated files

        Raises:
            NoRepositoriesError: If no repositories are discovered and
                ``allow_empty`` is ``False``.
        """
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Analyze repositories
        report_data = self.analyze_repositories(repos_path, allow_empty=allow_empty)

        project = self.config["project"]
        json_path = output_dir / "report_raw.json"
        markdown_path = output_dir / "report.md"
        html_path = output_dir / "report.html"
        config_path = output_dir / "config_resolved.json"

        generated_files = {}

        # Generate JSON report
        self.renderer.render_json_report(report_data, json_path)
        generated_files["json"] = json_path

        # Generate Markdown report
        self.renderer.render_markdown_report(report_data, markdown_path)
        generated_files["markdown"] = markdown_path

        # Generate HTML report (if not disabled)
        html_output_config = self.config.get("output", {})
        if not html_output_config.get("no_html", False):
            self.renderer.render_html_report(report_data, html_path)
            generated_files["html"] = html_path

        save_resolved_config(self.config, config_path)
        generated_files["config"] = config_path

        # Create ZIP bundle (if not disabled)
        zip_output_config = self.config.get("output", {})
        if not zip_output_config.get("no_zip", False):
            zip_path = create_report_bundle(output_dir, project, self.logger)
            generated_files["zip"] = zip_path

        return generated_files
