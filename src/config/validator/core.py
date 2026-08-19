# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Core configuration validator.

Holds ConfigValidator, which loads the bundled JSON schema and applies the
schema, semantic, compatibility, security and performance validation passes
to a configuration dictionary, plus the validate_config_file front door that
reads a YAML configuration from disk and runs it through the validator.
"""

import importlib.util
import json
from pathlib import Path
from typing import Any

from cli.error_helpers import wrap_config_error, wrap_file_error
from cli.errors import ConfigurationError

from .results import ValidationCategory, ValidationResult
from .schema_errors import _SCHEMA_ERROR_FORMATTERS, _extract_quoted


HAS_JSONSCHEMA = importlib.util.find_spec("jsonschema") is not None


class ConfigValidator:
    """Validates configuration against schema and semantic rules."""

    CURRENT_SCHEMA_VERSION = "1.5.0"
    COMPATIBLE_SCHEMA_VERSIONS = ["1.0.0", "1.1.0", "1.2.0", "1.3.0", "1.4.0", "1.5.0"]

    def __init__(self, schema_path: Path | None = None):
        """Initialize validator with optional custom schema.

        Args:
            schema_path: Path to JSON schema file. If None, uses bundled schema.
        """
        if not HAS_JSONSCHEMA:
            raise ConfigurationError(
                "jsonschema package is required for configuration validation",
                suggestion="Install with: pip install jsonschema",
            )

        # Import here after guard to satisfy type checker (possibly unbound)
        from jsonschema import Draft7Validator as _Draft7Validator

        if schema_path is None:
            # schema.json lives in the parent `config` package directory, one
            # level above this module now that `validator` is a package.
            schema_path = Path(__file__).parent.parent / "schema.json"

        self.schema_path = schema_path
        self.schema = self._load_schema()
        self.validator = _Draft7Validator(self.schema)

    def _load_schema(self) -> dict[str, Any]:
        """Load JSON schema from file."""
        if not self.schema_path.exists():
            raise ConfigurationError(
                f"Configuration schema not found: {self.schema_path}",
                suggestion="Ensure schema.json exists in the config module or specify a custom schema path",
            )

        try:
            with open(self.schema_path, encoding="utf-8") as f:
                schema: dict[str, Any] = json.load(f)
                return schema
        except json.JSONDecodeError as e:
            raise wrap_config_error(
                f"Invalid JSON in schema file: {e}",
                config_path=self.schema_path,
                suggestion="Check schema.json for valid JSON syntax",
            ) from e
        except Exception as e:
            raise wrap_file_error(e, self.schema_path, "read") from e

    def validate(self, config: dict[str, Any]) -> ValidationResult:
        """Validate configuration against schema and semantic rules.

        Args:
            config: Configuration dictionary to validate

        Returns:
            ValidationResult with errors, warnings, and info messages
        """
        result = ValidationResult(is_valid=True)

        # 1. JSON Schema validation
        self._validate_schema(config, result)

        # 2. Semantic validation (only if schema is valid)
        if result.is_valid:
            self._validate_semantics(config, result)

        # 3. Compatibility validation
        self._validate_compatibility(config, result)

        # 4. Security and performance checks
        self._validate_security(config, result)
        self._validate_performance(config, result)

        return result

    def _validate_schema(self, config: dict[str, Any], result: ValidationResult) -> None:
        """Validate against JSON schema."""
        errors = sorted(self.validator.iter_errors(config), key=lambda e: e.path)

        for error in errors:
            path = ".".join(str(p) for p in error.path) if error.path else "root"
            message = self._format_schema_error(error)
            suggestion = self._get_schema_error_suggestion(error)

            result.add_error(
                message=message,
                category=ValidationCategory.SCHEMA,
                path=path,
                suggestion=suggestion,
            )

    def _format_schema_error(self, error: Any) -> str:
        """Format JSON schema error message."""
        formatter = _SCHEMA_ERROR_FORMATTERS.get(error.validator)
        if formatter is not None:
            return formatter(error)
        return str(error.message)

    def _get_schema_error_suggestion(self, error: Any) -> str | None:
        """Get helpful suggestion for schema error."""
        if error.validator == "required":
            missing = _extract_quoted(error.message)
            if missing == "schema_version":
                return "Add 'schema_version: \"1.2.0\"' to your configuration"
            elif missing == "project":
                return "Add 'project: your-project-name' to your configuration"
        elif error.validator == "additionalProperties":
            # Find which property is not allowed
            if hasattr(error, "message") and "'" in error.message:
                extra_prop = _extract_quoted(error.message)
                return f"Remove '{extra_prop}' or check for typos in property name"

        return None

    def _validate_semantics(self, config: dict[str, Any], result: ValidationResult) -> None:
        """Validate semantic rules and logical consistency."""

        # Activity thresholds must be ordered correctly
        thresholds = config.get("activity_thresholds", {})
        current = thresholds.get("current_days")
        active = thresholds.get("active_days")

        if current and active and current >= active:
            result.add_error(
                message=f"activity_thresholds: current_days ({current}) must be less than active_days ({active})",
                category=ValidationCategory.SEMANTIC,
                path="activity_thresholds",
                suggestion="Set current_days < active_days (e.g., current=365, active=1095)",
            )

        # Time windows should be ordered
        windows = config.get("time_windows", {})
        if windows:
            self._validate_time_window_ordering(windows, result)

        # Gerrit validation
        gerrit = config.get("gerrit", {})
        if gerrit.get("enabled") and not gerrit.get("host"):
            result.add_error(
                message="Gerrit is enabled but no host specified",
                category=ValidationCategory.SEMANTIC,
                path="gerrit.host",
                suggestion="Set gerrit.host to your Gerrit server hostname",
            )

        # Jenkins validation
        jenkins = config.get("jenkins", {})
        if jenkins.get("enabled") and not jenkins.get("host"):
            result.add_error(
                message="Jenkins is enabled but no host specified",
                category=ValidationCategory.SEMANTIC,
                path="jenkins.host",
                suggestion="Set jenkins.host to your Jenkins server hostname",
            )

        # GitHub API validation
        extensions = config.get("extensions", {})
        github = extensions.get("github_api", {})
        if github.get("enabled") and not github.get("token"):
            result.add_warning(
                message="GitHub API is enabled but no token specified",
                category=ValidationCategory.SEMANTIC,
                path="extensions.github_api.token",
                suggestion="Set github_api.token or use GITHUB_TOKEN environment variable (or specify --github-token-env for custom variable)",
            )

    def _validate_time_window_ordering(
        self, windows: dict[str, int], result: ValidationResult
    ) -> None:
        """Validate that time windows are in ascending order."""
        expected_order = ["last_30_days", "last_90_days", "last_365_days", "last_3_years"]
        values: list[int] = [
            windows[key]
            for key in expected_order
            if key in windows and windows.get(key) is not None
        ]

        if values and values != sorted(values):
            result.add_warning(
                message="Time windows are not in ascending order",
                category=ValidationCategory.SEMANTIC,
                path="time_windows",
                suggestion="Ensure last_30_days < last_90_days < last_365_days < last_3_years",
            )

    def _validate_compatibility(self, config: dict[str, Any], result: ValidationResult) -> None:
        """Validate schema version compatibility."""
        schema_version = config.get("schema_version")

        if not schema_version:
            result.add_warning(
                message="No schema_version specified in configuration",
                category=ValidationCategory.COMPATIBILITY,
                path="schema_version",
                suggestion=f"Add 'schema_version: \"{self.CURRENT_SCHEMA_VERSION}\"'",
            )
            return

        if schema_version not in self.COMPATIBLE_SCHEMA_VERSIONS:
            result.add_error(
                message=f"Unsupported schema version: {schema_version}",
                category=ValidationCategory.COMPATIBILITY,
                path="schema_version",
                suggestion=f"Use one of: {', '.join(self.COMPATIBLE_SCHEMA_VERSIONS)}",
            )
        elif schema_version != self.CURRENT_SCHEMA_VERSION:
            result.add_info(
                message=f"Using compatible but not current schema version (current: {self.CURRENT_SCHEMA_VERSION})",
                category=ValidationCategory.COMPATIBILITY,
                path="schema_version",
            )

    def _validate_security(self, config: dict[str, Any], result: ValidationResult) -> None:
        """Check for potential security issues."""

        extensions = config.get("extensions", {})
        github = extensions.get("github_api", {})
        if github.get("token") and len(github.get("token", "")) > 10:
            result.add_warning(
                message="GitHub token appears to be hardcoded in configuration",
                category=ValidationCategory.SECURITY,
                path="extensions.github_api.token",
                suggestion="Use environment variable GITHUB_TOKEN instead (or specify --github-token-env for custom variable)",
            )

        privacy = config.get("privacy", {})
        if not privacy.get("mask_emails") and not privacy.get("anonymize_authors"):
            result.add_info(
                message="Email masking and author anonymization are both disabled",
                category=ValidationCategory.SECURITY,
                path="privacy",
                suggestion="Consider enabling privacy.mask_emails or privacy.anonymize_authors for public reports",
            )

    def _validate_performance(self, config: dict[str, Any], result: ValidationResult) -> None:
        """Check for performance-impacting settings."""

        performance = config.get("performance", {})
        max_workers = performance.get("max_workers", 8)

        if max_workers > 16:
            result.add_warning(
                message=f"High worker count ({max_workers}) may cause resource contention",
                category=ValidationCategory.PERFORMANCE,
                path="performance.max_workers",
                suggestion="Consider using 4-16 workers for optimal performance",
            )

        html = config.get("html_tables", {})
        entries_per_page = html.get("entries_per_page", 20)

        if entries_per_page > 200:
            result.add_warning(
                message=f"Large entries_per_page ({entries_per_page}) may slow down browser",
                category=ValidationCategory.PERFORMANCE,
                path="html_tables.entries_per_page",
                suggestion="Use 20-100 entries per page for better browser performance",
            )


def validate_config_file(config_path: Path) -> ValidationResult:
    """Validate a configuration file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        ValidationResult with validation status and issues

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is not valid YAML
    """
    import yaml

    if not config_path.exists():
        raise ConfigurationError(
            f"Configuration file not found: {config_path}",
            suggestion="Create a config.yaml file or specify a different path with --config",
        )

    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise wrap_config_error(
            f"Invalid YAML syntax: {e}",
            config_path=config_path,
            suggestion="Check YAML syntax - ensure proper indentation, no tabs, and valid structure",
        ) from e
    except Exception as e:
        raise wrap_file_error(e, config_path, "read") from e

    if config is None:
        config = {}

    validator = ConfigValidator()
    result = validator.validate(config)
    return result
