# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Built-in configuration templates offered by the wizard."""

# =============================================================================
# CONFIGURATION TEMPLATES
# =============================================================================

MINIMAL_TEMPLATE = {
    "project": "",
    "time_windows": {
        "reporting_window_days": 365,
        "recent_activity_days": 90,
        "active_contributor_days": 90,
    },
    "output": {
        "directory": "output",
        "formats": ["json", "md", "html"],
    },
}

STANDARD_TEMPLATE = {
    "project": "",
    "time_windows": {
        "reporting_window_days": 365,
        "recent_activity_days": 90,
        "active_contributor_days": 90,
        "abandoned_days": 180,
    },
    "output": {
        "directory": "output",
        "formats": ["json", "md", "html"],
        "create_bundle": True,
    },
    "api": {
        "github": {
            "enabled": True,
            "timeout": 30,
            "max_retries": 3,
        }
    },
    "features": {
        "ci_cd": {
            "github_actions": {"enabled": True},
            "jenkins": {"enabled": True},
        },
        "security": {
            "dependabot": {"enabled": True},
        },
        "documentation": {
            "readthedocs": {"enabled": True},
        },
    },
}

FULL_TEMPLATE = {
    "project": "",
    "time_windows": {
        "reporting_window_days": 365,
        "recent_activity_days": 90,
        "active_contributor_days": 90,
        "abandoned_days": 180,
        "new_contributor_days": 90,
    },
    "output": {
        "directory": "output",
        "formats": ["json", "md", "html"],
        "create_bundle": True,
        "bundle_name": "{project}-{date}",
    },
    "api": {
        "github": {
            "enabled": True,
            "token_env": "GITHUB_TOKEN",
            "timeout": 30,
            "max_retries": 3,
            "rate_limit_wait": True,
        },
        "gerrit": {
            "enabled": False,
            "base_url": "",
            "timeout": 30,
        },
        "jenkins": {
            "enabled": False,
            "base_url": "",
            "timeout": 30,
        },
    },
    "features": {
        "ci_cd": {
            "github_actions": {"enabled": True},
            "jenkins": {"enabled": True},
            "travis": {"enabled": True},
        },
        "build_package": {
            "maven": {"enabled": True},
            "npm": {"enabled": True},
            "pip": {"enabled": True},
        },
        "code_quality": {
            "sonarqube": {"enabled": True},
            "codecov": {"enabled": True},
        },
        "security": {
            "dependabot": {"enabled": True},
            "snyk": {"enabled": True},
        },
        "documentation": {
            "readthedocs": {"enabled": True},
            "github_pages": {"enabled": True},
        },
    },
    "performance": {
        "concurrency": {
            "enabled": True,
            "max_workers": 4,
        },
        "cache": {
            "enabled": True,
            "directory": ".cache",
            "ttl_hours": 24,
        },
    },
}
