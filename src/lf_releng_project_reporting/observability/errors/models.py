# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Error data structures and exception classification.

Holds the context and classified error dataclasses, together with the helper
that turns an arbitrary Python exception into a classified error.
"""

from dataclasses import dataclass, field
from typing import Any

from .taxonomy import (
    ERROR_TYPE_CATEGORY_MAP,
    ERROR_TYPE_SEVERITY_MAP,
    ErrorCategory,
    ErrorSeverity,
    ErrorType,
)


@dataclass
class ErrorContext:
    """
    Context information for an error occurrence.

    Attributes:
        repository: Repository where error occurred
        operation: Operation being performed
        phase: Processing phase
        window: Time window (if applicable)
        extra: Additional context fields
    """

    repository: str | None = None
    operation: str | None = None
    phase: str | None = None
    window: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {}
        if self.repository:
            result["repository"] = self.repository
        if self.operation:
            result["operation"] = self.operation
        if self.phase:
            result["phase"] = self.phase
        if self.window:
            result["window"] = self.window
        if self.extra:
            result.update(self.extra)
        return result


@dataclass
class ClassifiedError:
    """
    A classified error with type, severity, and context.

    Attributes:
        error_type: Type of error
        message: Error message
        severity: Error severity (defaults based on type)
        category: Error category (derived from type)
        context: Error context
        original_exception: Original exception if available
    """

    error_type: ErrorType
    message: str
    severity: ErrorSeverity | None = None
    category: ErrorCategory | None = None
    context: ErrorContext = field(default_factory=ErrorContext)
    original_exception: Exception | None = None

    def __post_init__(self) -> None:
        """Set default severity and category if not provided."""
        if self.severity is None:
            self.severity = ERROR_TYPE_SEVERITY_MAP.get(self.error_type, ErrorSeverity.MEDIUM)

        if self.category is None:
            self.category = ERROR_TYPE_CATEGORY_MAP.get(self.error_type, ErrorCategory.SYSTEM)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for reporting."""
        result: dict[str, Any] = {
            "error_type": self.error_type.value,
            "category": self.category.value if self.category else None,
            "severity": self.severity.value if self.severity else None,
            "message": self.message,
        }

        context = self.context.to_dict()
        if context:
            result["context"] = context

        if self.original_exception:
            result["exception_type"] = type(self.original_exception).__name__

        return result


def classify_exception(
    exception: Exception,
    context: ErrorContext | None = None,
) -> ClassifiedError:
    """
    Classify a Python exception into an error type.

    Args:
        exception: Exception to classify
        context: Error context

    Returns:
        Classified error
    """
    error_type = ErrorType.SYSTEM_UNKNOWN
    message = str(exception)

    # Classify based on exception type
    exc_type_name = type(exception).__name__

    if "Timeout" in exc_type_name or "timeout" in message.lower():
        error_type = ErrorType.NETWORK_TIMEOUT
    elif "Connection" in exc_type_name or "connection" in message.lower():
        error_type = ErrorType.NETWORK_CONNECTION
    elif "Permission" in exc_type_name or "permission" in message.lower():
        error_type = ErrorType.SYSTEM_PERMISSION
    elif "IOError" in exc_type_name or "FileNotFoundError" in exc_type_name:
        error_type = ErrorType.SYSTEM_IO
    elif "ValueError" in exc_type_name or "TypeError" in exc_type_name:
        error_type = ErrorType.VALIDATION_TYPE

    return ClassifiedError(
        error_type=error_type,
        message=message,
        context=context or ErrorContext(),
        original_exception=exception,
    )
