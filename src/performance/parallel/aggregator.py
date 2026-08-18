# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Thread-safe collection of results produced by parallel workers.

Accumulates per-item processing results under a lock, exposes progress
snapshots and builds the final aggregated result set.
"""

import threading
import time

from .models import AggregatedResults, ProcessingResult


class ResultAggregator:
    """
    Thread-safe result aggregator for collecting results from workers.

    Example:
        >>> aggregator = ResultAggregator(total_items=10)
        >>> aggregator.add_result(ProcessingResult(...))
        >>> results = aggregator.get_results()
    """

    def __init__(self, total_items: int):
        """
        Initialize result aggregator.

        Args:
            total_items: Total number of items to process
        """
        self.total_items = total_items
        self.lock = threading.Lock()
        self.results: list[ProcessingResult] = []
        self.completed_count = 0
        self.start_time = time.perf_counter()

    def add_result(self, result: ProcessingResult):
        """
        Add a result (thread-safe).

        Args:
            result: Processing result to add
        """
        with self.lock:
            self.results.append(result)
            self.completed_count += 1

    def get_progress(self) -> tuple[int, int]:
        """
        Get current progress.

        Returns:
            Tuple of (completed, total)
        """
        with self.lock:
            return (self.completed_count, self.total_items)

    def get_results(self) -> AggregatedResults:
        """
        Get aggregated results.

        Returns:
            AggregatedResults with all data
        """
        with self.lock:
            end_time = time.perf_counter()

            successful = [r for r in self.results if r.is_success]
            failed = [r for r in self.results if r.is_failure]

            results_dict = {r.item_id: r.result for r in successful if r.result is not None}
            errors_dict = {r.item_id: r.error for r in failed if r.error is not None}

            return AggregatedResults(
                total=self.total_items,
                successful=successful,
                failed=failed,
                results=results_dict,
                errors=errors_dict,
                total_duration=end_time - self.start_time,
            )
