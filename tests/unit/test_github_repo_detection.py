# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Tests for FeatureRegistry._is_github_repository detection.

Validates the section-aware git config parser that replaced the
naive ``"github.com" in content`` substring check (CodeQL CWE-20).
"""

import logging
from pathlib import Path

import pytest

from lf_releng_project_reporting.features.registry import FeatureRegistry


@pytest.fixture()
def registry() -> FeatureRegistry:
    """Create a minimal FeatureRegistry for testing."""
    config: dict = {"features": {"enabled": []}}
    logger = logging.getLogger("test")
    return FeatureRegistry(config, logger)


def _write_git_config(repo: Path, content: str) -> None:
    """Write a .git/config file inside *repo*."""
    git_dir = repo / ".git"
    git_dir.mkdir(parents=True, exist_ok=True)
    (git_dir / "config").write_text(content, encoding="utf-8")


class TestGitHubHTTPSRemotes:
    """HTTPS remote URLs pointing to GitHub."""

    def test_https_remote(self, tmp_path: Path, registry: FeatureRegistry) -> None:
        """Detect a standard HTTPS GitHub remote."""
        _write_git_config(
            tmp_path,
            '[remote "origin"]\n'
            "\turl = https://github.com/org/repo.git\n"
            "\tfetch = +refs/heads/*:refs/remotes/origin/*\n",
        )
        assert registry._is_github_repository(tmp_path) is True

    def test_https_remote_no_dotgit_suffix(self, tmp_path: Path, registry: FeatureRegistry) -> None:
        """Detect HTTPS remote without trailing .git."""
        _write_git_config(
            tmp_path,
            '[remote "origin"]\n\turl = https://github.com/org/repo\n',
        )
        assert registry._is_github_repository(tmp_path) is True

    def test_https_case_insensitive(self, tmp_path: Path, registry: FeatureRegistry) -> None:
        """Hostname comparison must be case-insensitive."""
        _write_git_config(
            tmp_path,
            '[remote "origin"]\n\turl = https://GitHub.COM/org/repo.git\n',
        )
        assert registry._is_github_repository(tmp_path) is True


class TestGitHubSSHRemotes:
    """SSH remote URLs pointing to GitHub."""

    def test_ssh_remote(self, tmp_path: Path, registry: FeatureRegistry) -> None:
        """Detect a standard SSH GitHub remote."""
        _write_git_config(
            tmp_path,
            '[remote "origin"]\n\turl = git@github.com:org/repo.git\n',
        )
        assert registry._is_github_repository(tmp_path) is True

    def test_ssh_remote_case_insensitive(self, tmp_path: Path, registry: FeatureRegistry) -> None:
        """SSH hostname comparison must be case-insensitive."""
        _write_git_config(
            tmp_path,
            '[remote "origin"]\n\turl = git@GITHUB.COM:org/repo.git\n',
        )
        assert registry._is_github_repository(tmp_path) is True


class TestNonGitHubRemotes:
    """Remotes that do NOT point to GitHub."""

    def test_gitlab_remote(self, tmp_path: Path, registry: FeatureRegistry) -> None:
        """A GitLab remote must not be detected as GitHub."""
        _write_git_config(
            tmp_path,
            '[remote "origin"]\n\turl = https://gitlab.com/org/repo.git\n',
        )
        assert registry._is_github_repository(tmp_path) is False

    def test_gerrit_remote(self, tmp_path: Path, registry: FeatureRegistry) -> None:
        """A Gerrit remote must not be detected as GitHub."""
        _write_git_config(
            tmp_path,
            '[remote "origin"]\n\turl = https://gerrit.example.org/r/project\n',
        )
        assert registry._is_github_repository(tmp_path) is False

    def test_evil_subdomain(self, tmp_path: Path, registry: FeatureRegistry) -> None:
        """A spoofed subdomain must not match.

        This is the attack vector the old substring check was
        vulnerable to: ``notgithub.com`` contains ``github.com``.
        """
        _write_git_config(
            tmp_path,
            '[remote "origin"]\n\turl = https://notgithub.com/org/repo.git\n',
        )
        assert registry._is_github_repository(tmp_path) is False

    def test_github_in_path_not_host(self, tmp_path: Path, registry: FeatureRegistry) -> None:
        """github.com appearing in the path must not match."""
        _write_git_config(
            tmp_path,
            '[remote "origin"]\n\turl = https://gitlab.com/mirrors/github.com.git\n',
        )
        assert registry._is_github_repository(tmp_path) is False


class TestCommentedAndNonRemoteSections:
    """The parser must skip comments and non-remote sections."""

    def test_commented_url_ignored(self, tmp_path: Path, registry: FeatureRegistry) -> None:
        """A commented-out URL line must be skipped."""
        _write_git_config(
            tmp_path,
            '[remote "origin"]\n'
            "\t# url = https://github.com/org/repo.git\n"
            "\turl = https://gitlab.com/org/repo.git\n",
        )
        assert registry._is_github_repository(tmp_path) is False

    def test_semicolon_comment_ignored(self, tmp_path: Path, registry: FeatureRegistry) -> None:
        """Git config also supports ; comments."""
        _write_git_config(
            tmp_path,
            '[remote "origin"]\n'
            "\t; url = https://github.com/org/repo.git\n"
            "\turl = https://gitlab.com/org/repo.git\n",
        )
        assert registry._is_github_repository(tmp_path) is False

    def test_url_in_non_remote_section(self, tmp_path: Path, registry: FeatureRegistry) -> None:
        """A url key in a non-remote section must be ignored."""
        _write_git_config(
            tmp_path,
            '[submodule "vendor/lib"]\n\turl = https://github.com/vendor/lib.git\n',
        )
        assert registry._is_github_repository(tmp_path) is False


class TestMultipleRemotes:
    """Configs with more than one remote section."""

    def test_second_remote_is_github(self, tmp_path: Path, registry: FeatureRegistry) -> None:
        """Detect GitHub even when it is the second remote."""
        _write_git_config(
            tmp_path,
            '[remote "gerrit"]\n'
            "\turl = https://gerrit.example.org/r/project\n"
            '[remote "github"]\n'
            "\turl = https://github.com/org/repo.git\n",
        )
        assert registry._is_github_repository(tmp_path) is True


class TestWorkflowFallback:
    """Workflow-directory fallback when git config has no GitHub remote."""

    def test_workflows_directory_detected(self, tmp_path: Path, registry: FeatureRegistry) -> None:
        """Presence of .github/workflows triggers the fallback."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text(
            '[remote "origin"]\n\turl = https://gerrit.example.org/r/project\n',
            encoding="utf-8",
        )
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "ci.yaml").write_text("name: CI\n", encoding="utf-8")

        assert registry._is_github_repository(tmp_path) is True

    def test_empty_workflows_directory_not_detected(
        self, tmp_path: Path, registry: FeatureRegistry
    ) -> None:
        """An empty .github/workflows must not trigger the fallback."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config").write_text(
            '[remote "origin"]\n\turl = https://gerrit.example.org/r/project\n',
            encoding="utf-8",
        )
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)

        assert registry._is_github_repository(tmp_path) is False


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_no_git_directory(self, tmp_path: Path, registry: FeatureRegistry) -> None:
        """A path with no .git directory returns False."""
        assert registry._is_github_repository(tmp_path) is False

    def test_no_config_file(self, tmp_path: Path, registry: FeatureRegistry) -> None:
        """A .git directory without a config file returns False."""
        (tmp_path / ".git").mkdir()
        assert registry._is_github_repository(tmp_path) is False

    def test_empty_config_file(self, tmp_path: Path, registry: FeatureRegistry) -> None:
        """An empty config file returns False."""
        _write_git_config(tmp_path, "")
        assert registry._is_github_repository(tmp_path) is False

    def test_nonexistent_path(self, tmp_path: Path, registry: FeatureRegistry) -> None:
        """A non-existent path returns False without raising."""
        assert registry._is_github_repository(tmp_path / "does-not-exist") is False
