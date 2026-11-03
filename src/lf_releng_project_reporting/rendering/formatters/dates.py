# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Date, time and age formatting utilities.

Human-readable rendering of ages in days and of dates and timestamps supplied
as strings or datetime objects.
"""

import datetime


# Unknown age sentinel (from util.formatting)
UNKNOWN_AGE = float("inf")


def format_age(days: int | float | None) -> str:
    """
    Format age in days as human-readable string.

    Args:
        days: Number of days (can be None or UNKNOWN_AGE sentinel)

    Returns:
        Formatted string (e.g., "2d", "3w", "5m", "2y", "unknown")

    Examples:
        >>> format_age(1)
        '1d'
        >>> format_age(14)
        '2w'
        >>> format_age(60)
        '2m'
        >>> format_age(730)
        '2y'
        >>> format_age(None)
        'unknown'
    """
    if days is None or days == UNKNOWN_AGE:
        return "unknown"

    days = float(days)

    if days < 0:
        return "unknown"
    elif days < 7:
        return f"{int(days)}d"
    elif days < 30:
        weeks = int(days / 7)
        return f"{weeks}w"
    elif days < 365:
        months = int(days / 30)
        return f"{months}m"
    else:
        years = int(days / 365)
        return f"{years}y"


def format_date(
    date: str | datetime.datetime | datetime.date | None, format_str: str = "%Y-%m-%d"
) -> str:
    """
    Format a date object or ISO string as a formatted date string.

    Args:
        date: Date to format (string, datetime, or date object)
        format_str: strftime format string

    Returns:
        Formatted date string

    Examples:
        >>> format_date("2025-01-16")
        '2025-01-16'
        >>> format_date(datetime.date(2025, 1, 16), "%B %d, %Y")
        'January 16, 2025'
    """
    if date is None:
        return "unknown"

    if isinstance(date, str):
        # Try to parse ISO format
        try:
            if "T" in date:
                parsed_date = datetime.datetime.fromisoformat(date.replace("Z", "+00:00"))
                return parsed_date.strftime(format_str)
            else:
                parsed_date = datetime.datetime.strptime(date, "%Y-%m-%d")
                return parsed_date.strftime(format_str)
        except (ValueError, AttributeError):
            return date  # Return as-is if can't parse

    if isinstance(date, (datetime.datetime, datetime.date)):
        return date.strftime(format_str)

    return str(date)  # type: ignore[unreachable]


def format_timestamp(
    timestamp: str | datetime.datetime | None, format_str: str = "%Y-%m-%d %H:%M:%S"
) -> str:
    """
    Format a timestamp with date and time.

    Args:
        timestamp: Timestamp to format
        format_str: strftime format string

    Returns:
        Formatted timestamp string

    Examples:
        >>> format_timestamp("2025-01-16T10:30:00")
        '2025-01-16 10:30:00'
    """
    return format_date(timestamp, format_str)
