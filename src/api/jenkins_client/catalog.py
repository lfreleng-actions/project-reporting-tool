# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Jenkins job catalogue.

Fetches and caches the full job listing for a Jenkins server; the
attribution strategies match against this cached catalogue.
"""

from typing import Any

import httpx

from ..base_client import BaseAPIClient


class JenkinsCatalogMixin(BaseAPIClient):
    """Cached retrieval of the complete Jenkins job listing."""

    # Assigned by JenkinsAPIClient.__init__; declared here for type checking.
    host: str
    base_url: str
    api_base_path: str | None
    client: httpx.Client
    _jobs_cache: dict[str, Any]
    _cache_populated: bool

    def get_all_jobs(self) -> dict[str, Any]:
        """
        Get all jobs from Jenkins with caching.

        Returns:
            Dictionary containing jobs array and metadata.
            Returns empty dict on error.

        Example:
            >>> client = JenkinsAPIClient("jenkins.example.com")
            >>> jobs_data = client.get_all_jobs()
            >>> for job in jobs_data.get('jobs', []):
            ...     print(job['name'])
        """
        # Return cached data if available
        if self._cache_populated and self._jobs_cache:
            self.logger.debug(
                f"Using cached Jenkins jobs data ({len(self._jobs_cache.get('jobs', []))} jobs)"
            )
            return self._jobs_cache

        if not self.api_base_path:
            self.logger.error(f"No valid API base path discovered for {self.host}")
            return {}

        try:
            url = (
                f"{self.base_url}{self.api_base_path}?tree=jobs[name,url,color,buildable,disabled]"
            )
            self.logger.debug(f"Fetching Jenkins jobs from: {url}")
            response = self.client.get(url)

            self.logger.debug(f"Jenkins API response: {response.status_code}")
            if response.status_code == 200:
                if self.stats:
                    self.stats.record_success("jenkins")
                data = response.json()
                job_count = len(data.get("jobs", []))
                self.logger.debug(f"Found {job_count} Jenkins jobs (cached for reuse)")

                # Cache the data
                self._jobs_cache = data
                self._cache_populated = True
                return dict(data)
            else:
                if self.stats:
                    self.stats.record_error("jenkins", response.status_code)
                self.logger.warning(
                    f"❌ Error: Jenkins API query returned error code: {response.status_code} for {url}"
                )
                self.logger.warning(f"Response text: {response.text[:500]}")
                return {}

        except Exception as e:
            if self.stats:
                self.stats.record_exception("jenkins")
            self.logger.error(f"❌ Error: Jenkins API query exception for {self.host}: {e}")
            return {}
