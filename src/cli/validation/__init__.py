# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Dry Run Validation Module

Comprehensive pre-flight checks for validating configuration and system state
before executing repository analysis.

Phase 9: CLI & UX Improvements
"""

from .models import ValidationResult
from .validator import DryRunValidator, dry_run


__all__ = [
    "ValidationResult",
    "DryRunValidator",
    "dry_run",
]
