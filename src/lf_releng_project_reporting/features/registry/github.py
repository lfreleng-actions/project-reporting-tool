# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
GitHub API backed checks and GitHub repository identity.

Everything that needs to know which GitHub repository a working tree
corresponds to, or that talks to the GitHub API: workflow runtime status
augmentation and GitHub mirror existence verification.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class GitHubChecksMixin:
    """GitHub mirror detection and GitHub API queries for the feature registry."""

    # Assigned by FeatureRegistry.__init__; declared here for type checking.
    config: dict[str, Any]
    logger: logging.Logger
    api_stats: Any
    github_org: str
    github_org_source: str

    def _augment_workflows_with_github_api(
        self, result: dict[str, Any], repo_path: Path, workflow_names: list[str]
    ) -> None:
        """Enrich workflow results with GitHub API runtime status when configured.

        No-op unless GitHub API integration is enabled, a token is available,
        an org is known, and the repository is a GitHub repository. Failures
        are logged and swallowed so static analysis results are preserved.
        """
        extensions_config = self.config.get("extensions", {})
        github_api_config = extensions_config.get("github_api", {})
        github_api_enabled = github_api_config.get("enabled", False)
        # Get the configured environment variable name (defaults to GITHUB_TOKEN)
        github_token_env = self.config.get("_github_token_env", "GITHUB_TOKEN")
        github_token = github_api_config.get("token") or os.environ.get(github_token_env)

        is_github_repo = self._is_github_repository(repo_path)

        self.logger.debug(
            f"GitHub API integration check for {repo_path.name}: "
            f"enabled={github_api_enabled}, has_token={bool(github_token)}, "
            f"github_org={self.github_org} (source={self.github_org_source}), "
            f"is_github_repo={is_github_repo}"
        )

        if github_api_enabled and not github_token:
            self.logger.warning(
                f"GitHub API enabled but token not available ({github_token_env}). "
                f"Workflow status will not be queried for {repo_path.name}"
            )

        if not (github_api_enabled and github_token and self.github_org and is_github_repo):
            return

        try:
            owner, repo_name = self._extract_github_repo_info(repo_path, self.github_org)
            self.logger.debug(f"Attempting GitHub API query for {owner}/{repo_name}")
            if not (owner and repo_name):
                return

            # Resolve through the package facade to retain the historical
            # ``features.registry.GitHubAPIClient`` patch point.
            from . import GitHubAPIClient

            github_client = GitHubAPIClient(github_token, stats=self.api_stats)
            github_status = github_client.get_repository_workflow_status_summary(owner, repo_name)

            # Merge GitHub API data with static analysis
            result["github_api_data"] = github_status
            result["has_runtime_status"] = True

            self.logger.debug(f"Retrieved GitHub workflow status for {owner}/{repo_name}")

            # If no local workflows were found but GitHub has workflows, use GitHub as source
            # This handles cases where Gerrit is primary but GitHub mirror has workflows
            if not workflow_names and github_status.get("workflows"):
                github_workflow_names = [
                    os.path.basename(workflow.get("path", ""))
                    for workflow in github_status.get("workflows", [])
                    if workflow.get("path")
                ]
                if github_workflow_names:
                    result["workflow_names"] = github_workflow_names
                    result["count"] = len(github_workflow_names)
                    self.logger.debug(
                        f"Using GitHub API as workflow source for {owner}/{repo_name}: "
                        f"{github_workflow_names}"
                    )

        except Exception as e:
            self.logger.warning(f"Failed to fetch GitHub workflow status for {repo_path}: {e}")

    def _check_github_mirror(self, repo_path: Path) -> dict[str, Any]:
        """
        Check if repository has a GitHub mirror that actually exists.

        Args:
            repo_path: Path to the repository

        Returns:
            Dict with keys: exists (bool), owner (str), repo (str), reason (str)
        """
        try:
            # First check if it looks like a GitHub repository
            has_github_indicators = self._is_github_repository(repo_path)

            if not has_github_indicators:
                return {
                    "exists": False,
                    "owner": "",
                    "repo": "",
                    "reason": "no_github_indicators",
                }

            # Check if the GitHub repository actually exists
            owner, repo_name = self._extract_github_repo_info(repo_path)
            if not owner or not repo_name:
                return {
                    "exists": False,
                    "owner": owner,
                    "repo": repo_name,
                    "reason": "cannot_determine_github_info",
                }

            # Verify the repository exists on GitHub
            exists = self._check_github_mirror_exists(repo_path)

            return {
                "exists": exists,
                "owner": owner,
                "repo": repo_name,
                "reason": "verified" if exists else "not_found_on_github",
            }

        except Exception as e:
            self.logger.debug(f"GitHub mirror check failed for {repo_path}: {e}")
            return {
                "exists": False,
                "owner": "",
                "repo": "",
                "reason": f"error: {str(e)}",
            }

    def _is_github_repository(self, repo_path: Path) -> bool:
        """
        Check if repository is hosted on GitHub by examining git remotes.

        Args:
            repo_path: Path to the repository

        Returns:
            True if repository has GitHub indicators
        """
        try:
            git_dir = repo_path / ".git"
            if not git_dir.exists():
                return False

            # Read git config or remote files
            config_file = git_dir / "config"
            if config_file.exists():
                with open(config_file, encoding="utf-8") as f:
                    content = f.read()
                    # Parse remote URLs from git config,
                    # restricting to [remote "..."] sections
                    # and skipping commented lines.
                    in_remote_section = False
                    for line in content.splitlines():
                        stripped = line.strip()

                        if not stripped or stripped.startswith(("#", ";")):
                            continue

                        section_match = re.match(r"^\[(.+)\]$", stripped)
                        if section_match:
                            section_name = section_match.group(1).strip().lower()
                            in_remote_section = section_name.startswith("remote ")
                            continue

                        if not in_remote_section:
                            continue

                        url_match = re.match(r"^url\s*=\s*(.+)$", stripped)
                        if not url_match:
                            continue

                        remote_url = url_match.group(1).strip()
                        parsed = urlparse(remote_url)
                        if parsed.hostname and parsed.hostname.lower() == "github.com":
                            return True
                        # Handle SSH URLs (git@github.com:org/repo)
                        ssh_match = re.match(r"[^@]+@([^:]+):", remote_url)
                        if ssh_match and ssh_match.group(1).lower() == "github.com":
                            return True

            # For ONAP and other projects that are mirrored on GitHub,
            # check if they have GitHub workflows (indicates GitHub presence)
            # If we have GitHub workflows, assume it's mirrored on GitHub
            workflows_dir = repo_path / ".github" / "workflows"
            return workflows_dir.exists() and any(workflows_dir.iterdir())
        except Exception:
            return False

    def _check_github_mirror_exists(self, repo_path: Path) -> bool:
        """
        Check if repository actually exists on GitHub by making an API call.

        Args:
            repo_path: Path to the repository

        Returns:
            True if repository exists on GitHub
        """
        try:
            owner, repo_name = self._extract_github_repo_info(repo_path)
            if not owner or not repo_name:
                return False

            # Try to access GitHub API to verify repository exists
            # Get the configured environment variable name (defaults to GITHUB_TOKEN)
            github_token_env = self.config.get("_github_token_env", "GITHUB_TOKEN")
            extensions_config = self.config.get("extensions", {})
            github_api_config = extensions_config.get("github_api", {})
            github_token = github_api_config.get("token") or os.environ.get(github_token_env)

            if github_token:
                try:
                    # Resolve through the package facade to retain the historical
                    # ``features.registry.GitHubAPIClient`` patch point.
                    from . import GitHubAPIClient

                    github_client = GitHubAPIClient(github_token, stats=self.api_stats)
                    response = github_client.client.get(f"/repos/{owner}/{repo_name}")
                    return bool(response.status_code == 200)
                except Exception as e:
                    self.logger.debug(f"GitHub API check failed for {owner}/{repo_name}: {e}")

            # Fallback: make a simple HTTP request without authentication
            try:
                import httpx

                with httpx.Client(timeout=10.0) as client:
                    response = client.get(f"https://api.github.com/repos/{owner}/{repo_name}")
                    return bool(response.status_code == 200)
            except Exception as e:
                self.logger.debug(
                    f"GitHub repository existence check failed for {owner}/{repo_name}: {e}"
                )
                return False

        except Exception:
            return False

    def _extract_github_repo_info(self, repo_path: Path, github_org: str = "") -> tuple[str, str]:
        """
        Extract GitHub owner and repo name from git remote or configuration.

        Args:
            repo_path: Path to the repository
            github_org: GitHub organization name from configuration (for Gerrit mirrors)

        Returns:
            Tuple of (owner, repo_name)
        """
        try:
            git_dir = repo_path / ".git"
            config_file = git_dir / "config"

            if not config_file.exists():
                # For mirrored repos, use configured github_org
                return self._infer_github_info_from_path(repo_path, github_org)

            with open(config_file) as f:
                content = f.read()

            # Look for GitHub remote URLs
            # Match both HTTPS and SSH formats
            patterns = [
                r"url = https://github\.com/([^/]+)/([^/\s]+)(?:\.git)?",
                r"url = git@github\.com:([^/]+)/([^/\s]+)(?:\.git)?",
            ]

            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    owner, repo = match.groups()
                    repo = repo.rstrip(".git")
                    return owner, repo

            # Fallback to path-based inference for mirrored repos
            return self._infer_github_info_from_path(repo_path, github_org)
        except Exception:
            return "", ""

    def _infer_github_info_from_path(
        self, repo_path: Path, github_org: str = ""
    ) -> tuple[str, str]:
        """
        Infer GitHub owner/repo from repository path for mirrored repos.

        For Gerrit repos mirrored to GitHub, the path structure is typically:
        ./gerrit.example.org/repo-name -> github_org/repo-name

        Args:
            repo_path: Path to the repository
            github_org: GitHub organization name from configuration

        Returns:
            Tuple of (owner, repo_name)
        """
        try:
            if not github_org:
                self.logger.debug(
                    f"Cannot infer GitHub info for {repo_path.name}: github_org not provided"
                )
                return "", ""

            # Get just the repository name from the path
            # For paths like ./gerrit.onap.org/aai/babel, we want "aai-babel"
            # For paths like ./gerrit.onap.org/simple-repo, we want "simple-repo"
            path_parts = repo_path.parts

            # Find the Gerrit host in the path (e.g., "gerrit.onap.org")
            gerrit_host_index = -1
            for i, part in enumerate(path_parts):
                # Only match actual Gerrit server hostnames (e.g., "gerrit.onap.org")
                # Not directory names like "lf-releng-project-reporting"
                if "gerrit." in part.lower() or part.lower().startswith("git."):
                    gerrit_host_index = i
                    break

            if gerrit_host_index >= 0 and gerrit_host_index < len(path_parts) - 1:
                repo_parts = path_parts[gerrit_host_index + 1 :]
                if repo_parts:
                    # Join multi-level paths with hyphens
                    # e.g., ["aai", "babel"] -> "aai-babel"
                    repo_name = "-".join(repo_parts)
                    self.logger.debug(
                        f"Inferred GitHub repo: {github_org}/{repo_name} from path {repo_path}"
                    )
                    return github_org, repo_name

            # Fallback: use just the repo name
            repo_name = repo_path.name
            self.logger.debug(
                f"Using fallback GitHub repo: {github_org}/{repo_name} from path {repo_path}"
            )
            return github_org, repo_name

        except Exception as e:
            self.logger.debug(f"Failed to infer GitHub info for {repo_path}: {e}")
            return "", ""
