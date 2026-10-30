# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Jenkins build and job detail queries.

Per-job detail retrieval plus the translation of Jenkins colour and
disabled/buildable fields into the standardised status vocabulary.
"""

from datetime import datetime
from typing import Any

import httpx

from ..base_client import BaseAPIClient


class JenkinsBuildsMixin(BaseAPIClient):
    """Job detail, job state and last-build queries for Jenkins."""

    # Assigned by JenkinsAPIClient.__init__; declared here for type checking.
    base_url: str
    api_base_path: str | None
    client: httpx.Client

    def get_job_details(self, job_name: str) -> dict[str, Any]:
        """
        Get detailed information about a specific job.

        Args:
            job_name: Name of the Jenkins job

        Returns:
            Dictionary with job details including status, state, color, URLs, and last build info.
            Returns empty dict on error.

        Example:
            >>> client = JenkinsAPIClient("jenkins.example.com")
            >>> details = client.get_job_details("my-project-verify")
            >>> print(details['status'])  # e.g., "success"
        """
        try:
            base_path = self.api_base_path.replace("/api/json", "") if self.api_base_path else ""
            url = f"{self.base_url}{base_path}/job/{job_name}/api/json"
            response = self.client.get(url)

            if response.status_code == 200:
                job_data = response.json()

                last_build_info = self.get_last_build_info(job_name)

                # Compute Jenkins job state from disabled field first
                disabled = job_data.get("disabled", False)
                buildable = job_data.get("buildable", True)
                state = self._compute_jenkins_job_state(disabled, buildable)

                original_color = job_data.get("color", "")

                # Compute standardized status from color field, considering state
                status = self._compute_job_status_from_color(original_color)

                # Override color if job is disabled (regardless of last build result)
                if state == "disabled":
                    color = "grey"
                    if status not in ("disabled", "not_built"):
                        status = "disabled"
                else:
                    color = original_color

                job_url = job_data.get("url", "")
                if not job_url and base_path:
                    # Fallback: construct URL if not provided by API
                    job_url = f"{self.base_url}{base_path}/job/{job_name}/"

                return {
                    "name": job_name,
                    "status": status,
                    "state": state,
                    "color": color,
                    "urls": {
                        "job_page": job_url,
                        "source": None,
                        "api": url,
                    },
                    "buildable": buildable,
                    "disabled": disabled,
                    "description": job_data.get("description", ""),
                    "last_build": last_build_info,
                }
            else:
                self.logger.debug(f"Jenkins job API returned {response.status_code} for {job_name}")
                return {}

        except Exception as e:
            self.logger.debug(f"Exception fetching job details for {job_name}: {e}")
            return {}

    def _compute_jenkins_job_state(self, disabled: bool, buildable: bool) -> str:
        """
        Convert Jenkins disabled and buildable fields to standardized state.

        Jenkins job states:
        - disabled=True: Job is explicitly disabled
        - disabled=False + buildable=True: Job is active and can be built
        - disabled=False + buildable=False: Job exists but cannot be built (treat as disabled)

        Args:
            disabled: Whether the job is disabled in Jenkins
            buildable: Whether the job is buildable

        Returns:
            State string: "active" or "disabled"
        """
        if disabled:
            return "disabled"
        elif buildable:
            return "active"
        else:
            # If not disabled but not buildable, consider it effectively disabled
            return "disabled"

    def _compute_job_status_from_color(self, color: str) -> str:
        """
        Convert Jenkins color field to standardized status.

        Jenkins color meanings:
        - blue: success
        - red: failure
        - yellow: unstable
        - grey: not built/disabled
        - aborted: aborted
        - *_anime: building (animated versions)

        Args:
            color: Jenkins color code

        Returns:
            Standardized status string
        """
        if not color:
            return "unknown"

        color_lower = color.lower()

        # Handle animated colors (building states)
        if color_lower.endswith("_anime"):
            return "building"

        # Map standard colors
        color_map = {
            "blue": "success",
            "red": "failure",
            "yellow": "unstable",
            "grey": "disabled",
            "gray": "disabled",
            "aborted": "aborted",
            "notbuilt": "not_built",
            "disabled": "disabled",
        }

        return color_map.get(color_lower, "unknown")

    def get_last_build_info(self, job_name: str) -> dict[str, Any]:
        """
        Get information about the last build of a job.

        Args:
            job_name: Name of the Jenkins job

        Returns:
            Dictionary with last build information (result, duration, timestamp, etc.)
            Returns empty dict if no build exists or on error.
        """
        try:
            base_path = self.api_base_path.replace("/api/json", "") if self.api_base_path else ""
            url = f"{self.base_url}{base_path}/job/{job_name}/lastBuild/api/json?tree=result,duration,timestamp,building,number"
            response = self.client.get(url)

            if response.status_code == 200:
                build_data = response.json()

                # Convert timestamp to readable format
                timestamp = build_data.get("timestamp", 0)
                if timestamp:
                    build_time = datetime.fromtimestamp(timestamp / 1000)
                    build_data["build_time"] = build_time.isoformat()

                # Convert duration to readable format
                duration_ms = build_data.get("duration", 0)
                if duration_ms:
                    duration_seconds = duration_ms / 1000
                    build_data["duration_seconds"] = duration_seconds

                return dict(build_data)
            else:
                return {}

        except Exception as e:
            self.logger.debug(f"Exception fetching last build info for {job_name}: {e}")
            return {}
