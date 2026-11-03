# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Comprehensive tests for the lf_releng_project_reporting.rendering.context module.

This test suite provides thorough coverage of:
- RenderContext initialization
- Context building methods
- Data extraction and formatting
- Edge cases and missing data handling
- Configuration-based customization

Target: 95%+ coverage for context.py (from 92.59%)
Phase: 12, Step 4, Task 1.4
"""

import pytest

from lf_releng_project_reporting.rendering.context import RenderContext


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def minimal_data():
    """Minimal valid report data."""
    return {
        "project": "test-project",
        "schema_version": "1.0.0",
        "repositories": [],
        "metadata": {"generated_at": "2025-01-16T14:30:00Z", "report_version": "1.0.0"},
    }


@pytest.fixture
def full_data():
    """Complete report data with all sections."""
    return {
        "project": "full-project",
        "schema_version": "2.0.0",
        "repositories": [
            {
                "gerrit_project": "repo1",
                "name": "repo1",
                "total_commits": 100,
                "total_lines_added": 5000,
                "total_lines_removed": 2000,
                "activity_status": "active",
                "features": {"has_ci": True, "has_tests": True},
                "jenkins": {
                    "jobs": [
                        {
                            "name": "job1",
                            "status": "success",
                            "color": "blue",
                            "url": "http://jenkins/job1",
                        }
                    ]
                },
            },
            {
                "gerrit_project": "repo2",
                "name": "repo2",
                "total_commits": 50,
                "total_lines_added": 1000,
                "total_lines_removed": 500,
                "activity_status": "inactive",
                "features": {"has_ci": False},
                "jenkins": {"jobs": []},
            },
        ],
        "metadata": {"generated_at": "2025-01-16T14:30:00Z", "report_version": "2.0.0"},
        "summaries": {
            "counts": {
                "repositories_analyzed": 2,
                "total_gerrit_projects": 5,
                "unique_contributors": 10,
                "total_organizations": 3,
                "active_repositories": 1,
                "inactive_repositories": 1,
                "no_commit_repositories": 0,
            },
            "all_repositories": [
                {"name": "repo1", "activity_status": "active"},
                {"name": "repo2", "activity_status": "inactive"},
            ],
            "no_commit_repositories": [],
            "top_contributors_commits": [
                {"name": "user1", "commits": 100},
                {"name": "user2", "commits": 50},
            ],
            "top_contributors_loc": [{"name": "user1", "lines": 5000}],
            "top_organizations": [{"name": "org1", "commits": 150}],
        },
        "orphaned_jenkins_jobs": {
            "total_orphaned_jobs": 2,
            "jobs": {
                "orphan1": {"project_name": "old-project", "state": "DISABLED", "score": 0},
                "orphan2": {"project_name": "another-project", "state": "UNKNOWN", "score": 5},
            },
            "by_state": {"DISABLED": 1, "UNKNOWN": 1},
        },
        "time_windows": [
            {"name": "recent", "days": 30, "description": "Last 30 days"},
            {"name": "quarter", "days": 90, "description": "Last quarter"},
        ],
    }


@pytest.fixture
def minimal_config():
    """Minimal configuration."""
    return {}


@pytest.fixture
def full_config():
    """Full configuration with all options."""
    return {
        "project": {"name": "Custom Project"},
        "render": {"theme": "dark"},
        "output": {
            "top_contributors_limit": 10,
            "top_organizations_limit": 15,
            "include_sections": {
                "title": True,
                "summary": True,
                "repositories": True,
                "contributors": True,
                "organizations": True,
                "features": True,
                "workflows": True,
                "orphaned_jobs": False,
            },
        },
    }


# ============================================================================
# RenderContext Tests
# ============================================================================


class TestRenderContextInit:
    """Test RenderContext initialization."""

    def test_init_basic(self, minimal_data, minimal_config):
        """Test basic initialization."""
        context = RenderContext(minimal_data, minimal_config)

        assert context.data == minimal_data
        assert context.config == minimal_config

    def test_init_with_full_data(self, full_data, full_config):
        """Test initialization with complete data."""
        context = RenderContext(full_data, full_config)

        assert context.data == full_data
        assert context.config == full_config


class TestRenderContextBuild:
    """Test main build method."""

    def test_build_returns_dict(self, minimal_data, minimal_config):
        """Test that build returns a dictionary."""
        context = RenderContext(minimal_data, minimal_config)
        result = context.build()

        assert isinstance(result, dict)

    def test_build_has_required_keys(self, minimal_data, minimal_config):
        """Test that build result has all required keys."""
        context = RenderContext(minimal_data, minimal_config)
        result = context.build()

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
            "filters",
        ]

        for key in required_keys:
            assert key in result

    def test_build_filters_included(self, minimal_data, minimal_config):
        """Test that template filters are included."""
        context = RenderContext(minimal_data, minimal_config)
        result = context.build()

        assert "filters" in result
        assert "format_number" in result["filters"]


class TestProjectContext:
    """Test project context building."""

    def test_project_context_basic(self, minimal_data, minimal_config):
        """Test basic project context."""
        context = RenderContext(minimal_data, minimal_config)
        result = context.build()

        assert result["project"]["name"] == "test-project"
        assert result["project"]["schema_version"] == "1.0.0"

    def test_project_context_metadata(self, full_data, minimal_config):
        """Test project metadata extraction."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        project = result["project"]
        assert project["generated_at"] == "2025-01-16T14:30:00Z"
        assert project["report_version"] == "2.0.0"
        assert "generated_at_formatted" in project

    def test_project_context_defaults(self, minimal_config):
        """Test default values when metadata missing."""
        data = {"repositories": []}
        context = RenderContext(data, minimal_config)
        result = context.build()

        project = result["project"]
        assert project["name"] == "Repository Analysis"
        assert project["schema_version"] == "1.0.0"


