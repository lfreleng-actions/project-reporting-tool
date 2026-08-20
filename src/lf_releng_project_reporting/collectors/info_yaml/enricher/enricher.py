# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Enricher construction and top-level enrichment entry points.

Owns the activity windows, URL validator and committer matcher, composes the
behaviour mixins into the public ``InfoYamlEnricher``, and provides the
module-level convenience wrappers.
"""

import logging
from typing import Any

from domain.info_yaml import ProjectInfo

from .matching import EnricherMatchingMixin
from .statistics import EnricherStatisticsMixin
from .urls import EnricherURLMixin


class InfoYamlEnricher(
    EnricherMatchingMixin,
    EnricherURLMixin,
    EnricherStatisticsMixin,
):
    """
    Enriches INFO.yaml project data with Git repository information.

    Matches projects to Git repositories, determines committer activity status,
    assigns color codes, and validates issue tracker URLs.
    """

    def __init__(
        self,
        activity_windows: dict[str, int] | None = None,
        validate_urls: bool = True,
        url_timeout: float = 10.0,
        url_retries: int = 2,
    ):
        """
        Initialize the enricher.

        Args:
            activity_windows: Activity thresholds in days
                {
                    "current": 365,  # Green - active within 365 days
                    "active": 1095,  # Orange - active 365-1095 days ago
                    # Red - inactive 1095+ days (implicit)
                }
            validate_urls: Enable URL validation (default: True)
            url_timeout: URL validation timeout in seconds (default: 10.0)
            url_retries: URL validation retry count (default: 2)
        """
        # Resolve dependencies through the package facade to preserve the
        # historical mock patch points after the module became a package.
        from . import CommitterMatcher, URLValidator

        self.logger = logging.getLogger(self.__class__.__name__)

        # Activity windows
        self.activity_windows = activity_windows or {
            "current": 365,
            "active": 1095,
        }

        # URL validation settings
        self.validate_urls = validate_urls
        self.url_validator = URLValidator(
            timeout=url_timeout,
            retries=url_retries,
            cache_enabled=True,
        )

        # Committer matcher
        self.matcher = CommitterMatcher()

        self.logger.info("InfoYamlEnricher initialized")
        self.logger.debug(f"Activity windows: {self.activity_windows}")
        self.logger.debug(f"URL validation: {self.validate_urls}")

    def enrich_project(
        self,
        project: ProjectInfo,
        git_metrics: list[dict[str, Any]],
    ) -> ProjectInfo:
        """
        Enrich a single project with Git data.

        Args:
            project: ProjectInfo object to enrich
            git_metrics: List of repository metrics from Git analysis

        Returns:
            Enriched ProjectInfo object
        """
        repo_lookup = self._build_repo_lookup(git_metrics)

        # Find matching repositories
        matched_repos = self._find_matching_repos(project, repo_lookup)

        if matched_repos:
            # Enrich with Git data
            project = self._enrich_with_git_data(project, matched_repos)
        else:
            # No Git data - mark as unknown
            project = self._mark_as_unknown(project)

        if self.validate_urls and project.issue_tracking.url:
            is_valid, error = self.url_validator.validate(project.issue_tracking.url)
            project.issue_tracking.is_valid = is_valid
            project.issue_tracking.validation_error = error

        return project

    def enrich_projects(
        self,
        projects: list[ProjectInfo],
        git_metrics: list[dict[str, Any]],
        use_async_validation: bool = True,
        max_concurrent_urls: int = 10,
    ) -> list[ProjectInfo]:
        """
        Enrich multiple projects with Git data.

        Args:
            projects: List of ProjectInfo objects to enrich
            git_metrics: List of repository metrics from Git analysis
            use_async_validation: Use async URL validation for better performance
            max_concurrent_urls: Maximum concurrent URL validations

        Returns:
            List of enriched ProjectInfo objects
        """
        # First pass: enrich with Git data (no URL validation yet)
        enriched = []
        for project in projects:
            enriched_project = self._enrich_project_without_url(project, git_metrics)
            enriched.append(enriched_project)

        # Second pass: batch validate URLs if enabled
        if self.validate_urls:
            if use_async_validation:
                self._validate_urls_async_batch(enriched, max_concurrent_urls)
            else:
                self._validate_urls_sync_batch(enriched)

        self.logger.info(f"Enriched {len(enriched)} projects")
        return enriched

    def _enrich_project_without_url(
        self,
        project: ProjectInfo,
        git_metrics: list[dict[str, Any]],
    ) -> ProjectInfo:
        """
        Enrich a project with Git data without URL validation.

        Args:
            project: ProjectInfo object to enrich
            git_metrics: List of repository metrics from Git analysis

        Returns:
            Enriched ProjectInfo object (URLs not yet validated)
        """
        repo_lookup = self._build_repo_lookup(git_metrics)

        # Find matching repositories
        matched_repos = self._find_matching_repos(project, repo_lookup)

        if matched_repos:
            # Enrich with Git data
            project = self._enrich_with_git_data(project, matched_repos)
        else:
            # No Git data - mark as unknown
            project = self._mark_as_unknown(project)

        return project


def enrich_project_with_git_data(
    project: ProjectInfo,
    git_metrics: list[dict[str, Any]],
    activity_windows: dict[str, int] | None = None,
) -> ProjectInfo:
    """
    Convenience function to enrich a single project.

    Args:
        project: ProjectInfo object to enrich
        git_metrics: List of repository metrics
        activity_windows: Optional activity thresholds

    Returns:
        Enriched ProjectInfo object
    """
    enricher = InfoYamlEnricher(activity_windows=activity_windows)
    return enricher.enrich_project(project, git_metrics)


def enrich_projects_with_git_data(
    projects: list[ProjectInfo],
    git_metrics: list[dict[str, Any]],
    activity_windows: dict[str, int] | None = None,
    use_async_validation: bool = True,
    max_concurrent_urls: int = 10,
) -> list[ProjectInfo]:
    """
    Convenience function to enrich multiple projects.

    Args:
        projects: List of ProjectInfo objects to enrich
        git_metrics: List of repository metrics
        activity_windows: Optional activity thresholds
        use_async_validation: Use async URL validation for better performance
        max_concurrent_urls: Maximum concurrent URL validations

    Returns:
        List of enriched ProjectInfo objects
    """
    enricher = InfoYamlEnricher(activity_windows=activity_windows)
    return enricher.enrich_projects(
        projects,
        git_metrics,
        use_async_validation=use_async_validation,
        max_concurrent_urls=max_concurrent_urls,
    )
