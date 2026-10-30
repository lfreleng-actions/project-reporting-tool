# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Data model definitions for git operation optimization.

Contains the clone strategy and git operation type enums, the git
configuration dataclass with its validation, and the record describing
the outcome of a single git operation.
"""

from dataclasses import dataclass
from enum import Enum


class CloneStrategy(Enum):
    """Strategy for cloning repositories."""

    FULL = "full"
    SHALLOW = "shallow"
    REFERENCE = "reference"
    SHALLOW_REFERENCE = "shallow_reference"


class GitOperationType(Enum):
    """Types of git operations."""

    CLONE = "clone"
    FETCH = "fetch"
    LOG = "log"
    DIFF = "diff"
    STATUS = "status"


@dataclass
class GitConfig:
    """
    Configuration for git optimization.

    Attributes:
        shallow_clone: Enable shallow clones
        shallow_depth: Depth for shallow clones
        use_reference_repos: Use reference repositories
        reference_dir: Directory for reference repositories
        parallel_fetch: Number of parallel fetch operations
        compression: Git compression level (0-9)
        http_post_buffer: HTTP post buffer size in bytes
    """

    shallow_clone: bool = True
    shallow_depth: int = 1
    use_reference_repos: bool = True
    reference_dir: str = "./.git-references"
    parallel_fetch: int = 4
    compression: int = 9
    http_post_buffer: int = 524288000  # 500MB

    def validate(self):
        """Validate configuration."""
        if self.shallow_depth < 1:
            raise ValueError(f"shallow_depth must be >= 1, got {self.shallow_depth}")
        if self.parallel_fetch < 1:
            raise ValueError(f"parallel_fetch must be >= 1, got {self.parallel_fetch}")
        if not 0 <= self.compression <= 9:
            raise ValueError(f"compression must be 0-9, got {self.compression}")
        if self.http_post_buffer < 1024:
            raise ValueError(f"http_post_buffer must be >= 1024, got {self.http_post_buffer}")


@dataclass
class GitOperationResult:
    """Result from a git operation."""

    operation: GitOperationType
    success: bool
    duration: float
    output: str = ""
    error: str = ""
    strategy: CloneStrategy | None = None

    @property
    def is_success(self) -> bool:
        """Check if operation was successful."""
        return self.success

    @property
    def is_failure(self) -> bool:
        """Check if operation failed."""
        return not self.success