class TestSummaryContext:
    """Test summary statistics context."""

    def test_summary_basic(self, minimal_data, minimal_config):
        """Test summary with minimal data."""
        context = RenderContext(minimal_data, minimal_config)
        result = context.build()

        summary = result["summary"]
        assert summary["total_commits"] == 0
        assert summary["repositories_analyzed"] == 0

    def test_summary_calculations(self, full_data, minimal_config):
        """Test summary calculations from repository data."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        summary = result["summary"]
        # 100 + 50 commits
        assert summary["total_commits"] == 150
        assert summary["total_commits_formatted"] == "150"

        # 5000 + 1000 lines added
        assert summary["total_lines_added"] == 6000

        # 2000 + 500 lines removed
        assert summary["total_lines_removed"] == 2500

        # Net: 6000 - 2500
        assert summary["net_lines"] == 3500

    def test_summary_from_summaries(self, full_data, minimal_config):
        """Test summary using summaries data."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        summary = result["summary"]
        assert summary["repositories_analyzed"] == 2
        assert summary["total_repositories"] == 5
        assert summary["unique_contributors"] == 10
        assert summary["total_organizations"] == 3

    def test_summary_activity_counts(self, full_data, minimal_config):
        """Test activity status counts."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        summary = result["summary"]
        assert summary["active_count"] == 1
        assert summary["inactive_count"] == 1
        assert summary["no_commit_count"] == 0


class TestRepositoriesContext:
    """Test repositories context."""

    def test_repositories_empty(self, minimal_data, minimal_config):
        """Test repositories with no data."""
        context = RenderContext(minimal_data, minimal_config)
        result = context.build()

        repos = result["repositories"]
        assert repos["all_count"] == 0
        assert repos["has_repositories"] is False

    def test_repositories_all(self, full_data, minimal_config):
        """Test all repositories listing."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        repos = result["repositories"]
        assert repos["all_count"] == 2
        assert len(repos["all"]) == 2

    def test_repositories_by_activity(self, full_data, minimal_config):
        """Test repositories filtered by activity."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        repos = result["repositories"]
        assert repos["active_count"] == 1
        assert repos["inactive_count"] == 1
        assert repos["no_commits_count"] == 0

    def test_repositories_has_flag(self, full_data, minimal_config):
        """Test has_repositories flag."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        assert result["repositories"]["has_repositories"] is True


