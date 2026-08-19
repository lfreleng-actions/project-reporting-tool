# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Git operation optimization module for the Repository Reporting System.

This module provides utilities for optimizing git operations including shallow
clones, reference repositories, batch operations, and efficient git configuration.

Classes:
    GitOptimizer: Main coordinator for git optimizations
    ReferenceRepository: Manage reference repositories for faster clones
    ShallowCloneStrategy: Strategy for determining shallow clone parameters
    GitOperationCache: Cache git operation results
    GitConfig: Git configuration optimization

Example:
    >>> from src.performance import GitOptimizer
    >>>
    >>> optimizer = GitOptimizer(use_shallow=True, use_references=True)
    >>> repo_path = optimizer.clone_optimized(
    ...     url="https://github.com/user/repo.git",
    ...     destination="./repos/repo"
    ... )
"""

from .models import CloneStrategy, GitConfig, GitOperationResult, GitOperationType
from .optimizer import GitOptimizer
from .strategies import ReferenceRepository, ShallowCloneStrategy
from .utils import estimate_clone_time, optimize_git_config_global


__all__ = [
    "CloneStrategy",
    "GitConfig",
    "GitOperationResult",
    "GitOperationType",
    "GitOptimizer",
    "ReferenceRepository",
    "ShallowCloneStrategy",
    "estimate_clone_time",
    "optimize_git_config_global",
]
