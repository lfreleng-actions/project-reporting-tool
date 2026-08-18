# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Base CLI error class carrying suggestions, context and recovery hints."""

from typing import Any


class CLIError(Exception):
    """
    Base CLI error with helpful context.

    This error class provides structured error information including:
    - Clear error message
    - Actionable suggestions for resolution
    - Links to relevant documentation

    Example:
        >>> raise CLIError(
        ...     "Configuration file not found: config.yaml",
        ...     suggestion="Create a config.yaml file or specify path with --config",
        ...     doc_link="https://docs.example.com/configuration"
        ... )
    """

    def __init__(
        self,
        message: str,
        suggestion: str | None = None,
        doc_link: str | None = None,
        context: dict[str, Any] | None = None,
        recovery_hints: list[str] | None = None,
    ):
        """
        Initialize CLI error.

        Args:
            message: Error message describing what went wrong
            suggestion: Optional suggestion for how to fix the error
            doc_link: Optional link to relevant documentation
            context: Optional context information dictionary
            recovery_hints: Optional list of step-by-step recovery instructions
        """
        self.message = message
        self.suggestion = suggestion
        self.doc_link = doc_link
        self.context = context or {}
        self.recovery_hints = recovery_hints or []
        super().__init__(message)

    def __str__(self) -> str:
        """Format error with suggestions and documentation."""
        parts = [f"❌ Error: {self.message}"]

        # Context information
        if self.context:
            parts.append("\n📋 Context:")
            for key, value in self.context.items():
                parts.append(f"  • {key}: {value}")

        # Recovery hints (step-by-step)
        if self.recovery_hints:
            parts.append("\n🔧 How to fix:")
            for i, hint in enumerate(self.recovery_hints, 1):
                parts.append(f"  {i}. {hint}")

        # Simple suggestion (backward compatible)
        elif self.suggestion:
            parts.append(f"\n💡 Suggestion: {self.suggestion}")

        # Documentation link
        if self.doc_link:
            parts.append(f"\n📖 Documentation: {self.doc_link}")

        return "\n".join(parts)

    def add_context(self, key: str, value: Any) -> "CLIError":
        """
        Add context information to error.

        Args:
            key: Context key
            value: Context value

        Returns:
            Self for chaining
        """
        self.context[key] = value
        return self

    def add_recovery_hint(self, hint: str) -> "CLIError":
        """
        Add a recovery hint.

        Args:
            hint: Recovery instruction

        Returns:
            Self for chaining
        """
        self.recovery_hints.append(hint)
        return self
