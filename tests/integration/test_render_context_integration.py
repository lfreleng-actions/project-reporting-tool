# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Integration tests for RenderContext data extraction.

These tests validate that RenderContext correctly extracts data from realistic
JSON report structures and transforms it into the format expected by templates.

This is critical because unit tests were using simplified/fake data that didn't
match the actual schema, allowing bugs to slip through. These integration tests
use fixtures that match the ACTUAL data structure produced by the aggregation
pipeline.
"""

from src.rendering.context import RenderContext


class TestRenderContextDataExtraction:
    """Test that RenderContext extracts data correctly from realistic JSON."""

    def test_extracts_project_metadata_correctly(self, realistic_report_data, minimal_config):
        """Verify project metadata is extracted with correct date formatting."""
        context = RenderContext(realistic_report_data, minimal_config)
        result = context.build()

        project = result["project"]
        assert project["name"] == "test-project"
        assert project["schema_version"] == "1.2.0"
        assert "generated_at" in project
        assert "generated_at_formatted" in project
        # Should be formatted as human-readable date, not "Unknown"
        assert project["generated_at_formatted"] != "Unknown"
        assert "UTC" in project["generated_at_formatted"]

    def test_extracts_summary_statistics_from_actual_data(
        self, realistic_report_data, minimal_config
    ):
        """Verify summary statistics are calculated from actual repo data."""
        context = RenderContext(realistic_report_data, minimal_config)
        result = context.build()

        summary = result["summary"]

        # Should extract from counts
        assert summary["repositories_analyzed"] == 2
        assert summary["total_repositories"] == 2

        # Should count authors from authors dict
        assert summary["unique_contributors"] == 2

        # Should sum total_commits_ever from all repos
        # repo1: 1250, repo2: 500 = 1750
        assert summary["total_commits"] == 1750
        assert summary["total_commits_formatted"] == "1.8K"

        # Should extract from counts
        assert summary["total_organizations"] == 1
        assert summary["active_count"] == 0
        assert summary["inactive_count"] == 1

        # Should calculate LOC from the configured, non-overlapping reporting window.
        assert summary["total_lines_added"] == 50000
        assert summary["total_lines_removed"] == 20000
        assert summary["net_lines"] == 30000

    def test_extracts_repositories_with_correct_structure(
        self, realistic_report_data, minimal_config
    ):
        """Verify repository data is transformed correctly."""
        context = RenderContext(realistic_report_data, minimal_config)
        result = context.build()

        repos = result["repositories"]

        # Should have repositories
        assert repos["has_repositories"] is True
        assert repos["all_count"] == 2

        # Check first repo transformation
        repo1 = repos["all"][0]
        assert repo1["gerrit_project"] == "project/repo1"
        assert repo1["name"] == "project/repo1"
        assert repo1["activity_status_text"] == "current"
        assert repo1["activity_status"] == "✅"  # Emoji for current
        assert repo1["last_commit_age"] == 5  # days_since_last_commit
        assert repo1["total_commits"] == 1250  # total_commits_ever
        # unique_contributors should be extracted as a number for display
        assert isinstance(repo1["unique_contributors"], int)
        assert repo1["unique_contributors"] == 35  # last_365 value
        assert repo1["jenkins_jobs_count"] == 2

    def test_extracts_contributors_with_time_windowed_data(
        self, realistic_report_data, minimal_config
    ):
        """Verify contributors are extracted with correct time-windowed metrics."""
        context = RenderContext(realistic_report_data, minimal_config)
        result = context.build()

        contributors = result["contributors"]

        assert contributors["has_contributors"] is True
        assert contributors["top_by_commits_count"] == 2

        # Check first contributor (Alice)
        alice = contributors["top_by_commits"][0]
        assert alice["name"] == "Alice Developer"
        assert alice["email"] == "alice@example.com"
        # Should extract last_3_years value from commits dict
        assert alice["total_commits"] == 120

        # Check LOC contributor
        alice_loc = contributors["top_by_loc"][0]
        assert alice_loc["name"] == "Alice Developer"
        # Should extract last_3_years values from LOC dicts
        # Field names changed to match template expectations
        assert alice_loc["total_lines_added"] == 30000  # last_365 value
        assert alice_loc["total_lines_removed"] == 12000  # last_365 value
        assert alice_loc["net_lines"] == 18000  # last_365 value

    def test_extracts_organizations_with_time_windowed_data(
        self, realistic_report_data, minimal_config
    ):
        """Verify organizations are extracted with correct time-windowed metrics."""
        context = RenderContext(realistic_report_data, minimal_config)
        result = context.build()

        orgs = result["organizations"]

        assert orgs["has_organizations"] is True
        assert orgs["total_count"] == 1

        # Check organization data
        org = orgs["top"][0]
        # Domain is used as name
        assert org["name"] == "example.com"
        assert org["domain"] == "example.com"
        # Should extract from contributor_count
        assert org["unique_contributors"] == 2
        # Should extract last_3_years from commits dict
        assert org["total_commits"] == 450
        # Should extract last_3_years from repositories_count dict
        assert org["repositories_count"] == 1  # last_365 value

    def test_extracts_features_matrix(self, realistic_report_data, minimal_config):
        """Verify features are extracted correctly."""
        context = RenderContext(realistic_report_data, minimal_config)
        result = context.build()

        features = result["features"]

        assert features["has_features"] is True
        assert features["repositories_count"] == 2
        # Should detect all unique features across repos
        # Note: features_list contains original names with has_ prefix
        assert "has_ci" in features["features_list"]
        assert "has_gitreview" in features["features_list"]

        # Check matrix structure
        assert len(features["matrix"]) == 2
        repo1_features = features["matrix"][0]
        assert repo1_features["repo_name"] == "project/repo1"
        # Features in matrix are normalized (has_ prefix stripped)
        assert repo1_features["features"]["ci"] is True
        assert repo1_features["features"]["gitreview"] is True

    def test_extracts_workflows_from_jenkins_data(self, realistic_report_data, minimal_config):
        """Verify CI/CD workflows are extracted from nested jenkins data."""
        context = RenderContext(realistic_report_data, minimal_config)
        result = context.build()

        workflows = result["workflows"]

        assert workflows["has_workflows"] is True
        assert workflows["total_count"] == 2

        # Check job extraction
        job1 = workflows["all"][0]
        assert job1["name"] == "repo1-verify"
        assert job1["repo"] == "project/repo1"
        assert job1["status"] == "SUCCESS"
        assert job1["url"] == "https://jenkins.example.com/job/repo1-verify"

        # Check status counts
        assert workflows["status_counts"]["SUCCESS"] == 2

    def test_extracts_orphaned_jobs(self, realistic_report_data, minimal_config):
        """Verify orphaned jobs are extracted and transformed."""
        context = RenderContext(realistic_report_data, minimal_config)
        result = context.build()

        orphaned = result["orphaned_jobs"]

        assert orphaned["has_orphaned_jobs"] is True
        assert orphaned["total_count"] == 2

        # Check job transformation
        job1 = orphaned["jobs"][0]  # Should be sorted by score
        assert "name" in job1
        assert "project" in job1
        assert "state" in job1
        assert "score" in job1
        assert job1["score"] > 0

        # Check by_state counts
        assert orphaned["by_state"]["READ_ONLY"] == 1
        assert orphaned["by_state"]["ARCHIVED"] == 1

    def test_extracts_time_windows(self, realistic_report_data, minimal_config):
        """Verify time windows are extracted correctly."""
        context = RenderContext(realistic_report_data, minimal_config)
        result = context.build()

        time_windows = result["time_windows"]

        assert len(time_windows) == 2

        # Check first window
        window1 = time_windows[0]
        assert window1["name"] == "last_30"
        assert window1["days"] == 30
        assert "start_date" in window1
        assert "end_date" in window1
        assert window1["commits"] == 45
        assert window1["contributors"] == 12
        assert window1["lines_added"] == 5000
        assert window1["lines_removed"] == 2000
        assert window1["net_lines"] == 3000


class TestRenderContextConfigHandling:
    """Test configuration handling and edge cases."""

    def test_handles_project_as_string(self, realistic_report_data):
        """Verify project can be a string (not just dict)."""
        config = {"project": "simple-string-name"}
        context = RenderContext(realistic_report_data, config)
        result = context.build()

        assert result["config"]["project_name"] == "simple-string-name"

    def test_handles_project_as_dict(self, realistic_report_data):
        """Verify project can be a dict with name field."""
        config = {"project": {"name": "Dict Project Name"}}
        context = RenderContext(realistic_report_data, config)
        result = context.build()

        assert result["config"]["project_name"] == "Dict Project Name"

    def test_applies_contributor_limit(self, realistic_report_data):
        """Verify contributor limit is applied."""
        config = {
            "output": {
                "top_contributors_limit": 1,
            }
        }
        context = RenderContext(realistic_report_data, config)
        result = context.build()

        # Should limit to 1 even though we have 2
        assert len(result["contributors"]["top_by_commits"]) == 1

    def test_applies_organization_limit(self, realistic_report_data):
        """Verify organization limit is applied."""
        config = {
            "output": {
                "top_organizations_limit": 0,  # Limit to 0
            }
        }
        context = RenderContext(realistic_report_data, config)
        result = context.build()

        # Should be empty due to limit
        assert len(result["organizations"]["top"]) == 0
        # But total_count should still be correct
        assert result["organizations"]["total_count"] == 1


class TestRenderContextTableOfContents:
    """Test table of contents generation."""

    def test_toc_includes_all_sections_with_data(self, realistic_report_data, full_config):
        """Verify TOC includes all sections that have data."""
        context = RenderContext(realistic_report_data, full_config)
        result = context.build()

        toc = result["toc"]

        assert toc["has_sections"] is True
        assert len(toc["sections"]) > 0

        # Extract section titles
        titles = [s["title"] for s in toc["sections"]]

        # Should include these sections (they have data)
        assert "Global Summary" in titles
        assert "Gerrit Projects" in titles
        assert "Top Contributors" in titles
        assert "Top Organizations" in titles
        assert "Repository Feature Matrix" in titles
        assert "Deployed CI/CD Jobs" in titles
        assert "Orphaned Jenkins Jobs" in titles

    def test_toc_excludes_sections_without_data(self, realistic_report_data, full_config):
        """Verify TOC excludes sections without data."""
        # Remove all repositories to make sections empty
        data = realistic_report_data.copy()
        data["repositories"] = []
        data["summaries"]["all_repositories"] = []
        data["summaries"]["top_contributors_commits"] = []
        data["summaries"]["top_contributors_loc"] = []
        data["summaries"]["top_organizations"] = []

        context = RenderContext(data, full_config)
        result = context.build()

        toc = result["toc"]
        titles = [s["title"] for s in toc["sections"]]

        # Should NOT include these (no data)
        assert "Gerrit Projects" not in titles
        assert "Top Contributors" not in titles
        assert "Top Organizations" not in titles
        assert "Repository Feature Matrix" not in titles

        # Should still include summary
        assert "Global Summary" in titles

    def test_toc_respects_config_disabled_sections(self, realistic_report_data):
        """Verify TOC respects section enable/disable config."""
        config = {
            "output": {
                "include_contributors": False,
                "include_organizations": False,
            }
        }

        context = RenderContext(realistic_report_data, config)
        result = context.build()

        toc = result["toc"]
        titles = [s["title"] for s in toc["sections"]]

        # Should NOT include disabled sections
        assert "Top Contributors" not in titles
        assert "Top Organizations" not in titles

        # Should still include enabled sections with data
        assert "Global Summary" in titles
        assert "Gerrit Projects" in titles


class TestRenderContextEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_empty_repositories(self, minimal_config):
        """Verify graceful handling of empty repositories."""
        data = {
            "schema_version": "1.0",
            "generated_at": "2025-01-01T00:00:00Z",
            "project": "test",
            "repositories": [],
            "authors": {},
            "organizations": {},
            "summaries": {
                "counts": {},
                "all_repositories": [],
                "no_commit_repositories": [],
                "top_contributors_commits": [],
                "top_contributors_loc": [],
                "top_organizations": [],
            },
            "orphaned_jenkins_jobs": {
                "jobs": {},
                "by_state": {},
            },
            "time_windows": [],
        }

        context = RenderContext(data, minimal_config)
        result = context.build()

        # Should not crash
        assert result["summary"]["total_commits"] == 0
        assert result["repositories"]["has_repositories"] is False
        assert result["contributors"]["has_contributors"] is False
        assert result["organizations"]["has_organizations"] is False

    def test_handles_missing_time_windows(self, realistic_report_data, minimal_config):
        """Verify graceful handling of missing time_windows."""
        data = realistic_report_data.copy()
        data["time_windows"] = None  # Not a list

        context = RenderContext(data, minimal_config)
        result = context.build()

        # Should return empty list, not crash
        assert result["time_windows"] == []

    def test_handles_missing_nested_jenkins_data(self, realistic_report_data, minimal_config):
        """Verify graceful handling of missing jenkins.jobs."""
        data = realistic_report_data.copy()
        # Remove jenkins data from repos
        for repo in data["repositories"]:
            repo["jenkins"] = {}  # No jobs key

        context = RenderContext(data, minimal_config)
        result = context.build()

        # Should handle gracefully
        assert result["workflows"]["total_count"] == 0
        assert result["workflows"]["has_workflows"] is False

    def test_calculates_loc_correctly_with_multiple_time_windows(
        self, realistic_report_data, minimal_config
    ):
        """Verify overlapping LOC windows are not summed together."""
        context = RenderContext(realistic_report_data, minimal_config)
        result = context.build()

        summary = result["summary"]

        # The report uses last_365. The shorter and longer windows overlap with
        # it, so only repo1's last_365 values belong in the summary.
        assert summary["total_lines_added"] == 50000
        assert summary["total_lines_removed"] == 20000
        assert summary["net_lines"] == 30000


class TestRenderContextDataIntegrity:
    """Test data integrity and consistency."""

    def test_repository_counts_are_consistent(self, realistic_report_data, minimal_config):
        """Verify repository counts are consistent across sections."""
        context = RenderContext(realistic_report_data, minimal_config)
        result = context.build()

        # Should be consistent
        assert result["summary"]["repositories_analyzed"] == 2
        assert result["repositories"]["all_count"] == 2
        assert len(result["repositories"]["all"]) == 2

    def test_contributor_counts_are_consistent(self, realistic_report_data, minimal_config):
        """Verify contributor counts are consistent."""
        context = RenderContext(realistic_report_data, minimal_config)
        result = context.build()

        # Should count from authors dict
        assert result["summary"]["unique_contributors"] == 2
        # Should have contributors in top lists
        assert result["contributors"]["top_by_commits_count"] >= 1

    def test_organization_counts_are_consistent(self, realistic_report_data, minimal_config):
        """Verify organization counts are consistent."""
        context = RenderContext(realistic_report_data, minimal_config)
        result = context.build()

        assert result["summary"]["total_organizations"] == 1
        assert result["organizations"]["total_count"] == 1

    def test_all_required_context_keys_present(self, realistic_report_data, minimal_config):
        """Verify all required context keys are present."""
        context = RenderContext(realistic_report_data, minimal_config)
        result = context.build()

        # Top-level keys that templates expect
        required_keys = [
            "project",
            "summary",
            "repositories",
            "contributors",
            "organizations",
            "features",
            "workflows",
            "orphaned_jobs",
            "time_windows",
            "config",
            "toc",
        ]

        for key in required_keys:
            assert key in result, f"Missing required key: {key}"

    def test_numeric_values_are_correct_types(self, realistic_report_data, minimal_config):
        """Verify numeric values are integers/floats, not dicts."""
        context = RenderContext(realistic_report_data, minimal_config)
        result = context.build()

        # These should be numeric, not dicts
        assert isinstance(result["summary"]["total_commits"], int)
        assert isinstance(result["summary"]["unique_contributors"], int)
        assert isinstance(result["summary"]["total_organizations"], int)

        # Contributor commits should be numeric
        if result["contributors"]["top_by_commits"]:
            first_contrib = result["contributors"]["top_by_commits"][0]
            assert isinstance(first_contrib["total_commits"], int)

        # Organization commits should be numeric
        if result["organizations"]["top"]:
            first_org = result["organizations"]["top"][0]
            assert isinstance(first_org["total_commits"], int)
            assert isinstance(first_org["unique_contributors"], int)
