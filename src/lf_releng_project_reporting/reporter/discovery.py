# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Repository discovery and per-repository analysis dispatch.

Determines the Gerrit server for a working directory, locates the Git
repositories beneath it, and runs the per-repository Git and feature
collection either sequentially or across a thread pool.
"""

import concurrent.futures
import logging
from pathlib import Path
from typing import Any


class ReporterDiscoveryMixin:
    """Repository discovery and per-repository analysis for the reporter."""

    # Assigned by RepositoryReporter.__init__; declared here for type checking.
    config: dict[str, Any]
    logger: logging.Logger
    git_collector: Any
    feature_registry: Any

    def _determine_gerrit_server(self, repos_path: Path) -> str:
        """
        Determine the Gerrit server name from the repositories path.

        The repos_path is typically the Gerrit server hostname (e.g., gerrit.onap.org)
        or contains it as the directory name.

        Args:
            repos_path: Path to the repositories directory

        Returns:
            Gerrit server name (e.g., "gerrit.onap.org", "git.opendaylight.org")
        """
        # Check if the directory name itself is a Gerrit server
        dir_name = repos_path.name

        # Common Gerrit server patterns
        if dir_name.startswith("gerrit.") or dir_name.startswith("git."):
            self.logger.debug(f"Gerrit server determined from directory name: {dir_name}")
            return dir_name

        # Check if there's a gerrit configuration or .gitreview file
        # that might indicate the server
        gitreview_path = repos_path / ".gitreview"
        if gitreview_path.exists():
            try:
                with open(gitreview_path) as f:
                    for line in f:
                        if line.startswith("host="):
                            server = line.split("=", 1)[1].strip()
                            self.logger.debug(f"Gerrit server from .gitreview: {server}")
                            return server
            except Exception as e:
                self.logger.debug(f"Could not read .gitreview: {e}")

        # Fallback: use the directory name
        self.logger.warning(
            f"Could not determine Gerrit server from {repos_path}, using directory name: {dir_name}"
        )
        return dir_name

    def _discover_repositories(self, repos_path: Path) -> list[Path]:
        """
        Find all repository directories recursively with no artificial depth limit.

        Args:
            repos_path: Root path to search for repositories

        Returns:
            List of paths to discovered Git repositories, sorted by depth
            (deepest first) to ensure child projects get processed before parents

        Raises:
            FileNotFoundError: If repos_path does not exist
        """
        if not repos_path.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repos_path}")

        self.logger.debug(f"Discovering repositories recursively under: {repos_path}")

        repo_dirs: list[Path] = []
        access_errors = 0

        # Use rglob to discover all .git directories without a depth limit
        try:
            for git_dir in repos_path.rglob(".git"):
                try:
                    repo_dir = self._validate_discovered_repo(git_dir, repos_path)
                    if repo_dir is not None:
                        repo_dirs.append(repo_dir)
                except (PermissionError, OSError) as e:
                    access_errors += 1
                    self.logger.debug(f"Cannot access potential repository at {git_dir}: {e}")
        except (PermissionError, OSError) as e:
            self.logger.warning(f"Error during repository discovery: {e}")

        # Deduplicate and sort results by path depth (deepest first) to ensure
        # child projects get processed before parent projects for Jenkins job allocation
        unique_repos = list({p.resolve() for p in repo_dirs})
        unique_repos.sort(key=lambda p: (-len(p.parts), str(p)))

        self.logger.info(f"Discovered {len(unique_repos)} git repositories")
        if access_errors:
            self.logger.debug(f"Encountered {access_errors} access errors during discovery")

        return unique_repos

    def _validate_discovered_repo(self, git_dir: Path, repos_path: Path) -> Path | None:
        """Resolve a discovered ``.git`` entry to its repository directory.

        Logs the discovery and, when a Gerrit projects cache is available,
        notes whether the repository is present in it.

        Returns:
            The repository directory, or None if the ``.git`` entry no longer
            exists.
        """
        if not git_dir.exists():
            return None

        repo_dir = git_dir.parent

        # Use relative path from repos_path for clean logging (fallback to absolute)
        try:
            rel_path = str(repo_dir.relative_to(repos_path))
        except ValueError:
            rel_path = str(repo_dir)

        self.logger.debug(f"Found git repository: {rel_path}")

        # Validate against Gerrit API cache if available
        cache = getattr(self.git_collector, "gerrit_projects_cache", None)
        if cache and rel_path in cache:
            self.logger.debug(f"Verified {rel_path} exists in Gerrit")
        elif cache:
            self.logger.warning(f"Repository {rel_path} not found in Gerrit API cache")

        return repo_dir

    def _analyze_repositories_parallel(self, repo_dirs: list[Path]) -> list[dict[str, Any]]:
        """
        Analyze repositories with optional concurrency.

        Args:
            repo_dirs: List of repository paths to analyze

        Returns:
            List of analysis results (metrics or error records)
        """
        performance_config = self.config.get("performance", {})
        max_workers = performance_config.get("max_workers", 8)

        if max_workers == 1:
            # Sequential processing
            return [self._analyze_single_repository(repo_dir) for repo_dir in repo_dirs]

        # Concurrent processing
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_repo = {
                executor.submit(self._analyze_single_repository, repo_dir): repo_dir
                for repo_dir in repo_dirs
            }

            for future in concurrent.futures.as_completed(future_to_repo):
                repo_dir = future_to_repo[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Failed to analyze {repo_dir.name}: {e}")
                    results.append(
                        {
                            "error": str(e),
                            "repo": repo_dir.name,
                            "category": "analysis_failure",
                        }
                    )

        return results

    def _analyze_single_repository(self, repo_path: Path) -> dict[str, Any]:
        """
        Analyze a single repository.

        Args:
            repo_path: Path to repository to analyze

        Returns:
            Repository metrics dictionary or error record
        """
        try:
            self.logger.debug(f"Analyzing repository: {repo_path.name}")

            # Collect Git metrics
            repo_metrics = self.git_collector.collect_repo_git_metrics(repo_path)

            # Scan features
            repo_features = self.feature_registry.detect_features(repo_path)
            repo_metrics["repository"]["features"] = repo_features

            return dict(repo_metrics)

        except Exception as e:
            self.logger.error(f"Error analyzing {repo_path.name}: {e}")
            return {
                "error": str(e),
                "repo": repo_path.name,
                "category": "repository_analysis",
            }
