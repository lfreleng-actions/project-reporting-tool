# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Error taxonomy enumerations and their static lookup tables.

Holds the category, severity and detailed type enumerations along with the
mappings that derive a category and a default severity from an error type.
"""

from enum import Enum


class ErrorCategory(Enum):
    """High-level error categories."""

    NETWORK = "network"
    API = "api"
    GIT = "git"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    DATA = "data"
    RENDERING = "rendering"
    SYSTEM = "system"


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorType(Enum):
    """
    Detailed error types organized by category.

    Extends the API error types to cover all system operations.
    """

    # Network errors
    NETWORK_TIMEOUT = "network_timeout"
    NETWORK_CONNECTION = "network_connection"
    NETWORK_DNS = "network_dns"

    # API errors (from API module)
    API_HTTP_CLIENT = "api_http_client"  # 4xx errors
    API_HTTP_SERVER = "api_http_server"  # 5xx errors
    API_RATE_LIMIT = "api_rate_limit"
    API_AUTHENTICATION = "api_authentication"
    API_AUTHORIZATION = "api_authorization"
    API_NOT_FOUND = "api_not_found"
    API_PARSE = "api_parse"
    API_TIMEOUT = "api_timeout"
    API_UNKNOWN = "api_unknown"

    # Git errors
    GIT_NOT_FOUND = "git_not_found"
    GIT_COMMAND_FAILED = "git_command_failed"
    GIT_PARSE_ERROR = "git_parse_error"
    GIT_INVALID_REPO = "git_invalid_repo"
    GIT_CLONE_FAILED = "git_clone_failed"
    GIT_CHECKOUT_FAILED = "git_checkout_failed"

    # Validation errors
    VALIDATION_DOMAIN_MODEL = "validation_domain_model"
    VALIDATION_SCHEMA = "validation_schema"
    VALIDATION_CONSTRAINT = "validation_constraint"
    VALIDATION_TYPE = "validation_type"
    VALIDATION_REQUIRED_FIELD = "validation_required_field"

    # Configuration errors
    CONFIG_MISSING = "config_missing"
    CONFIG_INVALID = "config_invalid"
    CONFIG_PARSE = "config_parse"
    CONFIG_SCHEMA = "config_schema"

    # Data errors
    DATA_MISSING = "data_missing"
    DATA_CORRUPT = "data_corrupt"
    DATA_INCONSISTENT = "data_inconsistent"
    DATA_CONVERSION = "data_conversion"

    RENDER_TEMPLATE = "render_template"
    RENDER_FORMAT = "render_format"
    RENDER_OUTPUT = "render_output"

    # System errors
    SYSTEM_IO = "system_io"
    SYSTEM_PERMISSION = "system_permission"
    SYSTEM_RESOURCE = "system_resource"
    SYSTEM_UNKNOWN = "system_unknown"


# Mapping of error types to categories
ERROR_TYPE_CATEGORY_MAP: dict[ErrorType, ErrorCategory] = {
    # Network
    ErrorType.NETWORK_TIMEOUT: ErrorCategory.NETWORK,
    ErrorType.NETWORK_CONNECTION: ErrorCategory.NETWORK,
    ErrorType.NETWORK_DNS: ErrorCategory.NETWORK,
    # API
    ErrorType.API_HTTP_CLIENT: ErrorCategory.API,
    ErrorType.API_HTTP_SERVER: ErrorCategory.API,
    ErrorType.API_RATE_LIMIT: ErrorCategory.API,
    ErrorType.API_AUTHENTICATION: ErrorCategory.API,
    ErrorType.API_AUTHORIZATION: ErrorCategory.API,
    ErrorType.API_NOT_FOUND: ErrorCategory.API,
    ErrorType.API_PARSE: ErrorCategory.API,
    ErrorType.API_TIMEOUT: ErrorCategory.API,
    ErrorType.API_UNKNOWN: ErrorCategory.API,
    # Git
    ErrorType.GIT_NOT_FOUND: ErrorCategory.GIT,
    ErrorType.GIT_COMMAND_FAILED: ErrorCategory.GIT,
    ErrorType.GIT_PARSE_ERROR: ErrorCategory.GIT,
    ErrorType.GIT_INVALID_REPO: ErrorCategory.GIT,
    ErrorType.GIT_CLONE_FAILED: ErrorCategory.GIT,
    ErrorType.GIT_CHECKOUT_FAILED: ErrorCategory.GIT,
    # Validation
    ErrorType.VALIDATION_DOMAIN_MODEL: ErrorCategory.VALIDATION,
    ErrorType.VALIDATION_SCHEMA: ErrorCategory.VALIDATION,
    ErrorType.VALIDATION_CONSTRAINT: ErrorCategory.VALIDATION,
    ErrorType.VALIDATION_TYPE: ErrorCategory.VALIDATION,
    ErrorType.VALIDATION_REQUIRED_FIELD: ErrorCategory.VALIDATION,
    # Configuration
    ErrorType.CONFIG_MISSING: ErrorCategory.CONFIGURATION,
    ErrorType.CONFIG_INVALID: ErrorCategory.CONFIGURATION,
    ErrorType.CONFIG_PARSE: ErrorCategory.CONFIGURATION,
    ErrorType.CONFIG_SCHEMA: ErrorCategory.CONFIGURATION,
    # Data
    ErrorType.DATA_MISSING: ErrorCategory.DATA,
    ErrorType.DATA_CORRUPT: ErrorCategory.DATA,
    ErrorType.DATA_INCONSISTENT: ErrorCategory.DATA,
    ErrorType.DATA_CONVERSION: ErrorCategory.DATA,
    ErrorType.RENDER_TEMPLATE: ErrorCategory.RENDERING,
    ErrorType.RENDER_FORMAT: ErrorCategory.RENDERING,
    ErrorType.RENDER_OUTPUT: ErrorCategory.RENDERING,
    # System
    ErrorType.SYSTEM_IO: ErrorCategory.SYSTEM,
    ErrorType.SYSTEM_PERMISSION: ErrorCategory.SYSTEM,
    ErrorType.SYSTEM_RESOURCE: ErrorCategory.SYSTEM,
    ErrorType.SYSTEM_UNKNOWN: ErrorCategory.SYSTEM,
}


# Mapping of error types to default severity
ERROR_TYPE_SEVERITY_MAP: dict[ErrorType, ErrorSeverity] = {
    # Network - generally medium severity
    ErrorType.NETWORK_TIMEOUT: ErrorSeverity.MEDIUM,
    ErrorType.NETWORK_CONNECTION: ErrorSeverity.MEDIUM,
    ErrorType.NETWORK_DNS: ErrorSeverity.MEDIUM,
    # API - varies by type
    ErrorType.API_HTTP_CLIENT: ErrorSeverity.LOW,
    ErrorType.API_HTTP_SERVER: ErrorSeverity.MEDIUM,
    ErrorType.API_RATE_LIMIT: ErrorSeverity.LOW,
    ErrorType.API_AUTHENTICATION: ErrorSeverity.HIGH,
    ErrorType.API_AUTHORIZATION: ErrorSeverity.HIGH,
    ErrorType.API_NOT_FOUND: ErrorSeverity.LOW,
    ErrorType.API_PARSE: ErrorSeverity.MEDIUM,
    ErrorType.API_TIMEOUT: ErrorSeverity.MEDIUM,
    ErrorType.API_UNKNOWN: ErrorSeverity.MEDIUM,
    # Git - generally high severity for repo access
    ErrorType.GIT_NOT_FOUND: ErrorSeverity.HIGH,
    ErrorType.GIT_COMMAND_FAILED: ErrorSeverity.MEDIUM,
    ErrorType.GIT_PARSE_ERROR: ErrorSeverity.MEDIUM,
    ErrorType.GIT_INVALID_REPO: ErrorSeverity.HIGH,
    ErrorType.GIT_CLONE_FAILED: ErrorSeverity.HIGH,
    ErrorType.GIT_CHECKOUT_FAILED: ErrorSeverity.MEDIUM,
    # Validation - medium severity (data quality issue)
    ErrorType.VALIDATION_DOMAIN_MODEL: ErrorSeverity.MEDIUM,
    ErrorType.VALIDATION_SCHEMA: ErrorSeverity.MEDIUM,
    ErrorType.VALIDATION_CONSTRAINT: ErrorSeverity.MEDIUM,
    ErrorType.VALIDATION_TYPE: ErrorSeverity.MEDIUM,
    ErrorType.VALIDATION_REQUIRED_FIELD: ErrorSeverity.MEDIUM,
    # Configuration - critical (blocks execution)
    ErrorType.CONFIG_MISSING: ErrorSeverity.CRITICAL,
    ErrorType.CONFIG_INVALID: ErrorSeverity.CRITICAL,
    ErrorType.CONFIG_PARSE: ErrorSeverity.CRITICAL,
    ErrorType.CONFIG_SCHEMA: ErrorSeverity.CRITICAL,
    # Data - varies by impact
    ErrorType.DATA_MISSING: ErrorSeverity.MEDIUM,
    ErrorType.DATA_CORRUPT: ErrorSeverity.HIGH,
    ErrorType.DATA_INCONSISTENT: ErrorSeverity.MEDIUM,
    ErrorType.DATA_CONVERSION: ErrorSeverity.MEDIUM,
    # Rendering - low to medium (report generation)
    ErrorType.RENDER_TEMPLATE: ErrorSeverity.MEDIUM,
    ErrorType.RENDER_FORMAT: ErrorSeverity.LOW,
    ErrorType.RENDER_OUTPUT: ErrorSeverity.HIGH,
    # System - critical (environment issue)
    ErrorType.SYSTEM_IO: ErrorSeverity.HIGH,
    ErrorType.SYSTEM_PERMISSION: ErrorSeverity.CRITICAL,
    ErrorType.SYSTEM_RESOURCE: ErrorSeverity.CRITICAL,
    ErrorType.SYSTEM_UNKNOWN: ErrorSeverity.MEDIUM,
}
