# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Serialisation of the report written to ``report_raw.json``.

The in-memory report keeps full repository and author objects in its ranked
``summaries`` lists, because the templates read them. Written verbatim, those
lists repeat every repository and author several times over. The raw report
instead stores each ranked entry as the key of its base entry in
``repositories`` (``gerrit_project``) or ``authors`` (``email``), and is
written as compact JSON.

A ranked item in the written report takes exactly one of three forms, told
apart by type and by the single wrapper field an object carries:

- a string: the key of a base entry the ranked entry equals;
- ``{"ref": key, "extra": {...}}``: the base entry with rank-specific fields
  added;
- ``{"entry": value}``: the ranked entry verbatim, written when it cannot be
  reduced to a reference.
"""

import json
from pathlib import Path
from typing import Any


# Version of the report written to ``report_raw.json``. Both the CLI and
# library callers of ``RepositoryReporter`` label their reports with it.
REPORT_SCHEMA_VERSION = "1.6.0"

# Ranked summary list -> (base collection, key field identifying an entry)
RANKED_REFERENCES: dict[str, tuple[str, str]] = {
    "all_repositories": ("repositories", "gerrit_project"),
    "top_current_repositories": ("repositories", "gerrit_project"),
    "top_active_repositories": ("repositories", "gerrit_project"),
    "least_active_repositories": ("repositories", "gerrit_project"),
    "top_contributors_commits": ("authors", "email"),
    "top_contributors_loc": ("authors", "email"),
}


def _index_by_key(entries: Any, key_field: str) -> dict[str, dict[str, Any]]:
    """Map each key to its entry, leaving out keys that are not unique."""
    index: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()
    if not isinstance(entries, list):
        return index
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = entry.get(key_field)
        if not isinstance(key, str):
            continue
        if key in index:
            duplicates.add(key)
        index[key] = entry
    for key in duplicates:
        del index[key]
    return index


def _reference(entry: Any, index: dict[str, dict[str, Any]], key_field: str) -> Any:
    """Reduce a ranked entry to its key, or keep it whole if it cannot resolve.

    An entry that carries every field of its base entry unchanged becomes the
    bare key. Fields only the ranked entry has go in a ``ref``/``extra``
    object. An entry that has no base entry, or disagrees with it, is wrapped
    whole in an ``entry`` object so no data is lost and no reader mistakes it
    for a reference.
    """
    if not isinstance(entry, dict):
        return {"entry": entry}
    key = entry.get(key_field)
    base = index.get(key) if isinstance(key, str) else None
    if base is None:
        return {"entry": entry}
    if entry is not base and any(
        field not in entry or entry[field] != value for field, value in base.items()
    ):
        return {"entry": entry}
    extras = {field: value for field, value in entry.items() if field not in base}
    if not extras:
        return key
    return {"ref": key, "extra": extras}


def raw_report_document(report_data: dict[str, Any]) -> dict[str, Any]:
    """Return the document written to ``report_raw.json``.

    The result shares its unchanged parts with ``report_data``; neither
    ``report_data`` nor its ``summaries`` is modified.
    """
    summaries = report_data.get("summaries")
    if not isinstance(summaries, dict):
        return report_data

    indexes: dict[str, dict[str, dict[str, Any]]] = {}
    raw_summaries = dict(summaries)
    for list_name, (collection, key_field) in RANKED_REFERENCES.items():
        entries = summaries.get(list_name)
        if not isinstance(entries, list):
            continue
        index = indexes.get(collection)
        if index is None:
            index = _index_by_key(report_data.get(collection), key_field)
            indexes[collection] = index
        raw_summaries[list_name] = [_reference(entry, index, key_field) for entry in entries]

    return {**report_data, "summaries": raw_summaries}


def to_raw_json(report_data: dict[str, Any]) -> str:
    """Serialise ``report_data`` as compact JSON with ranked lists as keys."""
    return json.dumps(
        raw_report_document(report_data),
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def write_raw_json(report_data: dict[str, Any], path: Path) -> None:
    """Write ``report_data`` to ``path`` in the raw report format."""
    path.write_text(to_raw_json(report_data), encoding="utf-8")
