# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Formatting utilities for template rendering.

This module provides reusable formatting functions that can be used as
Jinja2 template filters or standalone utilities.

Migrated from src/util/formatting.py for use in template rendering.

Phase: 8 - Renderer Modernization
"""

from .dates import UNKNOWN_AGE, format_age, format_date, format_timestamp
from .filters import get_template_filters
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


__all__ = [
    "UNKNOWN_AGE",
    "format_age",
    "format_bytes",
    "format_date",
    "format_feature_name",
    "format_list",
    "format_loc",
    "format_number",
    "format_number_raw",
    "format_percentage",
    "format_timestamp",
    "get_template_filters",
    "pluralize",
    "slugify",
    "status_emoji",
    "truncate",
]
