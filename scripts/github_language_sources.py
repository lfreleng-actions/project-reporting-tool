# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Language and project type data sources for the GitHub comparison script.

Collects language data from the GitHub API and project type data from
locally cloned repositories for ``scripts/compare_github_languages.py``.
"""

import logging
import sys
from pathlib import Path
from typing import Any


try:
    import httpx
except ImportError:
    print("Error: httpx is required. Install with: pip install httpx")
    sys.exit(1)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lf_releng_project_reporting.features.registry import FeatureRegistry


class GitHubLanguageAnalyzer:
    """Fetch and analyze GitHub language detection for repositories."""

    def __init__(self, token: str, timeout: float = 30.0):
        """Initialize GitHub API client."""
        self.token = token
        self.base_url = "https://api.github.com"
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "lf-releng-project-reporting/compare-languages",
            },
        )
        self.logger = logging.getLogger(__name__)

    def close(self):
        """Close the httpx client."""
        self.client.close()

    def get_organization_repos(self, org: str) -> list[dict[str, Any]]:
        """
        Fetch all repositories for an organization.

        Args:
            org: GitHub organization name

        Returns:
            List of repository information dicts
        """
        repos = []
        page = 1
        per_page = 100

        self.logger.info(f"Fetching repositories for organization: {org}")

        while True:
            try:
                response = self.client.get(
                    f"/orgs/{org}/repos",
                    params={"page": page, "per_page": per_page, "type": "all"},
                )
                response.raise_for_status()
                page_repos = response.json()

                if not page_repos:
                    break

                repos.extend(page_repos)
                self.logger.info(f"Fetched {len(repos)} repositories so far...")
                page += 1

            except httpx.HTTPStatusError as e:
                self.logger.error(f"HTTP error fetching repos: {e}")
                break
            except Exception as e:
                self.logger.error(f"Error fetching repos: {e}")
                break

        self.logger.info(f"Total repositories found: {len(repos)}")
        return repos

    def get_repository_languages(self, owner: str, repo: str) -> dict[str, int]:
        """
        Fetch language statistics for a repository.

        Args:
            owner: Repository owner/organization
            repo: Repository name

        Returns:
            Dict mapping language names to byte counts
        """
        try:
            response = self.client.get(f"/repos/{owner}/{repo}/languages")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            self.logger.warning(f"HTTP error fetching languages for {owner}/{repo}: {e}")
            return {}
        except Exception as e:
            self.logger.warning(f"Error fetching languages for {owner}/{repo}: {e}")
            return {}

    def analyze_organization(self, org: str) -> dict[str, dict[str, Any]]:
        """
        Analyze all repositories in an organization.

        Args:
            org: GitHub organization name

        Returns:
            Dict mapping repo names to their language data
        """
        repos = self.get_organization_repos(org)
        results = {}

        for repo in repos:
            repo_name = repo["name"]
            self.logger.debug(f"Fetching languages for {repo_name}")

            languages = self.get_repository_languages(org, repo_name)

            # Calculate primary language (most bytes)
            primary_language = None
            if languages:
                primary_language = max(languages.items(), key=lambda x: x[1])[0]

            results[repo_name] = {
                "full_name": repo["full_name"],
                "html_url": repo["html_url"],
                "github_primary_language": repo.get("language"),  # GitHub's reported primary
                "languages": languages,
                "calculated_primary": primary_language,
                "total_bytes": sum(languages.values()),
                "archived": repo.get("archived", False),
                "fork": repo.get("fork", False),
            }

        return results


class LocalProjectTypeAnalyzer:
    """Analyze project types using local detection."""

    def __init__(self):
        """Initialize local analyzer."""
        self.logger = logging.getLogger(__name__)
        config = {"features": {"enabled": ["project_types"]}}
        self.registry = FeatureRegistry(config, self.logger)

    def analyze_repository(self, repo_path: Path) -> dict[str, Any]:
        """
        Analyze a local repository.

        Args:
            repo_path: Path to repository

        Returns:
            Dict with detected project types
        """
        if not repo_path.exists():
            return {
                "error": "Repository path not found",
                "detected_types": [],
                "primary_type": None,
            }

        try:
            result = self.registry._check_project_types(repo_path)
            return result
        except Exception as e:
            self.logger.error(f"Error analyzing {repo_path}: {e}")
            return {
                "error": str(e),
                "detected_types": [],
                "primary_type": None,
            }

    def find_repository_path(self, base_path: Path, github_repo_name: str) -> Path | None:
        """
        Find repository path supporting both flat and Gerrit-style structures.

        GitHub repo names like "aai-aai-common" map to Gerrit structure like:
        - /base/aai/aai-common  (Gerrit style: project/subproject)
        - /base/aai-aai-common  (flat style)

        Args:
            base_path: Base directory containing repositories
            github_repo_name: GitHub repository name (e.g., "aai-aai-common")

        Returns:
            Path to repository if found, None otherwise
        """
        # Try flat structure first
        flat_path = base_path / github_repo_name
        if flat_path.exists() and flat_path.is_dir():
            return flat_path

        # Try Gerrit-style structure (project/subproject)
        # GitHub name format: {project}-{subproject} or variations
        parts = github_repo_name.split("-", 1)
        if len(parts) == 2:
            project, subproject = parts
            gerrit_path = base_path / project / subproject
            if gerrit_path.exists() and gerrit_path.is_dir():
                return gerrit_path

        # For repos with multiple hyphens, try different splits
        # e.g., "aai-aai-common" -> try "aai/aai-common"
        parts = github_repo_name.split("-")
        if len(parts) > 2:
            for i in range(1, len(parts)):
                project = "-".join(parts[:i])
                subproject = "-".join(parts[i:])
                gerrit_path = base_path / project / subproject
                if gerrit_path.exists() and gerrit_path.is_dir():
                    return gerrit_path

        return None

    def analyze_repositories(
        self, repos_path: Path, repo_names: list[str]
    ) -> dict[str, dict[str, Any]]:
        """
        Analyze multiple local repositories.

        Args:
            repos_path: Base path containing repositories
            repo_names: List of repository names to analyze

        Returns:
            Dict mapping repo names to detection results (only for repos found locally)
        """
        results = {}

        for repo_name in repo_names:
            # Try to find repo in Gerrit-style or flat structure
            repo_path = self.find_repository_path(repos_path, repo_name)

            if repo_path:
                self.logger.debug(f"Analyzing local repository: {repo_name} at {repo_path}")
                results[repo_name] = self.analyze_repository(repo_path)
            else:
                self.logger.debug(f"Repository not found locally, skipping: {repo_name}")
                # Don't add to results - we only want repos that exist locally

        return results
