# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Terminal rendering of configuration validation results.

Holds print_validation_result, which formats a ValidationResult as
user-facing output on stderr.
"""

# The print_validation_result helper renders configuration validation output to
# the terminal (stderr); print() is the intended output sink here, not leftover
# debugging.
# aislop-ignore-file python-print-debug -- intentional user-facing CLI output

from .results import ValidationResult


def print_validation_result(result: ValidationResult, verbose: bool = False) -> None:
    """Print validation result in a user-friendly format.

    Args:
        result: Validation result to print
        verbose: If True, include info messages
    """
    import sys

    if result.has_errors:
        print("❌ Configuration validation FAILED\n", file=sys.stderr)
        print(f"Found {len(result.errors)} error(s):\n", file=sys.stderr)
        for error in result.errors:
            print(f"  {error}\n", file=sys.stderr)
    else:
        print("✅ Configuration validation PASSED\n", file=sys.stderr)

    if result.has_warnings:
        print(f"⚠️  Found {len(result.warnings)} warning(s):\n", file=sys.stderr)
        for warning in result.warnings:
            print(f"  {warning}\n", file=sys.stderr)

    if verbose and result.infos:
        print(f"ℹ️  Information ({len(result.infos)}):\n", file=sys.stderr)
        for info in result.infos:
            print(f"  {info}\n", file=sys.stderr)
