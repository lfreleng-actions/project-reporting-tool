# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Commit parsing, author normalization, and metric aggregation."""

import datetime
import os
from pathlib import Path
from typing import Any

from .base import _CollectorState
from .commands import parse_git_iso_date, safe_git_command


class _CommitMetricsMixin(_CollectorState):
    """Parse commits and aggregate repository and author metrics."""

    def bucket_commit_into_windows(
        self,
        commit_datetime: datetime.datetime,
        time_windows: dict[str, dict[str, Any]],
    ) -> list[str]:
        """
        Determine which time windows a commit falls into.

        A commit belongs to a window if it occurred after the window's start time.
        """
        matching_windows = []
        commit_timestamp = commit_datetime.timestamp()

        for window_name, window_data in time_windows.items():
            if commit_timestamp >= window_data["start_timestamp"]:
                matching_windows.append(window_name)

        return matching_windows

    def extract_organizational_domain(self, full_domain: str) -> str:
        """
        Extract organizational domain from full domain by taking the last two parts.
        Uses configuration file for exceptions where full domain should be preserved.

        Examples:
        - users.noreply.github.com -> github.com
        - tnap-dev-vm-mangala.tnaplab.telekom.de -> telekom.de
        - contractor.linuxfoundation.org -> linuxfoundation.org
        - zte.com.cn -> zte.com.cn (preserved due to configuration)
        - simple.com -> simple.com (unchanged for 2-part domains)
        - localhost -> localhost (unchanged for single-part domains)
        """
        if not full_domain or full_domain in ["unknown", "localhost", ""]:
            return full_domain

        # Load domain configuration (with caching)
        if self._domain_config is None:
            self._domain_config = self._load_domain_config()

        # Check if domain should be preserved in full
        if full_domain in self._domain_config.get("preserve_full_domain", []):
            return full_domain

        custom_mappings = self._domain_config.get("custom_mappings", {})
        if full_domain in custom_mappings:
            return str(custom_mappings[full_domain])

        # Split domain into parts
        parts = full_domain.split(".")

        # If 2 or fewer parts, return as-is
        if len(parts) <= 2:
            return full_domain

        return ".".join(parts[-2:])

    def _load_domain_config(self) -> dict[str, Any]:
        """Load organizational domain configuration from YAML file."""
        import yaml

        config_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "configuration",
            "organizational_domains.yaml",
        )

        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
                self.logger.debug(f"Loaded organizational domain config from {config_path}")
                return config
        except FileNotFoundError:
            self.logger.warning(f"Organizational domain config file not found: {config_path}")
            return {}
        except Exception as e:
            self.logger.error(f"Error loading organizational domain config: {e}")
            return {}

    def normalize_author_identity(self, name: str, email: str) -> tuple[str, str]:
        """
        Normalize author identity with consistent format.

        - Email lowercase and trimmed
        - Username heuristic from email local part
        - Handle malformed emails gracefully
        - Domain extraction for organization analysis
        """
        clean_name = name.strip() if name else "Unknown"
        clean_email = email.lower().strip() if email else ""

        if not clean_email or "@" not in clean_email:
            data_quality_config = self.config.get("data_quality", {})
            unknown_placeholder = data_quality_config.get(
                "unknown_email_placeholder", "unknown@unknown"
            )
            clean_email = unknown_placeholder

        normalized = {
            "name": clean_name,
            "email": clean_email,
            "username": "",
            "domain": "",
        }

        if "@" in clean_email:
            # Always split on the LAST @ symbol to handle complex email addresses
            parts = clean_email.split("@")
            if len(parts) >= 2:
                normalized["username"] = "@".join(parts[:-1])
                normalized["domain"] = parts[-1].lower()
            else:
                # Shouldn't happen since we checked for @ above, but be safe
                normalized["username"] = clean_email
                normalized["domain"] = ""

        return (normalized["name"], normalized["email"])

    def _parse_git_log_output(self, git_output: str, repo_name: str) -> list[dict[str, Any]]:
        """
        Parse git log output into structured commit data.

        Expected format from git log --numstat --date=iso --pretty=format:%H|%ad|%an|%ae|%s
        """
        commits = []
        lines = git_output.strip().split("\n")
        current_commit = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this is a commit header line (contains |)
            if "|" in line and len(line.split("|")) >= 5:
                # Save previous commit if exists
                if current_commit:
                    commits.append(current_commit)

                # Parse commit header: hash|date|author_name|author_email|subject
                parts = line.split("|", 4)
                try:
                    commit_date = parse_git_iso_date(parts[1])
                    if commit_date.tzinfo is None:
                        commit_date = commit_date.replace(tzinfo=datetime.UTC)
                except (ValueError, IndexError) as e:
                    self.logger.warning(
                        f"Invalid date format in {repo_name}: {parts[1] if len(parts) > 1 else 'unknown'} - {e}"
                    )
                    continue

                current_commit = {
                    "hash": parts[0],
                    "date": commit_date,
                    "author_name": parts[2],
                    "author_email": parts[3],
                    "subject": parts[4] if len(parts) > 4 else "",
                    "files_changed": [],
                }
            else:
                # Parse numstat lines (format: added<tab>removed<tab>filename)
                parts = line.split("\t")
                if len(parts) >= 3 and current_commit:
                    try:
                        # Handle binary files (marked with -)
                        added = 0 if parts[0] == "-" else int(parts[0])
                        removed = 0 if parts[1] == "-" else int(parts[1])
                        filename = parts[2]

                        # Skip binary files if configured
                        data_quality_config = self.config.get("data_quality", {})
                        if data_quality_config.get("skip_binary_changes", True) and (
                            parts[0] == "-" or parts[1] == "-"
                        ):
                            continue

                        files_changed = current_commit["files_changed"]
                        assert isinstance(files_changed, list)
                        files_changed.append(
                            {
                                "filename": filename,
                                "added": added,
                                "removed": removed,
                            }
                        )
                    except (ValueError, IndexError):
                        # Skip malformed lines
                        continue

        # Don't forget the last commit
        if current_commit:
            commits.append(current_commit)

        return commits

    def _update_commit_metrics(self, commit: dict[str, Any], metrics: dict[str, Any]) -> None:
        """Process a single commit into the metrics structure."""
        applicable_windows = self.bucket_commit_into_windows(commit["date"], self.time_windows)

        # Normalize author identity
        norm_name, norm_email = self.normalize_author_identity(
            commit["author_name"], commit["author_email"]
        )
        author_email = norm_email

        author_info = {
            "name": norm_name,
            "email": norm_email,
            "username": norm_name.split()[0] if norm_name else "",
            "domain": self.extract_organizational_domain(norm_email.split("@")[-1])
            if "@" in norm_email
            else "",
        }

        # Calculate LOC changes for this commit
        total_added = sum(f["added"] for f in commit["files_changed"])
        total_removed = sum(f["removed"] for f in commit["files_changed"])
        net_lines = total_added - total_removed

        for window in applicable_windows:
            metrics["repository"]["commit_counts"][window] += 1
            metrics["repository"]["loc_stats"][window]["added"] += total_added
            metrics["repository"]["loc_stats"][window]["removed"] += total_removed
            metrics["repository"]["loc_stats"][window]["net"] += net_lines
            metrics["repository"]["unique_contributors"][window].add(author_email)

        if author_email not in metrics["authors"]:
            metrics["authors"][author_email] = {
                "name": author_info["name"],
                "email": author_email,
                "username": author_info["username"],
                "domain": author_info["domain"],
                "commit_counts": dict.fromkeys(self.time_windows, 0),
                "loc_stats": {
                    window: {"added": 0, "removed": 0, "net": 0} for window in self.time_windows
                },
                "repositories": {window: set() for window in self.time_windows},
            }

        author_metrics = metrics["authors"][author_email]
        for window in applicable_windows:
            author_metrics["commit_counts"][window] += 1
            author_metrics["loc_stats"][window]["added"] += total_added
            author_metrics["loc_stats"][window]["removed"] += total_removed
            author_metrics["loc_stats"][window]["net"] += net_lines
            author_metrics["repositories"][window].add(metrics["repository"]["gerrit_project"])

    def _finalize_repo_metrics(self, metrics: dict[str, Any], repo_name: str) -> None:
        """Finalize repository metrics after processing all commits."""
        repo_metrics = metrics["repository"]

        # Check if repository has any commits at all
        if repo_metrics.get("has_any_commits", False):
            # Repository has commits - find last commit date
            git_command = ["git", "log", "-1", "--date=iso", "--pretty=format:%ad"]
            success, output = safe_git_command(
                git_command, Path(repo_metrics["local_path"]), self.logger
            )

            if success and output.strip():
                try:
                    last_commit_date = parse_git_iso_date(output.strip())
                    if last_commit_date.tzinfo is None:
                        last_commit_date = last_commit_date.replace(tzinfo=datetime.UTC)

                    repo_metrics["last_commit_timestamp"] = last_commit_date.isoformat()

                    # Calculate days since last commit
                    now = datetime.datetime.now(datetime.UTC)
                    days_since = (now - last_commit_date).days
                    repo_metrics["days_since_last_commit"] = days_since

                    # Determine activity status using unified thresholds
                    activity_thresholds = self.config.get("activity_thresholds", {})
                    current_threshold = activity_thresholds.get("current_days", 365)
                    active_threshold = activity_thresholds.get("active_days", 1095)

                    has_recent_commits = any(
                        count > 0 for count in repo_metrics["commit_counts"].values()
                    )

                    if has_recent_commits and days_since <= current_threshold:
                        repo_metrics["activity_status"] = "current"
                    elif has_recent_commits and days_since <= active_threshold:
                        repo_metrics["activity_status"] = "active"
                    else:
                        repo_metrics["activity_status"] = "inactive"

                    if any(count > 0 for count in repo_metrics["commit_counts"].values()):
                        self.logger.debug(
                            f"Repository {repo_name} has {repo_metrics['total_commits_ever']} commits ({sum(repo_metrics['commit_counts'].values())} recent)"
                        )
                    else:
                        self.logger.debug(
                            f"Repository {repo_name} has {repo_metrics['total_commits_ever']} commits (all historical, none recent)"
                        )

                except ValueError as e:
                    self.logger.warning(f"Could not parse last commit date for {repo_name}: {e}")
        else:
            # Truly no commits - empty repository
            self.logger.info(f"Repository {repo_name} has no commits")

        # Convert author repository sets to counts for JSON serialization
        for _author_email, author_data in metrics["authors"].items():
            for window in self.time_windows:
                author_data["repositories"][window] = len(author_data["repositories"][window])

        # Embed authors data in repository record for aggregation
        repo_authors = []
        for _author_email, author_data in metrics["authors"].items():
            # Convert author data to expected format for aggregation
            author_record = {
                "name": author_data["name"],
                "email": author_data["email"],
                "username": author_data["username"],
                "domain": author_data["domain"],
                "commits": author_data["commit_counts"],
                "lines_added": {
                    window: author_data["loc_stats"][window]["added"]
                    for window in self.time_windows
                },
                "lines_removed": {
                    window: author_data["loc_stats"][window]["removed"]
                    for window in self.time_windows
                },
                "lines_net": {
                    window: author_data["loc_stats"][window]["net"] for window in self.time_windows
                },
                "repositories": author_data["repositories"],
            }
            repo_authors.append(author_record)

        metrics["repository"]["authors"] = repo_authors
