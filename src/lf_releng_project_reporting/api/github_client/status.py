# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
GitHub workflow status mapping.

Pure translation helpers that convert GitHub workflow conclusions, run
statuses and workflow states into the standardised status/colour
vocabulary shared with the Jenkins client.
"""


class GitHubStatusMixin:
    """Status and colour normalisation helpers for GitHub workflows."""

    def _compute_workflow_color_from_runtime_status(self, status: str) -> str:
        """
        Convert runtime workflow status to color for consistency with Jenkins jobs.

        Args:
            status: Runtime workflow status ("success", "failure", "building", etc.)

        Returns:
            Color string compatible with Jenkins color scheme
        """
        if not status:
            return "grey"

        status_lower = status.lower()

        # Map runtime statuses to colors (matching Jenkins scheme)
        status_color_map = {
            "success": "blue",
            "failure": "red",
            "building": "blue_anime",
            "in_progress": "blue_anime",
            "cancelled": "grey",
            "skipped": "grey",
            "unknown": "grey",
            "error": "red",
            "no_runs": "grey",
        }

        return status_color_map.get(status_lower, "grey")

    def _compute_workflow_status(self, conclusion: str, run_status: str) -> str:
        """
        Convert GitHub workflow conclusion and run status to standardized status.

        GitHub conclusions: success, failure, neutral, cancelled, skipped,
                          timed_out, action_required
        GitHub run statuses: queued, in_progress, completed

        Args:
            conclusion: GitHub workflow conclusion
            run_status: GitHub workflow run status

        Returns:
            Standardized status string
        """
        if not conclusion and not run_status:
            return "unknown"

        if run_status in ("queued", "in_progress"):
            return "building"

        if run_status == "completed":
            conclusion_map = {
                "success": "success",
                "failure": "failure",
                "neutral": "success",
                "cancelled": "cancelled",
                "skipped": "skipped",
                "timed_out": "failure",
                "action_required": "failure",
            }
            return conclusion_map.get(conclusion, "unknown")

        return "unknown"

    def _compute_workflow_color_from_state(self, state: str) -> str:
        """
        Convert GitHub workflow state to color for consistency with Jenkins jobs.

        Args:
            state: GitHub workflow state ("active", "disabled", etc.)

        Returns:
            Color string compatible with Jenkins color scheme
        """
        if not state:
            return "grey"

        state_lower = state.lower()

        # Map workflow states to colors
        state_color_map = {
            "active": "blue",
            "disabled": "grey",
            "deleted": "red",
        }

        return state_color_map.get(state_lower, "grey")
