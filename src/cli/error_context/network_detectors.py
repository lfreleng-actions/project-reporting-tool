# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Error context detectors for network connectivity and API failures."""

from typing import Any

from .models import ErrorContext


def detect_github_auth_error(status_code: int | None = None) -> ErrorContext:
    """
    Create context for GitHub authentication errors.

    Args:
        status_code: HTTP status code (401, 403, etc.)
    """
    context: dict[str, Any] = {"api": "GitHub"}
    if status_code:
        context["status_code"] = status_code

    if status_code == 401:
        message = "GitHub API authentication failed - invalid token"
        hints = [
            "Verify GITHUB_TOKEN environment variable is set",
            "Check that the token hasn't expired",
            "Generate a new personal access token at github.com/settings/tokens",
            "Ensure token has required scopes: repo, read:org",
        ]
    elif status_code == 403:
        message = "GitHub API access forbidden - insufficient permissions"
        hints = [
            "Check that your token has the required scopes",
            "For organization repos, ensure token has read:org scope",
            "For private repos, ensure token has repo scope",
            "Verify you have access to the repository/organization",
        ]
    else:
        message = "GitHub API authentication error"
        hints = [
            "Set GITHUB_TOKEN environment variable",
            "Generate a personal access token at github.com/settings/tokens",
            "Required scopes: repo, read:org",
            "Add to environment: export GITHUB_TOKEN=ghp_...",
        ]

    return ErrorContext(
        error_type="API Authentication Error",
        message=message,
        context=context,
        recovery_hints=hints,
        examples=[
            "# Generate token at: https://github.com/settings/tokens/new",
            "# Required scopes: repo, read:org",
            "",
            "# Set in environment:",
            "export GITHUB_TOKEN=ghp_your_token_here",
            "",
            "# Or in config.yaml:",
            "api:",
            "  github:",
            "    token: ${GITHUB_TOKEN}  # Reads from environment",
        ],
        related_errors=[
            "403 Forbidden - insufficient permissions",
            "404 Not Found - repository not accessible",
        ],
        doc_links=["docs/github-token-setup.md", "GITHUB_TOKEN_REQUIREMENTS.md"],
    )


def detect_rate_limit_error(api_name: str, reset_time: int | None = None) -> ErrorContext:
    """
    Create context for API rate limit errors.

    Args:
        api_name: Name of API (GitHub, Gerrit, etc.)
        reset_time: Unix timestamp when rate limit resets
    """
    context = {"api": api_name}
    if reset_time:
        from datetime import datetime

        reset_dt = datetime.fromtimestamp(reset_time)
        context["rate_limit_reset"] = reset_dt.strftime("%Y-%m-%d %H:%M:%S")

    return ErrorContext(
        error_type="API Rate Limit",
        message=f"{api_name} API rate limit exceeded",
        context=context,
        recovery_hints=[
            f"Wait for {api_name} rate limit to reset"
            + (f" (at {context.get('rate_limit_reset')})" if reset_time else ""),
            "Use a different API token if available",
            "Reduce the number of API calls with caching",
            "Use --workers 1 to slow down parallel requests",
        ],
        examples=[
            "# Wait and retry:",
            "python generate_reports.py --project myproject ...",
            "",
            "# Or use caching to reduce API calls:",
            "python generate_reports.py --cache --project myproject ...",
            "",
            "# For GitHub, authenticated requests get higher limits:",
            "export GITHUB_TOKEN=ghp_your_token",
        ],
        related_errors=["429 Too Many Requests", "403 Rate limit exceeded"],
        doc_links=[f"docs/api-limits.md#{api_name.lower()}", "docs/troubleshooting.md#rate-limits"],
    )


def detect_network_error(url: str | None = None, error_type: str | None = None) -> ErrorContext:
    """
    Create context for network connectivity errors.

    Args:
        url: URL that failed
        error_type: Type of network error (timeout, connection, dns, etc.)
    """
    context = {}
    if url:
        context["url"] = url
    if error_type:
        context["error_type"] = error_type

    hints = ["Check your internet connection"]
    examples = []

    if error_type == "timeout":
        hints.extend(
            [
                "Increase timeout with --timeout 300",
                "Check if the server is responding",
                "Verify firewall is not blocking connections",
            ]
        )
        examples.append("python generate_reports.py --timeout 300 ...")
    elif error_type == "dns":
        hints.extend(
            [
                "Verify the hostname is correct",
                "Check DNS resolution: ping api.github.com",
                "Try using a different DNS server",
            ]
        )
        examples.extend(
            ["# Test DNS resolution:", "ping api.github.com", "nslookup api.github.com"]
        )
    elif error_type == "ssl":
        hints.extend(
            [
                "Verify SSL certificates are installed",
                "Update CA certificates",
                "If using corporate proxy, check SSL inspection settings",
            ]
        )
        examples.extend(
            [
                "# Update certificates (Ubuntu/Debian):",
                "sudo apt-get update && sudo apt-get install --reinstall ca-certificates",
            ]
        )
    else:
        hints.extend(
            [
                "Verify you can reach the server",
                "Check proxy settings if behind a corporate firewall",
                "Test connectivity: curl -I https://api.github.com",
            ]
        )
        examples.append("curl -I https://api.github.com")

    # Build message with error type
    msg_parts = []
    if error_type:
        msg_parts.append(f"{error_type.title()}")
    msg_parts.append("network connectivity error" if not error_type else "error")
    if url:
        msg_parts.append(f"for {url}")

    message = " ".join(msg_parts) if msg_parts else "Network connectivity error"

    return ErrorContext(
        error_type="Network Error",
        message=message,
        context=context,
        recovery_hints=hints,
        examples=examples,
        doc_links=["docs/troubleshooting.md#network-issues", "docs/proxy-configuration.md"],
    )
