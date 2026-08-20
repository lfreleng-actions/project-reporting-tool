# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Issue tracker URL validation batching for the enricher.

Validates the issue tracking URLs of a batch of projects either serially or
concurrently, and exposes the underlying validator's cache controls.
"""

import asyncio
import logging

from domain.info_yaml import ProjectInfo

from ..validator import URLValidator


class EnricherURLMixin:
    """Batched URL validation and URL cache management."""

    # Assigned by InfoYamlEnricher.__init__; declared here for type checking.
    logger: logging.Logger
    url_validator: URLValidator

    def _validate_urls_sync_batch(self, projects: list[ProjectInfo]) -> None:
        """
        Validate URLs synchronously for a batch of projects.

        Args:
            projects: List of ProjectInfo objects to validate
        """
        for project in projects:
            if project.issue_tracking.url:
                is_valid, error = self.url_validator.validate(project.issue_tracking.url)
                project.issue_tracking.is_valid = is_valid
                project.issue_tracking.validation_error = error

    def _validate_urls_async_batch(
        self, projects: list[ProjectInfo], max_concurrent: int = 10
    ) -> None:
        """
        Validate URLs asynchronously for a batch of projects.

        Args:
            projects: List of ProjectInfo objects to validate
            max_concurrent: Maximum concurrent validations
        """
        # Collect all URLs to validate
        url_to_projects: dict[str, list[ProjectInfo]] = {}
        for project in projects:
            url = project.issue_tracking.url
            if url:
                if url not in url_to_projects:
                    url_to_projects[url] = []
                url_to_projects[url].append(project)

        if not url_to_projects:
            return

        urls = list(url_to_projects.keys())
        self.logger.info(
            f"Validating {len(urls)} unique URLs asynchronously (max_concurrent={max_concurrent})"
        )

        # Always use asyncio.run() in synchronous context
        results = asyncio.run(self.url_validator.validate_bulk_async(urls, max_concurrent))

        # Apply results to projects
        for url, (is_valid, error) in results.items():
            for project in url_to_projects[url]:
                project.issue_tracking.is_valid = is_valid
                project.issue_tracking.validation_error = error

    def clear_url_cache(self) -> None:
        """Clear the URL validation cache."""
        self.url_validator.clear_cache()
        self.logger.debug("URL validation cache cleared")

    def get_url_cache_stats(self) -> dict[str, int]:
        """
        Get URL validation cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        result = self.url_validator.get_cache_stats()
        return dict(result)