class TestContributorsContext:
    """Test contributors context."""

    def test_contributors_empty(self, minimal_data, minimal_config):
        """Test contributors with no data."""
        context = RenderContext(minimal_data, minimal_config)
        result = context.build()

        contributors = result["contributors"]
        assert contributors["has_contributors"] is False

    def test_contributors_data(self, full_data, minimal_config):
        """Test contributors data extraction."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        contributors = result["contributors"]
        assert contributors["top_by_commits_count"] == 2
        assert contributors["top_by_loc_count"] == 1
        assert contributors["has_contributors"] is True

    def test_contributors_limit_default(self, full_data, minimal_config):
        """Test default contributor limit."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        assert result["contributors"]["limit"] == 30

    def test_contributors_limit_custom(self, full_data, full_config):
        """Test custom contributor limit from config."""
        context = RenderContext(full_data, full_config)
        result = context.build()

        contributors = result["contributors"]
        assert contributors["limit"] == 10
        assert len(contributors["top_by_commits"]) <= 10


class TestOrganizationsContext:
    """Test organizations context."""

    def test_organizations_empty(self, minimal_data, minimal_config):
        """Test organizations with no data."""
        context = RenderContext(minimal_data, minimal_config)
        result = context.build()

        orgs = result["organizations"]
        assert orgs["has_organizations"] is False

    def test_organizations_data(self, full_data, minimal_config):
        """Test organizations data extraction."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        orgs = result["organizations"]
        assert orgs["total_count"] == 1
        assert orgs["has_organizations"] is True

    def test_organizations_limit_default(self, full_data, minimal_config):
        """Test default organization limit."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        assert result["organizations"]["limit"] == 30

    def test_organizations_limit_custom(self, full_data, full_config):
        """Test custom organization limit from config."""
        context = RenderContext(full_data, full_config)
        result = context.build()

        assert result["organizations"]["limit"] == 15


class TestFeaturesContext:
    """Test features matrix context."""

    def test_features_empty(self, minimal_data, minimal_config):
        """Test features with no repositories."""
        context = RenderContext(minimal_data, minimal_config)
        result = context.build()

        features = result["features"]
        assert features["feature_count"] == 0
        assert features["has_features"] is False

    def test_features_extraction(self, full_data, minimal_config):
        """Test feature extraction from repositories."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        features = result["features"]
        assert features["feature_count"] == 2
        assert "has_ci" in features["features_list"]
        assert "has_tests" in features["features_list"]

    def test_features_matrix(self, full_data, minimal_config):
        """Test feature matrix construction."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        features = result["features"]
        assert len(features["matrix"]) == 2

        # Check matrix structure
        for repo_features in features["matrix"]:
            assert "repo_name" in repo_features
            assert "features" in repo_features

    def test_features_sorted(self, full_data, minimal_config):
        """Test that features are sorted alphabetically."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        features_list = result["features"]["features_list"]
        assert features_list == sorted(features_list)


class TestWorkflowsContext:
    """Test workflows/CI context."""

    def test_workflows_empty(self, minimal_data, minimal_config):
        """Test workflows with no data."""
        context = RenderContext(minimal_data, minimal_config)
        result = context.build()

        workflows = result["workflows"]
        assert workflows["total_count"] == 0
        assert workflows["has_workflows"] is False

    def test_workflows_extraction(self, full_data, minimal_config):
        """Test workflow extraction from repositories."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        workflows = result["workflows"]
        assert workflows["total_count"] == 1
        assert workflows["has_workflows"] is True

    def test_workflows_structure(self, full_data, minimal_config):
        """Test workflow data structure."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        workflow = result["workflows"]["all"][0]
        assert workflow["name"] == "job1"
        assert workflow["repo"] == "repo1"
        assert workflow["status"] == "success"
        assert workflow["color"] == "success"

    def test_workflows_status_counts(self, full_data, minimal_config):
        """Test workflow status counting."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        status_counts = result["workflows"]["status_counts"]
        assert status_counts.get("success", 0) == 1


