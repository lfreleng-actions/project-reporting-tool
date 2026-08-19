# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Parallel repository processing coordination.

Drives the worker pool, dispatches per-repository work with optional
retry and profiling, aggregates results, and exposes the simple
``parallel_map`` convenience wrapper.
"""

import threading
import time
import traceback
from collections.abc import Callable
from concurrent.futures import Future, as_completed
from typing import Any

from .aggregator import ResultAggregator
from .models import AggregatedResults, ProcessingResult, ProcessingStatus, WorkerConfig
from .worker_pool import WorkerPool


class ParallelRepositoryProcessor:
    """
    Main coordinator for parallel repository processing.

    This class manages the parallel execution of repository analysis,
    handles result aggregation, error management, and progress tracking.

    Example:
        >>> processor = ParallelRepositoryProcessor(max_workers=4)
        >>>
        >>> def analyze(repo_path):
        ...     return {"path": repo_path, "files": 100}
        >>>
        >>> results = processor.process_repositories(
        ...     repositories=['repo1', 'repo2', 'repo3'],
        ...     processor_func=analyze
        ... )
        >>>
        >>> print(f"Success: {results.success_count}/{results.total}")
    """

    def __init__(
        self,
        max_workers: int | None = None,
        config: WorkerConfig | None = None,
        profiler: Any | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ):
        """
        Initialize parallel processor.

        Args:
            max_workers: Maximum number of workers (auto-detect if None)
            config: Worker configuration (creates default if None)
            profiler: Optional performance profiler
            progress_callback: Optional callback for progress updates (completed, total)
        """
        if config:
            self.config = config
        else:
            workers = max_workers if max_workers else WorkerConfig.auto_detect_workers()
            self.config = WorkerConfig(max_workers=workers)

        self.profiler = profiler
        self.progress_callback = progress_callback
        self._worker_counter = 0
        self._lock = threading.Lock()

    def _get_worker_id(self) -> int:
        """Get next worker ID (thread-safe)."""
        with self._lock:
            self._worker_counter += 1
            return self._worker_counter

    def _process_item(
        self, item: Any, processor_func: Callable[..., Any], worker_id: int, retry_count: int = 0
    ) -> ProcessingResult:
        """
        Process a single item.

        Args:
            item: Item to process
            processor_func: Function to process the item
            worker_id: ID of the worker
            retry_count: Current retry count

        Returns:
            ProcessingResult
        """
        item_id = str(item) if not isinstance(item, dict) else item.get("id", str(item))

        result = ProcessingResult(
            item_id=item_id,
            status=ProcessingStatus.RUNNING,
            start_time=time.perf_counter(),
            worker_id=worker_id,
            retry_count=retry_count,
        )

        try:
            # Track with profiler if available
            if self.profiler:
                with self.profiler.track_operation(
                    f"process_item_{item_id}",
                    category="analysis",
                    metadata={"worker_id": worker_id, "retry": retry_count},
                ):
                    output = processor_func(item)
            else:
                output = processor_func(item)

            result.result = output
            result.status = ProcessingStatus.SUCCESS

        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.error = str(e)
            result.error_traceback = traceback.format_exc()

            # Retry logic
            if self.config.retry_on_failure and retry_count < self.config.max_retries:
                # Recursive retry
                return self._process_item(item, processor_func, worker_id, retry_count + 1)

        finally:
            result.end_time = time.perf_counter()

        return result

    def _batch_items(self, items: list[Any]) -> list[list[Any]]:
        """
        Batch items for processing.

        Args:
            items: Items to batch

        Returns:
            List of batches
        """
        batch_size = self.config.batch_size
        return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]

    def process_repositories(
        self,
        repositories: list[Any],
        processor_func: Callable[[Any], Any],
        batch_mode: bool = False,  # noqa: ARG002
    ) -> AggregatedResults:
        """
        Process multiple repositories in parallel.

        Args:
            repositories: List of repositories to process
            processor_func: Function to process each repository
            batch_mode: If True, process in batches

        Returns:
            AggregatedResults with all processing results

        Example:
            >>> def analyze_repo(repo_path):
            ...     return {"path": repo_path, "size": 1000}
            >>>
            >>> processor = ParallelRepositoryProcessor(max_workers=4)
            >>> results = processor.process_repositories(
            ...     repositories=['repo1', 'repo2', 'repo3'],
            ...     processor_func=analyze_repo
            ... )
        """
        if not repositories:
            return AggregatedResults(total=0)

        aggregator = ResultAggregator(total_items=len(repositories))

        # Track overall operation
        if self.profiler:
            self.profiler.memory_snapshot("before_parallel_processing")

        with WorkerPool(
            max_workers=self.config.max_workers,
            worker_type=self.config.worker_type,
            worker_timeout=self.config.worker_timeout,
        ) as pool:
            # Submit all tasks
            futures: dict[Future[Any], tuple[Any, int]] = {}

            for item in repositories:
                worker_id = self._get_worker_id()
                future = pool.submit(self._process_item, item, processor_func, worker_id)
                futures[future] = (item, worker_id)

            # Collect results as they complete
            for future in as_completed(futures, timeout=self.config.worker_timeout):
                item, worker_id = futures[future]

                try:
                    result = future.result(timeout=1.0)
                    aggregator.add_result(result)

                    # Progress callback
                    if self.progress_callback:
                        completed, total = aggregator.get_progress()
                        self.progress_callback(completed, total)

                    # Stop on error if configured
                    if self.config.stop_on_error and result.is_failure:
                        # Cancel remaining futures
                        for f in futures:
                            if not f.done():
                                f.cancel()
                        break

                except TimeoutError:
                    # Task timed out
                    item_id = str(item)
                    timeout_result = ProcessingResult(
                        item_id=item_id,
                        status=ProcessingStatus.TIMEOUT,
                        error=f"Task timed out after {self.config.worker_timeout}s",
                        worker_id=worker_id,
                    )
                    aggregator.add_result(timeout_result)

                except Exception as e:
                    # Unexpected error
                    item_id = str(item)
                    error_result = ProcessingResult(
                        item_id=item_id,
                        status=ProcessingStatus.FAILED,
                        error=f"Unexpected error: {str(e)}",
                        error_traceback=traceback.format_exc(),
                        worker_id=worker_id,
                    )
                    aggregator.add_result(error_result)

        # Track memory after processing
        if self.profiler:
            self.profiler.memory_snapshot("after_parallel_processing")

        return aggregator.get_results()

    def get_worker_utilization(self, results: AggregatedResults) -> dict[str, Any]:
        """
        Calculate worker utilization statistics.

        Args:
            results: Aggregated results

        Returns:
            Dictionary with utilization stats
        """
        if not results.successful:
            return {
                "total_workers": self.config.max_workers,
                "utilized_workers": 0,
                "utilization_rate": 0.0,
                "avg_items_per_worker": 0.0,
            }

        # Count unique workers
        worker_ids = set()
        worker_counts: dict[int, int] = {}

        for result in results.successful + results.failed:
            if result.worker_id:
                worker_ids.add(result.worker_id)
                worker_counts[result.worker_id] = worker_counts.get(result.worker_id, 0) + 1

        utilized_workers = len(worker_ids)

        return {
            "total_workers": self.config.max_workers,
            "utilized_workers": utilized_workers,
            "utilization_rate": (utilized_workers / self.config.max_workers * 100),
            "avg_items_per_worker": results.total / utilized_workers if utilized_workers > 0 else 0,
            "items_per_worker": worker_counts,
        }


# Convenience function for simple parallel mapping
def parallel_map(
    func: Callable[..., Any], items: list[Any], max_workers: int | None = None, timeout: int = 300
) -> list[Any]:
    """
    Simple parallel map function.

    Args:
        func: Function to apply
        items: Items to process
        max_workers: Number of workers (auto-detect if None)
        timeout: Timeout per item in seconds

    Returns:
        List of results in same order as items

    Example:
        >>> def square(x):
        ...     return x * x
        >>> results = parallel_map(square, [1, 2, 3, 4], max_workers=2)
        >>> print(results)  # [1, 4, 9, 16]
    """
    workers = max_workers if max_workers else WorkerConfig.auto_detect_workers()

    with WorkerPool(max_workers=workers, worker_timeout=timeout) as pool:
        return list(pool.map(func, items))
