# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Error taxonomy and classification system for the repository reporting system.

This module provides a comprehensive error classification system that extends
the API error types to cover all operations including Git, data collection,
validation, and rendering.

Features:
- Hierarchical error classification
- Error context tracking
- Error aggregation and reporting
- Integration with structured logging
- Domain model validation errors
"""

from .models import ClassifiedError, ErrorContext, classify_exception
from .taxonomy import (
    ERROR_TYPE_CATEGORY_MAP,
    ERROR_TYPE_SEVERITY_MAP,
    ErrorCategory,
    ErrorSeverity,
    ErrorType,
)
from .tracker import ErrorTracker


__all__ = [
    "ERROR_TYPE_CATEGORY_MAP",
    "ERROR_TYPE_SEVERITY_MAP",
    "ClassifiedError",
    "ErrorCategory",
    "ErrorContext",
    "ErrorSeverity",
    "ErrorTracker",
    "ErrorType",
    "classify_exception",
]
