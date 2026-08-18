# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Argument parser construction and the top-level parse entry point."""

import argparse
from pathlib import Path

from .validators import validate_arguments


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create enhanced argument parser with improved help text.

    Returns:
        Configured ArgumentParser instance

    Example:
        >>> parser = create_argument_parser()
        >>> args = parser.parse_args(['--project', 'test', '--repos-path', '.'])
    """
    parser = argparse.ArgumentParser(
        prog="generate_reports.py",
        description="""
Repository Analysis Report Generator

Generate comprehensive analysis reports for repository collections including:
- Commit activity and contributor statistics
- CI/CD workflow status (Jenkins, GitHub Actions)
- Feature detection (Dependabot, pre-commit, ReadTheDocs, etc.)
- Organization and contributor rankings
- Inactive repository identification
        """.strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  %(prog)s --project my-project --repos-path /path/to/repos

  # With custom configuration
  %(prog)s --project my-project --repos-path ./repos --config-dir ./config

  # Validate configuration without running
  %(prog)s --project my-project --repos-path ./repos --dry-run

  # List all available feature checks
  %(prog)s --list-features

  # Generate only HTML report with verbose output
  %(prog)s --project my-project --repos-path ./repos --output-format html -vv

  # Show resolved configuration
  %(prog)s --project my-project --repos-path ./repos --show-config

Exit Codes:
  0 - Success (no errors or warnings)
  1 - Error (configuration, API, or processing failure)
  2 - Partial success (warnings or incomplete data)
  3 - Invalid arguments or usage
  4 - System error (permissions, disk space, etc.)

For more information, see docs/CLI_REFERENCE.md
        """,
    )

    # Required arguments (except in special modes)
    required = parser.add_argument_group("required arguments")
    required.add_argument(
        "--project",
        required=False,  # Made optional - validated later if not in special mode
        metavar="NAME",
        help="""
        Project name for reporting.
        Used for configuration overrides and output file naming.
        Example: --project my-project
        """,
    )
    required.add_argument(
        "--repos-path",
        required=False,  # Made optional - validated later if not in special mode
        type=Path,
        metavar="PATH",
        help="""
        Path to directory containing cloned repositories.
        All subdirectories will be analyzed as repositories.
        Example: --repos-path /workspace/repos
        """,
    )

    # Configuration options
    config = parser.add_argument_group("configuration options")
    config.add_argument(
        "--config-dir",
        type=Path,
        metavar="PATH",
        help="""
        Configuration directory containing YAML config files.
        Default: ./config
        Example: --config-dir /etc/repo-reports/config
        """,
    )
    config.add_argument(
        "--output-dir",
        type=Path,
        metavar="PATH",
        help="""
        Output directory for generated reports.
        Default: ./output
        Example: --output-dir /var/reports/output
        """,
    )
    config.add_argument(
        "--github-token-env",
        type=str,
        default="GITHUB_TOKEN",
        metavar="VAR_NAME",
        help="""
        Environment variable name for GitHub API token.
        Default: GITHUB_TOKEN (CI typically uses: CLASSIC_READ_ONLY_PAT_TOKEN)
        Example: --github-token-env CLASSIC_READ_ONLY_PAT_TOKEN
        """,
    )

    # Output format options
    output = parser.add_argument_group("output options")
    output.add_argument(
        "--output-format",
        type=str,
        choices=["json", "md", "html", "all"],
        default="all",
        metavar="FORMAT",
        help="""
        Output format(s) to generate.
        Choices: json, md, html, all
        Default: all
        Example: --output-format html
        """,
    )

    output.add_argument("--no-zip", action="store_true", help="Skip ZIP bundle creation")

    # Behavioral options
    behavior = parser.add_argument_group("behavioral options")
    behavior.add_argument(
        "--cache",
        action="store_true",
        help="Enable caching of git metrics to speed up subsequent runs",
    )
    behavior.add_argument(
        "--allow-empty",
        action="store_true",
        help=(
            "Allow report generation when no repositories are found. By "
            "default an empty repositories directory is treated as an error, "
            "since it usually indicates an upstream clone failure."
        ),
    )
    behavior.add_argument(
        "--workers",
        type=int,
        metavar="N",
        help="""
        Number of worker threads for parallel processing.
        Default: CPU count
        Example: --workers 8
        """,
    )

    # Verbosity options (mutually exclusive)
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="""
        Increase verbosity level. Can be used multiple times.
        -v: INFO, -vv: DEBUG, -vvv: TRACE
        """,
    )
    verbosity.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress non-error output (errors and warnings only)",
    )

    # Special modes
    modes = parser.add_argument_group("special modes")
    modes.add_argument(
        "--init",
        action="store_true",
        help="""
        Run interactive configuration wizard to create a new config file.
        Guides you through all configuration options with smart defaults.
        Example: --init
        """,
    )
    modes.add_argument(
        "--init-template",
        type=str,
        choices=["minimal", "standard", "full"],
        metavar="TEMPLATE",
        help="""
        Create configuration from template without interactive prompts.
        Requires --project. Choices: minimal, standard, full
        Example: --init-template standard --project my-project
        """,
    )
    modes.add_argument(
        "--config-output",
        type=Path,
        metavar="PATH",
        help="""
        Output path for configuration file (used with --init or --init-template).
        Default: config/{project}.yaml
        Example: --config-output custom-config.yaml
        """,
    )
    modes.add_argument(
        "--dry-run",
        action="store_true",
        help="""
        Validate configuration and setup without executing analysis.
        Useful for testing configuration changes.
        Example: --dry-run
        """,
    )
    modes.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate configuration file and exit (alias for --dry-run)",
    )
    modes.add_argument(
        "--list-features", action="store_true", help="List all available feature checks and exit"
    )
    modes.add_argument(
        "--show-feature",
        type=str,
        metavar="NAME",
        help="Show detailed information about a specific feature and exit",
    )
    modes.add_argument(
        "--show-config", action="store_true", help="Display resolved configuration and exit"
    )

    # Advanced options
    advanced = parser.add_argument_group("advanced options")
    advanced.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        metavar="LEVEL",
        help="Override log level from configuration",
    )
    advanced.add_argument(
        "--cache-dir",
        type=Path,
        metavar="PATH",
        help="Custom cache directory (default: .cache/repo-metrics)",
    )
    advanced.add_argument(
        "--config-override",
        action="append",
        metavar="KEY=VALUE",
        help="""
        Override configuration values.
        Can be used multiple times.
        Example: --config-override api.github.token=ghp_xxx
        """,
    )

    return parser


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """
    Parse and validate command-line arguments.

    Args:
        args: Optional list of arguments (defaults to sys.argv)

    Returns:
        Parsed arguments namespace

    Raises:
        InvalidArgumentError: If arguments are invalid or conflicting

    Example:
        >>> args = parse_arguments(['--project', 'test', '--repos-path', '.'])
        >>> print(args.project)
        test
    """
    parser = create_argument_parser()
    parsed_args = parser.parse_args(args)

    # Post-parse validation
    validate_arguments(parsed_args)

    return parsed_args
