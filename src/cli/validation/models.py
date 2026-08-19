# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Result object describing the outcome of a single validation check."""


class ValidationResult:
    """
    Result of a validation check.

    Attributes:
        passed: Whether the validation passed
        message: Description of the result
        suggestion: Optional suggestion for fixing failures
        severity: 'error', 'warning', or 'info'
    """

    def __init__(
        self, passed: bool, message: str, suggestion: str | None = None, severity: str = "error"
    ):
        """Initialize validation result."""
        self.passed = passed
        self.message = message
        self.suggestion = suggestion
        self.severity = severity

    def __repr__(self) -> str:
        """String representation."""
        status = "✓" if self.passed else "✗"
        return f"{status} {self.message}"
