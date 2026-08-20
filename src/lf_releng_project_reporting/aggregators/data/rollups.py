# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Author and organization rollups for the data aggregator.

Merges per-repository author records by email address and groups the
resulting authors by email domain into organization totals.
"""

import logging
from collections import defaultdict
from typing import Any, cast


class AggregatorRollupsMixin:
    """Cross-repository author and organization aggregation."""

    # Assigned by DataAggregator.__init__; declared here for type checking.
    logger: logging.Logger

    def compute_author_rollups(self, repo_metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Aggregate author metrics across all repositories.

        Merges author data by email address, summing metrics across all repos
        and tracking unique repositories touched per time window.
        """
        author_aggregates: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "name": "",
                "email": "",
                "username": "",
                "domain": "",
                "repositories_touched": defaultdict(set),
                "commits": defaultdict(int),
                "lines_added": defaultdict(int),
                "lines_removed": defaultdict(int),
                "lines_net": defaultdict(int),
            }
        )

        # Aggregate across all repositories
        for repo in repo_metrics:
            repo_name = repo.get("gerrit_project", "unknown")

            for author in repo.get("authors", []):
                email = author.get("email", "").lower().strip()
                if not email or email == "unknown@unknown":
                    continue

                # Initialize author info (first occurrence wins for name/username)
                if not author_aggregates[email]["name"]:
                    author_aggregates[email]["name"] = author.get("name", "")
                    author_aggregates[email]["email"] = email
                    author_aggregates[email]["username"] = author.get("username", "")
                    author_aggregates[email]["domain"] = author.get("domain", "")

                # Aggregate metrics for each time window
                for window_name in author.get("commits", {}):
                    repos_set = cast(
                        set[str],
                        author_aggregates[email]["repositories_touched"][window_name],
                    )
                    repos_set.add(repo_name)
                    author_aggregates[email]["commits"][window_name] += author.get(
                        "commits", {}
                    ).get(window_name, 0)
                    author_aggregates[email]["lines_added"][window_name] += author.get(
                        "lines_added", {}
                    ).get(window_name, 0)
                    author_aggregates[email]["lines_removed"][window_name] += author.get(
                        "lines_removed", {}
                    ).get(window_name, 0)
                    author_aggregates[email]["lines_net"][window_name] += author.get(
                        "lines_net", {}
                    ).get(window_name, 0)

        # Convert to list format and finalize repository counts
        authors: list[dict[str, Any]] = []
        for email, data in author_aggregates.items():
            author_record = {
                "name": data["name"],
                "email": email,
                "username": data["username"],
                "domain": data["domain"],
                "commits": dict(data["commits"]),
                "lines_added": dict(data["lines_added"]),
                "lines_removed": dict(data["lines_removed"]),
                "lines_net": dict(data["lines_net"]),
                "repositories_touched": {
                    window: set(repos) for window, repos in data["repositories_touched"].items()
                },
                "repositories_count": {
                    window: len(repos) for window, repos in data["repositories_touched"].items()
                },
            }
            authors.append(author_record)

        self.logger.info(f"Aggregated {len(authors)} unique authors across repositories")
        return authors

    def compute_org_rollups(self, authors: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Aggregate organization metrics from author data.

        Groups authors by email domain and aggregates their contributions.
        """
        org_aggregates: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "domain": "",
                "contributor_count": 0,
                "contributors": set(),
                "commits": defaultdict(int),
                "lines_added": defaultdict(int),
                "lines_removed": defaultdict(int),
                "lines_net": defaultdict(int),
                "repositories_count": defaultdict(set),
            }
        )

        # Aggregate by domain
        for author in authors:
            domain = author.get("domain", "").strip().lower()
            if not domain or domain in ["unknown", "localhost", ""]:
                continue

            org_aggregates[domain]["domain"] = domain
            contributors_set = cast(set[str], org_aggregates[domain]["contributors"])
            contributors_set.add(author.get("email", ""))

            # Sum metrics across all time windows
            author_commits = author.get("commits") or {}
            author_lines_added = author.get("lines_added", {})
            author_lines_removed = author.get("lines_removed", {})
            author_lines_net = author.get("lines_net", {})
            author_repositories_touched = author.get("repositories_touched", {})
            for window_name in author_commits:
                org_aggregates[domain]["commits"][window_name] += author_commits.get(window_name, 0)
                org_aggregates[domain]["lines_added"][window_name] += author_lines_added.get(
                    window_name, 0
                )
                org_aggregates[domain]["lines_removed"][window_name] += author_lines_removed.get(
                    window_name, 0
                )
                org_aggregates[domain]["lines_net"][window_name] += author_lines_net.get(
                    window_name, 0
                )

                # Track unique repositories per organization
                author_repos = author_repositories_touched.get(window_name, set())
                if author_repos:
                    repos_set = cast(
                        set[str],
                        org_aggregates[domain]["repositories_count"][window_name],
                    )
                    repos_set.update(author_repos)

        # Convert to list format
        organizations = []
        for domain, data in org_aggregates.items():
            org_record = {
                "domain": domain,
                "contributor_count": len(data["contributors"]),
                "commits": dict(data["commits"]),
                "lines_added": dict(data["lines_added"]),
                "lines_removed": dict(data["lines_removed"]),
                "lines_net": dict(data["lines_net"]),
                "repositories_count": {
                    window: len(repos) for window, repos in data["repositories_count"].items()
                },
            }
            organizations.append(org_record)

        self.logger.info(f"Aggregated {len(organizations)} organizations from author domains")
        return organizations
