# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Jinja2 filter registration.

Collects the individual formatting helpers into the filter mapping consumed
by the template renderer.
"""

from typing import Any

from .dates import format_age, format_date, format_timestamp
from .numeric import (
    format_bytes,
    format_loc,
    format_number,
    format_number_raw,
    format_percentage,
)
from .text import (
    format_feature_name,
    format_list,
    pluralize,
    slugify,
    status_emoji,
    truncate,
)


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
