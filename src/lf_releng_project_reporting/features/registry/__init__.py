# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Feature Registry Module

This module contains the FeatureRegistry class for detecting features in repositories.
Extracted from generate_reports.py as part of Phase 3 refactoring.

The FeatureRegistry provides a plugin-style architecture for feature detection:
- Dependabot configuration
- GitHub workflows and GitHub Actions
- Pre-commit hooks
- Documentation systems (ReadTheDocs, Sphinx, MkDocs)
- Project types (Maven, Gradle, Python, Node, etc.)
- CI/CD integrations (Jenkins, GitHub Actions)
- Code quality tools
"""

from api.github_client import GitHubAPIClient

from .registry import FeatureRegistry


# Preserve the class's historical import and pickle path after moving its
# implementation into the package's private ``registry`` module.
FeatureRegistry.__module__ = __name__

__all__ = ["FeatureRegistry", "GitHubAPIClient"]
