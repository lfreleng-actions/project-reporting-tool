# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Guard the top-level layout of the built wheel.

The wheel must install a single import package, lf_releng_project_reporting,
plus its dist-info metadata and the .data directory that carries the
shared-data examples, which installs under share/ rather than as an
importable name. A generic top-level name (rendering, templates,
themes and the like) would clash with other distributions in the same
environment, so this test fails as soon as the wheel ships one.
"""

import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_NAME = "lf_releng_project_reporting"


@pytest.fixture(scope="module")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the wheel with uv, or fall back to an existing dist/*.whl."""
    out_dir = tmp_path_factory.mktemp("wheel")
    uv = shutil.which("uv")
    if uv is not None:
        subprocess.run(
            [uv, "build", "--wheel", "--out-dir", str(out_dir), str(PROJECT_ROOT)],
            check=True,
            capture_output=True,
            timeout=300,
        )
        wheels = sorted(out_dir.glob("*.whl"))
    else:
        wheels = sorted((PROJECT_ROOT / "dist").glob("*.whl"))
    if not wheels:
        pytest.skip("uv is not available and dist/ holds no wheel")
    return wheels[-1]


def _top_level_entries(wheel: Path) -> set[str]:
    """Return the first path component of every entry in the wheel."""
    with zipfile.ZipFile(wheel) as archive:
        return {name.split("/", 1)[0] for name in archive.namelist()}


XFAIL_REASON = "templates, themes and rendering still ship outside the package"


@pytest.mark.slow
@pytest.mark.xfail(strict=True, reason=XFAIL_REASON)
def test_wheel_ships_only_the_package_and_dist_info(wheel: Path) -> None:
    """The wheel holds only the package directory and wheel metadata."""
    entries = _top_level_entries(wheel)

    unexpected = sorted(
        entry
        for entry in entries
        if entry != PACKAGE_NAME and not entry.endswith((".dist-info", ".data"))
    )
    assert PACKAGE_NAME in entries
    assert unexpected == [], f"{wheel.name} has unexpected top-level entries: {unexpected}"


@pytest.mark.slow
@pytest.mark.xfail(strict=True, reason=XFAIL_REASON)
def test_wheel_ships_templates_and_themes(wheel: Path) -> None:
    """Templates and themes travel inside the package directory."""
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

    for path in (
        f"{PACKAGE_NAME}/templates/html/base.html.j2",
        f"{PACKAGE_NAME}/templates/markdown/base.md.j2",
        f"{PACKAGE_NAME}/themes/default/theme.css",
        f"{PACKAGE_NAME}/rendering/renderer.py",
    ):
        assert path in names, f"{wheel.name} lacks {path}"
