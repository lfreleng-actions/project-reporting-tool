# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Request queuing, grouping and deduplication.

Provides the priority queue used to order pending API requests and the
batcher that groups requests into batches, removes duplicates and caches
results keyed by request signature.
"""

import logging
import threading
from collections import deque
from typing import Any

from .models import APIRequest, RequestPriority


logger = logging.getLogger(__name__)


class RequestQueue:
    """Priority queue for API requests."""

    def __init__(self):
        """Initialize request queue."""
        self._queues: dict[RequestPriority, deque[APIRequest]] = {
            priority: deque() for priority in RequestPriority
        }
        self._lock = threading.Lock()

    def enqueue(self, request: APIRequest) -> None:
        """Add request to queue."""
        with self._lock:
            self._queues[request.priority].append(request)

    def dequeue(self) -> APIRequest | None:
        """Get next request from queue (highest priority first)."""
        with self._lock:
            for priority in sorted(RequestPriority, key=lambda p: p.value, reverse=True):
                if self._queues[priority]:
                    request: APIRequest = self._queues[priority].popleft()
                    return request
            return None

    def peek(self) -> APIRequest | None:
        """Peek at next request without removing."""
        with self._lock:
            for priority in sorted(RequestPriority, key=lambda p: p.value, reverse=True):
                if self._queues[priority]:
                    request: APIRequest = self._queues[priority][0]
                    return request
            return None

    def size(self) -> int:
        """Get total queue size."""
        with self._lock:
            return sum(len(q) for q in self._queues.values())

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self.size() == 0

    def clear(self) -> None:
        """Clear all queues."""
        with self._lock:
            for queue in self._queues.values():
                queue.clear()


class RequestBatcher:
    """Request grouping and parallel execution."""

    def __init__(
        self,
        batch_size: int = 10,
        parallel_requests: int = 5,
        deduplicate: bool = True,
    ):
        """
        Initialize request batcher.

        Args:
            batch_size: Number of requests per batch
            parallel_requests: Number of parallel requests
            deduplicate: Remove duplicate requests
        """
        self.batch_size = batch_size
        self.parallel_requests = parallel_requests
        self.deduplicate = deduplicate

        self._request_cache: dict[str, Any] = {}
        self._cache_lock = threading.Lock()

        logger.info(
            f"Request batcher initialized: batch_size={batch_size}, "
            f"parallel={parallel_requests}, deduplicate={deduplicate}"
        )

    def batch_requests(
        self,
        requests: list[APIRequest],
    ) -> list[list[APIRequest]]:
        """
        Group requests into batches.

        Args:
            requests: List of API requests

        Returns:
            List of request batches
        """
        if self.deduplicate:
            requests = self._deduplicate_requests(requests)

        batches = []
        for i in range(0, len(requests), self.batch_size):
            batch = requests[i : i + self.batch_size]
            batches.append(batch)

        return batches

    def _deduplicate_requests(
        self,
        requests: list[APIRequest],
    ) -> list[APIRequest]:
        """Remove duplicate requests."""
        seen_keys = set()
        unique_requests = []

        for request in requests:
            cache_key = request.get_cache_key()
            if cache_key not in seen_keys:
                seen_keys.add(cache_key)
                unique_requests.append(request)

        if len(unique_requests) < len(requests):
            deduped = len(requests) - len(unique_requests)
            logger.debug(f"Deduplicated {deduped} requests")

        return unique_requests

    def get_cached_result(self, request: APIRequest) -> Any | None:
        """Get cached result for request."""
        if not self.deduplicate:
            return None

        cache_key = request.get_cache_key()
        with self._cache_lock:
            return self._request_cache.get(cache_key)

    def cache_result(self, request: APIRequest, result: Any) -> None:
        """Cache request result."""
        if not self.deduplicate:
            return

        cache_key = request.get_cache_key()
        with self._cache_lock:
            self._request_cache[cache_key] = result

    def clear_cache(self) -> None:
        """Clear request cache."""
        with self._cache_lock:
            self._request_cache.clear()
