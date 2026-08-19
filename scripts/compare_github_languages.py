#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Compare GitHub Language Detection with Local Project Type Detection

This script fetches language/project type data from GitHub for all repositories
in an organization and compares it with our local detection results to identify
gaps and alignment opportunities.

Usage:
    python scripts/compare_github_languages.py --org onap --github-token $GITHUB_TOKEN
    python scripts/compare_github_languages.py --org onap --github-token $GITHUB_TOKEN --repos-path ./repos
    python scripts/compare_github_languages.py --org onap --github-token $GITHUB_TOKEN --output comparison.json
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path


# Allow importing the sibling helper modules that live alongside this script
sys.path.insert(0, str(Path(__file__).parent))

from github_language_comparison import LanguageComparisonAnalyzer
from github_language_sources import GitHubLanguageAnalyzer, LocalProjectTypeAnalyzer


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Compare GitHub language detection with local project type detection"
    )
    parser.add_argument(
        "--org",
        required=True,
        help="GitHub organization name (e.g., onap)",
    )
    parser.add_argument(
        "--github-token",
        help="GitHub personal access token (or set GITHUB_TOKEN env var)",
    )
    parser.add_argument(
        "--repos-path",
        type=Path,
        help="Path to directory containing cloned repositories",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for detailed JSON comparison (default: stdout)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Get GitHub token
    github_token = args.github_token or os.environ.get("GITHUB_TOKEN")
    if not github_token:
        logger.error("GitHub token required. Use --github-token or set GITHUB_TOKEN env var")
        return 1

    try:
        # Fetch GitHub data
        logger.info(f"Fetching GitHub language data for organization: {args.org}")
        gh_analyzer = GitHubLanguageAnalyzer(github_token)
        github_data = gh_analyzer.analyze_organization(args.org)
        gh_analyzer.close()

        logger.info(f"Fetched data for {len(github_data)} repositories from GitHub")

        # Analyze local repositories if path provided
        local_data = {}
        if args.repos_path:
            logger.info(f"Analyzing local repositories in: {args.repos_path}")
            local_analyzer = LocalProjectTypeAnalyzer()
            repo_names = list(github_data)
            local_data = local_analyzer.analyze_repositories(args.repos_path, repo_names)
            logger.info(f"Analyzed {len(local_data)} local repositories")
        else:
            logger.warning("No --repos-path provided, skipping local analysis")

        # Compare
        logger.info("Comparing GitHub and local detection results")
        comparator = LanguageComparisonAnalyzer()
        comparison = comparator.compare_repositories(github_data, local_data)

        # Generate report
        report = comparator.generate_report(comparison)
        print("\n" + report)

        # Save detailed JSON if requested
        if args.output:
            output_data = {
                "github_data": github_data,
                "local_data": local_data,
                "comparison": comparison,
            }
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)
            logger.info(f"Detailed comparison saved to: {args.output}")

        return 0

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
