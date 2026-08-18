# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Comparison and reporting for GitHub versus local language detection.

Normalizes language names, compares the two data sources and renders the
human-readable report for ``scripts/compare_github_languages.py``.
"""

import logging
from collections import defaultdict
from typing import Any


class LanguageComparisonAnalyzer:
    """Compare GitHub and local language detection."""

    def __init__(self):
        """Initialize comparison analyzer."""
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def normalize_language_name(name: str) -> str:
        """
        Normalize language names for comparison.

        Args:
            name: Language or project type name

        Returns:
            Normalized name
        """
        # First, handle our combined types (Java/Maven, Java/Gradle) -> Java
        if name and "/" in name and name.startswith("Java/"):
            return "Java"

        # Mapping from GitHub names to our names
        name_mapping = {
            "Dockerfile": "Dockerfile",
            "JavaScript": "JavaScript",
            "TypeScript": "TypeScript",
            "Python": "Python",
            "Java": "Java",
            "C++": "C++",
            "C": "C",
            "Go": "Go",
            "Rust": "Rust",
            "Ruby": "Ruby",
            "PHP": "PHP",
            "Shell": "Shell",
            "HTML": "HTML",
            "CSS": "CSS",
            "SCSS": "SCSS",
            "Groovy": "Groovy",
            "Kotlin": "Kotlin",
            "Scala": "Scala",
            "Swift": "Swift",
            "Clojure": "Clojure",
            "Erlang": "Erlang",
            "Lua": "Lua",
            "D": "D",
            "HCL": "HCL",
            "Smarty": "Smarty",
            "EJS": "EJS",
            "RobotFramework": "Robot Framework",
            "Robot Framework": "Robot Framework",
            ".NET": ".NET",
            "C#": ".NET",
            "CMake": "C++",
            "Makefile": "C",
            "Maven": "Java",
            "Gradle": "Java",
        }

        return name_mapping.get(name, name)

    def compare_repositories(
        self,
        github_data: dict[str, dict[str, Any]],
        local_data: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Compare GitHub and local detection results.

        Args:
            github_data: GitHub language data
            local_data: Local detection data

        Returns:
            Comparison analysis
        """
        comparison = {
            "total_repos": len(github_data),
            "matches": [],
            "mismatches": [],
            "github_only": [],
            "local_only": [],
            "statistics": {
                "exact_matches": 0,
                "partial_matches": 0,
                "complete_mismatches": 0,
                "skipped_not_local": 0,
                "analyzed_locally": 0,
            },
            "language_gaps": defaultdict(int),
            "language_agreement": defaultdict(int),
        }

        for repo_name, gh_data in github_data.items():
            # Skip archived and forked repos
            if gh_data.get("archived") or gh_data.get("fork"):
                continue

            local_result = local_data.get(repo_name)

            # Skip repos not found locally (archived/removed repos)
            if not local_result:
                comparison["statistics"]["skipped_not_local"] += 1
                self.logger.debug(f"Skipping {repo_name} - not found locally")
                continue

            # Count repos analyzed locally (excluding archived/forked)
            comparison["statistics"]["analyzed_locally"] += 1

            # Get GitHub's primary language
            gh_primary = gh_data.get("github_primary_language")
            gh_languages = set(gh_data.get("languages", {}).keys())

            # Get our detected types
            local_primary = local_result.get("primary_type")
            local_types = set(local_result.get("detected_types", []))

            # Normalize names for comparison
            gh_primary_norm = self.normalize_language_name(gh_primary) if gh_primary else None
            local_primary_norm = (
                self.normalize_language_name(local_primary) if local_primary else None
            )
            local_types_norm = {self.normalize_language_name(t) for t in local_types}

            # Compare
            if gh_primary_norm and gh_primary_norm == local_primary_norm:
                comparison["statistics"]["exact_matches"] += 1
                comparison["language_agreement"][gh_primary_norm] += 1
                comparison["matches"].append(
                    {
                        "repo": repo_name,
                        "language": gh_primary_norm,
                        "github_languages": list(gh_languages),
                        "local_types": list(local_types),
                    }
                )
            elif gh_primary_norm and gh_primary_norm in local_types_norm:
                comparison["statistics"]["partial_matches"] += 1
                comparison["language_agreement"][gh_primary_norm] += 1
                comparison["matches"].append(
                    {
                        "repo": repo_name,
                        "language": gh_primary_norm,
                        "match_type": "partial",
                        "github_primary": gh_primary,
                        "local_primary": local_primary,
                        "github_languages": list(gh_languages),
                        "local_types": list(local_types),
                    }
                )
            else:
                comparison["statistics"]["complete_mismatches"] += 1
                comparison["mismatches"].append(
                    {
                        "repo": repo_name,
                        "github_primary": gh_primary,
                        "local_primary": local_primary,
                        "github_languages": list(gh_languages),
                        "local_types": list(local_types),
                    }
                )

                # Track gaps
                if gh_primary:
                    comparison["language_gaps"][gh_primary] += 1

        # Calculate percentages
        analyzed = comparison["statistics"]["analyzed_locally"]

        # Add analyzed_locally to top level for easy access
        comparison["analyzed_locally"] = comparison["statistics"]["analyzed_locally"]

        if analyzed > 0:
            comparison["statistics"]["exact_match_percentage"] = (
                comparison["statistics"]["exact_matches"] / analyzed * 100
            )
            comparison["statistics"]["partial_match_percentage"] = (
                comparison["statistics"]["partial_matches"] / analyzed * 100
            )
            comparison["statistics"]["mismatch_percentage"] = (
                comparison["statistics"]["complete_mismatches"] / analyzed * 100
            )

        return comparison

    def generate_report(self, comparison: dict[str, Any]) -> str:
        """
        Generate a human-readable comparison report.

        Args:
            comparison: Comparison analysis

        Returns:
            Formatted report text
        """
        report_lines = [
            "=" * 80,
            "GitHub vs Local Language Detection Comparison",
            "=" * 80,
            "",
            "Summary:",
            f"  Total GitHub repos: {comparison['total_repos']}",
            f"  Skipped (not found locally): {comparison['statistics']['skipped_not_local']}",
            f"  Analyzed locally: {comparison['statistics']['analyzed_locally']}",
            "",
            "Results for locally available repos:",
            f"  Exact matches: {comparison['statistics']['exact_matches']}",
            f"  Partial matches: {comparison['statistics']['partial_matches']}",
            f"  Complete mismatches: {comparison['statistics']['complete_mismatches']}",
            "",
        ]

        if comparison["statistics"]["analyzed_locally"] > 0:
            report_lines.extend(
                [
                    "Match Percentages:",
                    f"  Exact matches: {comparison['statistics'].get('exact_match_percentage', 0):.1f}%",
                    f"  Partial matches: {comparison['statistics'].get('partial_match_percentage', 0):.1f}%",
                    f"  Mismatches: {comparison['statistics'].get('mismatch_percentage', 0):.1f}%",
                    "",
                ]
            )

        # Language agreement
        if comparison["language_agreement"]:
            report_lines.extend(
                [
                    "Languages with Good Agreement:",
                    "  (GitHub primary language matched our detection)",
                ]
            )
            for lang, count in sorted(
                comparison["language_agreement"].items(), key=lambda x: x[1], reverse=True
            ):
                report_lines.append(f"  {lang}: {count} repos")
            report_lines.append("")

        # Language gaps
        if comparison["language_gaps"]:
            report_lines.extend(
                [
                    "Language Detection Gaps:",
                    "  (GitHub detected but we missed as primary)",
                ]
            )
            for lang, count in sorted(
                comparison["language_gaps"].items(), key=lambda x: x[1], reverse=True
            ):
                report_lines.append(f"  {lang}: {count} repos")
            report_lines.append("")

        # Sample mismatches
        if comparison["mismatches"]:
            report_lines.extend(
                [
                    "Sample Mismatches (first 10):",
                ]
            )
            for mismatch in comparison["mismatches"][:10]:
                report_lines.append(f"  Repository: {mismatch['repo']}")
                report_lines.append(f"    GitHub primary: {mismatch['github_primary']}")
                report_lines.append(f"    Our primary: {mismatch['local_primary']}")
                report_lines.append(
                    f"    GitHub languages: {', '.join(mismatch.get('github_languages', []))}"
                )
                report_lines.append(f"    Our types: {', '.join(mismatch.get('local_types', []))}")
                report_lines.append("")

        report_lines.append("=" * 80)
        return "\n".join(report_lines)
