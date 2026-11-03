# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Tests for the compact ``report_raw.json`` serialisation.

The written report must carry no indentation whitespace, must replace the
ranked repository and contributor lists in ``summaries`` with keys that
resolve to entries in ``repositories`` and ``authors``, and must leave every
other part of the document unchanged.
"""

import copy
import json
import logging
from typing import Any

import pytest

from lf_releng_project_reporting.aggregators import DataAggregator


WINDOW = "last_365"

REPOSITORY_LISTS = (
    "all_repositories",
    "top_current_repositories",
    "top_active_repositories",
    "least_active_repositories",
)
AUTHOR_LISTS = ("top_contributors_commits", "top_contributors_loc")


def _author(name: str, email: str, commits: int, net: int) -> dict[str, Any]:
    """Build a per-repository author record."""
    return {
        "name": name,
        "email": email,
        "username": email.split("@", 1)[0],
        "domain": email.split("@", 1)[1],
        "commits": {WINDOW: commits},
        "lines_added": {WINDOW: net + 1},
        "lines_removed": {WINDOW: 1},
        "lines_net": {WINDOW: net},
    }


def _repository(
    name: str,
    status: str,
    commits: int,
    days: int | None,
    authors: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a repository record as the git collector produces it."""
    return {
        "gerrit_project": name,
        "has_any_commits": commits > 0,
        "activity_status": status,
        "days_since_last_commit": days,
        "commit_counts": {WINDOW: commits},
        "loc_stats": {WINDOW: {"added": commits * 10, "removed": commits}},
        "authors": authors,
    }


def _report_data() -> dict[str, Any]:
    """Build a small report the way the analysis pipeline assembles it."""
    repositories = [
        _repository(
            "alpha",
            "current",
            12,
            3,
            [
                _author("Ada", "ada@example.org", 8, 120),
                _author("Zoë Ångström", "zoe@example.com", 4, 40),
            ],
        ),
        _repository(
            "beta/core",
            "active",
            5,
            200,
            [_author("Ada", "ada@example.org", 5, 30)],
        ),
        _repository(
            "gamma",
            "inactive",
            1,
            900,
            [_author("Bo", "bo@example.net", 1, -5)],
        ),
        _repository("empty", "inactive", 0, None, []),
    ]
    aggregator = DataAggregator(
        {"time_windows": {WINDOW: {"days": 365}}, "primary_reporting_window": WINDOW},
        logging.getLogger(__name__),
    )
    authors = aggregator.compute_author_rollups(repositories)
    return {
        "schema_version": "1.6.0",
        "project": "Example",
        "repositories": repositories,
        "authors": authors,
        "organizations": aggregator.compute_org_rollups(authors),
        "summaries": aggregator.aggregate_global_data(repositories),
        "errors": [],
    }


def _plain(data: Any) -> Any:
    """Return the JSON value the writer would produce for ``data``."""
    return json.loads(json.dumps(data, ensure_ascii=False, default=str))


def _resolve(raw: dict[str, Any], list_name: str) -> list[Any]:
    """Expand a reference list from the written report back to full entries."""
    if list_name in AUTHOR_LISTS:
        collection, key_field = raw["authors"], "email"
    else:
        collection, key_field = raw["repositories"], "gerrit_project"
    index = {entry[key_field]: entry for entry in collection}
    resolved = []
    for item in raw["summaries"][list_name]:
        if isinstance(item, str):
            resolved.append(index[item])
        elif "ref" in item:
            resolved.append({**index[item["ref"]], **item["extra"]})
        else:
            resolved.append(item["entry"])
    return resolved


