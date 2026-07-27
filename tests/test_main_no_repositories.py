# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Tests for main() exit-code handling of the "no repositories" condition.

When repository discovery yields nothing, main() must exit with a non-zero,
retryable exit code (1) and must NOT produce a report. This protects
downstream consumers (for example, the GitHub Pages publish step) from having
good reports overwritten with empty output after a transient clone failure.
"""

import logging
from types import SimpleNamespace

import pytest

import lf_releng_project_reporting.main as main_module
from lf_releng_project_reporting.exceptions import NoRepositoriesError


class _RaisingReporter:
    """Stand-in reporter whose analysis always reports zero repositories."""

    def __init__(self, *args, **kwargs):
        pass

    def analyze_repositories(self, repos_path, allow_empty=False):
        raise NoRepositoriesError(f"No repositories found to analyze under '{repos_path}'.")


@pytest.fixture
def patched_main(monkeypatch, tmp_path):
    """Neutralise config loading/logging so only exit-code mapping is tested."""
    monkeypatch.setattr(
        main_module, "load_configuration", lambda project, config_dir: {"project": project}
    )
    monkeypatch.setattr(
        main_module, "_prepare_run_config", lambda args, config: logging.getLogger("test")
    )
    monkeypatch.setattr(main_module, "write_config_to_step_summary", lambda *a, **k: None)
    monkeypatch.setattr(main_module, "RepositoryReporter", _RaisingReporter)

    return SimpleNamespace(
        project="test-project",
        repos_path=tmp_path / "gerrit.onap.org",
        config_dir=tmp_path / "configuration",
        output_dir=tmp_path / "reports",
        validate_only=False,
        verbose=0,
        allow_empty=False,
    )


def test_main_returns_error_exit_code_on_no_repositories(patched_main):
    """main() returns exit code 1 (retryable) when no repositories are found."""
    exit_code = main_module.main(patched_main)
    assert exit_code == 1


def test_main_no_repositories_is_retryable(patched_main):
    """The returned exit code is classified as retryable for CI re-runs."""
    from cli.exit_codes import should_retry

    exit_code = main_module.main(patched_main)
    assert should_retry(exit_code) is True
