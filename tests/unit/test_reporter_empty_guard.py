# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Tests for the "no repositories" fast-fail guard in RepositoryReporter.

An empty working directory almost always means an upstream clone step failed
transiently (for example, a Gerrit discovery/clone problem). Generating a
report from zero repositories produces empty, misleading output that can
overwrite previously good data. These tests lock in the behaviour that such a
situation is a hard, retryable error by default, and that callers can opt out
via ``allow_empty``.
"""

import logging
from pathlib import Path

import pytest

from lf_releng_project_reporting.exceptions import NoRepositoriesError
from lf_releng_project_reporting.reporter import RepositoryReporter


def _make_reporter() -> RepositoryReporter:
    """Build a reporter with INFO.yaml collection disabled for offline tests."""
    config = {"project": "test-project", "info_yaml": {"enabled": False}}
    logger = logging.getLogger(__name__)
    return RepositoryReporter(config, logger)


class TestEmptyRepositoriesGuard:
    """Behaviour when no repositories are discovered under repos_path."""

    def test_raises_when_repos_dir_is_empty(self, tmp_path: Path):
        """An empty repos directory raises NoRepositoriesError by default."""
        repos_path = tmp_path / "gerrit.onap.org"
        repos_path.mkdir()

        reporter = _make_reporter()

        with pytest.raises(NoRepositoriesError):
            reporter.analyze_repositories(repos_path)

    def test_error_message_is_actionable(self, tmp_path: Path):
        """The raised error explains the likely cause and how to recover."""
        repos_path = tmp_path / "gerrit.onap.org"
        repos_path.mkdir()

        reporter = _make_reporter()

        with pytest.raises(NoRepositoriesError) as exc_info:
            reporter.analyze_repositories(repos_path)

        message = str(exc_info.value)
        assert "No repositories found" in message
        assert "clone" in message.lower()

    def test_guard_runs_before_info_master_clone(self, tmp_path: Path, monkeypatch):
        """The guard fails fast, before any (network) info-master clone."""
        repos_path = tmp_path / "gerrit.onap.org"
        repos_path.mkdir()

        reporter = _make_reporter()

        def _fail_if_called():
            raise AssertionError("info-master clone must not run for empty repos")

        monkeypatch.setattr(reporter, "_clone_info_master_repo", _fail_if_called)

        with pytest.raises(NoRepositoriesError):
            reporter.analyze_repositories(repos_path)

    def test_allow_empty_skips_guard(self, tmp_path: Path, monkeypatch):
        """With allow_empty=True an empty directory is analysed without error."""
        repos_path = tmp_path / "gerrit.onap.org"
        repos_path.mkdir()

        reporter = _make_reporter()

        # Keep the analysis fully offline: no info-master clone, no INFO.yaml.
        monkeypatch.setattr(reporter, "_clone_info_master_repo", lambda: None)
        monkeypatch.setattr(
            reporter,
            "_collect_info_yaml_data",
            lambda *args, **kwargs: None,
        )

        report_data = reporter.analyze_repositories(repos_path, allow_empty=True)

        assert report_data["repositories"] == []

    def test_does_not_raise_when_repositories_present(self, tmp_path: Path, monkeypatch):
        """A populated directory passes the guard (no false positive)."""
        repos_path = tmp_path / "gerrit.onap.org"
        (repos_path / "example-repo" / ".git").mkdir(parents=True)

        reporter = _make_reporter()

        # Stub out the heavy/network stages; we only care that the guard did
        # not raise for a directory that contains at least one repository.
        monkeypatch.setattr(reporter, "_clone_info_master_repo", lambda: None)
        monkeypatch.setattr(
            reporter,
            "_collect_info_yaml_data",
            lambda *args, **kwargs: None,
        )
        monkeypatch.setattr(
            reporter,
            "_analyze_repositories_parallel",
            lambda repo_dirs: [],
        )

        # Should not raise NoRepositoriesError.
        report_data = reporter.analyze_repositories(repos_path)
        assert "repositories" in report_data