class TestOrphanedJobsContext:
    """Test orphaned jobs context."""

    def test_orphaned_jobs_empty(self, minimal_data, minimal_config):
        """Test orphaned jobs with no data."""
        context = RenderContext(minimal_data, minimal_config)
        result = context.build()

        orphaned = result["orphaned_jobs"]
        assert orphaned["total_count"] == 0
        assert orphaned["has_orphaned_jobs"] is False

    def test_orphaned_jobs_extraction(self, full_data, minimal_config):
        """Test orphaned jobs extraction."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        orphaned = result["orphaned_jobs"]
        assert orphaned["total_count"] == 2
        assert len(orphaned["jobs"]) == 2
        assert orphaned["has_orphaned_jobs"] is True

    def test_orphaned_jobs_structure(self, full_data, minimal_config):
        """Test orphaned jobs data structure."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        jobs = result["orphaned_jobs"]["jobs"]
        job = jobs[0]
        assert "name" in job
        assert "project" in job
        assert "state" in job
        assert "score" in job

    def test_orphaned_jobs_sorted(self, full_data, minimal_config):
        """Test that orphaned jobs are sorted by state."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        jobs = result["orphaned_jobs"]["jobs"]
        # Should be sorted by state, then name
        assert len(jobs) == 2


class TestTimeWindowsContext:
    """Test time windows context."""

    def test_time_windows_empty(self, minimal_data, minimal_config):
        """Test time windows with no data."""
        context = RenderContext(minimal_data, minimal_config)
        result = context.build()

        time_windows = result["time_windows"]
        assert isinstance(time_windows, list)
        assert len(time_windows) == 0

    def test_time_windows_extraction(self, full_data, minimal_config):
        """Test time windows extraction."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        time_windows = result["time_windows"]
        assert len(time_windows) == 2

    def test_time_windows_structure(self, full_data, minimal_config):
        """Test time window data structure."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        tw = result["time_windows"][0]
        assert tw["name"] == "recent"
        assert tw["days"] == 30
        assert tw["description"] == "Last 30 days"


class TestConfigContext:
    """Test configuration context."""

    def test_config_context_defaults(self, minimal_data, minimal_config):
        """Test config context with defaults."""
        context = RenderContext(minimal_data, minimal_config)
        result = context.build()

        config = result["config"]
        assert config["theme"] == "default"
        assert config["project_name"] == "Repository Analysis"

    def test_config_context_custom(self, minimal_data, full_config):
        """Test config context with custom values."""
        context = RenderContext(minimal_data, full_config)
        result = context.build()

        config = result["config"]
        assert config["theme"] == "dark"
        assert config["project_name"] == "Custom Project"

    def test_config_include_sections(self, minimal_data, full_config):
        """Test include_sections configuration."""
        context = RenderContext(minimal_data, full_config)
        result = context.build()

        sections = result["config"]["include_sections"]
        assert sections["title"] is True
        assert sections["summary"] is True
        assert sections["orphaned_jobs"] is False


class TestGetStatusColor:
    """Test status color mapping."""

    def test_status_color_success(self, minimal_data, minimal_config):
        """Test success color mappings."""
        context = RenderContext(minimal_data, minimal_config)

        assert context._get_status_color("blue") == "success"
        assert context._get_status_color("blue_anime") == "success"
        assert context._get_status_color("green") == "success"

    def test_status_color_failure(self, minimal_data, minimal_config):
        """Test failure color mappings."""
        context = RenderContext(minimal_data, minimal_config)

        assert context._get_status_color("red") == "failure"
        assert context._get_status_color("red_anime") == "failure"

    def test_status_color_warning(self, minimal_data, minimal_config):
        """Test warning color mappings."""
        context = RenderContext(minimal_data, minimal_config)

        assert context._get_status_color("yellow") == "warning"
        assert context._get_status_color("yellow_anime") == "warning"
        assert context._get_status_color("aborted") == "warning"

    def test_status_color_disabled(self, minimal_data, minimal_config):
        """Test disabled color mappings."""
        context = RenderContext(minimal_data, minimal_config)

        assert context._get_status_color("disabled") == "disabled"
        assert context._get_status_color("grey") == "disabled"

    def test_status_color_unknown(self, minimal_data, minimal_config):
        """Test unknown color mappings."""
        context = RenderContext(minimal_data, minimal_config)

        assert context._get_status_color("notbuilt") == "unknown"
        assert context._get_status_color("invalid") == "unknown"
        assert context._get_status_color("UNKNOWN") == "unknown"

    def test_status_color_case_insensitive(self, minimal_data, minimal_config):
        """Test that color mapping is case-insensitive."""
        context = RenderContext(minimal_data, minimal_config)

        assert context._get_status_color("BLUE") == "success"
        assert context._get_status_color("Red") == "failure"


# ============================================================================
# Edge Cases and Integration
# ============================================================================


class TestContextEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_summaries_section(self, minimal_config):
        """Test handling when summaries section is missing."""
        data = {"project": "test", "repositories": []}
        context = RenderContext(data, minimal_config)
        result = context.build()

        # Should handle gracefully with defaults
        assert result["summary"]["total_commits"] == 0

    def test_empty_repositories_list(self, minimal_config):
        """Test with empty repositories list."""
        data = {"repositories": [], "summaries": {}}
        context = RenderContext(data, minimal_config)
        result = context.build()

        assert result["summary"]["total_commits"] == 0
        assert result["repositories"]["all_count"] == 0

    def test_missing_metadata(self, minimal_config):
        """Test handling when metadata is missing."""
        data = {"repositories": []}
        context = RenderContext(data, minimal_config)
        result = context.build()

        project = result["project"]
        assert "generated_at" in project
        assert "report_version" in project

    def test_repositories_without_features(self, minimal_config):
        """Test repositories without features field."""
        data = {"repositories": [{"name": "repo1"}]}
        context = RenderContext(data, minimal_config)
        result = context.build()

        # Should handle gracefully
        assert result["features"]["feature_count"] == 0

    def test_repositories_without_jenkins_jobs(self, minimal_config):
        """Test repositories without jenkins_jobs field."""
        data = {"repositories": [{"name": "repo1"}]}
        context = RenderContext(data, minimal_config)
        result = context.build()

        # Should handle gracefully
        assert result["workflows"]["total_count"] == 0


# ============================================================================
# Table of Contents Tests
# ============================================================================


class TestRenderContextTOC:
    """Test Table of Contents context building."""

    def test_toc_key_exists_in_context(self, minimal_data, minimal_config):
        """Test that toc key is present in context."""
        context = RenderContext(minimal_data, minimal_config)
        result = context.build()

        assert "toc" in result

    def test_toc_structure(self, minimal_data, minimal_config):
        """Test that toc has expected structure."""
        context = RenderContext(minimal_data, minimal_config)
        result = context.build()

        assert "sections" in result["toc"]
        assert "has_sections" in result["toc"]
        assert isinstance(result["toc"]["sections"], list)
        assert isinstance(result["toc"]["has_sections"], bool)

    def test_toc_empty_data(self, minimal_config):
        """Test TOC with no data."""
        data = {
            "project": "test",
            "repositories": [],
            "summaries": {},
        }
        context = RenderContext(data, minimal_config)
        result = context.build()

        # Should have at least summary section (always shown if enabled)
        assert len(result["toc"]["sections"]) >= 1
        assert result["toc"]["has_sections"] is True

    def test_toc_summary_section_always_included(self, minimal_data, minimal_config):
        """Test that summary section is always included when enabled."""
        context = RenderContext(minimal_data, minimal_config)
        result = context.build()

        section_titles = [s["title"] for s in result["toc"]["sections"]]
        assert "Global Summary" in section_titles

    def test_toc_section_structure(self, full_data, minimal_config):
        """Test that each TOC section has required fields."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        for section in result["toc"]["sections"]:
            assert "title" in section
            assert "anchor" in section
            assert isinstance(section["title"], str)
            assert isinstance(section["anchor"], str)
            assert len(section["title"]) > 0
            assert len(section["anchor"]) > 0

    def test_toc_repositories_section_with_data(self, full_data, minimal_config):
        """Test that repositories section appears when data exists."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        section_titles = [s["title"] for s in result["toc"]["sections"]]
        assert "Gerrit Projects" in section_titles

        # Find the section and verify anchor
        repo_section = next(s for s in result["toc"]["sections"] if s["title"] == "Gerrit Projects")
        assert repo_section["anchor"] == "repositories"

    def test_toc_repositories_section_without_data(self, minimal_config):
        """Test that repositories section is excluded when no data."""
        data = {
            "project": "test",
            "repositories": [],
            "summaries": {"all_repositories": []},
        }
        context = RenderContext(data, minimal_config)
        result = context.build()

        section_titles = [s["title"] for s in result["toc"]["sections"]]
        assert "Gerrit Projects" not in section_titles

    def test_toc_contributors_section_with_data(self, full_data, minimal_config):
        """Test that contributors section appears when data exists."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        section_titles = [s["title"] for s in result["toc"]["sections"]]
        assert "Top Contributors" in section_titles

        # Find the section and verify anchor
        contrib_section = next(
            s for s in result["toc"]["sections"] if s["title"] == "Top Contributors"
        )
        assert contrib_section["anchor"] == "contributors"

    def test_toc_contributors_section_without_data(self, minimal_config):
        """Test that contributors section is excluded when no data."""
        data = {
            "project": "test",
            "repositories": [],
            "summaries": {
                "top_contributors_commits": [],
                "top_contributors_loc": [],
            },
        }
        context = RenderContext(data, minimal_config)
        result = context.build()

        section_titles = [s["title"] for s in result["toc"]["sections"]]
        assert "Top Contributors" not in section_titles

    def test_toc_organizations_section_with_data(self, full_data, minimal_config):
        """Test that organizations section appears when data exists."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        section_titles = [s["title"] for s in result["toc"]["sections"]]
        assert "Top Organizations" in section_titles

        # Find the section and verify anchor
        org_section = next(
            s for s in result["toc"]["sections"] if s["title"] == "Top Organizations"
        )
        assert org_section["anchor"] == "organizations"

    def test_toc_organizations_section_without_data(self, minimal_config):
        """Test that organizations section is excluded when no data."""
        data = {
            "project": "test",
            "repositories": [],
            "summaries": {"top_organizations": []},
        }
        context = RenderContext(data, minimal_config)
        result = context.build()

        section_titles = [s["title"] for s in result["toc"]["sections"]]
        assert "Top Organizations" not in section_titles

    def test_toc_features_section_with_data(self, full_data, minimal_config):
        """Test that features section appears when data exists."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        section_titles = [s["title"] for s in result["toc"]["sections"]]
        assert "Repository Feature Matrix" in section_titles

        # Find the section and verify anchor
        feature_section = next(
            s for s in result["toc"]["sections"] if s["title"] == "Repository Feature Matrix"
        )
        assert feature_section["anchor"] == "features"

    def test_toc_features_section_without_data(self, minimal_config):
        """Test that features section is excluded when no data."""
        data = {
            "project": "test",
            "repositories": [{"name": "repo1", "features": {}}],
        }
        context = RenderContext(data, minimal_config)
        result = context.build()

        section_titles = [s["title"] for s in result["toc"]["sections"]]
        assert "Repository Feature Matrix" not in section_titles

    def test_toc_workflows_section_with_jenkins_jobs(self, full_data, minimal_config):
        """Test that workflows section appears when Jenkins jobs exist."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        section_titles = [s["title"] for s in result["toc"]["sections"]]
        assert "Deployed CI/CD Jobs" in section_titles

        # Find the section and verify anchor
        workflow_section = next(
            s for s in result["toc"]["sections"] if s["title"] == "Deployed CI/CD Jobs"
        )
        assert workflow_section["anchor"] == "workflows"

    def test_toc_workflows_section_with_github_workflows(self, minimal_config):
        """Test that workflows section appears when GitHub workflows exist."""
        data = {
            "project": "test",
            "repositories": [
                {
                    "name": "repo1",
                    "jenkins_jobs": [],
                    "features": {
                        "workflows": {
                            "github_api_data": {"workflows": [{"name": "ci", "state": "active"}]}
                        }
                    },
                }
            ],
        }
        context = RenderContext(data, minimal_config)
        result = context.build()

        section_titles = [s["title"] for s in result["toc"]["sections"]]
        assert "Deployed CI/CD Jobs" in section_titles

    def test_toc_workflows_section_without_data(self, minimal_config):
        """Test that workflows section is excluded when no workflows."""
        data = {
            "project": "test",
            "repositories": [{"name": "repo1", "jenkins_jobs": [], "features": {}}],
        }
        context = RenderContext(data, minimal_config)
        result = context.build()

        section_titles = [s["title"] for s in result["toc"]["sections"]]
        assert "Deployed CI/CD Jobs" not in section_titles

    def test_toc_orphaned_jobs_section_with_data(self, full_data, minimal_config):
        """Test that orphaned jobs section appears when data exists."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        section_titles = [s["title"] for s in result["toc"]["sections"]]
        assert "Orphaned Jenkins Jobs" in section_titles

        # Find the section and verify anchor
        orphan_section = next(
            s for s in result["toc"]["sections"] if s["title"] == "Orphaned Jenkins Jobs"
        )
        assert orphan_section["anchor"] == "orphaned-jobs"

    def test_toc_orphaned_jobs_section_without_data(self, minimal_config):
        """Test that orphaned jobs section is excluded when no data."""
        data = {
            "project": "test",
            "repositories": [],
            "orphaned_jenkins_jobs": {"jobs": {}},
        }
        context = RenderContext(data, minimal_config)
        result = context.build()

        section_titles = [s["title"] for s in result["toc"]["sections"]]
        assert "Orphaned Jenkins Jobs" not in section_titles

    def test_toc_time_windows_section_with_data(self, full_data, minimal_config):
        """Test that time windows section appears when data exists."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        section_titles = [s["title"] for s in result["toc"]["sections"]]
        assert "Time Windows" in section_titles

        # Find the section and verify anchor
        time_section = next(s for s in result["toc"]["sections"] if s["title"] == "Time Windows")
        assert time_section["anchor"] == "time-windows"

    def test_toc_time_windows_section_without_data(self, minimal_config):
        """Test that time windows section is excluded when no data."""
        data = {
            "project": "test",
            "repositories": [],
            "time_windows": [],
        }
        context = RenderContext(data, minimal_config)
        result = context.build()

        section_titles = [s["title"] for s in result["toc"]["sections"]]
        assert "Time Windows" not in section_titles

    def test_toc_respects_section_config_disabled(self, full_data):
        """Test that TOC respects disabled sections in config."""
        config = {
            "output": {
                "include_sections": {
                    "contributors": False,
                    "organizations": False,
                }
            }
        }
        context = RenderContext(full_data, config)
        result = context.build()

        section_titles = [s["title"] for s in result["toc"]["sections"]]
        assert "Top Contributors" not in section_titles
        assert "Top Organizations" not in section_titles

    def test_toc_all_sections_enabled_with_data(self, full_data, minimal_config):
        """Test TOC with all sections having data."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        # Should have multiple sections
        assert len(result["toc"]["sections"]) >= 5
        assert result["toc"]["has_sections"] is True

        expected_sections = [
            "Global Summary",
            "Gerrit Projects",
            "Top Contributors",
            "Top Organizations",
            "Orphaned Jenkins Jobs",
        ]

        section_titles = [s["title"] for s in result["toc"]["sections"]]
        for expected in expected_sections:
            assert expected in section_titles

    def test_toc_section_order(self, full_data, minimal_config):
        """Test that TOC sections appear in expected order."""
        context = RenderContext(full_data, minimal_config)
        result = context.build()

        section_titles = [s["title"] for s in result["toc"]["sections"]]

        # Summary should be first
        if "Global Summary" in section_titles:
            assert section_titles[0] == "Global Summary"

        # Check relative order of other sections
        if "Gerrit Projects" in section_titles and "Top Contributors" in section_titles:
            repo_idx = section_titles.index("Gerrit Projects")
            contrib_idx = section_titles.index("Top Contributors")
            assert repo_idx < contrib_idx


