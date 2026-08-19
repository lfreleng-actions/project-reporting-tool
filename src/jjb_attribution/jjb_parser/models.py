# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Data models for JJB attribution.

Dataclasses describing the job definitions and project blocks extracted from
Jenkins Job Builder YAML files.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class JJBJobDefinition:
    """Represents a Jenkins job definition from JJB."""

    template_name: str
    project_name: str
    parameters: dict[str, Any] = field(default_factory=dict)
    expanded_names: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"JJBJobDefinition(template={self.template_name}, project={self.project_name})"


@dataclass
class JJBProject:
    """Represents a project block from a JJB YAML file."""

    name: str
    gerrit_project: str | None
    jobs: list[JJBJobDefinition] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"JJBProject(name={self.name}, gerrit={self.gerrit_project}, jobs={len(self.jobs)})"
