# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Integration tests for third-party assets referenced by HTML reports.

A published report must not pull a floating version of an external
asset, and every external asset must carry Subresource Integrity so a
compromised CDN cannot change what the page runs.
"""

import logging
import re
from html.parser import HTMLParser

import pytest

from rendering.renderer import ModernReportRenderer


PINNED_VERSION = re.compile(r"@\d+\.\d+\.\d+(/|$)")


class _ExternalAssetCollector(HTMLParser):
    """Collect <script src> and <link href> tags that load from another origin."""

    def __init__(self) -> None:
        super().__init__()
        self.assets: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        url = None
        if tag == "script":
            url = attributes.get("src")
        elif tag == "link":
            url = attributes.get("href")
        if url and url.startswith(("http://", "https://", "//")):
            self.assets.append({"tag": tag, "url": url, **attributes})


@pytest.fixture
def external_assets(realistic_report_data):
    """Render a full HTML report and return its third-party asset tags."""
    config = {"project": "TestProject"}
    renderer = ModernReportRenderer(config, logging.getLogger(__name__))
    collector = _ExternalAssetCollector()
    collector.feed(renderer.render_html(realistic_report_data))
    return collector.assets


def test_html_report_pins_external_assets(external_assets):
    """Every third-party asset names an exact release, never @latest."""
    assert external_assets, "Expected the DataTables CDN includes in the report"
    for asset in external_assets:
        assert "@latest" not in asset["url"], f"Floating version in {asset['url']}"
        assert PINNED_VERSION.search(asset["url"]), f"Unpinned version in {asset['url']}"


def test_html_report_external_assets_have_integrity(external_assets):
    """Every third-party asset carries an SRI hash and a CORS mode."""
    assert external_assets
    for asset in external_assets:
        integrity = asset.get("integrity") or ""
        assert integrity.startswith("sha384-"), f"Missing integrity on {asset['url']}"
        assert asset.get("crossorigin") == "anonymous", f"Missing crossorigin on {asset['url']}"
