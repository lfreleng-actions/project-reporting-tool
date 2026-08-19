# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Helpers that format validation errors and suggest common fixes."""

from typing import Any


def format_validation_errors(errors: list[dict[str, Any]]) -> str:
    """
    Format multiple validation errors into readable message.

    Args:
        errors: List of validation error dictionaries with 'path' and 'message'

    Returns:
        Formatted error message

    Example:
        >>> errors = [
        ...     {'path': 'project', 'message': 'Required field missing'},
        ...     {'path': 'api.github.token', 'message': 'Invalid token format'}
        ... ]
        >>> print(format_validation_errors(errors))
        Configuration validation failed with 2 error(s):
          - project: Required field missing
          - api.github.token: Invalid token format
    """
    if not errors:
        return "Validation passed"

    lines = [f"Configuration validation failed with {len(errors)} error(s):"]
    for error in errors:
        path = error.get("path", "unknown")
        message = error.get("message", "Unknown error")
        lines.append(f"  - {path}: {message}")

    return "\n".join(lines)


def suggest_common_fixes(error: Exception) -> str | None:
    """
    Suggest common fixes based on error type and message.

    Args:
        error: The exception that was raised

    Returns:
        Suggestion string or None if no common fix available

    Example:
        >>> error = FileNotFoundError("config.yaml")
        >>> print(suggest_common_fixes(error))
        Create a config.yaml file using config.example.yaml as template
    """
    error_str = str(error).lower()

    # Check error type first
    if isinstance(error, FileNotFoundError):
        if "config" in error_str:
            return "Create a config.yaml file using config.example.yaml as template"
        return "Verify the file path exists and is accessible"

    # Common error patterns and suggestions
    if "config.yaml" in error_str and "not found" in error_str:
        return "Create a config.yaml file using config.example.yaml as template"

    if "permission denied" in error_str:
        return "Check file permissions or run with appropriate privileges"

    if "connection" in error_str or "network" in error_str:
        return "Check network connectivity and firewall settings"

    if "authentication" in error_str or "401" in error_str:
        return "Verify API credentials and tokens are correct"

    if "not found" in error_str and "repository" in error_str:
        return "Verify repository path exists and is accessible"

    if "disk" in error_str or "space" in error_str:
        return "Free up disk space or use --no-cache flag"

    if "yaml" in error_str and ("invalid" in error_str or "parse" in error_str):
        return "Check YAML syntax - ensure proper indentation and no tabs"

    return None
