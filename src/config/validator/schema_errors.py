# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Human-readable formatting of JSON Schema validation errors.

Holds the per-validator message formatters and the lookup table that maps
a jsonschema validator name to its formatter.
"""

from collections.abc import Callable
from typing import Any


def _extract_quoted(message: str) -> str:
    """Return the first single-quoted token in a schema error message.

    Falls back to the raw message when it contains no quoted token, so a
    differently phrased jsonschema error cannot raise IndexError.
    """
    parts = message.split("'")
    return parts[1] if len(parts) >= 3 else message


def _format_required_error(e: Any) -> str:
    return f"Missing required field: '{_extract_quoted(e.message)}'"


def _format_type_error(e: Any) -> str:
    return f"Invalid type: expected {e.validator_value}, got {type(e.instance).__name__}"


def _format_enum_error(e: Any) -> str:
    valid_values = ", ".join(f"'{v}'" for v in e.validator_value)
    return f"Invalid value. Must be one of: {valid_values}"


def _format_minimum_error(e: Any) -> str:
    return f"Value {e.instance} is below minimum {e.validator_value}"


def _format_maximum_error(e: Any) -> str:
    return f"Value {e.instance} exceeds maximum {e.validator_value}"


def _format_pattern_error(e: Any) -> str:
    return f"Value does not match required pattern: {e.validator_value}"


# Table-driven formatting for JSON Schema validation errors, keyed by the
# jsonschema validator that produced the error. Any validator absent from this
# table falls back to the raw error message.
_SCHEMA_ERROR_FORMATTERS: dict[str, Callable[[Any], str]] = {
    "required": _format_required_error,
    "type": _format_type_error,
    "enum": _format_enum_error,
    "minimum": _format_minimum_error,
    "maximum": _format_maximum_error,
    "pattern": _format_pattern_error,
}
