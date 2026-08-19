# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Dry-run validator orchestration and formatted result reporting."""

# This module renders dry-run validation results to the terminal; print() is
# the intended output sink here, not leftover debugging.
# aislop-ignore-file python-print-debug -- intentional user-facing CLI output

import logging
from typing import Any

from .checks import _ValidationChecks
from .models import ValidationResult


class DryRunValidator(_ValidationChecks):
    """
    Comprehensive validation for dry run mode.

    Performs pre-flight checks including:
    - Configuration schema and semantic validation
    - API connectivity and credentials
    - Filesystem permissions and disk space
    - Required tools and dependencies

    Example:
        >>> validator = DryRunValidator(config, logger)
        >>> success, results = validator.validate_all()
        >>> if not success:
        ...     validator.print_results(results)
    """

    def __init__(self, config: dict[str, Any], logger: logging.Logger | None = None):
        """
        Initialize validator.

        Args:
            config: Configuration dictionary
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    def validate_all(self, skip_network: bool = False) -> tuple[bool, list[ValidationResult]]:
        """
        Run all validation checks.

        Args:
            skip_network: Skip network connectivity checks

        Returns:
            Tuple of (success: bool, results: list[ValidationResult])
        """
        results = []

        # Configuration validation
        results.append(self._validate_config_structure())
        results.append(self._validate_required_fields())
        results.append(self._validate_project_name())
        results.append(self._validate_repos_path())

        # API validation
        results.append(self._validate_api_credentials())

        if not skip_network:
            results.append(self._validate_network_connectivity())
            results.append(self._validate_api_endpoints())

        # Filesystem validation
        results.append(self._validate_output_directory())
        results.append(self._validate_disk_space())
        results.append(self._validate_cache_directory())

        # System validation
        results.append(self._validate_git_available())
        results.append(self._validate_python_version())

        # Determine overall success
        has_errors = any(not r.passed and r.severity == "error" for r in results)
        success = not has_errors

        return success, results

    def print_results(self, results: list[ValidationResult]) -> None:
        """
        Print validation results in formatted output.

        Args:
            results: List of validation results
        """
        print("\n" + "=" * 70)
        print("🔍 DRY RUN VALIDATION RESULTS")
        print("=" * 70 + "\n")

        # Group by severity
        errors = [r for r in results if not r.passed and r.severity == "error"]
        warnings = [r for r in results if r.severity == "warning"]
        successes = [r for r in results if r.passed and r.severity != "warning"]
        info = [r for r in results if r.severity == "info"]

        # Print errors
        if errors:
            print("❌ ERRORS:")
            for result in errors:
                print(f"  {result}")
                if result.suggestion:
                    print(f"     💡 {result.suggestion}")
            print()

        # Print warnings
        if warnings:
            print("⚠️  WARNINGS:")
            for result in warnings:
                print(f"  {result}")
                if result.suggestion:
                    print(f"     💡 {result.suggestion}")
            print()

        # Print successes
        if successes:
            print("✅ PASSED:")
            for result in successes:
                print(f"  {result}")
            print()

        # Print info
        if info:
            for result in info:
                print(f"ℹ️  {result}")

        # Summary
        print("-" * 70)
        total = len(results)
        passed = len([r for r in results if r.passed])
        failed = len(errors)
        warned = len(warnings)

        print(f"Total checks: {total}")
        print(f"Passed: {passed}")
        if failed:
            print(f"Failed: {failed}")
        if warned:
            print(f"Warnings: {warned}")

        print("=" * 70)

        if errors:
            print("\n❌ Validation FAILED - fix errors before running")
        elif warnings:
            print("\n⚠️  Validation passed with WARNINGS - review before running")
        else:
            print("\n✅ All validations PASSED - ready to run!")

        print()


def dry_run(
    config: dict[str, Any], logger: logging.Logger | None = None, skip_network: bool = False
) -> int:
    """
    Execute dry run validation.

    Validates configuration and system state without executing analysis.

    Args:
        config: Configuration dictionary
        logger: Optional logger instance
        skip_network: Skip network connectivity checks

    Returns:
        Exit code (0 for success, 1 for failure)

    Example:
        >>> config = load_config('config.yaml')
        >>> exit_code = dry_run(config)
        >>> sys.exit(exit_code)
    """
    validator = DryRunValidator(config, logger)
    success, results = validator.validate_all(skip_network=skip_network)
    validator.print_results(results)

    return 0 if success else 1
