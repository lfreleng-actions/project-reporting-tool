# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Jenkins Job Builder (JJB) Attribution Parser.

This module parses JJB YAML files from ci-management repositories to extract
job definitions and map them to Gerrit projects. It provides accurate Jenkins
job attribution based on authoritative JJB configuration files.
"""

from .models import JJBJobDefinition, JJBProject
from .parser import JJBAttribution


__all__ = [
    "JJBAttribution",
    "JJBJobDefinition",
    "JJBProject",
]
