# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
CLI Package

Command-line interface utilities for the repository reporting system.

This package provides:
- Standardized exit codes
- Enhanced error classes with suggestions
- Argument parsing with improved help text
- Feature discovery
- Progress indicators

Phase 9: CLI & UX Improvements
"""

from .arguments import (
    OutputFormat,
    VerbosityLevel,
    create_argument_parser,
    get_log_level,
    get_output_formats,
    get_verbosity_level,
    is_special_mode,
    is_wizard_mode,
    parse_arguments,
    should_generate_zip,
    validate_arguments,
)
from .errors import (
    APIError,
    CLIError,
    ConfigurationError,
    DiskSpaceError,
    InvalidArgumentError,
    NetworkError,
    PermissionError,
    ValidationError,
    format_validation_errors,
    suggest_common_fixes,
)
from .exit_codes import (
    EXIT_API_ERROR,
    EXIT_CONFIG_ERROR,
    EXIT_DISK_FULL,
    EXIT_INVALID_ARGS,
    EXIT_PARTIAL_SUCCESS,
    EXIT_PERMISSION_DENIED,
    EXIT_PROCESSING_ERROR,
    EXIT_SUCCESS,
    ExitCode,
    format_exit_message,
    get_exit_code_description,
    should_retry,
)
from .features import (
    AVAILABLE_FEATURES,
    format_feature_list_compact,
    get_all_categories,
    get_category_count,
    get_feature_category,
    get_feature_count,
    get_feature_description,
    get_features_by_category,
    get_features_in_category,
    list_all_features,
    search_features,
)
from .metrics import (
    APIStatistics,
    MetricsCollector,
    OperationMetrics,
    ResourceUsage,
    TimingMetric,
    format_bytes,
    format_duration,
    format_percentage,
    get_metrics_collector,
    print_debug_metrics,
    print_performance_summary,
    record_api_call,
    reset_metrics_collector,
    time_operation,
)
from .progress import (
    TQDM_AVAILABLE,
    OperationFeedback,
    ProgressIndicator,
    estimate_time_remaining,
    format_count,
    progress_bar,
)
from .validation import (
    DryRunValidator,
    ValidationResult,
    dry_run,
)
from .wizard import (
    FULL_TEMPLATE,
    MINIMAL_TEMPLATE,
    STANDARD_TEMPLATE,
    ConfigurationWizard,
    create_config_from_template,
    run_wizard,
)


__all__ = [
    # Exit codes
    "ExitCode",
    "get_exit_code_description",
    "format_exit_message",
    "should_retry",
    "EXIT_SUCCESS",
    "EXIT_CONFIG_ERROR",
    "EXIT_API_ERROR",
    "EXIT_PROCESSING_ERROR",
    "EXIT_PARTIAL_SUCCESS",
    "EXIT_INVALID_ARGS",
    "EXIT_PERMISSION_DENIED",
    "EXIT_DISK_FULL",
    # Errors
    "CLIError",
    "ConfigurationError",
    "InvalidArgumentError",
    "APIError",
    "PermissionError",
    "DiskSpaceError",
    "ValidationError",
    "NetworkError",
    "format_validation_errors",
    "suggest_common_fixes",
    # Arguments
    "create_argument_parser",
    "parse_arguments",
    "validate_arguments",
    "get_verbosity_level",
    "get_log_level",
    "get_output_formats",
    "should_generate_zip",
    "is_special_mode",
    "is_wizard_mode",
    "OutputFormat",
    "VerbosityLevel",
    # Features
    "AVAILABLE_FEATURES",
    "get_features_by_category",
    "list_all_features",
    "get_feature_description",
    "get_feature_category",
    "get_features_in_category",
    "get_all_categories",
    "search_features",
    "format_feature_list_compact",
    "get_feature_count",
    "get_category_count",
    # Validation
    "ValidationResult",
    "DryRunValidator",
    "dry_run",
    # Progress
    "ProgressIndicator",
    "OperationFeedback",
    "progress_bar",
    "estimate_time_remaining",
    "format_count",
    "TQDM_AVAILABLE",
    # Wizard
    "run_wizard",
    "create_config_from_template",
    "ConfigurationWizard",
    "MINIMAL_TEMPLATE",
    "STANDARD_TEMPLATE",
    "FULL_TEMPLATE",
    # Metrics
    "MetricsCollector",
    "get_metrics_collector",
    "reset_metrics_collector",
    "time_operation",
    "record_api_call",
    "print_performance_summary",
    "print_debug_metrics",
    "format_duration",
    "format_bytes",
    "format_percentage",
    "TimingMetric",
    "APIStatistics",
    "ResourceUsage",
    "OperationMetrics",
]

__version__ = "1.0.0"
