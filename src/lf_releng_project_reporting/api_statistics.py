# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
External API call statistics tracking.

Records per-API success and error counts for GitHub, Gerrit and Jenkins plus
the info-master clone outcome, and renders them for the console and the
GitHub Step Summary.
"""

import logging
import os
from typing import Any


logger = logging.getLogger(__name__)


class APIStatistics:
    """Track statistics for external API calls (GitHub, Gerrit, Jenkins)."""

    def __init__(self):
        """Initialize statistics tracker."""
        self.stats: dict[str, dict[str, Any]] = {
            "github": {"success": 0, "errors": {}},
            "gerrit": {"success": 0, "errors": {}},
            "jenkins": {"success": 0, "errors": {}},
            "info_master": {"success": False, "error": None},
        }
        self.github_org: str = ""
        self.github_org_source: str = ""

    def record_success(self, api_type: str) -> None:
        """Record a successful API call."""
        if api_type in self.stats and isinstance(self.stats[api_type]["success"], int):
            self.stats[api_type]["success"] += 1

    def record_error(self, api_type: str, status_code: int) -> None:
        """Record an API error by status code."""
        if api_type in self.stats:
            errors: dict[int | str, int] = self.stats[api_type]["errors"]
            errors[status_code] = errors.get(status_code, 0) + 1

    def record_exception(self, api_type: str, error_type: str = "exception") -> None:
        """Record an API exception (non-HTTP error)."""
        if api_type in self.stats:
            errors: dict[int | str, int] = self.stats[api_type]["errors"]
            errors[error_type] = errors.get(error_type, 0) + 1

    def record_info_master(self, success: bool, error: str | None = None) -> None:
        """Record info-master clone status."""
        self.stats["info_master"]["success"] = success
        if error:
            self.stats["info_master"]["error"] = error

    def set_github_org(self, github_org: str, source: str = "") -> None:
        """Set the GitHub organization being used for API queries."""
        self.github_org = github_org
        self.github_org_source = source

    def get_total_calls(self, api_type: str) -> int:
        """Get total number of API calls (success + errors)."""
        if api_type not in self.stats:
            return 0
        success = self.stats[api_type]["success"]
        if not isinstance(success, int):
            return 0
        errors_dict: dict[int | str, int] = self.stats[api_type]["errors"]
        errors = sum(errors_dict.values())
        return success + errors

    def get_total_errors(self, api_type: str) -> int:
        """Get total number of errors for an API."""
        if api_type not in self.stats:
            return 0
        errors_dict: dict[int | str, int] = self.stats[api_type]["errors"]
        return sum(errors_dict.values())

    def has_errors(self) -> bool:
        """Check if any API has errors."""
        for api_type in ["github", "gerrit", "jenkins"]:
            if self.get_total_errors(api_type) > 0:
                return True
        return bool(not self.stats["info_master"]["success"] and self.stats["info_master"]["error"])

    def format_console_output(self) -> str:
        """Format statistics for console output."""
        lines = []

        # GitHub API stats
        if self.get_total_calls("github") > 0:
            lines.append("\n📊 GitHub API Statistics:")
            lines.append(f"   ✅ Successful calls: {self.stats['github']['success']}")
            total_errors = self.get_total_errors("github")
            if total_errors > 0:
                lines.append(f"   ❌ Failed calls: {total_errors}")
                errors_dict: dict[int | str, int] = self.stats["github"]["errors"]
                for code, count in sorted(errors_dict.items(), key=lambda x: str(x[0])):
                    lines.append(f"      • Error {code}: {count}")

        # Gerrit API stats
        if self.get_total_calls("gerrit") > 0:
            lines.append("\n📊 Gerrit API Statistics:")
            lines.append(f"   ✅ Successful calls: {self.stats['gerrit']['success']}")
            total_errors = self.get_total_errors("gerrit")
            if total_errors > 0:
                lines.append(f"   ❌ Failed calls: {total_errors}")
                gerrit_errors: dict[int | str, int] = self.stats["gerrit"]["errors"]
                for code, count in sorted(gerrit_errors.items(), key=lambda x: str(x[0])):
                    lines.append(f"      • Error {code}: {count}")

        # Jenkins API stats
        if self.get_total_calls("jenkins") > 0:
            lines.append("\n📊 Jenkins API Statistics:")
            lines.append(f"   ✅ Successful calls: {self.stats['jenkins']['success']}")
            total_errors = self.get_total_errors("jenkins")
            if total_errors > 0:
                lines.append(f"   ❌ Failed calls: {total_errors}")
                jenkins_errors: dict[int | str, int] = self.stats["jenkins"]["errors"]
                for code, count in sorted(jenkins_errors.items(), key=lambda x: str(x[0])):
                    lines.append(f"      • Error {code}: {count}")

        # Info-master clone status
        if self.stats["info_master"]["success"]:
            lines.append("\n📊 Info-Master Clone:")
            lines.append("   ✅ Successfully cloned")
        elif self.stats["info_master"]["error"]:
            lines.append("\n📊 Info-Master Clone:")
            lines.append(f"   ❌ {self.stats['info_master']['error']}")

        return "\n".join(lines) if lines else ""

    def write_to_step_summary(self) -> None:
        """Write API statistics to GitHub Step Summary."""
        step_summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
        if not step_summary_file:
            return

        try:
            with open(step_summary_file, "a") as f:
                f.write("\n## 📊 API Statistics\n\n")

                # Track if any stats were written
                stats_written = False

                # GitHub API
                if self.get_total_calls("github") > 0:
                    f.write("### GitHub API\n")
                    if self.github_org:
                        source_display = ""
                        if self.github_org_source == "environment_variable":
                            source_display = " (from PROJECTS_JSON)"
                        elif self.github_org_source == "auto_derived":
                            source_display = " (auto-derived)"
                        f.write(f"- **Organization:** `{self.github_org}`{source_display}\n")
                    f.write(f"- ✅ Successful calls: {self.stats['github']['success']}\n")
                    total_errors = self.get_total_errors("github")
                    if total_errors > 0:
                        f.write(f"- ❌ Failed calls: {total_errors}\n")
                        for code, count in sorted(self.stats["github"]["errors"].items()):
                            f.write(f"  - Error {code}: {count}\n")
                    f.write("\n")
                    stats_written = True

                # Gerrit API
                if self.get_total_calls("gerrit") > 0:
                    f.write("### Gerrit API\n")
                    f.write(f"- ✅ Successful calls: {self.stats['gerrit']['success']}\n")
                    total_errors = self.get_total_errors("gerrit")
                    if total_errors > 0:
                        f.write(f"- ❌ Failed calls: {total_errors}\n")
                        for code, count in sorted(self.stats["gerrit"]["errors"].items()):
                            f.write(f"  - Error {code}: {count}\n")
                    f.write("\n")
                    stats_written = True

                # Jenkins API
                if self.get_total_calls("jenkins") > 0:
                    f.write("### Jenkins API\n")
                    f.write(f"- ✅ Successful calls: {self.stats['jenkins']['success']}\n")
                    total_errors = self.get_total_errors("jenkins")
                    if total_errors > 0:
                        f.write(f"- ❌ Failed calls: {total_errors}\n")
                        for code, count in sorted(self.stats["jenkins"]["errors"].items()):
                            f.write(f"  - Error {code}: {count}\n")
                    f.write("\n")
                    stats_written = True

                # Info-master
                if self.stats["info_master"]["success"] or self.stats["info_master"]["error"]:
                    f.write("### Info-Master Clone\n")
                    if self.stats["info_master"]["success"]:
                        f.write("- ✅ Successfully cloned\n")
                    elif self.stats["info_master"]["error"]:
                        f.write(f"- ❌ {self.stats['info_master']['error']}\n")
                    f.write("\n")
                    stats_written = True

                # If no stats were recorded, write a message indicating this
                if not stats_written:
                    f.write("ℹ️ No external API calls were made during this run.\n\n")
                    f.write(
                        "*This may indicate that API statistics tracking is not properly configured, "
                    )
                    f.write("or that no features requiring external API calls were enabled.*\n\n")

        except Exception as e:
            logger.warning("Could not write API stats to step summary: %s", e)