@pytest.mark.xfail(strict=True, reason="compact raw report not yet implemented")
class TestToRawJson:
    """Serialisation of the report written to ``report_raw.json``."""

    def test_output_has_no_indentation(self):
        """The document is compact: no newlines or padded separators."""
        from lf_releng_project_reporting.raw_report import to_raw_json

        text = to_raw_json(_report_data())

        assert "\n" not in text
        assert text == json.dumps(json.loads(text), separators=(",", ":"), ensure_ascii=False)

    def test_non_ascii_is_written_verbatim(self):
        """Names keep their characters rather than ``\\u`` escapes."""
        from lf_releng_project_reporting.raw_report import to_raw_json

        text = to_raw_json(_report_data())

        assert "Zoë Ångström" in text

    def test_ranked_lists_are_references(self):
        """Every ranked entry is a key that resolves to a base entry."""
        from lf_releng_project_reporting.raw_report import to_raw_json

        raw = json.loads(to_raw_json(_report_data()))
        repository_keys = {repo["gerrit_project"] for repo in raw["repositories"]}
        author_keys = {author["email"] for author in raw["authors"]}

        for list_name in REPOSITORY_LISTS:
            assert raw["summaries"][list_name], list_name
            assert all(isinstance(item, str) for item in raw["summaries"][list_name])
            assert set(raw["summaries"][list_name]) <= repository_keys
        for list_name in AUTHOR_LISTS:
            assert raw["summaries"][list_name], list_name
            assert all(isinstance(item, str) for item in raw["summaries"][list_name])
            assert set(raw["summaries"][list_name]) <= author_keys

    def test_references_resolve_to_original_entries(self):
        """Resolving each key yields the entry the in-memory summary held."""
        from lf_releng_project_reporting.raw_report import to_raw_json

        report_data = _report_data()
        raw = json.loads(to_raw_json(report_data))

        for list_name in REPOSITORY_LISTS + AUTHOR_LISTS:
            expected = _plain(report_data["summaries"][list_name])
            assert _resolve(raw, list_name) == expected, list_name

    def test_rest_of_document_is_unchanged(self):
        """Only the ranked lists in ``summaries`` differ from a plain dump."""
        from lf_releng_project_reporting.raw_report import to_raw_json

        report_data = _report_data()
        raw = json.loads(to_raw_json(report_data))
        expected = _plain(report_data)

        for list_name in REPOSITORY_LISTS + AUTHOR_LISTS:
            del raw["summaries"][list_name]
            del expected["summaries"][list_name]
        assert raw == expected

    def test_in_memory_report_is_not_modified(self):
        """Renderers keep receiving the full summary objects."""
        from lf_releng_project_reporting.raw_report import to_raw_json

        report_data = _report_data()
        before = copy.deepcopy(report_data)

        to_raw_json(report_data)

        assert report_data == before

    def test_rank_specific_fields_stay_beside_the_key(self):
        """Fields the base entry lacks are kept in a small object."""
        from lf_releng_project_reporting.raw_report import to_raw_json

        report_data = _report_data()
        first = report_data["summaries"]["all_repositories"][0]
        report_data["summaries"]["all_repositories"][0] = {**first, "rank": 1}

        raw = json.loads(to_raw_json(report_data))

        assert raw["summaries"]["all_repositories"][0] == {
            "ref": first["gerrit_project"],
            "extra": {"rank": 1},
        }
        assert _resolve(raw, "all_repositories")[0] == _plain({**first, "rank": 1})

    def test_unresolvable_entries_are_written_in_full(self):
        """An entry with no matching base entry is not reduced to a key."""
        from lf_releng_project_reporting.raw_report import to_raw_json

        report_data = _report_data()
        stray = {"gerrit_project": "not-analysed", "commit_counts": {WINDOW: 1}}
        report_data["summaries"]["top_current_repositories"].append(stray)
        changed = dict(report_data["summaries"]["top_active_repositories"][0])
        changed["commit_counts"] = {WINDOW: 999}
        report_data["summaries"]["top_active_repositories"][0] = changed

        raw = json.loads(to_raw_json(report_data))

        assert raw["summaries"]["top_current_repositories"][-1] == {"entry": stray}
        assert raw["summaries"]["top_active_repositories"][0] == {"entry": _plain(changed)}

    def test_partial_entry_is_not_mistaken_for_a_reference(self):
        """A partial entry and a base entry with extras round-trip distinctly."""
        from lf_releng_project_reporting.raw_report import to_raw_json

        report_data = _report_data()
        first = report_data["summaries"]["all_repositories"][0]
        extended = {**first, "rank": 1}
        partial = {"gerrit_project": first["gerrit_project"], "rank": 1}
        report_data["summaries"]["all_repositories"][:2] = [extended, partial]

        raw = json.loads(to_raw_json(report_data))
        items = raw["summaries"]["all_repositories"]

        assert items[0] != items[1]
        assert _resolve(raw, "all_repositories")[:2] == _plain([extended, partial])

    def test_report_writers_use_the_raw_format(self, tmp_path):
        """Both writers of ``report_raw.json`` produce the same document."""
        from lf_releng_project_reporting.raw_report import to_raw_json, write_raw_json
        from lf_releng_project_reporting.rendering.renderer import ModernReportRenderer

        report_data = _report_data()
        written = tmp_path / "written.json"
        rendered = tmp_path / "rendered" / "report_raw.json"

        write_raw_json(report_data, written)
        ModernReportRenderer({}, logging.getLogger(__name__)).render_json_report(
            report_data, rendered
        )

        assert written.read_text(encoding="utf-8") == to_raw_json(report_data)
        assert rendered.read_text(encoding="utf-8") == to_raw_json(report_data)


@pytest.mark.xfail(strict=True, reason="compact raw report not yet implemented")
class TestReportSchemaVersion:
    """Every report in the raw format is labelled with its schema version."""

    def test_cli_uses_the_raw_report_version(self):
        """The CLI injects the version the raw report format defines."""
        from lf_releng_project_reporting import main
        from lf_releng_project_reporting.raw_report import REPORT_SCHEMA_VERSION

        assert REPORT_SCHEMA_VERSION == "1.6.0"
        assert main.SCHEMA_VERSION == REPORT_SCHEMA_VERSION

    def test_library_reports_use_the_raw_report_version(self, tmp_path, monkeypatch):
        """A reporter built without the CLI labels its report correctly."""
        from lf_releng_project_reporting.raw_report import REPORT_SCHEMA_VERSION
        from lf_releng_project_reporting.reporter import RepositoryReporter

        reporter = RepositoryReporter(
            {"project": "Example", "info_yaml": {"enabled": False}},
            logging.getLogger(__name__),
        )
        monkeypatch.setattr(reporter, "_clone_info_master_repo", lambda: None)
        monkeypatch.setattr(reporter, "_collect_info_yaml_data", lambda *args, **kwargs: None)
        repos_path = tmp_path / "repos"
        repos_path.mkdir()

        report_data = reporter.analyze_repositories(repos_path, allow_empty=True)

        assert report_data["schema_version"] == REPORT_SCHEMA_VERSION
