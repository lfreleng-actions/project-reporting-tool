#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Main entry point for lf-releng-project-reporting.

This module provides the core orchestration logic for report generation,
coordinating configuration loading, repository analysis, and output generation.
"""

import logging
import sys
from typing import Any


# Verify PyYAML is importable (not merely discoverable on sys.path) so
# that broken installs, missing C extensions, or shadowed modules are
# surfaced with a friendly error at startup rather than crashing deep
# inside lf_releng_project_reporting.config when it imports yaml.
try:
    # aislop-ignore-next-line unused-import -- deliberate PyYAML importability check
    import yaml as _yaml  # noqa: F401
except ImportError:
    print(
        "ERROR: PyYAML is required. Install with: pip install 'PyYAML>=6.0.3' "
        "(see the project's pyproject.toml for the authoritative version pin).",
        file=sys.stderr,
    )
    sys.exit(1)

# Import utility modules
# Import configuration utilities
from lf_releng_project_reporting.api_statistics import APIStatistics
from lf_releng_project_reporting.config import (
    compute_config_digest,
    load_configuration,
    save_resolved_config,
)
from lf_releng_project_reporting.exceptions import NoRepositoriesError
from lf_releng_project_reporting.reporter import RepositoryReporter
from lf_releng_project_reporting.step_summary import write_config_to_step_summary
from util.github_org import determine_github_org
from util.zip_bundle import create_report_bundle


logger = logging.getLogger(__name__)


try:
    from lf_releng_project_reporting import __version__
except ImportError:
    __version__ = "0.0.0"  # Fallback if not installed

SCHEMA_VERSION = "1.5.0"
DEFAULT_CONFIG_DIR = "configuration"
DEFAULT_OUTPUT_DIR = "reports"

# Default time windows (can be overridden in config)
DEFAULT_TIME_WINDOWS = {
    "last_30": 30,
    "last_90": 90,
    "last_365": 365,
    "last_3_years": 1095,
}


# Global API statistics instance
api_stats = APIStatistics()


def setup_logging(level: str = "INFO", include_timestamps: bool = True) -> logging.Logger:
    """Configure logging with structured format."""
    log_format = "[%(levelname)s]"
    if include_timestamps:
        log_format = "[%(asctime)s] " + log_format
    log_format += " %(message)s"

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )

    # Reduce noise from HTTP libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    return logging.getLogger(__name__)


def _prepare_run_config(args, config: dict[str, Any]) -> logging.Logger:
    """Resolve the GitHub org, inject runtime config, and set up logging.

    Returns the configured logger. Mutates ``config`` in place with the derived
    GitHub organization, version metadata, token env name, and log level.
    """
    # Determine GitHub organization once - centralized
    github_org, github_org_source = determine_github_org(args.repos_path)

    if github_org:
        # Store in config for all components to use
        config["github"] = github_org
        config["_github_org_source"] = github_org_source

        # Store in API stats for reporting
        api_stats.set_github_org(github_org, github_org_source)

        if github_org_source == "auto_derived":
            print(
                f"ℹ️  Derived GitHub organization '{github_org}' from repository path",
                file=sys.stderr,
            )
        elif github_org_source == "environment_variable":
            print(f"ℹ️  GitHub organization '{github_org}' from PROJECTS_JSON", file=sys.stderr)

    # Inject script and schema versions into config for reporter
    config["_script_version"] = __version__
    config["_schema_version"] = SCHEMA_VERSION

    # Store GitHub token environment variable name in config
    github_token_env = getattr(args, "github_token_env", "GITHUB_TOKEN")
    config["_github_token_env"] = github_token_env

    # Override log level if specified
    if hasattr(args, "log_level") and args.log_level:
        config.setdefault("logging", {})["level"] = args.log_level
    elif hasattr(args, "verbose") and args.verbose:
        config.setdefault("logging", {})["level"] = "DEBUG"

    log_config = config.get("logging", {})
    logger = setup_logging(
        level=log_config.get("level", "INFO"),
        include_timestamps=log_config.get("include_timestamps", True),
    )

    logger.info(f"Repository Reporting System v{__version__}")
    logger.info(f"Project: {args.project}")
    logger.info(f"Configuration digest: {compute_config_digest(config)[:12]}...")
    logger.debug(f"Using GitHub token from environment variable: {github_token_env}")

    return logger


def _write_report_outputs(
    reporter: RepositoryReporter,
    report_data: dict[str, Any],
    config: dict[str, Any],
    args,
    project_output_dir,
    logger: logging.Logger,
) -> None:
    """Write JSON/Markdown/HTML reports, save config, and print the summary."""
    json_path = project_output_dir / "report_raw.json"
    md_path = project_output_dir / "report.md"
    html_path = project_output_dir / "report.html"
    config_path = project_output_dir / "config_resolved.json"

    import json

    logger.info(f"Writing JSON report to {json_path}")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)

    # Generate Markdown report using modern template system
    logger.info(f"Generating Markdown report to {md_path}")
    reporter.renderer.render_markdown_report(report_data, md_path)

    # Generate HTML report using modern template system (unless disabled)
    if not (hasattr(args, "no_html") and args.no_html):
        logger.info(f"Converting to HTML report at {html_path}")
        reporter.renderer.render_html_report(report_data, html_path)

    save_resolved_config(config, config_path)

    # Create ZIP bundle (unless disabled)
    if not (hasattr(args, "no_zip") and args.no_zip):
        create_report_bundle(project_output_dir, args.project, logger)

    repo_count = len(report_data["repositories"])
    error_count = len(report_data["errors"])

    print("\n✅ Report generation completed successfully!")
    print(f"   - Analyzed: {repo_count} repositories")
    print(f"   - Errors: {error_count}")
    print(f"   - Output directory: {project_output_dir}")

    if error_count > 0:
        print(f"   - Check {json_path} for error details")

    api_stats_output = api_stats.format_console_output()
    if api_stats_output:
        print(api_stats_output)

    api_stats.write_to_step_summary()


def main(args=None) -> int:
    """
    Main entry point for report generation.

    Args:
        args: Parsed arguments namespace (from argparse or CLI)

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # If args not provided, parse from command line
        if args is None:
            from cli import parse_arguments

            args = parse_arguments()

        try:
            config = load_configuration(args.project, args.config_dir)
        except Exception as e:
            import traceback

            print(f"ERROR: Failed to load configuration: {e}", file=sys.stderr)
            traceback.print_exc()
            return 1

        # Determine GitHub organization and finalize runtime configuration
        logger = _prepare_run_config(args, config)

        write_config_to_step_summary(config, args.project)

        # Validate-only mode
        if hasattr(args, "validate_only") and args.validate_only:
            logger.info("Configuration validation successful")
            features = config.get("features", {})
            print(f"✅ Configuration valid for project '{args.project}'")
            print(f"   - Schema version: {config.get('schema_version', 'Unknown')}")
            print(f"   - Time windows: {list(config.get('time_windows', {}).keys())}")
            print(f"   - Features enabled: {len(features.get('enabled', []))}")
            return 0

        args.output_dir.mkdir(parents=True, exist_ok=True)
        project_output_dir = args.output_dir / args.project
        project_output_dir.mkdir(parents=True, exist_ok=True)

        reporter = RepositoryReporter(config, logger, api_stats)

        # Analyze repositories
        allow_empty = bool(getattr(args, "allow_empty", False))
        report_data = reporter.analyze_repositories(args.repos_path, allow_empty=allow_empty)

        # Generate outputs
        _write_report_outputs(reporter, report_data, config, args, project_output_dir, logger)

        return 0

    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user", file=sys.stderr)
        return 130
    except NoRepositoriesError as e:
        # Empty working directory: almost always a transient upstream clone
        # failure. Fail loudly with a retryable exit code rather than emitting
        # an empty report that could overwrite previously good output.
        print(f"❌ {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        if args is not None and hasattr(args, "verbose") and args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
