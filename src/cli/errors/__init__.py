# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
CLI Error Classes

Enhanced error classes for better user experience with actionable suggestions
and documentation links.

Phase 9: CLI & UX Improvements
Phase 13, Step 4: Enhanced Error Messages with Context
"""

from .base import CLIError
from .messages import format_validation_errors, suggest_common_fixes
from .types import (
    APIError,
    ConfigurationError,
    DiskSpaceError,
    InvalidArgumentError,
    NetworkError,
    PermissionError,
    ValidationError,
)


__all__ = [
    "CLIError",
    "ConfigurationError",
    "InvalidArgumentError",
    "APIError",
    "PermissionError",
    "DiskSpaceError",
    "ValidationError",
    "NetworkError",
    "format_validation_errors",
    "suggest_common_fixes",
]
