# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Structured logging framework for the repository reporting system.

This module provides a context-aware logging system that enhances standard
Python logging with structured fields, performance tracking, and integration
with domain models.

Features:
- Context propagation (repository, phase, operation)
- Performance timing
- Structured field injection
- Domain model integration
- Log aggregation and summarization
- JSON-compatible output
"""

from .aggregation import LogAggregator
from .context import LogContext, LogEntry, LogLevel, LogPhase
from .logger import (
    StructuredLogger,
    create_structured_logger,
    log_with_context,
)


__all__ = [
    "LogAggregator",
    "LogContext",
    "LogEntry",
    "LogLevel",
    "LogPhase",
    "StructuredLogger",
    "create_structured_logger",
    "log_with_context",
]
