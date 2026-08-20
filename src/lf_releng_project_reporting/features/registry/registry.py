# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Feature registry construction and dispatch.

Registers the default feature checks and dispatches the enabled ones over
a repository, composing the per-domain detection mixins into the public
``FeatureRegistry``.
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .configs import FeatureConfigChecksMixin
from .project_types import ProjectTypeChecksMixin
from .workflows import WorkflowChecksMixin


class FeatureRegistry(
    FeatureConfigChecksMixin,
    ProjectTypeChecksMixin,
    WorkflowChecksMixin,
):
    """
    Registry for repository feature detection functions.

    This class maintains a registry of feature detection functions and provides
    methods to scan repositories for various features like CI/CD configurations,
    documentation setups, dependency management, and project types.

    Features are detected by examining:
    - Configuration files (e.g., .github/dependabot.yml)
    - Project structure (e.g., presence of docs/ directory)
    - Git configuration (e.g., .gitreview for Gerrit)
    - GitHub API (e.g., workflow run status)

    Example:
        >>> config = {"features": {"enabled": ["dependabot", "workflows"]}}
        >>> logger = logging.getLogger(__name__)
        >>> registry = FeatureRegistry(config, logger)
        >>> features = registry.detect_features(Path("./my-repo"))
        >>> print(features["dependabot"])
        {"present": True, "files": [".github/dependabot.yml"]}
    """

    def __init__(
        self, config: dict[str, Any], logger: logging.Logger, api_stats: Any | None = None
    ) -> None:
        """
        Initialize the feature registry.

        Args:
            config: Configuration dictionary containing feature settings
            logger: Logger instance for debug/info/warning messages
            api_stats: Optional API statistics tracker for monitoring external API calls
        """
        self.config = config
        self.logger = logger
        self.api_stats = api_stats
        self.checks: dict[str, Callable[..., Any]] = {}

        # Get GitHub organization from config (already determined centrally in main())
        self.github_org = self.config.get("github", "")
        self.github_org_source = self.config.get("_github_org_source", "not_configured")

        if self.github_org:
            self.logger.debug(
                f"GitHub organization: '{self.github_org}' (source: {self.github_org_source})"
            )

        self._register_default_checks()

    def register(self, feature_name: str, check_function: Callable[..., Any]) -> None:
        """
        Register a feature detection function.

        Args:
            feature_name: Unique name for the feature
            check_function: Callable that takes a Path and returns feature info dict
        """
        self.checks[feature_name] = check_function

    def _register_default_checks(self) -> None:
        """Register all default feature detection checks."""
        self.register("dependabot", self._check_dependabot)
        self.register("github2gerrit_workflow", self._check_github2gerrit_workflow)
        self.register("g2g", self._check_g2g)
        self.register("pre_commit", self._check_pre_commit)
        self.register("readthedocs", self._check_readthedocs)
        self.register("sonatype_config", self._check_sonatype_config)
        self.register("project_types", self._check_project_types)
        self.register("workflows", self._check_workflows)
        self.register("gitreview", self._check_gitreview)
        self.register("github_mirror", self._check_github_mirror)

    def detect_features(self, repo_path: Path) -> dict[str, Any]:
        """
        Scan repository for all enabled features.

        Args:
            repo_path: Path to the repository to scan

        Returns:
            Dictionary mapping feature names to their detection results

        Example:
            >>> features = registry.detect_features(Path("./repo"))
            >>> if features["dependabot"]["present"]:
            ...     print("Dependabot is configured!")
        """
        features_config = self.config.get("features", {})
        enabled_features = features_config.get("enabled", [])
        results = {}

        for feature_name in enabled_features:
            if feature_name in self.checks:
                try:
                    results[feature_name] = self.checks[feature_name](repo_path)
                except Exception as e:
                    self.logger.warning(
                        f"Feature check '{feature_name}' failed for {repo_path.name}: {e}"
                    )
                    results[feature_name] = {"error": str(e)}

        return results
