# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Accessors that derive runtime options from parsed arguments."""

import argparse

from .models import OutputFormat, VerbosityLevel


def get_verbosity_level(args: argparse.Namespace) -> VerbosityLevel:
    """
    Determine verbosity level from arguments.

    Args:
        args: Parsed arguments

    Returns:
        VerbosityLevel enum value

    Example:
        >>> args = parse_arguments(['-vv'])
        >>> level = get_verbosity_level(args)
        >>> print(level)
        VerbosityLevel.DEBUG
    """
    if hasattr(args, "quiet") and args.quiet:
        return VerbosityLevel.QUIET

    if hasattr(args, "verbose"):
        verbose_count = args.verbose
        return {
            0: VerbosityLevel.NORMAL,
            1: VerbosityLevel.VERBOSE,
            2: VerbosityLevel.DEBUG,
        }.get(verbose_count, VerbosityLevel.TRACE)

    return VerbosityLevel.NORMAL


def get_log_level(args: argparse.Namespace) -> str:
    """
    Determine log level from arguments.

    Args:
        args: Parsed arguments

    Returns:
        Log level string (DEBUG, INFO, WARNING, ERROR)

    Example:
        >>> args = parse_arguments(['-v'])
        >>> level = get_log_level(args)
        >>> print(level)
        INFO
    """
    # Explicit log level takes precedence
    if hasattr(args, "log_level") and args.log_level:
        return str(args.log_level)

    # Otherwise determine from verbosity
    verbosity = get_verbosity_level(args)

    if verbosity == VerbosityLevel.QUIET:
        return "WARNING"
    elif verbosity == VerbosityLevel.NORMAL or verbosity == VerbosityLevel.VERBOSE:
        return "INFO"
    elif verbosity == VerbosityLevel.DEBUG:
        return "DEBUG"
    else:  # TRACE
        return "DEBUG"


def get_output_formats(args: argparse.Namespace) -> list[OutputFormat]:
    """
    Determine which output formats to generate.

    Args:
        args: Parsed arguments

    Returns:
        List of OutputFormat enum values

    Example:
        >>> args = parse_arguments(['--output-format', 'html'])
        >>> formats = get_output_formats(args)
        >>> print(formats)
        [<OutputFormat.HTML: 'html'>]
    """
    # Handle --output-format argument
    # Handle --output-format
    if hasattr(args, "output_format"):
        format_str = args.output_format.lower()

        format_map = {
            "all": [OutputFormat.JSON, OutputFormat.MARKDOWN, OutputFormat.HTML],
            "json": [OutputFormat.JSON],
            "md": [OutputFormat.MARKDOWN],
            "html": [OutputFormat.HTML],
        }
        if format_str in format_map:
            return format_map[format_str]

    # Default: all formats
    return [OutputFormat.JSON, OutputFormat.MARKDOWN, OutputFormat.HTML]


def should_generate_zip(args: argparse.Namespace) -> bool:
    """
    Determine if ZIP bundle should be generated.

    Args:
        args: Parsed arguments

    Returns:
        True if ZIP should be generated, False otherwise
    """
    return not (hasattr(args, "no_zip") and args.no_zip)


def is_special_mode(args: argparse.Namespace) -> bool:
    """
    Check if running in a special mode (dry-run, list-features, etc.).

    Special modes exit early without full analysis.

    Args:
        args: Parsed arguments

    Returns:
        True if in special mode, False otherwise
    """
    special_flags = [
        "dry_run",
        "validate_only",
        "list_features",
        "show_feature",
        "show_config",
        "init",
    ]
    return (
        any(getattr(args, flag, False) for flag in special_flags)
        or getattr(args, "init_template", None) is not None
    )


def is_wizard_mode(args: argparse.Namespace) -> bool:
    """
    Check if running in wizard mode (--init or --init-template).

    Args:
        args: Parsed arguments

    Returns:
        True if in wizard mode, False otherwise
    """
    return getattr(args, "init", False) or getattr(args, "init_template", None) is not None
