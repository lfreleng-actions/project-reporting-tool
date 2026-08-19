# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Text formatting utilities.

Slugs, truncation, list joining, pluralisation, feature-name titling and
status emoji mapping.
"""

import re
from typing import Any


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

    text = re.sub(r"-+", "-", text)

    # Strip leading/trailing hyphens
    text = text.strip("-")

    return text


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
