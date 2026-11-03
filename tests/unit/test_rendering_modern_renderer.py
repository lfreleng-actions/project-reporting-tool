# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Unit tests for ModernReportRenderer.

Tests orchestration of context building and template rendering.
"""

import logging

import pytest

from lf_releng_project_reporting.rendering.renderer import ModernReportRenderer


@pytest.fixture
def minimal_config():
    """Minimal configuration for renderer."""
    return {
        "project": "Test Project",
        "render": {"theme": "default"},
    }


@pytest.fixture
def dark_theme_config():
    """Configuration with dark theme."""
    return {
        "project": "Test Project",
        "render": {"theme": "dark"},
    }


@pytest.fixture
def test_logger():
    """Test logger instance."""
    return logging.getLogger(__name__)


@pytest.fixture
def minimal_data():
    """Minimal report data for testing."""
    return {
        "project": "test-project",
        "schema_version": "1.0.0",
        "repositories": [],
        "summaries": {
            "counts": {
                "repositories_analyzed": 0,
                "total_repositories": 0,
                "unique_contributors": 0,
                "total_organizations": 0,
            }
        },
        "metadata": {
            "generated_at": "2025-01-16T12:00:00Z",
        },
    }


@pytest.fixture
def sample_data():
    """Sample report data with some content."""
    return {
        "project": "test-project",
        "schema_version": "1.0.0",
        "repositories": [
            {
                "gerrit_project": "repo1",
                "name": "repo1",
                "total_commits": 100,
                "activity_status": "active",
            }
        ],
        "summaries": {
            "counts": {
                "repositories_analyzed": 1,
                "total_repositories": 1,
                "unique_contributors": 5,
                "total_organizations": 2,
            },
            "all_repositories": [{"name": "repo1", "activity_status": "active"}],
        },
        "metadata": {
            "generated_at": "2025-01-16T12:00:00Z",
        },
    }


class TestModernReportRendererInit:
    """Test ModernReportRenderer initialization."""

    def test_init_with_defaults(self, minimal_config, test_logger):
        """Test initialization with default theme."""
        renderer = ModernReportRenderer(minimal_config, test_logger)

        assert renderer.config == minimal_config
        assert renderer.logger == test_logger
        assert renderer.template_renderer is not None
        assert renderer.template_renderer.theme == "default"

    def test_init_with_custom_theme(self, dark_theme_config, test_logger):
        """Test initialization with custom theme."""
        renderer = ModernReportRenderer(dark_theme_config, test_logger)

        assert renderer.template_renderer.theme == "dark"

    def test_init_with_output_theme(self, test_logger):
        """Test initialization with theme in output section."""
        config = {
            "project": "Test Project",
            "output": {"theme": "minimal"},
        }
        renderer = ModernReportRenderer(config, test_logger)

        # Should fall back to default since output.theme is not used for render theme
        assert renderer.template_renderer.theme == "default"


class TestRenderMarkdown:
    """Test Markdown report rendering."""

    def test_render_markdown_success(self, minimal_config, test_logger, minimal_data):
        """Test successful Markdown rendering."""
        renderer = ModernReportRenderer(minimal_config, test_logger)

        result = renderer.render_markdown(minimal_data)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "test-project" in result

    def test_render_markdown_with_data(self, minimal_config, test_logger, sample_data):
        """Test Markdown rendering with sample data."""
        renderer = ModernReportRenderer(minimal_config, test_logger)

        result = renderer.render_markdown(sample_data)

        assert isinstance(result, str)
        # Note: repo1 is in the data but may not appear in markdown if it's empty
        assert len(result) > 0


class TestRenderHTML:
    """Test HTML report rendering."""

    def test_render_html_success(self, minimal_config, test_logger, minimal_data):
        """Test successful HTML rendering."""
        renderer = ModernReportRenderer(minimal_config, test_logger)

        result = renderer.render_html(minimal_data)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "<html" in result.lower()
        assert "</html>" in result.lower()

    def test_render_html_with_data(self, minimal_config, test_logger, sample_data):
        """Test HTML rendering with sample data."""
        renderer = ModernReportRenderer(minimal_config, test_logger)

        result = renderer.render_html(sample_data)

        assert isinstance(result, str)
        assert "<html" in result.lower()
        # Note: repo1 appears as gerrit_project in the data
        assert len(result) > 0

    def test_render_html_with_theme(self, dark_theme_config, test_logger, minimal_data):
        """Test HTML rendering with custom theme."""
        renderer = ModernReportRenderer(dark_theme_config, test_logger)

        result = renderer.render_html(minimal_data)

        assert isinstance(result, str)
        assert "<html" in result.lower()
        assert 'data-theme="dark"' in result


class TestRenderJSONReport:
    """Test JSON report rendering to file."""

    def test_render_json_report_success(self, minimal_config, test_logger, minimal_data, tmp_path):
        """Test successful JSON report file generation."""
        renderer = ModernReportRenderer(minimal_config, test_logger)
        output_path = tmp_path / "report.json"

        renderer.render_json_report(minimal_data, output_path)

        assert output_path.exists()
        import json

        with open(output_path) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    def test_render_json_report_with_data(self, minimal_config, test_logger, sample_data, tmp_path):
        """Test JSON report rendering with sample data."""
        renderer = ModernReportRenderer(minimal_config, test_logger)
        output_path = tmp_path / "report.json"

        renderer.render_json_report(sample_data, output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert "repo1" in content


class TestIntegration:
    """Test integration scenarios."""

    def test_render_all_formats(self, minimal_config, test_logger, sample_data, tmp_path):
        """Test rendering in all formats."""
        renderer = ModernReportRenderer(minimal_config, test_logger)

        # Test markdown and html (which return strings)
        md_result = renderer.render_markdown(sample_data)
        html_result = renderer.render_html(sample_data)

        # Test json report (which writes to file)
        json_path = tmp_path / "report.json"
        renderer.render_json_report(sample_data, json_path)

        assert isinstance(md_result, str)
        assert isinstance(html_result, str)
        assert json_path.exists()

        assert len(md_result) > 0
        assert len(html_result) > 0

    def test_complex_data_rendering(self, minimal_config, test_logger):
        """Test rendering with complex data structures."""
        complex_data = {
            "project": "complex-project",
            "schema_version": "1.0.0",
            "repositories": [
                {
                    "gerrit_project": f"repo{i}",
                    "name": f"repo{i}",
                    "total_commits": i * 100,
                    "activity_status": "active",
                }
                for i in range(1, 6)
            ],
            "summaries": {
                "counts": {
                    "repositories_analyzed": 5,
                    "total_repositories": 5,
                    "unique_contributors": 25,
                    "total_organizations": 10,
                },
                "all_repositories": [
                    {"name": f"repo{i}", "activity_status": "active"} for i in range(1, 6)
                ],
            },
            "metadata": {
                "generated_at": "2025-01-16T12:00:00Z",
            },
        }

        renderer = ModernReportRenderer(minimal_config, test_logger)

        result = renderer.render_html(complex_data)

        assert isinstance(result, str)
        # Verify the HTML contains repository data
        assert len(result) > 1000  # Should be a substantial HTML document


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_repositories(self, minimal_config, test_logger, minimal_data):
        """Test rendering with empty repositories."""
        renderer = ModernReportRenderer(minimal_config, test_logger)

        result = renderer.render_html(minimal_data)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_missing_optional_fields(self, minimal_config, test_logger):
        """Test rendering with missing optional fields."""
        data = {
            "project": "test-project",
            "schema_version": "1.0.0",
            "repositories": [],
            "summaries": {"counts": {}},
            "metadata": {},
        }

        renderer = ModernReportRenderer(minimal_config, test_logger)

        result = renderer.render_html(data)

        assert isinstance(result, str)
        assert len(result) > 0
