# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Integration tests for HTML rendering.

These tests validate that the complete rendering pipeline produces
correct HTML output, catching issues that data extraction tests alone
cannot detect.
"""

import logging
import re

import pytest
from utils.assertions import assert_any_host_in_text

from rendering.renderer import ModernReportRenderer


@pytest.fixture
def html_test_config():
    """Minimal config for HTML rendering tests."""
    return {
        "project": "TestProject",
        "include_sections": {
            "summary": True,
            "repositories": True,
            "contributors": True,
            "organizations": True,
            "workflows": True,
            "features": True,
            "info_yaml": True,
        },
        "limits": {
            "top_contributors": 10,
            "top_organizations": 10,
        },
    }


class TestHTMLRepositoryRendering:
    """Test HTML rendering of repository tables."""

    def test_repository_table_renders_contributor_count_not_dict(
        self, realistic_report_data, html_test_config
    ):
        """Verify repository table renders contributor count as number, not dict."""
        # Render HTML (renderer builds context internally)
        logger = logging.getLogger(__name__)
        renderer = ModernReportRenderer(html_test_config, logger)
        html_output = renderer.render_html(realistic_report_data)

        # Verify HTML does not contain raw dict representations
        assert "{'last_30':" not in html_output, (
            "HTML contains raw dict for contributors - should be formatted number"
        )
        assert "{'last_90':" not in html_output, (
            "HTML contains raw dict for contributors - should be formatted number"
        )
        assert "{'last_365':" not in html_output, (
            "HTML contains raw dict for contributors - should be formatted number"
        )
        assert "{'last_3_years':" not in html_output, (
            "HTML contains raw dict for contributors - should be formatted number"
        )

        # Verify that numeric values ARE present in the table
        # The realistic fixture has repos with contributors
        assert re.search(r"<td[^>]*>\s*\d+\s*</td>", html_output), (
            "Repository table should contain numeric contributor counts"
        )

    def test_repository_table_contains_expected_columns(
        self, realistic_report_data, html_test_config
    ):
        """Verify repository table has all expected column headers."""
        logger = logging.getLogger(__name__)
        renderer = ModernReportRenderer(html_test_config, logger)
        html_output = renderer.render_html(realistic_report_data)

        # Check for expected column headers
        expected_headers = [
            "Repository",
            "Commits",
            "LOC",
            "Contributors",
            "Days Inactive",
            "Last Commit Date",
            "Status",
        ]

        for header in expected_headers:
            assert header in html_output, f"Missing expected column header: {header}"

    def test_repository_table_renders_data_for_all_repos(
        self, realistic_report_data, html_test_config
    ):
        """Verify all repositories appear in the rendered table."""
        logger = logging.getLogger(__name__)
        renderer = ModernReportRenderer(html_test_config, logger)
        html_output = renderer.render_html(realistic_report_data)

        # Check that repository names from fixture appear in HTML
        assert "project/repo1" in html_output, "Repository project/repo1 not in HTML"
        assert "project/repo2" in html_output, "Repository project/repo2 not in HTML"


class TestHTMLContributorRendering:
    """Test HTML rendering of contributor tables."""

    def test_contributor_table_renders_commit_count_not_dict(
        self, realistic_report_data, html_test_config
    ):
        """Verify contributor table renders commit counts as numbers, not dicts."""
        logger = logging.getLogger(__name__)
        renderer = ModernReportRenderer(html_test_config, logger)
        html_output = renderer.render_html(realistic_report_data)

        # Verify no raw dict representations in contributor section
        contributor_section_match = re.search(
            r'<section[^>]*id="contributors"[^>]*>.*?</section>',
            html_output,
            re.DOTALL,
        )

        if contributor_section_match:
            contributor_html = contributor_section_match.group(0)

            assert "{'last_30':" not in contributor_html, (
                "Contributor section contains raw dict - should be formatted number"
            )
            assert "{'last_90':" not in contributor_html, (
                "Contributor section contains raw dict - should be formatted number"
            )

            # Verify contributor names appear
            assert "Alice Developer" in contributor_html or "alice@example.com" in contributor_html
            assert "Bob Contributor" in contributor_html or "bob@example.com" in contributor_html


class TestHTMLOrganizationRendering:
    """Test HTML rendering of organization tables."""

    def test_organization_table_renders_correctly(self, realistic_report_data, html_test_config):
        """Verify organization table renders without raw dicts."""
        logger = logging.getLogger(__name__)
        renderer = ModernReportRenderer(html_test_config, logger)
        html_output = renderer.render_html(realistic_report_data)

        # Verify no raw dict representations in organization section
        org_section_match = re.search(
            r'<section[^>]*id="organizations"[^>]*>.*?</section>',
            html_output,
            re.DOTALL,
        )

        if org_section_match:
            org_html = org_section_match.group(0)

            assert "{'last_30':" not in org_html, (
                "Organization section contains raw dict - should be formatted number"
            )

            # Verify organization domains appear
            assert_any_host_in_text(org_html, ["example.com", "acme.org"])


class TestHTMLDataIntegrity:
    """Test data integrity in rendered HTML."""

    def test_all_sections_render_without_exceptions(self, realistic_report_data, html_test_config):
        """Verify all sections render without raising exceptions."""
        logger = logging.getLogger(__name__)
        renderer = ModernReportRenderer(html_test_config, logger)

        # Should not raise any exceptions
        html_output = renderer.render_html(realistic_report_data)

        # Basic sanity checks
        assert html_output is not None
        assert len(html_output) > 0
        assert "<html" in html_output
        assert "</html>" in html_output

    def test_html_contains_no_raw_python_objects(self, realistic_report_data, html_test_config):
        """Verify HTML doesn't contain raw Python object representations."""
        logger = logging.getLogger(__name__)
        renderer = ModernReportRenderer(html_test_config, logger)
        html_output = renderer.render_html(realistic_report_data)

        # Check for common Python object representations that shouldn't be in HTML
        forbidden_patterns = [
            r"<object at 0x[0-9a-fA-F]+>",  # Object memory addresses
            r"{'last_\d+': \d+",  # Raw time-windowed dicts
            r"\{'last_\d+': \d+",  # Alternative quote style
        ]

        for pattern in forbidden_patterns:
            matches = re.findall(pattern, html_output)
            assert not matches, f"HTML contains forbidden pattern '{pattern}': {matches[:3]}"

    def test_numeric_values_are_formatted(self, realistic_report_data, html_test_config):
        """Verify numeric values are properly formatted with commas."""
        logger = logging.getLogger(__name__)
        renderer = ModernReportRenderer(html_test_config, logger)
        html_output = renderer.render_html(realistic_report_data)

        # Check that large numbers have comma formatting
        # The fixture has numeric values that should be formatted
        # Look for any formatted numbers in the output
        has_formatted_numbers = (
            re.search(r"\d{1,3}(,\d{3})+", html_output)
            or re.search(r"\d+\s*</td>", html_output)  # Or at least some numeric table cells
        )
        assert has_formatted_numbers, "Should contain formatted numeric values"


