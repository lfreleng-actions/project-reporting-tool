# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
GitHub API Client

Client for interacting with GitHub API to fetch workflow run status,
repository information, and other GitHub-related data.

Extracted from generate_reports.py as part of Phase 2 refactoring.
Enhanced with standardized error handling and response envelopes.
"""

from .client import GitHubAPIClient
from .status import GitHubStatusMixin
from .workflows import GitHubWorkflowsMixin


__all__ = [
    "GitHubAPIClient",
    "GitHubStatusMixin",
    "GitHubWorkflowsMixin",
]
