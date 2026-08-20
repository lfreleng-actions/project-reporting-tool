# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
INFO.yaml enricher module.

Enriches INFO.yaml project data with Git repository information,
calculating committer activity status and coloring based on recent commits.

Supports both synchronous and asynchronous URL validation for optimal performance.
"""

import asyncio
import logging
from typing import Any

from domain.info_yaml import CommitterInfo, ProjectInfo

from ..matcher import CommitterMatcher
from ..validator import URLValidator
from .enricher import (
    InfoYamlEnricher,
    enrich_project_with_git_data,
    enrich_projects_with_git_data,
)


logger = logging.getLogger(__name__)

# Keep introspection and serialized references on the historical public path.
InfoYamlEnricher.__module__ = __name__

__all__ = [
    "Any",
    "CommitterInfo",
    "CommitterMatcher",
    "InfoYamlEnricher",
    "ProjectInfo",
    "URLValidator",
    "asyncio",
    "enrich_project_with_git_data",
    "enrich_projects_with_git_data",
    "logger",
    "logging",
]
