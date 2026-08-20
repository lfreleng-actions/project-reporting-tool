# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Configuration-file feature checks.

Detection of features that are established purely by inspecting files in
the repository working tree: Dependabot, GitHub-to-Gerrit workflows, g2g
workflow files, pre-commit, Read the Docs, Sonatype and ``.gitreview``.
"""

import logging
import re
from pathlib import Path
from typing import Any


class FeatureConfigChecksMixin:
    """Configuration-file presence checks for the feature registry."""

    # Assigned by FeatureRegistry.__init__; declared here for type checking.
    config: dict[str, Any]
    logger: logging.Logger

    def _check_dependabot(self, repo_path: Path) -> dict[str, Any]:
        """
        Check for Dependabot configuration.

        Args:
            repo_path: Path to the repository

        Returns:
            Dict with keys: present (bool), files (list)
        """
        config_files = [".github/dependabot.yml", ".github/dependabot.yaml"]

        found_files = []
        for config_file in config_files:
            file_path = repo_path / config_file
            if file_path.exists():
                found_files.append(config_file)

        return {"present": len(found_files) > 0, "files": found_files}

    def _check_github2gerrit_workflow(self, repo_path: Path) -> dict[str, Any]:
        """
        Check for GitHub to Gerrit workflow patterns.

        Args:
            repo_path: Path to the repository

        Returns:
            Dict with keys: present (bool), workflows (list of dicts)
        """
        workflows_dir = repo_path / ".github" / "workflows"
        if not workflows_dir.exists():
            return {"present": False, "workflows": []}

        gerrit_patterns = [
            "gerrit",
            "review",
            "submit",
            "replication",
            "github2gerrit",
            "gerrit-review",
            "gerrit-submit",
        ]

        matching_workflows: list[dict[str, str]] = []
        try:
            for glob_pattern in ("*.yml", "*.yaml"):
                for workflow_file in workflows_dir.glob(glob_pattern):
                    match = self._match_workflow_content_patterns(workflow_file, gerrit_patterns)
                    if match is not None:
                        matching_workflows.append(match)
        except OSError:
            return {"present": False, "workflows": []}

        return {"present": len(matching_workflows) > 0, "workflows": matching_workflows}

    def _match_workflow_content_patterns(
        self, workflow_file: Path, patterns: list[str]
    ) -> dict[str, str] | None:
        """Return the first content pattern matched in a workflow file, or None.

        Files that cannot be read are skipped (treated as non-matching).
        """
        try:
            with open(workflow_file, encoding="utf-8") as f:
                content = f.read().lower()
        except (OSError, UnicodeDecodeError):
            return None

        for pattern in patterns:
            if pattern in content:
                return {"file": workflow_file.name, "pattern": pattern}
        return None

    def _check_g2g(self, repo_path: Path) -> dict[str, Any]:
        """
        Check for specific GitHub to Gerrit workflow files.

        Checks for workflow files in .github/workflows/ directory. The list of
        workflow filenames can be customized per-project via configuration.

        Configuration supports both exact filenames and regex patterns:

        Exact filenames:
          features:
            g2g:
              workflow_files:
                - "github2gerrit.yaml"
                - "call-github2gerrit.yaml"
                - "custom-workflow.yaml"

        Regex patterns (prefix with "regex:"):
          features:
            g2g:
              workflow_files:
                - "regex:.*github2gerrit.*"
                - "regex:g2g-.*\\.ya?ml$"

        Mixed (exact and regex):
          features:
            g2g:
              workflow_files:
                - "github2gerrit.yaml"
                - "regex:.*github2gerrit.*"

        Regex patterns are case-insensitive by default. Use (?-i) at the start
        of the pattern for case-sensitive matching.

        If not specified in config, defaults to: github2gerrit.yaml, call-github2gerrit.yaml

        Args:
            repo_path: Path to the repository

        Returns:
            Dict with keys: present (bool), file_paths (list), file_path (str or None),
                          matched_patterns (dict mapping patterns to matched files)
        """
        workflows_dir = repo_path / ".github" / "workflows"

        # Get workflow files from config, with backward-compatible defaults
        default_g2g_files = ["github2gerrit.yaml", "call-github2gerrit.yaml"]
        features_config = self.config.get("features", {})
        g2g_config = features_config.get("g2g", {})
        g2g_files = g2g_config.get("workflow_files", default_g2g_files)

        # Ensure g2g_files is a list
        if isinstance(g2g_files, str):
            g2g_files = [g2g_files]

        # Check if workflows directory exists
        if not workflows_dir.exists() or not workflows_dir.is_dir():
            return {
                "present": False,
                "file_paths": [],
                "file_path": None,
                "matched_patterns": {},
            }

        # Separate exact filenames from regex patterns
        exact_filenames = []
        regex_patterns = []
        for pattern in g2g_files:
            if isinstance(pattern, str) and pattern.startswith("regex:"):
                # Extract the regex pattern (everything after "regex:")
                regex_str = pattern[6:]  # Remove "regex:" prefix
                try:
                    # Compile with case-insensitive flag by default
                    # Users can override with (?-i) in their pattern
                    compiled_pattern = re.compile(regex_str, re.IGNORECASE)
                    regex_patterns.append((pattern, compiled_pattern))
                except re.error as e:
                    self.logger.warning(
                        f"Invalid regex pattern '{regex_str}' in g2g configuration: {e}"
                    )
            else:
                exact_filenames.append(pattern)

        found_files = []
        matched_patterns: dict[str, list[str]] = {}

        for filename in exact_filenames:
            file_path = workflows_dir / filename
            if file_path.exists():
                found_files.append(f".github/workflows/{filename}")
                if filename not in matched_patterns:
                    matched_patterns[filename] = []
                matched_patterns[filename].append(filename)

        if regex_patterns:
            self._match_regex_workflow_files(
                workflows_dir, regex_patterns, found_files, matched_patterns
            )

        # Sort found files for consistent ordering
        found_files.sort()

        return {
            "present": len(found_files) > 0,
            "file_paths": found_files,
            "file_path": found_files[0] if found_files else None,  # Backward compatibility
            "matched_patterns": matched_patterns,
        }

    def _match_regex_workflow_files(
        self,
        workflows_dir: Path,
        regex_patterns: list[tuple[str, Any]],
        found_files: list[str],
        matched_patterns: dict[str, list[str]],
    ) -> None:
        """Match workflow files against regex patterns, updating results in place."""
        try:
            workflow_files = [
                f for f in workflows_dir.iterdir() if f.is_file() and not f.name.startswith(".")
            ]
        except OSError as e:
            self.logger.warning(f"Error reading workflows directory {workflows_dir}: {e}")
            return

        # Test each workflow file against each regex pattern
        for workflow_file in workflow_files:
            workflow_filename = workflow_file.name
            relative_path = f".github/workflows/{workflow_filename}"

            for pattern_str, compiled_pattern in regex_patterns:
                if not compiled_pattern.search(workflow_filename):
                    continue
                if relative_path not in found_files:
                    found_files.append(relative_path)
                matched_patterns.setdefault(pattern_str, []).append(workflow_filename)

    def _check_pre_commit(self, repo_path: Path) -> dict[str, Any]:
        """
        Check for pre-commit configuration.

        Args:
            repo_path: Path to the repository

        Returns:
            Dict with keys: present (bool), config_file (str or None), repos_count (int)
        """
        config_files = [".pre-commit-config.yaml", ".pre-commit-config.yml"]

        found_config = None
        for config_file in config_files:
            file_path = repo_path / config_file
            if file_path.exists():
                found_config = config_file
                break

        result: dict[str, Any] = {
            "present": found_config is not None,
            "config_file": found_config,
        }

        # If config exists, try to extract some basic info
        if found_config:
            try:
                config_path = repo_path / found_config
                with open(config_path, encoding="utf-8") as f:
                    content = f.read()
                    # Count number of repos/hooks (basic analysis)
                    repos_count = len(re.findall(r"^\s*-\s*repo:", content, re.MULTILINE))
                    result["repos_count"] = repos_count
            except (OSError, UnicodeDecodeError):
                pass

        return result

    def _check_readthedocs(self, repo_path: Path) -> dict[str, Any]:
        """
        Check for Read the Docs configuration.

        Args:
            repo_path: Path to the repository

        Returns:
            Dict with keys: present (bool), config_type (str or None), config_files (list)
        """
        rtd_configs = [
            ".readthedocs.yml",
            ".readthedocs.yaml",
            "readthedocs.yml",
            "readthedocs.yaml",
        ]

        sphinx_configs = ["docs/conf.py", "doc/conf.py", "documentation/conf.py"]

        mkdocs_configs = ["mkdocs.yml", "mkdocs.yaml"]

        found_configs = []
        config_type = None

        for config in rtd_configs:
            if (repo_path / config).exists():
                found_configs.append(config)
                config_type = "readthedocs"

        for config in sphinx_configs:
            if (repo_path / config).exists():
                found_configs.append(config)
                if not config_type:
                    config_type = "sphinx"

        for config in mkdocs_configs:
            if (repo_path / config).exists():
                found_configs.append(config)
                if not config_type:
                    config_type = "mkdocs"

        return {
            "present": len(found_configs) > 0,
            "config_type": config_type,
            "config_files": found_configs,
        }

    def _check_sonatype_config(self, repo_path: Path) -> dict[str, Any]:
        """
        Check for Sonatype configuration files.

        Args:
            repo_path: Path to the repository

        Returns:
            Dict with keys: present (bool), config_files (list)
        """
        sonatype_configs = [
            ".sonatype-lift.yaml",
            ".sonatype-lift.yml",
            "lift.toml",
            "lifecycle.json",
            ".lift.toml",
            "sonatype-lift.yml",
            "sonatype-lift.yaml",
        ]

        found_configs = []
        for config in sonatype_configs:
            if (repo_path / config).exists():
                found_configs.append(config)

        return {"present": len(found_configs) > 0, "config_files": found_configs}

    def _check_gitreview(self, repo_path: Path) -> dict[str, Any]:
        """
        Check for .gitreview configuration file.

        Args:
            repo_path: Path to the repository

        Returns:
            Dict with keys: present (bool), file (str or None), config (dict)
        """
        gitreview_file = repo_path / ".gitreview"

        if not gitreview_file.exists():
            return {"present": False, "file": None, "config": {}}

        config = {}
        try:
            with open(gitreview_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        config[key.strip()] = value.strip()
        except (OSError, UnicodeDecodeError):
            # File exists but couldn't be read
            pass

        return {"present": True, "file": ".gitreview", "config": config}
