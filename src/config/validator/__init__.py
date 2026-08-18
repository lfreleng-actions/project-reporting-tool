# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Configuration validation module for repository reporting system.

This module provides comprehensive validation of configuration files using
JSON Schema, with detailed error reporting and backwards compatibility checking.

Features:
- JSON Schema-based validation
- Semantic validation (e.g., threshold ordering)
- Detailed error messages with suggestions
- Configuration warnings for deprecated/risky settings
- Schema version compatibility checking

Example:
    >>> from src.config.validator import ConfigValidator
    >>> validator = ConfigValidator()
    >>> result = validator.validate(config)
    >>> if not result.is_valid:
    ...     for error in result.errors:
    ...         print(f"ERROR: {error.message}")
    ...     for warning in result.warnings:
    ...         print(f"WARNING: {warning.message}")
"""

from .core import HAS_JSONSCHEMA, ConfigValidator, validate_config_file
from .reporting import print_validation_result
from .results import (
    ValidationCategory,
    ValidationIssue,
    ValidationLevel,
    ValidationResult,
)


__all__ = [
    "HAS_JSONSCHEMA",
    "ConfigValidator",
    "ValidationCategory",
    "ValidationIssue",
    "ValidationLevel",
    "ValidationResult",
    "print_validation_result",
    "validate_config_file",
]
