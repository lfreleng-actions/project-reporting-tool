# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Configuration management and validation package.

This package provides configuration loading, validation, and management
for the repository reporting system.

Features:
- YAML loading and template/project configuration merging (``loading``)
- JSON Schema-based configuration validation
- Semantic validation (ordering, dependencies, etc.)
- Detailed error messages with suggestions
- Security and performance warnings
- Schema version compatibility checking

Example:
    >>> from lf_releng_project_reporting.config import (
    ...     ConfigValidator,
    ...     validate_config_file,
    ... )
    >>> result = validate_config_file(Path("config/myproject.config"))
    >>> if not result.is_valid:
    ...     for error in result.errors:
    ...         print(error)
"""

from .loading import (
    apply_auto_derivation,
    compute_config_digest,
    deep_merge_dicts,
    load_configuration,
    load_yaml_config,
    save_resolved_config,
    setup_time_windows,
    validate_loaded_config,
    write_config_to_step_summary,
)
from .validator import (
    ConfigValidator,
    ValidationCategory,
    ValidationIssue,
    ValidationLevel,
    ValidationResult,
    print_validation_result,
    validate_config_file,
)


__all__ = [
    "ConfigValidator",
    "ValidationCategory",
    "ValidationIssue",
    "ValidationLevel",
    "ValidationResult",
    "apply_auto_derivation",
    "compute_config_digest",
    "deep_merge_dicts",
    "load_configuration",
    "load_yaml_config",
    "print_validation_result",
    "save_resolved_config",
    "setup_time_windows",
    "validate_config_file",
    "validate_loaded_config",
    "write_config_to_step_summary",
]

__version__ = "1.0.0"