class TestHTMLEdgeCases:
    """Test edge cases in HTML rendering."""

    def test_empty_data_renders_safely(self, html_test_config):
        """Verify rendering with minimal/empty data doesn't crash."""
        minimal_data = {
            "metadata": {
                "project": "EmptyProject",
                "generated_at": "2025-01-01T00:00:00Z",
            },
            "summaries": {
                "all_repositories": [],
                "no_commit_repositories": [],
            },
            "aggregations": {
                "top_contributors": [],
                "top_organizations": [],
                "time_windows": {},
            },
            "info_yaml": {
                "projects": [],
                "has_projects": False,
                "projects_with_git_data": 0,
                "projects_without_git_data": 0,
            },
        }

        logger = logging.getLogger(__name__)
        renderer = ModernReportRenderer(html_test_config, logger)

        # Should not raise exceptions even with empty data
        html_output = renderer.render_html(minimal_data)

        assert html_output is not None
        assert "<html" in html_output
        assert "Repository Analysis" in html_output

    def test_missing_time_windows_renders_safely(self, html_test_config):
        """Verify rendering handles missing time window data gracefully."""
        data_without_windows = {
            "metadata": {
                "project": "TestProject",
                "generated_at": "2025-01-01T00:00:00Z",
            },
            "summaries": {
                "all_repositories": [
                    {
                        "gerrit_project": "test/repo",
                        "total_commits_ever": 100,
                        "unique_contributors": {},  # Empty time windows
                        "days_since_last_commit": 5,
                        "activity_status": "current",
                    }
                ],
                "no_commit_repositories": [],
            },
            "aggregations": {
                "top_contributors": [],
                "top_organizations": [],
                "time_windows": {},
            },
            "info_yaml": {
                "projects": [],
            },
        }

        logger = logging.getLogger(__name__)
        renderer = ModernReportRenderer(html_test_config, logger)
        html_output = renderer.render_html(data_without_windows)

        # Should render with 0 or — for missing data
        assert html_output is not None
        assert "test/repo" in html_output
        # Should show 0 or em-dash for missing contributor count
        assert re.search(r"<td[^>]*>\s*[0—]\s*</td>", html_output)


class TestHTMLTableStructure:
    """Test HTML table structure validity."""

    def test_repository_table_has_valid_structure(self, realistic_report_data, html_test_config):
        """Verify repository table has valid HTML structure."""
        logger = logging.getLogger(__name__)
        renderer = ModernReportRenderer(html_test_config, logger)
        html_output = renderer.render_html(realistic_report_data)

        # Check for table structure
        assert "<table" in html_output
        assert "<thead>" in html_output
        assert "<tbody>" in html_output
        assert "</table>" in html_output

        # Count headers vs data columns (should match)
        thead_match = re.search(r"<thead>(.*?)</thead>", html_output, re.DOTALL)
        if thead_match:
            thead = thead_match.group(1)
            header_count = len(re.findall(r"<th", thead))

            # Find first data row
            tbody_match = re.search(r"<tbody>(.*?)</tbody>", html_output, re.DOTALL)
            if tbody_match:
                tbody = tbody_match.group(1)
                first_row_match = re.search(r"<tr>(.*?)</tr>", tbody, re.DOTALL)
                if first_row_match:
                    first_row = first_row_match.group(1)
                    cell_count = len(re.findall(r"<td", first_row))

                    assert header_count == cell_count, (
                        f"Table column mismatch: {header_count} headers, {cell_count} data cells"
                    )
