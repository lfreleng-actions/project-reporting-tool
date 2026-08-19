# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Error tracking and aggregation.

Holds the tracker that collects classified errors during a run and derives
summary statistics, API failure breakdowns and partial failure reports.
"""

from collections import defaultdict
from typing import Any

from .models import ClassifiedError, ErrorContext
from .taxonomy import (
    ERROR_TYPE_CATEGORY_MAP,
    ErrorCategory,
    ErrorSeverity,
    ErrorType,
)


class ErrorTracker:
    """
    Tracks and aggregates errors across the reporting process.

    Provides error statistics, grouping, and reporting capabilities.
    """

    def __init__(self) -> None:
        self.errors: list[ClassifiedError] = []
        self.errors_by_type: dict[ErrorType, list[ClassifiedError]] = defaultdict(list)
        self.errors_by_category: dict[ErrorCategory, list[ClassifiedError]] = defaultdict(list)
        self.errors_by_severity: dict[ErrorSeverity, list[ClassifiedError]] = defaultdict(list)
        self.errors_by_repo: dict[str, list[ClassifiedError]] = defaultdict(list)

    def add_error(
        self,
        error_type: ErrorType,
        message: str,
        severity: ErrorSeverity | None = None,
        context: ErrorContext | None = None,
        exception: Exception | None = None,
    ) -> ClassifiedError:
        """
        Add an error to the tracker.

        Args:
            error_type: Type of error
            message: Error message
            severity: Error severity (optional, defaults based on type)
            context: Error context
            exception: Original exception if available

        Returns:
            The classified error
        """
        error = ClassifiedError(
            error_type=error_type,
            message=message,
            severity=severity,
            context=context or ErrorContext(),
            original_exception=exception,
        )

        self.errors.append(error)
        self.errors_by_type[error.error_type].append(error)
        if error.category:
            self.errors_by_category[error.category].append(error)
        if error.severity:
            self.errors_by_severity[error.severity].append(error)

        if error.context.repository:
            self.errors_by_repo[error.context.repository].append(error)

        return error

    def get_error_count(self) -> int:
        """Get total number of errors."""
        return len(self.errors)

    def get_errors_by_severity(self, severity: ErrorSeverity) -> list[ClassifiedError]:
        """Get all errors of a specific severity."""
        return self.errors_by_severity[severity]

    def get_errors_by_category(self, category: ErrorCategory) -> list[ClassifiedError]:
        """Get all errors of a specific category."""
        return self.errors_by_category[category]

    def get_errors_by_type(self, error_type: ErrorType) -> list[ClassifiedError]:
        """Get all errors of a specific type."""
        return self.errors_by_type[error_type]

    def get_errors_by_repository(self, repository: str) -> list[ClassifiedError]:
        """Get all errors for a specific repository."""
        return self.errors_by_repo[repository]

    def get_summary(self) -> dict[str, Any]:
        """
        Get error summary statistics.

        Returns:
            Dictionary with error counts by various dimensions.
        """
        return {
            "total_errors": len(self.errors),
            "by_severity": {
                severity.value: len(errors) for severity, errors in self.errors_by_severity.items()
            },
            "by_category": {
                category.value: len(errors) for category, errors in self.errors_by_category.items()
            },
            "by_type": {
                error_type.value: len(errors) for error_type, errors in self.errors_by_type.items()
            },
            "repositories_affected": len(self.errors_by_repo),
        }

    def get_api_failures(self) -> dict[str, Any]:
        """
        Get API-specific failure summary.

        Returns:
            Dictionary with API error details.
        """
        api_errors = self.errors_by_category[ErrorCategory.API]

        if not api_errors:
            return {}

        return {
            "total_api_errors": len(api_errors),
            "by_type": {
                error_type.value: len(self.errors_by_type[error_type])
                for error_type in ErrorType
                if error_type in self.errors_by_type
                and ERROR_TYPE_CATEGORY_MAP.get(error_type) == ErrorCategory.API
            },
            "rate_limit_hits": len(self.errors_by_type[ErrorType.API_RATE_LIMIT]),
            "authentication_failures": len(self.errors_by_type[ErrorType.API_AUTHENTICATION]),
        }

    def get_partial_failures(self) -> list[dict[str, Any]]:
        """
        Get repositories with errors but some successful processing.

        Returns:
            List of repositories with error details.
        """
        partial_failures = []

        for repo, errors in self.errors_by_repo.items():
            # Consider it a partial failure if there are errors but not critical ones
            critical_errors = [e for e in errors if e.severity == ErrorSeverity.CRITICAL]

            if errors and not critical_errors:
                partial_failures.append(
                    {
                        "repository": repo,
                        "error_count": len(errors),
                        "severity_breakdown": {
                            severity.value: len([e for e in errors if e.severity == severity])
                            for severity in ErrorSeverity
                            if any(e.severity == severity for e in errors)
                        },
                        "sample_errors": [e.message for e in errors[:3]],
                    }
                )

        return partial_failures

    def get_detailed_report(self) -> list[dict[str, Any]]:
        """
        Get detailed list of all errors.

        Returns:
            List of error dictionaries with full details.
        """
        return [error.to_dict() for error in self.errors]
