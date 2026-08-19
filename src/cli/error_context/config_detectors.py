# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Error context detectors for configuration and filesystem problems."""

import contextlib
import os
from pathlib import Path
from typing import Any

from .models import ErrorContext


def detect_missing_config() -> ErrorContext:
    """Create context for missing configuration file."""
    return ErrorContext(
        error_type="Configuration Error",
        message="Configuration file not found",
        context={"expected_location": "config/template.yaml", "current_directory": os.getcwd()},
        recovery_hints=[
            "Copy config.example.yaml to config.yaml",
            "Edit config.yaml with your project settings",
            "Or specify a custom config with --config-dir /path/to/config",
        ],
        examples=[
            "cp config.example.yaml config.yaml",
            "python generate_reports.py --config-dir /custom/path",
        ],
        doc_links=["docs/configuration.md", "docs/quick-start.md#configuration"],
    )


def detect_invalid_yaml(file_path: Path, line: int | None = None) -> ErrorContext:
    """
    Create context for invalid YAML syntax.

    Args:
        file_path: Path to YAML file
        line: Line number with error (if available)
    """
    context: dict[str, Any] = {
        "file": str(file_path),
        "common_causes": "indentation, tabs, special characters",
    }

    if line:
        context["line"] = line

    return ErrorContext(
        error_type="YAML Syntax Error",
        message=f"Invalid YAML syntax in {file_path}",
        context=context,
        recovery_hints=[
            "Check indentation - use spaces, not tabs",
            "Ensure colons have spaces after them (key: value)",
            "Quote strings with special characters",
            "Validate YAML online at yamllint.com",
        ],
        examples=[
            "✓ Correct:   project: my-project",
            "✗ Wrong:     project:my-project (missing space)",
            "✓ Correct:   name: 'project: name'",
            "✗ Wrong:     name: project: name (unquoted colon)",
        ],
        related_errors=[
            "ConfigurationError: missing required field",
            "ParserError: invalid character",
        ],
        doc_links=["docs/configuration.md#yaml-syntax", "https://yaml.org/spec/1.2/spec.html"],
    )


def detect_missing_repos_path(path: Path) -> ErrorContext:
    """Create context for missing repositories directory."""
    return ErrorContext(
        error_type="Invalid Argument",
        message=f"Repositories path does not exist: {path}",
        context={
            "provided_path": str(path),
            "absolute_path": str(path.absolute()),
            "current_directory": os.getcwd(),
        },
        recovery_hints=[
            "Verify the path is correct",
            "Clone repositories to the specified location",
            "Or provide the correct path with --repos-path",
            "Check for typos in the path",
        ],
        examples=[
            "# Clone repositories first:",
            "mkdir -p ~/repos",
            "cd ~/repos && git clone https://github.com/org/repo.git",
            "",
            "# Then run with correct path:",
            "python generate_reports.py --project myproject --repos-path ~/repos",
        ],
        doc_links=["docs/quick-start.md#cloning-repositories"],
    )


def detect_permission_error(path: Path, operation: str = "access") -> ErrorContext:
    """
    Create context for file permission errors.

    Args:
        path: Path that couldn't be accessed
        operation: Operation that failed (read, write, execute)
    """
    stat_info = None
    with contextlib.suppress(Exception):
        stat_info = path.stat()

    context = {
        "path": str(path),
        "operation": operation,
        "current_user": os.getenv("USER", "unknown"),
    }

    if stat_info:
        import stat as stat_module

        mode = stat_module.filemode(stat_info.st_mode)
        context["permissions"] = mode

    return ErrorContext(
        error_type="Permission Error",
        message=f"Permission denied: cannot {operation} {path}",
        context=context,
        recovery_hints=[
            f"Check file permissions for {path}",
            "Ensure your user has the necessary permissions",
            "Try running with appropriate privileges if needed",
            "Or choose a different output directory you can write to",
        ],
        examples=[
            "# Check permissions:",
            f"ls -la {path}",
            "",
            "# Fix permissions (if you own the file):",
            f"chmod u+rw {path}",
            "",
            "# Or use a different output directory:",
            "python generate_reports.py --output-dir ~/my-reports ...",
        ],
        doc_links=["docs/troubleshooting.md#permission-errors"],
    )


def detect_disk_space_error(path: Path) -> ErrorContext:
    """Create context for disk space errors."""
    try:
        import shutil

        total, used, free = shutil.disk_usage(path)
        free_gb = free / (1024**3)
        context = {"path": str(path), "free_space": f"{free_gb:.2f} GB"}
    except Exception:
        context = {"path": str(path)}

    return ErrorContext(
        error_type="Disk Space Error",
        message=f"Insufficient disk space at {path}",
        context=context,
        recovery_hints=[
            "Free up disk space",
            "Use a different output directory with more space",
            "Use --no-cache to reduce disk usage",
            "Use --output-format json to skip HTML generation",
        ],
        examples=[
            "# Check disk space:",
            "df -h",
            "",
            "# Use different output directory:",
            "python generate_reports.py --output-dir /mnt/data/reports ...",
            "",
            "# Reduce disk usage:",
            "python generate_reports.py --no-cache --output-format json ...",
        ],
        doc_links=["docs/troubleshooting.md#disk-space"],
    )


def detect_validation_error(
    field: str, value: Any, expected: str, config_path: Path | None = None
) -> ErrorContext:
    """
    Create context for validation errors.

    Args:
        field: Field that failed validation
        value: Invalid value
        expected: Expected value format
        config_path: Path to config file
    """
    context = {"field": field, "provided_value": str(value), "expected_format": expected}

    if config_path:
        context["config_file"] = str(config_path)

    return ErrorContext(
        error_type="Validation Error",
        message=f"Invalid value for '{field}'",
        context=context,
        recovery_hints=[
            f"Update the '{field}' field in your configuration",
            f"Expected format: {expected}",
            "Check config.example.yaml for valid examples",
            "Validate your config with: --dry-run",
        ],
        examples=[
            "# In config.yaml:",
            f"{field}: <valid_value>  # {expected}",
            "",
            "# Validate before running:",
            "python generate_reports.py --dry-run ...",
        ],
        doc_links=["docs/configuration.md#validation", "docs/configuration.md#schema"],
    )
