# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Integration tests for DataTables functionality.

Tests that DataTables CSS/JS is properly injected and that
table classes are correctly applied.
"""

from pathlib import Path

import pytest


def test_datatables_css_macro_exists():
    """Test that DataTables support macro file exists."""
    macro_file = (
        Path(__file__).parent.parent
        / "src/lf_releng_project_reporting/templates/html/components/datatables_support.html.j2"
    )
    assert macro_file.exists(), "DataTables support macro file should exist"


def test_datatables_theme_css_exists():
    """Test that all themes have DataTables CSS."""
    themes_dir = Path(__file__).parent.parent / "src/lf_releng_project_reporting/themes"

    for theme in ["default", "dark", "minimal"]:
        theme_css = themes_dir / theme / "theme.css"
        assert theme_css.exists(), f"Theme {theme} CSS should exist"

        # Check for DataTables-specific classes
        content = theme_css.read_text()
        assert ".dataTable-wrapper" in content, (
            f"Theme {theme} should have DataTables wrapper styles"
        )
        assert ".dataTable-search" in content, f"Theme {theme} should have DataTables search styles"
        assert ".dataTable-pagination" in content, (
            f"Theme {theme} should have DataTables pagination styles"
        )


def test_base_template_has_datatables_import():
    """Test that base template imports DataTables macros."""
    base_template = (
        Path(__file__).parent.parent / "src/lf_releng_project_reporting/templates/html/base.html.j2"
    )
    content = base_template.read_text()

    assert "datatables_support.html.j2" in content, "Base template should import datatables_support"
    assert "datatables_css(config)" in content, (
        "Base template should call datatables_css macro with config"
    )
    assert "datatables_js(config)" in content, (
        "Base template should call datatables_js macro with config"
    )


def test_repositories_section_uses_dt_enabled():
    """Test that repositories section uses dt-enabled class."""
    repos_template = (
        Path(__file__).parent.parent
        / "src/lf_releng_project_reporting/templates/html/sections/repositories.html.j2"
    )
    content = repos_template.read_text()

    assert "dt-enabled" in content, "Repositories table should use dt-enabled class"


def test_features_section_disables_features():
    """Test that features section disables search and pagination."""
    features_template = (
        Path(__file__).parent.parent
        / "src/lf_releng_project_reporting/templates/html/sections/features.html.j2"
    )
    content = features_template.read_text()

    assert "dt-enabled" in content, "Features table should use dt-enabled class"
    assert "dt-no-search" in content, "Features table should disable search"
    assert "dt-no-pagination" in content, "Features table should disable pagination"


def test_data_table_component_supports_datatables():
    """Test that data_table component supports DataTables parameters."""
    component = (
        Path(__file__).parent.parent
        / "src/lf_releng_project_reporting/templates/html/components/data_table.html.j2"
    )
    content = component.read_text()

    assert "enable_datatables" in content, "Component should support enable_datatables parameter"
    assert "enable_search" in content, "Component should support enable_search parameter"
    assert "enable_pagination" in content, "Component should support enable_pagination parameter"
    assert "datatables_support" in content, "Component should import datatables_support"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