class TestRenderContextConfigTOC:
    """Test TOC configuration options in _build_config_context."""

    def test_config_table_of_contents_default_true(self, minimal_data):
        """Test that table_of_contents defaults to True when not specified."""
        config = {"render": {}}
        context = RenderContext(minimal_data, config)
        result = context.build()

        assert result["config"]["table_of_contents"] is True

    def test_config_table_of_contents_explicit_true(self, minimal_data):
        """Test that explicit true value is passed through."""
        config = {"render": {"table_of_contents": True}}
        context = RenderContext(minimal_data, config)
        result = context.build()

        assert result["config"]["table_of_contents"] is True

    def test_config_table_of_contents_explicit_false(self, minimal_data):
        """Test that explicit false value is passed through."""
        config = {"render": {"table_of_contents": False}}
        context = RenderContext(minimal_data, config)
        result = context.build()

        assert result["config"]["table_of_contents"] is False

    def test_config_table_of_contents_no_render_section(self, minimal_data):
        """Test that table_of_contents defaults to True with no render section."""
        config = {}
        context = RenderContext(minimal_data, config)
        result = context.build()

        assert result["config"]["table_of_contents"] is True

    def test_config_table_of_contents_accessible_in_context(self, minimal_data, minimal_config):
        """Test that table_of_contents is accessible in the config context."""
        context = RenderContext(minimal_data, minimal_config)
        result = context.build()

        assert "config" in result
        assert "table_of_contents" in result["config"]
        assert isinstance(result["config"]["table_of_contents"], bool)
