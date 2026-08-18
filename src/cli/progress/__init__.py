# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Progress Indicators Module

Provides progress bars and operation feedback for long-running operations.
Supports both tqdm-based progress bars and simple text-based indicators.

Phase 9: CLI & UX Improvements
"""

from .bars import TQDM_AVAILABLE, ProgressIndicator, progress_bar
from .feedback import OperationFeedback
from .formatting import estimate_time_remaining, format_count


__all__ = [
    "ProgressIndicator",
    "OperationFeedback",
    "progress_bar",
    "estimate_time_remaining",
    "format_count",
    "TQDM_AVAILABLE",
]
