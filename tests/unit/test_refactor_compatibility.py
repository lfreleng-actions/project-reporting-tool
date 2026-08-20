# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Regression tests for module-to-package compatibility facades."""

import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lf_releng_project_reporting.aggregators.data import DataAggregator
from lf_releng_project_reporting.collectors.git import GitDataCollector
from lf_releng_project_reporting.collectors.info_yaml.enricher import InfoYamlEnricher
from lf_releng_project_reporting.collectors.info_yaml.validator import (
    URLValidator,
    validate_url,
    validate_urls,
    validate_urls_async,
)
from lf_releng_project_reporting.features.registry import FeatureRegistry
from lf_releng_project_reporting.reporter import RepositoryReporter
from rendering.context import RenderContext


def test_public_classes_keep_historical_module_paths():
    """Moved classes retain their import and pickle identities."""
    assert DataAggregator.__module__ == "lf_releng_project_reporting.aggregators.data"
    assert FeatureRegistry.__module__ == "lf_releng_project_reporting.features.registry"
    assert RepositoryReporter.__module__ == "lf_releng_project_reporting.reporter"
    assert InfoYamlEnricher.__module__ == (
        "lf_releng_project_reporting.collectors.info_yaml.enricher"
    )
    assert URLValidator.__module__ == ("lf_releng_project_reporting.collectors.info_yaml.validator")
    assert RenderContext.__module__ == "rendering.context"


def test_reporter_resolves_constructor_dependencies_through_facade():
    """Historical reporter mock paths continue to intercept construction."""
    logger = MagicMock()

    with (
        patch("lf_releng_project_reporting.reporter.GitDataCollector") as git_collector,
        patch("lf_releng_project_reporting.reporter.FeatureRegistry") as feature_registry,
        patch("lf_releng_project_reporting.reporter.DataAggregator") as aggregator,
        patch("lf_releng_project_reporting.reporter.ModernReportRenderer") as renderer,
        patch("lf_releng_project_reporting.reporter.INFOYamlCollector") as info_collector,
    ):
        reporter = RepositoryReporter({}, logger)

    assert reporter.git_collector is git_collector.return_value
    assert reporter.feature_registry is feature_registry.return_value
    assert reporter.aggregator is aggregator.return_value
    assert reporter.renderer is renderer.return_value
    assert reporter.info_yaml_collector is info_collector.return_value


def test_enricher_resolves_dependencies_through_facade():
    """Historical enricher mock paths continue to intercept construction."""
    with (
        patch(
            "lf_releng_project_reporting.collectors.info_yaml.enricher.URLValidator"
        ) as validator,
        patch(
            "lf_releng_project_reporting.collectors.info_yaml.enricher.CommitterMatcher"
        ) as matcher,
    ):
        enricher = InfoYamlEnricher()

    assert enricher.url_validator is validator.return_value
    assert enricher.matcher is matcher.return_value


def test_validator_functions_resolve_dependency_through_facade():
    """Synchronous helpers use the historical URLValidator patch point."""
    with patch(
        "lf_releng_project_reporting.collectors.info_yaml.validator.URLValidator"
    ) as validator:
        validator.return_value.validate.return_value = (True, "")
        validator.return_value.validate_bulk.return_value = {"https://example.com": (True, "")}

        assert validate_url("https://example.com") == (True, "")
        assert validate_urls(["https://example.com"]) == {"https://example.com": (True, "")}

    assert validator.call_count == 2


@pytest.mark.asyncio
async def test_async_validator_function_resolves_dependency_through_facade():
    """The asynchronous helper uses the historical URLValidator patch point."""
    with patch(
        "lf_releng_project_reporting.collectors.info_yaml.validator.URLValidator"
    ) as validator:
        validator.return_value.validate_bulk_async = AsyncMock(
            return_value={"https://example.com": (True, "")}
        )

        result = await validate_urls_async(["https://example.com"])

    assert result == {"https://example.com": (True, "")}
    validator.assert_called_once()


def test_git_collector_caches_complete_metrics_envelope(tmp_path: Path):
    """Repository cache writes the same complete envelope returned to callers."""
    repo_path = tmp_path / "repo"
    (repo_path / ".git").mkdir(parents=True)
    collector = GitDataCollector(
        {
            "gerrit": {"enabled": False},
            "jenkins": {"enabled": False},
        },
        {"last_365": {"start_timestamp": 0}},
        logging.getLogger(__name__),
    )
    collector.repos_path = tmp_path
    collector.cache_enabled = True

    with (
        patch.object(collector, "_load_from_cache", return_value=None),
        patch.object(collector, "_parse_git_log_output", return_value=[]),
        patch.object(collector, "_finalize_repo_metrics"),
        patch.object(collector, "_save_cached_metrics") as save_metrics,
        patch(
            "lf_releng_project_reporting.collectors.git.repository.safe_git_command",
            return_value=(True, ""),
        ),
    ):
        metrics = collector.collect_repo_git_metrics(repo_path)

    save_metrics.assert_called_once_with(repo_path, metrics)
    assert "repository" in save_metrics.call_args.args[1]
    assert "authors" in save_metrics.call_args.args[1]
