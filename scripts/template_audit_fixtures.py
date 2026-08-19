# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Synthetic test data for the template field audit.

Provides the fallback data structure used by ``scripts/audit_templates.py``
when the minimal production data fixture is not available.
"""

from typing import Any


def _synthetic_test_data() -> dict[str, Any]:
    """Return a realistic synthetic data structure for template auditing.

    Used as a fallback when the minimal production data fixture is absent.
    """
    return {
        "summaries": _synthetic_summaries(),
        "repositories": _synthetic_repositories(),
    }


def _synthetic_summaries() -> dict[str, Any]:
    """Return the synthetic ``summaries`` section for template auditing."""
    return {
        "all_repositories": [
            {
                "gerrit_project": "test/repo1",
                "unique_contributors": {"last_3_years": 10, "last_365": 8, "last_90": 5},
                "loc_stats": {"last_3_years": {"added": 5000, "removed": 2000, "net": 3000}},
                "last_commit_timestamp": "2026-01-10T12:00:00Z",
                "total_commits_ever": 100,
                "days_since_last_commit": 2,
                "activity_status": "current",
                "state": "ACTIVE",
            },
            {
                "gerrit_project": "test/repo2",
                "unique_contributors": {"last_3_years": 5},
                "loc_stats": {"last_3_years": {"added": 2000, "removed": 500, "net": 1500}},
                "last_commit_timestamp": "2025-12-01T12:00:00Z",
                "total_commits_ever": 50,
                "days_since_last_commit": 42,
                "activity_status": "active",
                "state": "ACTIVE",
            },
        ],
        "top_organizations": [
            {
                "domain": "example.com",
                "contributor_count": 10,
                "commits": {"last_3_years": 100, "last_365": 80},
                "lines_added": {"last_3_years": 5000, "last_365": 4000},
                "lines_removed": {"last_3_years": 2000, "last_365": 1500},
                "lines_net": {"last_3_years": 3000, "last_365": 2500},
                "repositories_count": {"last_3_years": 5, "last_365": 4},
            },
            {
                "domain": "test.org",
                "contributor_count": 8,
                "commits": {"last_3_years": 75},
                "lines_added": {"last_3_years": 3000},
                "lines_removed": {"last_3_years": 1000},
                "lines_net": {"last_3_years": 2000},
                "repositories_count": {"last_3_years": 3},
            },
        ],
        "top_contributors_commits": [
            {
                "name": "Test User",
                "email": "test@example.com",
                "domain": "example.com",
                "commits": {"last_3_years": 100, "last_365": 80},
                "lines_added": {"last_3_years": 5000, "last_365": 4000},
                "lines_removed": {"last_3_years": 2000, "last_365": 1500},
                "lines_net": {"last_3_years": 3000, "last_365": 2500},
                "repositories_touched": {"last_3_years": {"repo1", "repo2", "repo3"}},
            },
            {
                "name": "Another User",
                "email": "another@test.org",
                "domain": "test.org",
                "commits": {"last_3_years": 75},
                "lines_added": {"last_3_years": 3000},
                "lines_removed": {"last_3_years": 1000},
                "lines_net": {"last_3_years": 2000},
                "repositories_touched": {"last_3_years": {"repo1", "repo4"}},
            },
        ],
        "top_contributors_loc": [],
    }


def _synthetic_repositories() -> list[dict[str, Any]]:
    """Return the synthetic ``repositories`` section for template auditing."""
    return [
        {
            "gerrit_project": "test/repo1",
            "activity_status": "current",
            "days_since_last_commit": 2,
            "features": {
                "project_types": {"types": ["Java/Maven"]},
                "dependabot": {"present": True},
                "pre_commit": {"present": False},
                "readthedocs": {"present": True},
                "gitreview": {"present": True},
                "g2g": {"present": True},
            },
            "jenkins": {
                "jobs": [
                    {
                        "name": "test-job-1",
                        "status": "success",
                        "color": "blue",
                        "url": "https://jenkins.example.org/job/test-job-1/",
                    },
                    {
                        "name": "test-job-2",
                        "status": "failure",
                        "color": "red",
                        "url": "https://jenkins.example.org/job/test-job-2/",
                    },
                ]
            },
            "github_workflows": [
                {
                    "name": "ci.yaml",
                    "path": ".github/workflows/ci.yaml",
                    "state": "active",
                    "status": "success",
                }
            ],
        },
        {
            "gerrit_project": "test/repo2",
            "activity_status": "active",
            "days_since_last_commit": 42,
            "features": {
                "project_types": {"types": ["Go"]},
                "dependabot": {"present": False},
                "pre_commit": {"present": True},
                "readthedocs": {"present": False},
                "gitreview": {"present": True},
                "g2g": {"present": False},
            },
            "jenkins": {
                "jobs": [
                    {
                        "name": "test-job-3",
                        "status": "success",
                        "color": "blue",
                        "url": "https://jenkins.example.org/job/test-job-3/",
                    }
                ]
            },
            "github_workflows": [],
        },
    ]
