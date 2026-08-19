# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Human-readable formatting helpers for progress output."""


def estimate_time_remaining(current: int, total: int, elapsed: float) -> str:
    """
    Estimate time remaining for an operation.

    Args:
        current: Number of items completed
        total: Total number of items
        elapsed: Elapsed time in seconds

    Returns:
        Human-readable time estimate (e.g., "2m 30s")

    Example:
        >>> estimate = estimate_time_remaining(50, 100, 60.0)
        >>> print(estimate)
        1m 0s
    """
    if current == 0 or total == 0:
        return "unknown"

    rate = current / elapsed
    remaining = total - current
    seconds_left = remaining / rate

    if seconds_left < 60:
        return f"{int(seconds_left)}s"
    elif seconds_left < 3600:
        minutes = int(seconds_left / 60)
        seconds = int(seconds_left % 60)
        return f"{minutes}m {seconds}s"
    else:
        hours = int(seconds_left / 3600)
        minutes = int((seconds_left % 3600) / 60)
        return f"{hours}h {minutes}m"


def format_count(count: int, singular: str, plural: str | None = None) -> str:
    """
    Format count with appropriate singular/plural form.

    Args:
        count: Number to format
        singular: Singular form (e.g., "repository")
        plural: Plural form (optional, defaults to singular + "s" or singular[:-1] + "ies" for -y endings)

    Returns:
        Formatted string (e.g., "1 repository" or "5 repositories")

    Example:
        >>> format_count(1, "repository")
        '1 repository'
        >>> format_count(5, "repository")
        '5 repositories'
        >>> format_count(1, "entry", "entries")
        '1 entry'
    """
    if plural is None:
        # Handle -y endings (repository -> repositories)
        if singular.endswith("y") and len(singular) > 1 and singular[-2] not in "aeiou":
            plural = singular[:-1] + "ies"
        else:
            plural = singular + "s"

    word = singular if count == 1 else plural
    return f"{count} {word}"
