# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Jenkins API Client

Client for interacting with Jenkins API to fetch job information
and build status.

Extracted from generate_reports.py as part of Phase 2 refactoring.
"""

from .builds import JenkinsBuildsMixin
from .catalog import JenkinsCatalogMixin
from .client import JenkinsAPIClient
from .discovery import JenkinsDiscoveryMixin
from .jjb import (
    JJB_ATTRIBUTION_AVAILABLE,
    JenkinsJJBMixin,
    JJBAttribution,
    JJBRepoManager,
)
from .jobs import JenkinsJobsMixin
from .matching import JenkinsMatchingMixin


__all__ = [
    "JJB_ATTRIBUTION_AVAILABLE",
    "JJBAttribution",
    "JJBRepoManager",
    "JenkinsAPIClient",
    "JenkinsBuildsMixin",
    "JenkinsCatalogMixin",
    "JenkinsDiscoveryMixin",
    "JenkinsJJBMixin",
    "JenkinsJobsMixin",
    "JenkinsMatchingMixin",
]
