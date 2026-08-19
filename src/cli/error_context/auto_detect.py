# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Automatic selection of an error context from a raised exception."""

from pathlib import Path

from .config_detectors import (
    detect_disk_space_error,
    detect_invalid_yaml,
    detect_missing_config,
    detect_missing_repos_path,
    detect_permission_error,
)
from .models import ErrorContext
from .network_detectors import (
    detect_github_auth_error,
    detect_network_error,
    detect_rate_limit_error,
)


def auto_detect_error_context(error: Exception, **kwargs) -> ErrorContext:
    """
    Automatically detect error context based on exception.

    Args:
        error: The exception that was raised
        **kwargs: Additional context (path, api_name, etc.)

    Returns:
        ErrorContext with appropriate recovery information
    """
    error_str = str(error).lower()
    error_type = type(error).__name__

    # File not found errors
    if isinstance(error, FileNotFoundError) or "not found" in error_str:
        if "config" in error_str:
            return detect_missing_config()
        elif "path" in kwargs:
            return detect_missing_repos_path(Path(kwargs["path"]))

    # YAML errors
    if "yaml" in error_type.lower() or "yaml" in error_str:
        path = kwargs.get("path", Path("config.yaml"))
        line = kwargs.get("line")
        return detect_invalid_yaml(Path(path), line)

    # Permission errors
    if isinstance(error, PermissionError) or "permission" in error_str:
        path = kwargs.get("path", Path("."))
        operation = kwargs.get("operation", "access")
        return detect_permission_error(Path(path), operation)

    # Network errors
    if "network" in error_str or "connection" in error_str or "timeout" in error_str:
        url = kwargs.get("url")
        net_error_type = None
        if "timeout" in error_str:
            net_error_type = "timeout"
        elif "dns" in error_str or "resolve" in error_str:
            net_error_type = "dns"
        elif "ssl" in error_str or "certificate" in error_str:
            net_error_type = "ssl"

        ctx = detect_network_error(url, net_error_type)
        # Preserve original error message if it has more detail
        if len(str(error)) > len(ctx.message):
            ctx.message = str(error)
        return ctx

    # API errors
    if "401" in error_str or "unauthorized" in error_str:
        return detect_github_auth_error(401)
    elif "403" in error_str:
        if "rate limit" in error_str:
            api_name = kwargs.get("api_name", "GitHub")
            reset_time = kwargs.get("reset_time")
            return detect_rate_limit_error(api_name, reset_time)
        else:
            return detect_github_auth_error(403)

    # Disk space errors
    if "disk" in error_str or "space" in error_str or isinstance(error, OSError):
        path = kwargs.get("path", Path("."))
        return detect_disk_space_error(Path(path))

    # Generic fallback
    return ErrorContext(
        error_type=error_type,
        message=str(error),
        context=kwargs,
        recovery_hints=[
            "Check the error message for details",
            "Run with --verbose for more information",
            "Consult documentation for troubleshooting",
        ],
        doc_links=["docs/troubleshooting.md"],
    )
