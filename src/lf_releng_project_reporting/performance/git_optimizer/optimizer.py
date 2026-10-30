# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Main coordinator for git operation optimizations.

Combines the shallow clone strategy and reference repositories into
optimized clone, fetch, log and batch clone operations, and reports
statistics over the resulting operation records.
"""

import contextlib
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from .models import CloneStrategy, GitConfig, GitOperationResult, GitOperationType
from .strategies import ReferenceRepository, ShallowCloneStrategy


class GitOptimizer:
    """
    Main coordinator for git operation optimizations.

    This class provides optimized git operations including shallow clones,
    reference repositories, and efficient git configuration.

    Example:
        >>> optimizer = GitOptimizer(use_shallow=True, use_references=True)
        >>> result = optimizer.clone_optimized(
        ...     url="https://github.com/user/repo.git",
        ...     destination="./repos/repo"
        ... )
        >>> if result.is_success:
        ...     print(f"Cloned in {result.duration:.2f}s")
    """

    def __init__(self, config: GitConfig | None = None, profiler: Any | None = None):
        """
        Initialize git optimizer.

        Args:
            config: Git configuration (uses defaults if None)
            profiler: Optional performance profiler
        """
        self.config = config or GitConfig()
        self.config.validate()
        self.profiler = profiler

        self.shallow_strategy = ShallowCloneStrategy(default_depth=self.config.shallow_depth)

        self.reference_repo = None
        if self.config.use_reference_repos:
            self.reference_repo = ReferenceRepository(reference_dir=self.config.reference_dir)

    def _apply_git_config(self, repo_path: str):
        """
        Apply optimized git configuration to repository.

        Args:
            repo_path: Path to repository
        """
        configs = [
            ("fetch.parallel", str(self.config.parallel_fetch)),
            ("core.compression", str(self.config.compression)),
            ("http.postBuffer", str(self.config.http_post_buffer)),
        ]

        for key, value in configs:
            with contextlib.suppress(Exception):
                subprocess.run(
                    ["git", "config", key, value],
                    cwd=repo_path,
                    check=False,
                    capture_output=True,
                    timeout=5,
                )

    def _run_git_command(
        self,
        args: list[str],
        operation: GitOperationType,
        cwd: str | None = None,
        timeout: int = 300,
    ) -> GitOperationResult:
        """
        Run a git command with timing and error handling.

        Args:
            args: Git command arguments
            operation: Type of git operation
            cwd: Working directory
            timeout: Timeout in seconds

        Returns:
            GitOperationResult
        """
        start_time = time.perf_counter()

        try:
            result = subprocess.run(args, cwd=cwd, capture_output=True, timeout=timeout, text=True)

            duration = time.perf_counter() - start_time

            return GitOperationResult(
                operation=operation,
                success=result.returncode == 0,
                duration=duration,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else "",
            )

        except subprocess.TimeoutExpired:
            duration = time.perf_counter() - start_time
            return GitOperationResult(
                operation=operation,
                success=False,
                duration=duration,
                error=f"Command timed out after {timeout}s",
            )

        except Exception as e:
            duration = time.perf_counter() - start_time
            return GitOperationResult(
                operation=operation, success=False, duration=duration, error=str(e)
            )

    def clone_optimized(
        self,
        url: str,
        destination: str,
        strategy: CloneStrategy | None = None,
        branch: str | None = None,
    ) -> GitOperationResult:
        """
        Clone repository with optimizations.

        Args:
            url: Repository URL
            destination: Destination path
            strategy: Clone strategy (auto-detect if None)
            branch: Specific branch to clone

        Returns:
            GitOperationResult
        """
        # Auto-detect strategy
        if strategy is None:
            if self.config.use_reference_repos and self.config.shallow_clone:
                strategy = CloneStrategy.SHALLOW_REFERENCE
            elif self.config.use_reference_repos:
                strategy = CloneStrategy.REFERENCE
            elif self.config.shallow_clone:
                strategy = CloneStrategy.SHALLOW
            else:
                strategy = CloneStrategy.FULL

        cmd = ["git", "clone"]

        # Add shallow clone options
        if strategy in (CloneStrategy.SHALLOW, CloneStrategy.SHALLOW_REFERENCE):
            cmd.extend(["--depth", str(self.config.shallow_depth)])
            cmd.append("--single-branch")

        # Add reference repository
        if (
            strategy in (CloneStrategy.REFERENCE, CloneStrategy.SHALLOW_REFERENCE)
            and self.reference_repo
        ):
            ref_path = self.reference_repo.get_reference(url, auto_create=True)
            if ref_path:
                cmd.extend(["--reference", str(ref_path)])

        # Add branch if specified
        if branch:
            cmd.extend(["--branch", branch])

        # Add URL and destination
        cmd.extend([url, destination])

        # Track with profiler if available
        if self.profiler:
            with self.profiler.track_operation(
                f"git_clone_{Path(destination).name}",
                category="git",
                metadata={"strategy": strategy.value, "url": url},
            ):
                result = self._run_git_command(cmd, GitOperationType.CLONE, timeout=600)
        else:
            result = self._run_git_command(cmd, GitOperationType.CLONE, timeout=600)

        result.strategy = strategy

        # Apply git config if successful
        if result.is_success and os.path.exists(destination):
            self._apply_git_config(destination)

        return result

    def fetch_optimized(
        self, repo_path: str, remote: str = "origin", prune: bool = True
    ) -> GitOperationResult:
        """
        Fetch with optimizations.

        Args:
            repo_path: Path to repository
            remote: Remote name
            prune: Prune deleted branches

        Returns:
            GitOperationResult
        """
        cmd = ["git", "fetch", remote]

        if prune:
            cmd.append("--prune")

        if self.profiler:
            with self.profiler.track_operation(f"git_fetch_{Path(repo_path).name}", category="git"):
                return self._run_git_command(cmd, GitOperationType.FETCH, cwd=repo_path)
        else:
            return self._run_git_command(cmd, GitOperationType.FETCH, cwd=repo_path)

    def get_log(
        self,
        repo_path: str,
        max_count: int | None = None,
        since: str | None = None,
        format: str = "oneline",
    ) -> GitOperationResult:
        """
        Get git log with optimizations.

        Args:
            repo_path: Path to repository
            max_count: Maximum number of commits
            since: Get commits since date/time
            format: Log format

        Returns:
            GitOperationResult
        """
        cmd = ["git", "log", f"--format={format}"]

        if max_count:
            cmd.extend(["-n", str(max_count)])

        if since:
            cmd.extend(["--since", since])

        return self._run_git_command(cmd, GitOperationType.LOG, cwd=repo_path, timeout=60)

    def batch_clone(
        self, repositories: list[tuple[str, str]], parallel_processor: Any | None = None
    ) -> list[GitOperationResult]:
        """
        Clone multiple repositories, optionally in parallel.

        Args:
            repositories: List of (url, destination) tuples
            parallel_processor: Optional ParallelRepositoryProcessor

        Returns:
            List of GitOperationResults
        """
        if parallel_processor:
            # Use parallel processing
            def clone_func(repo_info):
                url, dest = repo_info
                return self.clone_optimized(url, dest)

            aggregated = parallel_processor.process_repositories(
                repositories=repositories, processor_func=clone_func
            )

            results = []
            for item in aggregated.successful:
                results.append(item.result)
            for item in aggregated.failed:
                url, dest = repositories[len(results)]
                results.append(
                    GitOperationResult(
                        operation=GitOperationType.CLONE,
                        success=False,
                        duration=item.duration,
                        error=item.error or "Unknown error",
                    )
                )

            return results
        else:
            # Sequential cloning
            results = []
            for url, destination in repositories:
                result = self.clone_optimized(url, destination)
                results.append(result)

            return results

    def get_statistics(self, results: list[GitOperationResult]) -> dict[str, Any]:
        """
        Get statistics from git operation results.

        Args:
            results: List of git operation results

        Returns:
            Dictionary with statistics
        """
        if not results:
            return {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "total_duration": 0.0,
                "avg_duration": 0.0,
            }

        successful = [r for r in results if r.is_success]
        failed = [r for r in results if r.is_failure]

        total_duration = sum(r.duration for r in results)
        avg_duration = total_duration / len(results)

        # Group by strategy
        strategy_counts: dict[str, int] = {}
        for result in results:
            if result.strategy:
                key = result.strategy.value
                strategy_counts[key] = strategy_counts.get(key, 0) + 1

        return {
            "total": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(results) * 100,
            "total_duration": total_duration,
            "avg_duration": avg_duration,
            "min_duration": min(r.duration for r in results),
            "max_duration": max(r.duration for r in results),
            "strategies": strategy_counts,
        }
