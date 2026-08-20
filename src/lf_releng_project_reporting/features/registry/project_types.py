# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Project type detection.

Scores a repository against the project type catalogue, folds Java plus
Maven/Gradle detections into combined build-system types, applies
context-sensitive priority boosts and falls back to documentation
classification when no programming language is found.
"""

import logging
from pathlib import Path
from typing import Any

from .catalog import _PROJECT_TYPE_PATTERNS


class ProjectTypeChecksMixin:
    """Project type detection for the feature registry."""

    # Assigned by FeatureRegistry.__init__; declared here for type checking.
    logger: logging.Logger

    def _check_project_types(self, repo_path: Path) -> dict[str, Any]:
        """
        Detect project types based on configuration files and repository characteristics.

        Args:
            repo_path: Path to the repository

        Returns:
            Dict with keys: detected_types (list), primary_type (str), details (list)
        """
        repo_name = repo_path.name.lower()

        # Static classifications based on repository names
        if repo_name == "ci-management":
            return {
                "detected_types": ["jjb"],
                "primary_type": "jjb",
                "details": [{"type": "jjb", "files": ["repository_name"], "confidence": 100}],
            }

        detected_types, confidence_scores = self._score_project_types(repo_path)

        # Post-process to create combined Java/Maven and Java/Gradle types
        detected_types = self._combine_java_build_types(detected_types, confidence_scores)

        # Apply priority boosts for certain project types
        self._apply_type_priority_boosts(repo_path, repo_name, confidence_scores)

        # Determine primary type (highest confidence)
        primary_type = None
        if detected_types:
            primary_type = max(confidence_scores.items(), key=lambda x: x[1])[0]

        # If no programming language detected, check for documentation as fallback
        if not detected_types and self._is_documentation_repository(repo_path):
            return {
                "detected_types": ["documentation"],
                "primary_type": "documentation",
                "details": [
                    {
                        "type": "documentation",
                        "files": self._get_doc_indicators(repo_path),
                        "confidence": 50,
                    }
                ],
            }

        return {
            "detected_types": [t["type"] for t in detected_types],
            "primary_type": primary_type,
            "details": detected_types,
        }

    def _score_project_types(self, repo_path: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """Detect project types by matching configuration files and glob patterns.

        Returns:
            Tuple of ``(detected_types, confidence_scores)`` where each detected
            type carries the matched files and a confidence equal to the number
            of matches.
        """
        detected_types: list[dict[str, Any]] = []
        confidence_scores: dict[str, int] = {}

        for project_type, config_files in _PROJECT_TYPE_PATTERNS.items():
            matches: list[str] = []
            for config_pattern in config_files:
                if "*" in config_pattern:
                    try:
                        matching_files = list(repo_path.glob(config_pattern))
                    except OSError:
                        continue
                    if matching_files:
                        matches.extend([f.name for f in matching_files])
                elif (repo_path / config_pattern).exists():
                    matches.append(config_pattern)

            if matches:
                detected_types.append(
                    {"type": project_type, "files": matches, "confidence": len(matches)}
                )
                confidence_scores[project_type] = len(matches)

        return detected_types, confidence_scores

    def _combine_java_build_types(
        self, detected_types: list[dict[str, Any]], confidence_scores: dict[str, int]
    ) -> list[dict[str, Any]]:
        """Fold Java + Maven/Gradle detections into combined build-system types.

        Mutates ``confidence_scores`` in place and returns the (possibly
        rewritten) detected-types list.
        """
        has_maven = "Maven" in confidence_scores
        has_gradle = "Gradle" in confidence_scores
        has_java = "Java" in confidence_scores

        # If we have Java files with Maven or Gradle, create combined types
        if has_java and has_maven:
            combined_confidence = confidence_scores.get("Java", 0) + confidence_scores.get(
                "Maven", 0
            )
            detected_types.append(
                {"type": "Java/Maven", "files": [], "confidence": combined_confidence}
            )
            confidence_scores["Java/Maven"] = combined_confidence
            detected_types = [t for t in detected_types if t["type"] not in ["Java", "Maven"]]
            confidence_scores.pop("Java", None)
            confidence_scores.pop("Maven", None)
        elif has_maven and not has_java:
            # Maven without Java files, rename to Java/Maven
            for t in detected_types:
                if t["type"] == "Maven":
                    t["type"] = "Java/Maven"
            if "Maven" in confidence_scores:
                confidence_scores["Java/Maven"] = confidence_scores.pop("Maven")

        if has_java and has_gradle:
            combined_confidence = confidence_scores.get("Java", 0) + confidence_scores.get(
                "Gradle", 0
            )
            detected_types.append(
                {"type": "Java/Gradle", "files": [], "confidence": combined_confidence}
            )
            confidence_scores["Java/Gradle"] = combined_confidence
            detected_types = [t for t in detected_types if t["type"] not in ["Java", "Gradle"]]
            confidence_scores.pop("Java", None)
            confidence_scores.pop("Gradle", None)
        elif has_gradle and not has_java:
            # Gradle without Java files, rename to Java/Gradle
            for t in detected_types:
                if t["type"] == "Gradle":
                    t["type"] = "Java/Gradle"
            if "Gradle" in confidence_scores:
                confidence_scores["Java/Gradle"] = confidence_scores.pop("Gradle")

        return detected_types

    def _apply_type_priority_boosts(
        self, repo_path: Path, repo_name: str, confidence_scores: dict[str, int]
    ) -> None:
        """Boost confidence scores for context-sensitive project types in place."""
        repo_name_lower = repo_name.lower()

        # Boost Dockerfile priority if found at root
        if "Dockerfile" in confidence_scores:
            dockerfile_at_root = (repo_path / "Dockerfile").exists()
            docker_compose_at_root = (repo_path / "docker-compose.yml").exists() or (
                repo_path / "docker-compose.yaml"
            ).exists()
            if dockerfile_at_root or docker_compose_at_root:
                # Boost by 50% if Dockerfile/docker-compose at root
                confidence_scores["Dockerfile"] = int(confidence_scores["Dockerfile"] * 1.5)

        # Boost Robot Framework priority for test-related repos
        if "Robot Framework" in confidence_scores and (
            "test" in repo_name_lower or "testsuite" in repo_name_lower
        ):
            # Boost by 100% for test repos
            confidence_scores["Robot Framework"] = int(confidence_scores["Robot Framework"] * 2.0)

        # Boost Shell priority if many shell scripts found
        if "Shell" in confidence_scores and confidence_scores["Shell"] >= 5:
            # Boost shell if we found 5+ shell scripts
            confidence_scores["Shell"] = int(confidence_scores["Shell"] * 1.3)

    def _is_documentation_repository(self, repo_path: Path) -> bool:
        """
        Determine if a repository is primarily for documentation (fallback only).

        Args:
            repo_path: Path to the repository

        Returns:
            True if repository appears to be primarily documentation
        """
        repo_name = repo_path.name.lower()

        # Only classify as documentation if repository name strongly indicates it
        strong_doc_patterns = ["documentation", "manual", "wiki", "guide", "tutorial"]
        if any(
            repo_name == pattern or repo_name.endswith(f"-{pattern}")
            for pattern in strong_doc_patterns
        ):
            return True

        # For repos named exactly "doc" or "docs"
        if repo_name in ["doc", "docs"]:
            return True

        # Check directory structure and file patterns - be more restrictive
        doc_indicators = self._get_doc_indicators(repo_path)
        return len(doc_indicators) >= 5  # Require more indicators for stronger confidence

    def _get_doc_indicators(self, repo_path: Path) -> list[str]:
        """
        Get list of documentation indicators found in the repository.

        Args:
            repo_path: Path to the repository

        Returns:
            List of documentation indicator file/directory names
        """
        indicators = []

        doc_files = [
            "README.md",
            "README.rst",
            "README.txt",
            "DOCS.md",
            "DOCUMENTATION.md",
            "index.md",
            "index.rst",
            "index.html",
            "sphinx.conf",
            "conf.py",  # Sphinx
            "mkdocs.yml",
            "_config.yml",  # MkDocs/Jekyll
            "Gemfile",  # Jekyll
        ]

        for doc_file in doc_files:
            if (repo_path / doc_file).exists():
                indicators.append(doc_file)

        doc_dirs = [
            "docs",
            "doc",
            "documentation",
            "_docs",
            "manual",
            "guides",
            "tutorials",
        ]
        for doc_dir in doc_dirs:
            if (repo_path / doc_dir).is_dir():
                indicators.append(f"{doc_dir}/")

        try:
            doc_extensions = [".md", ".rst", ".adoc", ".txt"]
            for ext in doc_extensions:
                if list(repo_path.glob(f"*{ext}")):
                    indicators.append(f"*{ext}")
        except OSError:
            self.logger.debug("Failed to scan %s for documentation files", repo_path, exc_info=True)

        static_generators = [
            ".gitbook",  # GitBook
            "_config.yml",  # Jekyll
            "mkdocs.yml",  # MkDocs
            "conf.py",  # Sphinx
            "book.toml",  # mdBook
            "docusaurus.config.js",  # Docusaurus
        ]

        for generator in static_generators:
            if (repo_path / generator).exists():
                indicators.append(generator)

        return indicators
