# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Numeric formatting utilities.

Human-readable rendering of counts, lines of code, percentages and byte sizes.
"""


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
