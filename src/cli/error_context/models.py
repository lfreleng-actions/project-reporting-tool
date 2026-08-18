# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Rich error context value object with recovery information."""

from typing import Any


class ErrorContext:
    """
    Rich error context with recovery information.

    Attributes:
        error_type: Type of error that occurred
        message: Error message
        context: Additional context information
        recovery_hints: Step-by-step recovery instructions
        examples: Code examples for fixing the issue
        related_errors: Related common errors
        doc_links: Relevant documentation links
    """

    def __init__(
        self,
        error_type: str,
        message: str,
        context: dict[str, Any] | None = None,
        recovery_hints: list[str] | None = None,
        examples: list[str] | None = None,
        related_errors: list[str] | None = None,
        doc_links: list[str] | None = None,
    ):
        """Initialize error context."""
        self.error_type = error_type
        self.message = message
        self.context = context or {}
        self.recovery_hints = recovery_hints or []
        self.examples = examples or []
        self.related_errors = related_errors or []
        self.doc_links = doc_links or []

    def format(self, verbose: bool = False) -> str:
        """
        Format error context for display.

        Args:
            verbose: Include all details

        Returns:
            Formatted error message
        """
        lines = []

        # Error header
        lines.append(f"❌ {self.error_type}: {self.message}")
        lines.append("")

        # Context information
        if self.context:
            lines.append("📋 Context:")
            for key, value in self.context.items():
                lines.append(f"  • {key}: {value}")
            lines.append("")

        # Recovery hints
        if self.recovery_hints:
            lines.append("🔧 How to fix:")
            for i, hint in enumerate(self.recovery_hints, 1):
                lines.append(f"  {i}. {hint}")
            lines.append("")

        # Examples
        if self.examples and verbose:
            lines.append("💡 Examples:")
            for example in self.examples:
                lines.append(f"  {example}")
            lines.append("")

        # Related errors
        if self.related_errors and verbose:
            lines.append("🔗 Related issues:")
            for error in self.related_errors:
                lines.append(f"  • {error}")
            lines.append("")

        # Documentation links
        if self.doc_links:
            lines.append("📖 Documentation:")
            for link in self.doc_links:
                lines.append(f"  • {link}")
            lines.append("")

        return "\n".join(lines)
