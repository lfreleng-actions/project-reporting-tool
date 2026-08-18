# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Parallel repository processing module for the Repository Reporting System.

This module provides utilities for processing multiple repositories in parallel
using a worker pool architecture. It handles result aggregation, error management,
and progress tracking across workers.

Classes:
    ParallelRepositoryProcessor: Main coordinator for parallel processing
    WorkerPool: Worker lifecycle management
    ResultAggregator: Thread-safe result collection
    WorkerConfig: Configuration for parallel processing
    ProcessingResult: Result from processing a repository

Example:
    >>> from src.performance import ParallelRepositoryProcessor
    >>>
    >>> processor = ParallelRepositoryProcessor(max_workers=4)
    >>> repos = ['repo1', 'repo2', 'repo3']
    >>> results = processor.process_repositories(repos, analyze_function)
    >>> print(f"Processed {len(results.successful)} repositories")
"""

from .aggregator import ResultAggregator
from .models import (
    AggregatedResults,
    ProcessingResult,
    ProcessingStatus,
    WorkerConfig,
    WorkerType,
)
from .processor import ParallelRepositoryProcessor, parallel_map
from .worker_pool import WorkerPool


__all__ = [
    "AggregatedResults",
    "ParallelRepositoryProcessor",
    "ProcessingResult",
    "ProcessingStatus",
    "ResultAggregator",
    "WorkerConfig",
    "WorkerPool",
    "WorkerType",
    "parallel_map",
]
