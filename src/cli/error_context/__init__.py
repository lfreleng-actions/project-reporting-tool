# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Error Context System

Provides rich contextual information for errors including:
- Recovery hints with step-by-step instructions
- Code examples for common fixes
- Related documentation links
- Auto-detection of common issues

Phase 13, Step 4: Enhanced Error Messages
"""

from .auto_detect import auto_detect_error_context
from .config_detectors import (
    detect_disk_space_error,
    detect_invalid_yaml,
    detect_missing_config,
    detect_missing_repos_path,
    detect_permission_error,
    detect_validation_error,
)
from .models import ErrorContext
from .network_detectors import (
    detect_github_auth_error,
    detect_network_error,
    detect_rate_limit_error,
)


__all__ = [
    "ErrorContext",
    "detect_missing_config",
    "detect_invalid_yaml",
    "detect_missing_repos_path",
    "detect_github_auth_error",
    "detect_rate_limit_error",
    "detect_network_error",
    "detect_permission_error",
    "detect_disk_space_error",
    "detect_validation_error",
    "auto_detect_error_context",
]
