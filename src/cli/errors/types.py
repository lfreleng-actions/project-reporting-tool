# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Concrete CLI error classes for configuration, arguments, API and I/O."""

from typing import Any

from .base import CLIError


class ConfigurationError(CLIError):
    """
    Configuration-related error.

    Raised when configuration file is missing, invalid, or contains errors.
    """

    def __init__(
        self,
        message: str,
        suggestion: str | None = None,
        context: dict[str, Any] | None = None,
        recovery_hints: list[str] | None = None,
    ):
        """Initialize configuration error."""
        default_suggestion = (
            "Check your configuration file syntax and required fields. "
            "See config.example.yaml for a template."
        )
        default_hints = [
            "Verify YAML syntax is correct (no tabs, proper indentation)",
            "Check for required fields in configuration",
            "Compare with config.example.yaml template",
            "Validate with: python generate_reports.py --dry-run",
        ]
        super().__init__(
            message,
            suggestion=suggestion or default_suggestion,
            doc_link="docs/configuration.md",
            context=context,
            recovery_hints=recovery_hints or default_hints,
        )


class InvalidArgumentError(CLIError):
    """
    Invalid command-line argument error.

    Raised when user provides invalid or conflicting arguments.
    """

    def __init__(
        self,
        message: str,
        suggestion: str | None = None,
        context: dict[str, Any] | None = None,
        recovery_hints: list[str] | None = None,
    ):
        """Initialize invalid argument error."""
        default_suggestion = "Run with --help to see valid arguments and usage examples."
        default_hints = [
            "Check the command-line arguments for typos",
            "Run with --help to see all available options",
            "See docs/CLI_REFERENCE.md for detailed usage",
            "Use --list-features to see available features",
        ]
        super().__init__(
            message,
            suggestion=suggestion or default_suggestion,
            doc_link="docs/CLI_REFERENCE.md",
            context=context,
            recovery_hints=recovery_hints or default_hints,
        )


class APIError(CLIError):
    """
    API-related error.

    Raised when external API calls fail (GitHub, Gerrit, Jenkins).
    """

    def __init__(
        self,
        message: str,
        api_name: str | None = None,
        suggestion: str | None = None,
        context: dict[str, Any] | None = None,
        recovery_hints: list[str] | None = None,
        status_code: int | None = None,
    ):
        """Initialize API error."""
        ctx = context or {}
        if api_name:
            message = f"{api_name} API error: {message}"
            ctx["api"] = api_name
        if status_code:
            ctx["status_code"] = status_code

        default_suggestion = (
            "Check network connectivity and API credentials. "
            "Verify that API endpoints are accessible."
        )

        # Specific hints based on status code (only used if no custom hints/suggestion provided)
        default_hints = []
        if not suggestion and not recovery_hints:
            if status_code == 401:
                default_hints = [
                    "Verify API token is set in environment or config",
                    "Check that the token hasn't expired",
                    "Regenerate token if needed",
                    "Ensure token has required permissions",
                ]
            elif status_code == 403:
                default_hints = [
                    "Check API token permissions/scopes",
                    "Verify access to the resource",
                    "Check for rate limiting",
                    "Ensure organization membership if applicable",
                ]
            elif status_code == 404:
                default_hints = [
                    "Verify the resource exists",
                    "Check the resource URL/path",
                    "Ensure you have access to the resource",
                    "Verify repository/organization name spelling",
                ]
            else:
                default_hints = [
                    "Check network connectivity",
                    "Verify API credentials are correct",
                    "Check API endpoint is accessible",
                    "Review API documentation for requirements",
                ]

        super().__init__(
            message,
            suggestion=suggestion or default_suggestion,
            doc_link="docs/troubleshooting.md#api-errors",
            context=ctx,
            recovery_hints=recovery_hints or (default_hints if default_hints else None),
        )


class PermissionError(CLIError):
    """
    Permission-related error.

    Raised when operations fail due to insufficient permissions.
    """

    def __init__(
        self, message: str, path: str | None = None, context: dict[str, Any] | None = None
    ):
        """Initialize permission error."""
        ctx = context or {}
        if path:
            message = f"Permission denied: {path}"
            ctx["path"] = path

        suggestion = (
            "Check file/directory permissions. "
            "You may need to run with appropriate privileges or "
            "choose a different output directory."
        )

        recovery_hints = [
            "Check file/directory permissions with: ls -la",
            "Ensure your user has necessary access rights",
            "Try using a different output directory",
            "Fix permissions with: chmod u+rw <path> (if you own it)",
        ]

        super().__init__(message, suggestion=suggestion, context=ctx, recovery_hints=recovery_hints)


class DiskSpaceError(CLIError):
    """
    Disk space error.

    Raised when operations fail due to insufficient disk space.
    """

    def __init__(
        self, message: str, path: str | None = None, context: dict[str, Any] | None = None
    ):
        """Initialize disk space error."""
        ctx = context or {}
        if path:
            ctx["path"] = path

        suggestion = (
            "Free up disk space or choose a different output directory. "
            "Consider using --no-cache to reduce disk usage."
        )

        recovery_hints = [
            "Check available disk space with: df -h",
            "Free up space by removing unnecessary files",
            "Use a different output directory with more space",
            "Use --no-cache to reduce disk usage",
            "Use --output-format json to skip HTML generation",
        ]

        super().__init__(message, suggestion=suggestion, context=ctx, recovery_hints=recovery_hints)


class ValidationError(CLIError):
    """
    Validation error.

    Raised when data validation fails.
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        context: dict[str, Any] | None = None,
        recovery_hints: list[str] | None = None,
    ):
        """Initialize validation error."""
        ctx = context or {}
        if field:
            message = f"Validation failed for '{field}': {message}"
            ctx["field"] = field

        default_hints = [
            "Check the value format and type",
            "Compare with config.example.yaml for valid examples",
            "Validate configuration with: --dry-run",
            "See docs/configuration.md for field requirements",
        ]

        super().__init__(message, context=ctx, recovery_hints=recovery_hints or default_hints)


class NetworkError(CLIError):
    """
    Network connectivity error.

    Raised when network operations fail.
    """

    def __init__(
        self,
        message: str,
        suggestion: str | None = None,
        context: dict[str, Any] | None = None,
        recovery_hints: list[str] | None = None,
    ):
        """Initialize network error."""
        default_suggestion = (
            "Check your network connection. "
            "Verify that you can reach the required endpoints. "
            "You may need to configure proxy settings."
        )

        default_hints = [
            "Check internet connectivity",
            "Test endpoint reachability (e.g., ping api.github.com)",
            "Verify firewall/proxy settings",
            "Check for DNS resolution issues",
            "Try again after a few moments",
        ]

        super().__init__(
            message,
            suggestion=suggestion or default_suggestion,
            doc_link="docs/troubleshooting.md#network-issues",
            context=context,
            recovery_hints=recovery_hints or default_hints,
        )
