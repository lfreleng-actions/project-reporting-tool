# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Validation result model for configuration validation.

Holds the severity and category enumerations, the individual issue record,
and the aggregate result object that collects errors, warnings and infos.
"""

from dataclasses import dataclass, field
from enum import Enum


class ValidationLevel(Enum):
    """Severity level for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationCategory(Enum):
    """Category of validation issue."""

    SCHEMA = "schema"  # JSON schema violation
    SEMANTIC = "semantic"  # Logical inconsistency
    COMPATIBILITY = "compatibility"  # Version/compatibility issue
    SECURITY = "security"  # Security concern
    PERFORMANCE = "performance"  # Performance impact
    DEPRECATED = "deprecated"  # Deprecated setting


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""

    level: ValidationLevel
    category: ValidationCategory
    message: str
    path: str = ""
    suggestion: str | None = None

    def __str__(self) -> str:
        """Format issue for display."""
        parts = [f"[{self.level.value.upper()}]"]
        if self.path:
            parts.append(f"at '{self.path}':")
        parts.append(self.message)
        if self.suggestion:
            parts.append(f"\n  Suggestion: {self.suggestion}")
        return " ".join(parts)


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    is_valid: bool
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    infos: list[ValidationIssue] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    def add_error(
        self,
        message: str,
        category: ValidationCategory = ValidationCategory.SCHEMA,
        path: str = "",
        suggestion: str | None = None,
    ) -> None:
        """Add an error to the result."""
        self.errors.append(
            ValidationIssue(
                level=ValidationLevel.ERROR,
                category=category,
                message=message,
                path=path,
                suggestion=suggestion,
            )
        )
        self.is_valid = False

    def add_warning(
        self,
        message: str,
        category: ValidationCategory = ValidationCategory.SEMANTIC,
        path: str = "",
        suggestion: str | None = None,
    ) -> None:
        """Add a warning to the result."""
        self.warnings.append(
            ValidationIssue(
                level=ValidationLevel.WARNING,
                category=category,
                message=message,
                path=path,
                suggestion=suggestion,
            )
        )

    def add_info(
        self,
        message: str,
        category: ValidationCategory = ValidationCategory.COMPATIBILITY,
        path: str = "",
        suggestion: str | None = None,
    ) -> None:
        """Add an info message to the result."""
        self.infos.append(
            ValidationIssue(
                level=ValidationLevel.INFO,
                category=category,
                message=message,
                path=path,
                suggestion=suggestion,
            )
        )
