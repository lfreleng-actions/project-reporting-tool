# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Worker pool lifecycle management.

Wraps thread and process pool executors behind a single context-managed
interface for submitting individual tasks or mapping over items.
"""

from collections.abc import Callable
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from typing import Any

from .models import WorkerType


class WorkerPool:
    """
    Worker pool for managing parallel execution.

    Example:
        >>> with WorkerPool(max_workers=4, worker_type=WorkerType.THREAD) as pool:
        ...     results = pool.map(func, items)
    """

    def __init__(
        self,
        max_workers: int = 4,
        worker_type: WorkerType = WorkerType.THREAD,
        worker_timeout: int = 300,
    ):
        """
        Initialize worker pool.

        Args:
            max_workers: Maximum number of workers
            worker_type: Type of workers (thread or process)
            worker_timeout: Timeout per task in seconds
        """
        self.max_workers = max_workers
        self.worker_type = worker_type
        self.worker_timeout = worker_timeout
        self.executor: ThreadPoolExecutor | ProcessPoolExecutor | None = None

    def __enter__(self):
        """Enter context manager."""
        if self.worker_type == WorkerType.THREAD:
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        else:
            self.executor = ProcessPoolExecutor(max_workers=self.max_workers)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if self.executor:
            self.executor.shutdown(wait=True)
        return False

    def submit(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Future[Any]:
        """
        Submit a task to the pool.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Future object
        """
        if not self.executor:
            raise RuntimeError("WorkerPool must be used as context manager")
        return self.executor.submit(func, *args, **kwargs)

    def map(self, func: Callable[..., Any], items: list[Any]) -> list[Any]:
        """
        Map function over items in parallel.

        Args:
            func: Function to apply
            items: Items to process

        Returns:
            List of results
        """
        if not self.executor:
            raise RuntimeError("WorkerPool must be used as context manager")
        return list(self.executor.map(func, items, timeout=self.worker_timeout))
