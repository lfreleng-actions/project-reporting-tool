#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
"""Validate that `.python-version` stays consistent with pyproject.toml.

This guard exists because `.python-version` (the default interpreter for
local development, ``uv``, and CI) is a hand-maintained pin that is easy
to forget when the supported Python range changes in ``pyproject.toml``.
A drift here is exactly what broke the scheduled production reporting run:
``requires-python`` was raised to ``>=3.11`` while ``.python-version``
still pinned ``3.10``, so ``uv sync`` refused to resolve an interpreter.

The hook enforces two invariants:

1. The version in ``.python-version`` MUST satisfy the ``requires-python``
   constraint declared in ``pyproject.toml`` (prevents the breakage).
2. The version in ``.python-version`` MUST be the LATEST version declared
   in the ``Programming Language :: Python :: 3.x`` trove classifiers, so
   the project runs against its newest supported interpreter by default.

Run manually with::

    python scripts/check-python-version.py

It also runs automatically via pre-commit whenever ``.python-version`` or
``pyproject.toml`` changes.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import NoReturn


try:
    from packaging.specifiers import InvalidSpecifier, SpecifierSet
    from packaging.version import InvalidVersion, Version
except ModuleNotFoundError:
    # Emit an actionable message rather than a bare traceback when the
    # optional dependency is missing (e.g. when run outside pre-commit).
    sys.stderr.write(
        "::error::The 'packaging' package is required to run "
        "check-python-version.py. Install it (for example "
        "`uv pip install packaging`) or run the check through pre-commit, "
        "which provisions it automatically.\n"
    )
    raise SystemExit(1) from None


REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
PYTHON_VERSION_FILE = REPO_ROOT / ".python-version"

CLASSIFIER_PREFIX = "Programming Language :: Python :: "


def _fail(message: str) -> NoReturn:
    """Print a GitHub-Actions-friendly error and exit non-zero."""
    print(f"::error::{message}")
    sys.exit(1)


def read_pinned_version() -> str:
    """Return the interpreter version pinned in ``.python-version``.

    Comment lines (SPDX headers, explanatory notes) and blank lines are
    ignored so the file can carry documentation alongside the pin.
    """
    for raw_line in PYTHON_VERSION_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            return line
    _fail(f"No version pin found in {PYTHON_VERSION_FILE.name}")


def latest_supported_version(classifiers: list[str]) -> Version | None:
    """Return the highest ``3.x`` version from the trove classifiers."""
    versions: list[Version] = []
    for classifier in classifiers:
        if not classifier.startswith(CLASSIFIER_PREFIX):
            continue
        suffix = classifier[len(CLASSIFIER_PREFIX) :].strip()
        # Skip the bare "3" classifier and any non-numeric entries.
        if "." not in suffix:
            continue
        try:
            versions.append(Version(suffix))
        except ValueError:
            continue
    return max(versions) if versions else None


def main() -> int:
    """Validate the pin and report the first mismatch found."""
    with PYPROJECT.open("rb") as handle:
        pyproject = tomllib.load(handle)

    project = pyproject.get("project", {})
    requires_python = project.get("requires-python")
    classifiers = project.get("classifiers", [])

    pinned_raw = read_pinned_version()
    try:
        pinned = Version(pinned_raw)
    except InvalidVersion:
        _fail(f".python-version pins {pinned_raw!r}, which is not a valid Python version.")

    if requires_python:
        try:
            specifier = SpecifierSet(requires_python)
        except InvalidSpecifier:
            _fail(
                f"requires-python {requires_python!r} in pyproject.toml is "
                f"not a valid version specifier."
            )
        if not specifier.contains(pinned, prereleases=True):
            _fail(
                f".python-version pins {pinned_raw!r}, which does not satisfy "
                f"requires-python {requires_python!r} in pyproject.toml. "
                f"Update .python-version to a compatible release."
            )

    latest = latest_supported_version(classifiers)
    if latest is not None and pinned != latest:
        _fail(
            f".python-version pins {pinned_raw!r}, but the latest supported "
            f"release declared in the pyproject.toml classifiers is "
            f"{latest}. Pin the latest supported version so the project runs "
            f"against its newest interpreter by default (or drop the unused "
            f"classifier)."
        )

    print(
        f"✅ .python-version ({pinned_raw}) satisfies requires-python "
        f"({requires_python}) and matches the latest supported classifier."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
