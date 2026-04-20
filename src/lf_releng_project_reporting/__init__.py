# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Reporting Tool - Comprehensive Multi-Repository Analysis Tool

A modern Python package for analyzing Git repositories and generating
comprehensive reports with metrics, feature detection, and contributor analysis.

Key Features:
- Git activity metrics across configurable time windows
- Automatic CI/CD workflow detection (Jenkins, GitHub Actions)
- Contributor and organization analysis
- Multi-format output (JSON, Markdown, HTML, ZIP)
- Gerrit API integration
- Performance-optimized with concurrent processing

Usage:
    From command line:
        $ lf-releng-project-reporting generate --project my-project --repos-path ./repos

    With configuration:
        $ lf-releng-project-reporting generate --project my-project --config-dir ./config

For more information:
    - GitHub: https://github.com/lfreleng-actions/lf-releng-project-reporting
    - License: Apache-2.0
"""

# Resolve __version__ without depending on the hatch-vcs-generated
# _version.py being present. In installed environments
# importlib.metadata.version() returns the wheel's version. In source
# checkouts where the package has not been installed (e.g. the
# isolated pre-commit.ci basedpyright environment), fall back to
# "0.0.0" so static analysers can always see a str-typed attribute.
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version


try:
    __version__: str = _pkg_version("lf-releng-project-reporting")
except PackageNotFoundError:
    __version__ = "0.0.0"


__author__ = "The Linux Foundation"
__license__ = "Apache-2.0"

# Public API (to be implemented)
__all__ = [
    "__version__",
    "__author__",
    "__license__",
]
