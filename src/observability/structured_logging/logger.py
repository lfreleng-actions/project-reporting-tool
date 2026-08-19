# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Structured logger and its convenience helpers.

Holds the logger wrapper that manages the context stack, performance timing
and aggregation, plus the factory and context-logging helper functions.
"""

import logging
import time
from contextlib import contextmanager
from typing import Any

from .aggregation import LogAggregator
from .context import LogContext, LogEntry, LogLevel, LogPhase


class StructuredLogger:
    """
    Wrapper around standard Python logger with structured logging support.

    Provides context management, performance tracking, and log aggregation.
    """

    def __init__(self, logger: logging.Logger, aggregator: LogAggregator | None = None):
        """
        Initialize structured logger.

        Args:
            logger: Underlying Python logger
            aggregator: Optional log aggregator for summary reporting
        """
        self.logger = logger
        self.aggregator = aggregator or LogAggregator()
        self._context_stack: list[LogContext] = [LogContext()]

    @property
    def current_context(self) -> LogContext:
        """Get current logging context."""
        # Merge all contexts in the stack
        result = LogContext()
        for ctx in self._context_stack:
            result = result.merge(ctx)
        return result

    def _log(
        self, level: LogLevel, message: str, duration_ms: float | None = None, **extra_context: Any
    ) -> None:
        """
        Internal logging method.

        Args:
            level: Log level
            message: Log message
            duration_ms: Optional duration for performance tracking
            extra_context: Additional context fields
        """
        context = self.current_context
        if extra_context:
            context = LogContext(
                repository=context.repository,
                phase=context.phase,
                operation=context.operation,
                window=context.window,
                extra={**context.extra, **extra_context},
            )

        entry = LogEntry(
            level=level,
            message=message,
            context=context,
            duration_ms=duration_ms,
        )

        # Add to aggregator
        self.aggregator.add_entry(entry)

        log_level = getattr(logging, level.value)
        context_dict = context.to_dict()

        # Format message with context
        if context_dict or duration_ms is not None:
            extra_parts = []
            if duration_ms is not None:
                extra_parts.append(f"duration_ms={duration_ms:.2f}")
            for key, value in context_dict.items():
                extra_parts.append(f"{key}={value}")

            formatted_message = f"{message} [{', '.join(extra_parts)}]"
        else:
            formatted_message = message

        self.logger.log(log_level, formatted_message)

    def debug(self, message: str, **extra: Any) -> None:
        """Log debug message with context."""
        self._log(LogLevel.DEBUG, message, **extra)

    def info(self, message: str, **extra: Any) -> None:
        """Log info message with context."""
        self._log(LogLevel.INFO, message, **extra)

    def warning(self, message: str, **extra: Any) -> None:
        """Log warning message with context."""
        self._log(LogLevel.WARNING, message, **extra)

    def error(self, message: str, **extra: Any) -> None:
        """Log error message with context."""
        self._log(LogLevel.ERROR, message, **extra)

    def critical(self, message: str, **extra: Any) -> None:
        """Log critical message with context."""
        self._log(LogLevel.CRITICAL, message, **extra)

    @contextmanager
    def context(
        self,
        repository: str | None = None,
        phase: LogPhase | None = None,
        operation: str | None = None,
        window: str | None = None,
        **extra: Any,
    ):
        """
        Context manager for adding logging context.

        Args:
            repository: Repository name
            phase: Processing phase
            operation: Operation name
            window: Time window
            extra: Additional context fields

        Example:
            with logger.context(repository="foo/bar", phase=LogPhase.COLLECTION):
                logger.info("Processing repository")
        """
        ctx = LogContext(
            repository=repository,
            phase=phase,
            operation=operation,
            window=window,
            extra=extra,
        )

        self._context_stack.append(ctx)
        try:
            yield
        finally:
            self._context_stack.pop()

    @contextmanager
    def timed(self, operation: str):
        """
        Context manager for timing operations.

        Args:
            operation: Name of the operation being timed

        Example:
            with logger.timed("git_log"):
                # perform git operation
                pass
        """
        start_time = time.time()

        with self.context(operation=operation):
            try:
                yield
            finally:
                duration_ms = (time.time() - start_time) * 1000
                self._log(
                    LogLevel.DEBUG,
                    f"Operation completed: {operation}",
                    duration_ms=duration_ms,
                )

    def get_summary(self) -> dict[str, Any]:
        """Get aggregated log summary."""
        return self.aggregator.get_summary()

    def get_partial_failures(self) -> list[dict[str, Any]]:
        """Get list of repositories with partial failures."""
        return self.aggregator.get_partial_failures()


def create_structured_logger(
    name: str, level: int = logging.INFO, aggregator: LogAggregator | None = None
) -> StructuredLogger:
    """
    Create a structured logger instance.

    Args:
        name: Logger name
        level: Logging level
        aggregator: Optional log aggregator (creates new one if not provided)

    Returns:
        StructuredLogger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    return StructuredLogger(logger, aggregator)


def log_with_context(logger: StructuredLogger, level: str, message: str, **context: Any) -> None:
    """
    Helper function to log with context fields.

    Args:
        logger: Structured logger instance
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        message: Log message
        context: Context fields

    Example:
        log_with_context(
            logger,
            "INFO",
            "Repository processed",
            repository="foo/bar",
            commits=100
        )
    """
    log_method = getattr(logger, level.lower())
    log_method(message, **context)
