# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Post-parse consistency checks for the parsed argument namespace."""

import argparse

from ..errors import InvalidArgumentError


def validate_arguments(args: argparse.Namespace) -> None:
    """
    Validate parsed arguments for consistency and correctness.

    Args:
        args: Parsed arguments namespace

    Raises:
        InvalidArgumentError: If arguments are invalid or conflicting
    """
    # Check if we're in a special mode that doesn't need standard arguments
    special_mode = (
        getattr(args, "list_features", False)
        or getattr(args, "show_feature", None) is not None
        or getattr(args, "init", False)
    )

    # For --init-template, we need --project but not --repos-path
    template_mode = getattr(args, "init_template", None) is not None
    if template_mode and not getattr(args, "project", None):
        raise InvalidArgumentError(
            "The --init-template mode requires --project",
            suggestion="Provide --project with your project name when using --init-template",
        )

    # Require --project and --repos-path unless in special mode or template mode
    if not special_mode and not template_mode:
        if not hasattr(args, "project") or not args.project:
            raise InvalidArgumentError(
                "The --project argument is required",
                suggestion="Provide --project with your project name, or use --list-features to see available features",
            )
        if not hasattr(args, "repos_path") or not args.repos_path:
            raise InvalidArgumentError(
                "The --repos-path argument is required",
                suggestion="Provide --repos-path with the path to your repositories directory",
            )

    # Validate paths exist where required
    if hasattr(args, "repos_path") and args.repos_path:
        if not args.repos_path.exists():
            raise InvalidArgumentError(
                f"Repository path does not exist: {args.repos_path}",
                suggestion="Ensure the path is correct and accessible",
            )
        if not args.repos_path.is_dir():
            raise InvalidArgumentError(
                f"Repository path is not a directory: {args.repos_path}",
                suggestion="Provide a path to a directory containing repositories",
            )

    # Validate worker count
    if hasattr(args, "workers") and args.workers is not None:
        if args.workers < 1:
            raise InvalidArgumentError(
                f"Worker count must be at least 1, got: {args.workers}",
                suggestion="Use --workers 1 or higher",
            )
        if args.workers > 32:
            raise InvalidArgumentError(
                f"Worker count seems too high: {args.workers}",
                suggestion="Consider using --workers 16 or lower for stability",
            )

    # Handle validate-only as alias for dry-run
    if hasattr(args, "validate_only") and args.validate_only:
        args.dry_run = True
