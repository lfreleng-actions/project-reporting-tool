# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Thread-safe error collection for concurrent operations.

Holds ConcurrentErrorHandler, which gathers ErrorRecord entries from
multiple workers, classifies their severity, and summarises them for
reporting and debugging.
"""

import logging
import threading
import traceback
from typing import Any

from .records import ErrorRecord, ErrorSeverity


class ConcurrentErrorHandler:
    """
    Thread-safe error collection and analysis for concurrent operations.

    Collects errors from multiple workers, classifies severity, and provides
    error summaries for reporting and debugging.

    Example:
        >>> handler = ConcurrentErrorHandler()
        >>>
        >>> # In worker thread:
        >>> try:
        >>>     process_repo(repo)
        >>> except Exception as e:
        >>>     handler.record_error(
        >>>         context=repo.name,
        >>>         error=e,
        >>>         metadata={'repo_path': str(repo.path)}
        >>>     )
        >>>
        >>> # After all workers complete:
        >>> summary = handler.get_summary()
        >>> print(f"Total errors: {summary['total_errors']}")
    """

    def __init__(self, logger: logging.Logger | None = None):
        """
        Initialize error handler.

        Args:
            logger: Logger for error reporting (default: module logger)
        """
        self.logger = logger or logging.getLogger(__name__)
        self._errors: list[ErrorRecord] = []
        self._lock = threading.Lock()

    def record_error(
        self,
        context: str,
        error: Exception,
        severity: ErrorSeverity | None = None,
        retry_count: int = 0,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Record an error that occurred during execution.

        Thread-safe: Can be called from multiple threads concurrently.

        Args:
            context: Context identifier (e.g., repository name)
            error: Exception that occurred
            severity: Error severity (auto-detected if None)
            retry_count: Number of retries attempted
            metadata: Additional context information
        """
        error_type = type(error).__name__
        error_message = str(error)

        # Auto-detect severity if not provided
        if severity is None:
            severity = self._classify_severity(error)

        # Capture traceback
        tb = traceback.format_exc()

        record = ErrorRecord(
            context=context,
            error_type=error_type,
            error_message=error_message,
            severity=severity,
            traceback=tb,
            retry_count=retry_count,
            metadata=metadata or {},
        )

        with self._lock:
            self._errors.append(record)

        if severity == ErrorSeverity.TRANSIENT:
            self.logger.warning(
                f"Transient error in {context}: {error_type}: {error_message} "
                f"(retries: {retry_count})"
            )
        else:
            self.logger.error(
                f"Error in {context}: {error_type}: {error_message} (retries: {retry_count})"
            )

    def _classify_severity(self, error: Exception) -> ErrorSeverity:
        """
        Classify error severity based on exception type.

        Args:
            error: Exception to classify

        Returns:
            Classified severity level
        """
        # Transient errors (network, timeouts)
        transient_types = (
            "TimeoutError",
            "ConnectionError",
            "HTTPError",
            "NetworkError",
            "TemporaryError",
            "ServiceUnavailable",
        )

        # Permanent errors (configuration, not found)
        permanent_types = (
            "ValueError",
            "KeyError",
            "AttributeError",
            "FileNotFoundError",
            "PermissionError",
            "NotImplementedError",
        )

        error_type = type(error).__name__

        if error_type in transient_types:
            return ErrorSeverity.TRANSIENT
        elif error_type in permanent_types:
            return ErrorSeverity.PERMANENT
        else:
            return ErrorSeverity.UNKNOWN

    def get_errors(self) -> list[ErrorRecord]:
        """
        Get all recorded errors.

        Returns:
            List of all ErrorRecord objects
        """
        with self._lock:
            return list(self._errors)

    def get_summary(self) -> dict[str, Any]:
        """
        Get error summary for reporting.

        Returns:
            Dictionary with error statistics and groupings:
                - total_errors: Total number of errors
                - errors_by_severity: Count by severity level
                - errors_by_type: Count by exception type
                - failed_contexts: List of contexts that failed
                - transient_errors: Count of transient errors
                - permanent_errors: Count of permanent errors
                - unknown_errors: Count of unknown errors
        """
        with self._lock:
            errors = list(self._errors)

        if not errors:
            return {
                "total_errors": 0,
                "errors_by_severity": {},
                "errors_by_type": {},
                "failed_contexts": [],
                "transient_errors": 0,
                "permanent_errors": 0,
                "unknown_errors": 0,
            }

        # Group by severity
        by_severity: dict[str, int] = {}
        for error in errors:
            severity = error.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1

        # Group by type
        by_type: dict[str, int] = {}
        for error in errors:
            error_type = error.error_type
            by_type[error_type] = by_type.get(error_type, 0) + 1

        failed_contexts = list({e.context for e in errors})

        return {
            "total_errors": len(errors),
            "errors_by_severity": by_severity,
            "errors_by_type": by_type,
            "failed_contexts": failed_contexts,
            "transient_errors": by_severity.get("transient", 0),
            "permanent_errors": by_severity.get("permanent", 0),
            "unknown_errors": by_severity.get("unknown", 0),
        }

    def has_errors(self) -> bool:
        """
        Check if any errors have been recorded.

        Returns:
            True if errors exist, False otherwise
        """
        with self._lock:
            return len(self._errors) > 0

    def clear(self):
        """Clear all recorded errors."""
        with self._lock:
            self._errors.clear()
