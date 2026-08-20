# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
GitHub Actions workflow analysis.

Static analysis of the workflow files under ``.github/workflows``:
counting them, classifying each as verify/merge/other by filename and
content scoring, and extracting triggers and job counts.
"""

import re
from pathlib import Path
from typing import Any

from .github import GitHubChecksMixin


class WorkflowChecksMixin(GitHubChecksMixin):
    """Workflow file discovery and classification for the feature registry.

    ``config``, ``logger`` and ``api_stats`` are declared on
    ``GitHubChecksMixin``; they are assigned by ``FeatureRegistry.__init__``.
    """

    def _check_workflows(self, repo_path: Path) -> dict[str, Any]:
        """
        Analyze GitHub workflows with optional GitHub API integration.

        Args:
            repo_path: Path to the repository

        Returns:
            Dict with workflow count, classification, and optional runtime status
        """
        workflows_dir = repo_path / ".github" / "workflows"
        if not workflows_dir.exists():
            return {
                "count": 0,
                "classified": {"verify": 0, "merge": 0, "other": 0},
                "files": [],
            }

        workflows_config = self.config.get("workflows", {})
        workflow_config = workflows_config.get("classify", {})
        verify_patterns = workflow_config.get("verify", ["verify", "test", "ci", "check"])
        merge_patterns = workflow_config.get("merge", ["merge", "release", "deploy", "publish"])

        workflow_files = []
        classified = {"verify": 0, "merge": 0, "other": 0}

        try:
            for workflow_file in workflows_dir.glob("*.yml"):
                workflow_info = self._analyze_workflow_file(
                    workflow_file, verify_patterns, merge_patterns
                )
                workflow_files.append(workflow_info)
                classified[workflow_info["classification"]] += 1

            for workflow_file in workflows_dir.glob("*.yaml"):
                workflow_info = self._analyze_workflow_file(
                    workflow_file, verify_patterns, merge_patterns
                )
                workflow_files.append(workflow_info)
                classified[workflow_info["classification"]] += 1

        except OSError:
            return {
                "count": 0,
                "classified": {"verify": 0, "merge": 0, "other": 0},
                "files": [],
            }

        workflow_names = [workflow_info["name"] for workflow_info in workflow_files]

        # Base result with static analysis
        result = {
            "count": len(workflow_files),
            "classified": classified,
            "files": workflow_files,
            "workflow_names": workflow_names,
            "has_runtime_status": False,
        }

        # Try GitHub API integration if enabled and token available
        self._augment_workflows_with_github_api(result, repo_path, workflow_names)

        return result

    def _analyze_workflow_file(
        self, workflow_file: Path, verify_patterns: list[str], merge_patterns: list[str]
    ) -> dict[str, Any]:
        """
        Analyze a single workflow file for classification.

        Args:
            workflow_file: Path to the workflow file
            verify_patterns: List of patterns indicating verify/test workflows
            merge_patterns: List of patterns indicating merge/release workflows

        Returns:
            Dict with workflow information and classification
        """
        workflow_info: dict[str, Any] = {
            "name": workflow_file.name,
            "classification": "other",
            "triggers": [],
            "jobs": 0,
        }

        try:
            with open(workflow_file, encoding="utf-8") as f:
                content = f.read().lower()
                filename_lower = workflow_file.name.lower()

                # Classification based on filename and content with scoring
                verify_score = 0
                merge_score = 0

                # Score verify patterns (filename matches count more)
                for pattern in verify_patterns:
                    pattern_lower = pattern.lower()
                    if pattern_lower in filename_lower:
                        verify_score += 3  # Higher weight for filename matches
                    elif re.search(r"\b" + re.escape(pattern_lower) + r"\b", content):
                        verify_score += 1

                # Score merge patterns (filename matches count more)
                for pattern in merge_patterns:
                    pattern_lower = pattern.lower()
                    if pattern_lower in filename_lower:
                        merge_score += 3  # Higher weight for filename matches
                    elif re.search(r"\b" + re.escape(pattern_lower) + r"\b", content):
                        merge_score += 1

                # Classify based on highest score
                if merge_score > verify_score:
                    workflow_info["classification"] = "merge"
                elif verify_score > 0:
                    workflow_info["classification"] = "verify"
                # else remains "other"

                # Extract basic info
                # Find triggers (on: section)
                trigger_matches = re.findall(r"on:\s*\n\s*-?\s*(\w+)", content)
                if trigger_matches:
                    workflow_info["triggers"] = trigger_matches
                else:
                    # Try alternative format
                    if "on: push" in content:
                        workflow_info["triggers"].append("push")
                    if "on: pull_request" in content:
                        workflow_info["triggers"].append("pull_request")

                # Count jobs
                job_matches = re.findall(r"^\s*(\w+):\s*$", content, re.MULTILINE)
                # Filter out common YAML keys that aren't jobs
                non_job_keys = {"on", "env", "defaults", "jobs", "name", "run-name"}
                jobs = [
                    job
                    for job in job_matches
                    if job not in non_job_keys and not job.startswith("step")
                ]
                workflow_info["jobs"] = len(set(jobs))  # Remove duplicates

        except (OSError, UnicodeDecodeError):
            # File couldn't be read, return basic info
            pass

        return workflow_info
