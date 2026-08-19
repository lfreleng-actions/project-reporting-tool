# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Field extraction and verification for the template field audit.

Holds the static template scan, the runtime context build and the
comparison between the two used by ``scripts/audit_templates.py``.
"""

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from template_audit_fixtures import _synthetic_test_data


def extract_template_fields(template_dir: Path) -> dict[str, dict[str, set[str]]]:
    """
    Extract all field accesses from templates.

    Args:
        template_dir: Path to templates directory

    Returns:
        Dict mapping template paths to categories to field sets
    """
    field_accesses = defaultdict(lambda: defaultdict(set))

    # Fields to ignore (these are rendered content, not data)
    ignore_fields = {"html", "md", "count", "percentage", "state"}

    # Patterns to match field accesses: object.field
    patterns = [
        (r"summary\.(\w+)", "summary"),
        (r"org\.(\w+)", "organization"),
        (r"contributor\.(\w+)", "contributor"),
        (r"repo\.(\w+)", "repository"),
        (r"repo_data\.(\w+)", "feature_matrix"),
        (r"workflows\.(\w+)", "workflows"),
        (r"features\.(\w+)", "features"),
        (r"repositories\.(\w+)", "repositories"),
        (r"organizations\.(\w+)", "organizations"),
        (r"contributors\.(\w+)", "contributors"),
    ]

    # Scan all template files
    for template_file in template_dir.rglob("*.j2"):
        content = template_file.read_text()

        for pattern, category in patterns:
            matches = re.findall(pattern, content)
            if matches:
                for field in matches:
                    if field not in ignore_fields:
                        field_accesses[str(template_file.relative_to(template_dir))][category].add(
                            field
                        )

    return dict(field_accesses)


def build_runtime_context() -> dict[str, Any]:
    """
    Build actual context using context builders with real production data.

    Uses minimal production data from fixtures if available,
    falls back to synthetic test data if not.

    Returns:
        Dict with actual runtime context from all builders
    """
    # Import here to avoid issues if run from different directory
    import json
    import sys
    from pathlib import Path

    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    sys.path.insert(0, str(project_root / "src"))

    from rendering.context import RenderContext

    # Try to load real production data from fixtures
    fixture_file = project_root / "tests" / "fixtures" / "minimal_production_data.json"

    if fixture_file.exists():
        print("   Using real production data from fixtures...")
        with open(fixture_file) as f:
            test_data = json.load(f)
    else:
        print("   Using synthetic test data (fixtures not found)...")
        # Fallback: Realistic test data structure matching actual production data
        test_data = _synthetic_test_data()

    # Build context
    config = {"output": {}}
    ctx = RenderContext(test_data, config)

    # Execute all context builders and collect results
    runtime_context = {
        "summary": ctx._build_summary_context(),
        "organizations": ctx._build_organizations_context(),
        "contributors": ctx._build_contributors_context(),
        "repositories": ctx._build_repositories_context(),
        "features": ctx._build_features_context(),
        "workflows": ctx._build_workflows_context(),
    }

    return runtime_context


def extract_runtime_fields(runtime_context: dict[str, Any]) -> dict[str, dict[str, set[str]]]:
    """
    Extract what fields are actually available in runtime context.

    Args:
        runtime_context: Actual runtime context from builders

    Returns:
        Dict mapping context names to field information
    """
    results = {}

    for context_name, context_data in runtime_context.items():
        top_level = set(context_data.keys())
        items = set()

        # Find list fields and extract item keys
        list_fields = ["top", "top_by_commits", "all", "matrix", "repositories"]
        for list_field in list_fields:
            if list_field in context_data and context_data[list_field]:
                items_list = context_data[list_field]
                if isinstance(items_list, list) and len(items_list) > 0:
                    first_item = items_list[0]
                    if isinstance(first_item, dict):
                        items.update(first_item.keys())

        results[context_name] = {"top_level": top_level, "items": items}

    return results


def verify_template_fields(
    template_fields: dict[str, dict[str, set[str]]], runtime_fields: dict[str, dict[str, set[str]]]
) -> list[tuple[str, str, set[str]]]:
    """
    Verify template field accesses against runtime context.

    Args:
        template_fields: Fields accessed by templates
        runtime_fields: Fields available at runtime

    Returns:
        List of (template_path, category, missing_fields) for any issues
    """
    # Map template categories to runtime contexts
    category_mapping = {
        "summary": ("summary", "top_level"),
        "organizations": ("organizations", "top_level"),
        "organization": ("organizations", "items"),
        "contributors": ("contributors", "top_level"),
        "contributor": ("contributors", "items"),
        "repositories": ("repositories", "top_level"),
        "repository": ("repositories", "items"),
        "features": ("features", "top_level"),
        "feature_matrix": ("features", "items"),
        "workflows": ("workflows", "top_level"),
    }

    issues = []

    for template_path, categories in template_fields.items():
        for category, expected_fields in categories.items():
            if category not in category_mapping:
                continue

            runtime_cat, level = category_mapping[category]

            # Get available fields from runtime
            runtime_cat_fields = runtime_fields.get(runtime_cat, {})
            available = runtime_cat_fields.get(level, set())

            # Special case: repository in workflows context
            if category == "repository" and "workflows" in template_path:
                workflows_data = runtime_fields.get("workflows", {})
                workflow_items = workflows_data.get("items", set())
                available = available | workflow_items

            # Check for nested field access (e.g., features.dependabot)
            # These are accessed as repo_data.features.dependabot in templates
            if category == "features" and level == "top_level":
                # Features at top level are checking feature presence in items
                # Get features from feature_matrix items
                features_data = runtime_fields.get("features", {})
                feature_items = features_data.get("items", set())
                if "features" in feature_items:
                    # The 'features' field is a dict, individual features are checked within it
                    # This is not a missing field issue
                    expected_fields = expected_fields - {
                        "dependabot",
                        "g2g",
                        "gitreview",
                        "pre_commit",
                        "readthedocs",
                    }

            missing = expected_fields - available

            if missing:
                issues.append((template_path, category, missing))

    return issues
