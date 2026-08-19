# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Data model definitions for parallel repository processing.

Contains the worker/status enums, the worker pool configuration and the
per-item and aggregated result dataclasses used across the parallel
processing components.
"""

import multiprocessing
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WorkerType(Enum):
    """Type of worker pool to use."""

    THREAD = "thread"
    PROCESS = "process"


class ProcessingStatus(Enum):
    """Status of a processing task."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class WorkerConfig:
    """Configuration for parallel processing."""

    max_workers: int = 4
    worker_type: WorkerType = WorkerType.THREAD
    worker_timeout: int = 300  # seconds
    batch_size: int = 10
    retry_on_failure: bool = False
    max_retries: int = 2
    stop_on_error: bool = False

    def __post_init__(self):
        """Validate configuration."""
        if self.max_workers < 1:
            raise ValueError(f"max_workers must be >= 1, got {self.max_workers}")
        if self.max_workers > 64:
            raise ValueError(f"max_workers must be <= 64, got {self.max_workers}")
        if self.worker_timeout < 1:
            raise ValueError(f"worker_timeout must be >= 1, got {self.worker_timeout}")
        if self.batch_size < 1:
            raise ValueError(f"batch_size must be >= 1, got {self.batch_size}")
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {self.max_retries}")

    @staticmethod
    def auto_detect_workers() -> int:
        """
        Auto-detect optimal number of workers.

        Returns:
            Recommended worker count
        """
        cpu_count = multiprocessing.cpu_count()
        # Use CPU count for I/O-bound tasks (repository analysis is I/O heavy)
        # Cap at 16 to avoid overwhelming system
        return min(cpu_count, 16)


@dataclass
class ProcessingResult:
    """Result from processing a single repository."""

    item_id: str
    status: ProcessingStatus
    result: Any = None
    error: str | None = None
    error_traceback: str | None = None
    start_time: float = 0.0
    end_time: float = 0.0
    worker_id: int | None = None
    retry_count: int = 0

    @property
    def duration(self) -> float:
        """Duration in seconds."""
        return self.end_time - self.start_time if self.end_time > 0 else 0.0

    @property
    def is_success(self) -> bool:
        """Check if processing was successful."""
        return self.status == ProcessingStatus.SUCCESS

    @property
    def is_failure(self) -> bool:
        """Check if processing failed."""
        return self.status in (ProcessingStatus.FAILED, ProcessingStatus.TIMEOUT)


@dataclass
class AggregatedResults:
    """Aggregated results from parallel processing."""

    total: int
    successful: list[ProcessingResult] = field(default_factory=list)
    failed: list[ProcessingResult] = field(default_factory=list)
    results: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    total_duration: float = 0.0

    @property
    def success_count(self) -> int:
        """Number of successful results."""
        return len(self.successful)

    @property
    def failure_count(self) -> int:
        """Number of failed results."""
        return len(self.failed)

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        return (self.success_count / self.total * 100) if self.total > 0 else 0.0

    @property
    def avg_duration(self) -> float:
        """Average processing duration."""
        if not self.successful:
            return 0.0
        return sum(r.duration for r in self.successful) / len(self.successful)
