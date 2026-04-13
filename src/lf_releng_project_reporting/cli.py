# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Modern CLI interface using Typer for lf-releng-project-reporting.

This module provides a rich, user-friendly command-line interface with:
- Type-safe argument parsing
- Beautiful output formatting with Rich
- Shell completion support
- Interactive help and documentation
- Modern CLI conventions
"""

import sys
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from rich import print as rprint
from rich.console import Console


# Initialize Typer app with rich formatting
app = typer.Typer(
    name="lf-releng-project-reporting",
    help="📊 Comprehensive Multi-Repository Analysis Tool",
    add_completion=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=True,
)

# Rich console for beautiful output
console = Console()


class OutputFormat(str, Enum):
    """Output format options."""

    JSON = "json"
    MARKDOWN = "md"
    HTML = "html"
    ALL = "all"


class InitTemplate(str, Enum):
    """Configuration template options."""

    MINIMAL = "minimal"
    STANDARD = "standard"
    FULL = "full"


class ExitCode(int, Enum):
    """Standard exit codes."""

    SUCCESS = 0
    ERROR = 1
    PARTIAL = 2
    USAGE_ERROR = 3
    SYSTEM_ERROR = 4


# Version callback
def version_callback(value: bool):
    """Show version and exit."""
    if value:
        from lf_releng_project_reporting import __version__

        rprint(
            f"[bold cyan]lf-releng-project-reporting[/bold cyan] version [green]{__version__}[/green]"
        )
        raise typer.Exit()


@app.command()
def generate(
    # Required arguments
    project: Annotated[
        str | None,
        typer.Option(
            "--project",
            "-p",
            help="Project name for reporting and configuration",
            rich_help_panel="Required Arguments",
        ),
    ] = None,
    repos_path: Annotated[
        Path | None,
        typer.Option(
            "--repos-path",
            "-r",
            help="Path to directory containing cloned repositories",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            rich_help_panel="Required Arguments",
        ),
    ] = None,
    # Configuration options
    config_dir: Annotated[
        Path | None,
        typer.Option(
            "--config-dir",
            help="Configuration directory containing YAML files",
            exists=True,
            file_okay=False,
            dir_okay=True,
            rich_help_panel="Configuration",
        ),
    ] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "--output-dir",
            "-o",
            help="Output directory for generated reports",
            rich_help_panel="Configuration",
        ),
    ] = None,
    github_token_env: Annotated[
        str,
        typer.Option(
            "--github-token-env",
            help="Environment variable name for GitHub API token (default: GITHUB_TOKEN, CI uses: CLASSIC_READ_ONLY_PAT_TOKEN)",
            rich_help_panel="Configuration",
        ),
    ] = "GITHUB_TOKEN",
    # Output options
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--output-format",
            "-f",
            help="Output format(s) to generate",
            rich_help_panel="Output Options",
        ),
    ] = OutputFormat.ALL,
    no_zip: Annotated[
        bool,
        typer.Option(
            "--no-zip",
            help="Skip ZIP bundle creation",
            rich_help_panel="Output Options",
        ),
    ] = False,
    # Behavioral options
    cache: Annotated[
        bool,
        typer.Option(
            "--cache",
            help="Enable caching of git metrics for faster subsequent runs",
            rich_help_panel="Performance",
        ),
    ] = False,
    workers: Annotated[
        int | None,
        typer.Option(
            "--workers",
            "-w",
            help="Number of worker threads (default: CPU count, 'auto' for optimal)",
            min=1,
            rich_help_panel="Performance",
        ),
    ] = None,
    # Verbosity options
    verbose: Annotated[
        int,
        typer.Option(
            "--verbose",
            "-v",
            count=True,
            help="Increase verbosity (-v: INFO, -vv: DEBUG, -vvv: TRACE)",
            rich_help_panel="Logging",
        ),
    ] = 0,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            "-q",
            help="Suppress non-error output",
            rich_help_panel="Logging",
        ),
    ] = False,
    # Validation options
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Validate configuration without executing analysis",
            rich_help_panel="Validation",
        ),
    ] = False,
    # Version
    _version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = None,
):
    """
    Generate comprehensive analysis reports for repository collections.

    Analyzes Git repositories to generate detailed reports including:

    • 📈 Commit activity and contributor statistics

    • 🔍 CI/CD workflow status (Jenkins, GitHub Actions)

    • ✨ Feature detection (Dependabot, pre-commit, ReadTheDocs, etc.)

    • 👥 Organization and contributor rankings

    • 📊 Inactive repository identification

    \b
    Examples:
        # Basic usage
        lf-releng-project-reporting generate --project my-project --repos-path ./repos

        # With custom configuration
        lf-releng-project-reporting generate -p my-project -r ./repos --config-dir ./config

        # Validate without running
        lf-releng-project-reporting generate -p my-project -r ./repos --dry-run

        # Generate only HTML with verbose output
        lf-releng-project-reporting generate -p my-project -r ./repos -f html -vv

        # With caching and parallel processing
        lf-releng-project-reporting generate -p my-project -r ./repos --cache --workers 8

        # CI environment with custom token variable
        lf-releng-project-reporting generate -p my-project -r ./repos --github-token-env CLASSIC_READ_ONLY_PAT_TOKEN
    """
    # Import here to avoid circular imports and speed up CLI loading
    from argparse import Namespace

    from lf_releng_project_reporting.main import main as reporting_main

    # Validate required arguments
    if not project:
        console.print("[red]Error:[/red] --project is required")
        raise typer.Exit(code=ExitCode.USAGE_ERROR)
    if not repos_path:
        console.print("[red]Error:[/red] --repos-path is required")
        raise typer.Exit(code=ExitCode.USAGE_ERROR)

    # Build arguments namespace for main function
    args = Namespace(
        project=project,
        repos_path=repos_path,
        config_dir=config_dir or Path("configuration"),
        output_dir=output_dir or Path("reports"),
        output_format=output_format.value,
        no_zip=no_zip,
        no_html=output_format not in [OutputFormat.HTML, OutputFormat.ALL],
        cache=cache,
        workers=workers,
        verbose=verbose,
        quiet=quiet,
        validate_only=dry_run,
        log_level=None,
        github_token_env=github_token_env,
    )

    # Set log level based on verbosity
    if quiet:
        args.log_level = "ERROR"
    elif verbose >= 2:
        args.log_level = "DEBUG"
    elif verbose >= 1:
        args.log_level = "INFO"

    # Call main function directly
    try:
        exit_code = reporting_main(args)
        raise typer.Exit(code=exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(code=130) from None


# Note: init command removed - not yet implemented
# Users should manually copy from /config/default.yaml to /configuration/


# Note: list-features command removed - not yet implemented
# Feature detection happens automatically during report generation


# Note: validate command removed - not yet implemented
# Use 'lf-releng-project-reporting generate --dry-run' for configuration validation


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    _version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = None,
):
    """
    📊 Reporting Tool - Comprehensive Multi-Repository Analysis Tool

    A modern Python package for analyzing Git repositories and generating
    comprehensive reports with metrics, feature detection, and contributor analysis.

    \b
    🚀 Quick Start:
        lf-releng-project-reporting generate --project my-project --repos-path ./repos

    \b
    📖 Main Command:
        generate        Generate analysis reports (main command)

    \b
    🐛 Report Issues:
        https://github.com/lfreleng-actions/lf-releng-project-reporting/issues
    """
    if ctx.invoked_subcommand is None:
        # No subcommand provided, show help
        console.print(ctx.get_help())


def cli_main():
    """Entry point for console script."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(code=130) from None
    except Exception as e:
        console.print(f"[red bold]Error:[/red bold] {e}")
        if "--verbose" in sys.argv or "-v" in sys.argv:
            console.print_exception()
        raise typer.Exit(code=ExitCode.ERROR) from None


if __name__ == "__main__":
    cli_main()
