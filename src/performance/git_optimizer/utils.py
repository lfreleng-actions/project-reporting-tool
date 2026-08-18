# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Standalone git optimization helpers.

Provides global git configuration tuning and clone time estimation for
callers that do not need a full GitOptimizer instance.
"""

import contextlib
import subprocess

from .models import CloneStrategy


# Utility functions


def optimize_git_config_global():
    """
    Apply optimized git configuration globally.

    This sets system-wide git config for better performance.
    """
    configs = {
        "fetch.parallel": "4",
        "core.compression": "9",
        "http.postBuffer": "524288000",
        "core.preloadindex": "true",
        "core.fscache": "true",
        "gc.auto": "256",
    }

    for key, value in configs.items():
        with contextlib.suppress(Exception):
            subprocess.run(
                ["git", "config", "--global", key, value],
                check=False,
                capture_output=True,
                timeout=5,
            )


def estimate_clone_time(repo_size_mb: float, strategy: CloneStrategy) -> float:
    """
    Estimate clone time based on repository size and strategy.

    Args:
        repo_size_mb: Repository size in megabytes
        strategy: Clone strategy

    Returns:
        Estimated time in seconds
    """
    # Base rate: MB per second (conservative estimate)
    base_rate = 5.0

    # Strategy multipliers
    multipliers = {
        CloneStrategy.FULL: 1.0,
        CloneStrategy.SHALLOW: 0.3,
        CloneStrategy.REFERENCE: 0.5,
        CloneStrategy.SHALLOW_REFERENCE: 0.2,
    }

    multiplier = multipliers.get(strategy, 1.0)

    return (repo_size_mb / base_rate) * multiplier
