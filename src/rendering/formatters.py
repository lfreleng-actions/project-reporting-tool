# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Formatting utilities for template rendering.

This module provides reusable formatting functions that can be used as
Jinja2 template filters or standalone utilities.

Migrated from src/util/formatting.py for use in template rendering.

Phase: 8 - Renderer Modernization
"""

import datetime
import re
from typing import Any


# Unknown age sentinel (from util.formatting)
UNKNOWN_AGE = float("inf")


def format_number(value: int | float | None) -> str:
    """
    Format a number with K/M/B suffixes for readability.

    Args:
        value: Number to format (can be None)

    Returns:
        Formatted string (e.g., "1.2K", "3.4M", "5.6B")
        Returns "0" for None or zero values

    Examples:
        >>> format_number(1234)
        '1.2K'
        >>> format_number(1234567)
        '1.2M'
        >>> format_number(1234567890)
        '1.2B'
        >>> format_number(42)
        '42'
    """
    if value is None or value == 0:
        return "0"

    value = float(value)

    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    elif abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"
    else:
        return str(int(value))


def format_number_raw(value: int | float | None) -> str:
    """
    Format a number without abbreviation (raw number with comma separators).

    Args:
        value: Number to format (can be None)

    Returns:
        Formatted string with comma separators (e.g., "1,234", "1,234,567")
        Returns "0" for None or zero values

    Examples:
        >>> format_number_raw(1234)
        '1,234'
        >>> format_number_raw(1234567)
        '1,234,567'
        >>> format_number_raw(42)
        '42'
        >>> format_number_raw(None)
        '0'
    """
    if value is None or value == 0:
        return "0"

    return f"{int(value):,}"


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


def format_loc(value: int | float | None) -> str:
    """
    Format Lines of Code with '+' prefix for positive numbers.

    Args:
        value: LOC value to format (can be None)

    Returns:
        Formatted string with '+' prefix for positive numbers

    Examples:
        >>> format_loc(100)
        '+100'
        >>> format_loc(0)
        '0'
        >>> format_loc(-50)
        '-50'
        >>> format_loc(None)
        '0'
    """
    if value is None or value == 0:
        return "0"

    num_value = int(value)
    if num_value > 0:
        return f"+{num_value}"
    else:
        return str(num_value)


def format_percentage(
    value: int | float | None, total: int | float | None = None, decimals: int = 1
) -> str:
    """
    Format a number as a percentage.

    Can be used in two ways:
    1. Pass pre-calculated percentage (0-100 range): format_percentage(45.678)
    2. Calculate from value and total: format_percentage(10, 100)

    Args:
        value: Number to format or numerator for calculation
        total: Optional denominator for percentage calculation
        decimals: Number of decimal places

    Returns:
        Formatted percentage string (e.g., "45.2%")

    Examples:
        >>> format_percentage(45.678)
        '45.7%'
        >>> format_percentage(10, 100)
        '10.0%'
        >>> format_percentage(10, 100, decimals=2)
        '10.00%'
        >>> format_percentage(None)
        '0.0%'
        >>> format_percentage(10, 0)
        '0.0%'
    """
    if value is None:
        value = 0.0

    # If total is provided, calculate percentage
    if total is not None:
        if total == 0:
            return f"{0.0:.{decimals}f}%"
        value = (float(value) / float(total)) * 100.0

    return f"{value:.{decimals}f}%"


def slugify(text: str) -> str:
    """
    Convert text to URL-friendly slug.

    Args:
        text: Text to slugify

    Returns:
        Lowercase slug with hyphens (e.g., "hello-world")

    Examples:
        >>> slugify("Hello World")
        'hello-world'
        >>> slugify("Test_123 (Special)")
        'test-123-special'
    """
    if not text:
        return ""

    # Convert to lowercase
    text = text.lower()

    # Replace spaces and underscores with hyphens
    text = re.sub(r"[\s_]+", "-", text)

    # Remove non-alphanumeric characters (except hyphens)
    text = re.sub(r"[^a-z0-9-]", "", text)

    # Remove duplicate hyphens
    text = re.sub(r"-+", "-", text)

    # Strip leading/trailing hyphens
    text = text.strip("-")

    return text


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

    if isinstance(date, datetime.datetime | datetime.date):
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


def truncate(text: str, length: int = 50, suffix: str = "...") -> str:
    """
    Truncate text to specified length with suffix.

    Args:
        text: Text to truncate
        length: Maximum length
        suffix: Suffix to append if truncated

    Returns:
        Truncated text

    Examples:
        >>> truncate("This is a very long text", 10)
        'This is...'
    """
    if not text or len(text) <= length:
        return text

    return text[: length - len(suffix)] + suffix


def format_list(items: list[Any], separator: str = ", ", final_separator: str = " and ") -> str:
    """
    Format a list as a grammatically correct string.

    Args:
        items: List of items to format
        separator: Separator between items
        final_separator: Separator before last item

    Returns:
        Formatted string

    Examples:
        >>> format_list(["apple", "banana", "cherry"])
        'apple, banana and cherry'
        >>> format_list(["apple", "banana"])
        'apple and banana'
        >>> format_list(["apple"])
        'apple'
    """
    if not items:
        return ""

    str_items: list[str] = [str(item) for item in items]

    if len(str_items) == 1:
        return str_items[0]
    elif len(str_items) == 2:
        return f"{str_items[0]}{final_separator}{str_items[1]}"
    else:
        return f"{separator.join(str_items[:-1])}{final_separator}{str_items[-1]}"


def format_bytes(bytes_value: int | float | None) -> str:
    """
    Format bytes as human-readable size.

    Args:
        bytes_value: Number of bytes

    Returns:
        Formatted string (e.g., "1.2 KB", "3.4 MB")

    Examples:
        >>> format_bytes(1024)
        '1.0 KB'
        >>> format_bytes(1536)
        '1.5 KB'
        >>> format_bytes(1048576)
        '1.0 MB'
    """
    if bytes_value is None or bytes_value == 0:
        return "0 B"

    bytes_value = float(bytes_value)

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(bytes_value) < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0

    return f"{bytes_value:.1f} PB"


def pluralize(count: int | float | None, singular: str = "", plural: str = "s") -> str:
    """
    Return singular or plural form based on count.

    Args:
        count: Number to check
        singular: Singular form (default: empty string)
        plural: Plural form (default: "s")

    Returns:
        Singular form if count is 1, plural form otherwise

    Examples:
        >>> pluralize(1)
        ''
        >>> pluralize(2)
        's'
        >>> pluralize(1, "item", "items")
        'item'
        >>> pluralize(5, "item", "items")
        'items'
    """
    if count is None:
        count = 0

    return singular if abs(count) == 1 else plural


def format_feature_name(name: str) -> str:
    """
    Format feature name from snake_case to Title Case.

    Args:
        name: Feature name in snake_case

    Returns:
        Formatted feature name in Title Case

    Examples:
        >>> format_feature_name("dependabot")
        'Dependabot'
        >>> format_feature_name("pre_commit")
        'Pre-commit'
        >>> format_feature_name("github2gerrit_workflow")
        'GitHub2Gerrit Workflow'
        >>> format_feature_name("readthedocs")
        'ReadTheDocs'
    """
    if not name:
        return ""

    # Special cases for known feature names
    special_cases = {
        "dependabot": "Dependabot",
        "pre_commit": "Pre-commit",
        "readthedocs": "ReadTheDocs",
        "gitreview": ".gitreview",
        "g2g": "G2G",
        "github2gerrit_workflow": "GitHub2Gerrit",
        "sonatype_config": "Sonatype Config",
        "project_types": "Type",
        "workflows": "Workflows",
    }

    if name.lower() in special_cases:
        return special_cases[name.lower()]

    # Default: Convert snake_case to Title Case
    return " ".join(word.capitalize() for word in name.split("_"))


def status_emoji(status: str | None) -> str:
    """
    Map repository activity status to emoji.

    Args:
        status: Activity status string ('current', 'active', 'inactive')

    Returns:
        Emoji representing the status

    Examples:
        >>> status_emoji('current')
        '✅'
        >>> status_emoji('active')
        '☑️'
        >>> status_emoji('inactive')
        '🛑'
        >>> status_emoji('unknown')
        '❓'
        >>> status_emoji(None)
        '❓'
    """
    if not status:
        return "❓"

    status_map = {
        "current": "✅",
        "active": "☑️",
        "inactive": "🛑",
    }

    return status_map.get(status.lower(), "❓")


# Jinja2 filter registration helper
def get_template_filters() -> dict[str, Any]:
    """
    Get dictionary of all formatters for Jinja2 filter registration.

    Returns:
        Dictionary mapping filter names to functions
    """
    return {
        "format_number": format_number,
        "format_number_raw": format_number_raw,
        "format_loc": format_loc,
        "format_age": format_age,
        "format_percentage": format_percentage,
        "slugify": slugify,
        "format_date": format_date,
        "format_timestamp": format_timestamp,
        "truncate": truncate,
        "format_list": format_list,
        "format_bytes": format_bytes,
        "pluralize": pluralize,
        "format_feature_name": format_feature_name,
        "status_emoji": status_emoji,
    }
