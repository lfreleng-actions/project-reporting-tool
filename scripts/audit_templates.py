#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Template Field Audit Script - Runtime Verification

This script performs a comprehensive audit of all Jinja2 templates by:
1. Extracting all field accesses from templates (static analysis)
2. Building actual context with realistic test data (runtime verification)
3. Comparing template expectations against actual runtime data

This approach is more reliable than pure static analysis because it uses
the actual context builders with real data to verify all fields are present.

Usage:
    python scripts/audit_templates.py

Exit codes:
    0 - Success (all fields verified)
    1 - Failure (missing fields detected)
"""

import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


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


def _synthetic_test_data() -> dict[str, Any]:
    """Return a realistic synthetic data structure for template auditing.

    Used as a fallback when the minimal production data fixture is absent.
    """
    return {
        "summaries": _synthetic_summaries(),
        "repositories": _synthetic_repositories(),
    }


def _synthetic_summaries() -> dict[str, Any]:
    """Return the synthetic ``summaries`` section for template auditing."""
    return {
        "all_repositories": [
            {
                "gerrit_project": "test/repo1",
                "unique_contributors": {"last_3_years": 10, "last_365": 8, "last_90": 5},
                "loc_stats": {"last_3_years": {"added": 5000, "removed": 2000, "net": 3000}},
                "last_commit_timestamp": "2026-01-10T12:00:00Z",
                "total_commits_ever": 100,
                "days_since_last_commit": 2,
                "activity_status": "current",
                "state": "ACTIVE",
            },
            {
                "gerrit_project": "test/repo2",
                "unique_contributors": {"last_3_years": 5},
                "loc_stats": {"last_3_years": {"added": 2000, "removed": 500, "net": 1500}},
                "last_commit_timestamp": "2025-12-01T12:00:00Z",
                "total_commits_ever": 50,
                "days_since_last_commit": 42,
                "activity_status": "active",
                "state": "ACTIVE",
            },
        ],
        "top_organizations": [
            {
                "domain": "example.com",
                "contributor_count": 10,
                "commits": {"last_3_years": 100, "last_365": 80},
                "lines_added": {"last_3_years": 5000, "last_365": 4000},
                "lines_removed": {"last_3_years": 2000, "last_365": 1500},
                "lines_net": {"last_3_years": 3000, "last_365": 2500},
                "repositories_count": {"last_3_years": 5, "last_365": 4},
            },
            {
                "domain": "test.org",
                "contributor_count": 8,
                "commits": {"last_3_years": 75},
                "lines_added": {"last_3_years": 3000},
                "lines_removed": {"last_3_years": 1000},
                "lines_net": {"last_3_years": 2000},
                "repositories_count": {"last_3_years": 3},
            },
        ],
        "top_contributors_commits": [
            {
                "name": "Test User",
                "email": "test@example.com",
                "domain": "example.com",
                "commits": {"last_3_years": 100, "last_365": 80},
                "lines_added": {"last_3_years": 5000, "last_365": 4000},
                "lines_removed": {"last_3_years": 2000, "last_365": 1500},
                "lines_net": {"last_3_years": 3000, "last_365": 2500},
                "repositories_touched": {"last_3_years": {"repo1", "repo2", "repo3"}},
            },
            {
                "name": "Another User",
                "email": "another@test.org",
                "domain": "test.org",
                "commits": {"last_3_years": 75},
                "lines_added": {"last_3_years": 3000},
                "lines_removed": {"last_3_years": 1000},
                "lines_net": {"last_3_years": 2000},
                "repositories_touched": {"last_3_years": {"repo1", "repo4"}},
            },
        ],
        "top_contributors_loc": [],
    }


def _synthetic_repositories() -> list[dict[str, Any]]:
    """Return the synthetic ``repositories`` section for template auditing."""
    return [
        {
            "gerrit_project": "test/repo1",
            "activity_status": "current",
            "days_since_last_commit": 2,
            "features": {
                "project_types": {"types": ["Java/Maven"]},
                "dependabot": {"present": True},
                "pre_commit": {"present": False},
                "readthedocs": {"present": True},
                "gitreview": {"present": True},
                "g2g": {"present": True},
            },
            "jenkins": {
                "jobs": [
                    {
                        "name": "test-job-1",
                        "status": "success",
                        "color": "blue",
                        "url": "https://jenkins.example.org/job/test-job-1/",
                    },
                    {
                        "name": "test-job-2",
                        "status": "failure",
                        "color": "red",
                        "url": "https://jenkins.example.org/job/test-job-2/",
                    },
                ]
            },
            "github_workflows": [
                {
                    "name": "ci.yaml",
                    "path": ".github/workflows/ci.yaml",
                    "state": "active",
                    "status": "success",
                }
            ],
        },
        {
            "gerrit_project": "test/repo2",
            "activity_status": "active",
            "days_since_last_commit": 42,
            "features": {
                "project_types": {"types": ["Go"]},
                "dependabot": {"present": False},
                "pre_commit": {"present": True},
                "readthedocs": {"present": False},
                "gitreview": {"present": True},
                "g2g": {"present": False},
            },
            "jenkins": {
                "jobs": [
                    {
                        "name": "test-job-3",
                        "status": "success",
                        "color": "blue",
                        "url": "https://jenkins.example.org/job/test-job-3/",
                    }
                ]
            },
            "github_workflows": [],
        },
    ]


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


def print_template_summary(template_fields: dict[str, dict[str, set[str]]]) -> None:
    """Print summary of template field accesses."""
    print("=" * 80)
    print("TEMPLATE FIELD ACCESS SUMMARY")
    print("=" * 80)

    total_templates = len(template_fields)
    total_accesses = sum(
        len(fields) for cats in template_fields.values() for fields in cats.values()
    )

    print("\n📊 Statistics:")
    print(f"   Templates scanned: {total_templates}")
    print(f"   Total field accesses: {total_accesses}")

    # Count by category
    category_counts = defaultdict(int)
    for categories in template_fields.values():
        for category, fields in categories.items():
            category_counts[category] += len(fields)

    print("\n📋 Field accesses by category:")
    for category, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"   {category:20} {count:3} fields")


def print_runtime_summary(runtime_fields: dict[str, dict[str, set[str]]]) -> None:
    """Print summary of runtime context."""
    print("\n" + "=" * 80)
    print("RUNTIME CONTEXT VERIFICATION")
    print("=" * 80)

    for context_name in sorted(runtime_fields.keys()):
        fields = runtime_fields[context_name]

        print(f"\n✓ {context_name.upper()} context:")

        if fields["top_level"]:
            print(f"   Top-level: {len(fields['top_level'])} fields")

        if fields["items"]:
            print(f"   List items: {len(fields['items'])} fields")


def print_verification_results(issues: list[tuple[str, str, set[str]]]) -> bool:
    """
    Print verification results.

    Returns:
        True if no issues, False if issues found
    """
    print("\n" + "=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)

    if not issues:
        print("\n✅ SUCCESS - All template fields verified!")
        print("\n   All field accesses in templates are provided by context builders.")
        print("   Templates will render without 'Undefined variable' errors.")
        return True

    print("\n❌ ISSUES FOUND - Missing fields detected!\n")

    # Group by template
    by_template = defaultdict(list)
    for template, category, missing in issues:
        by_template[template].append((category, missing))

    for template in sorted(by_template.keys()):
        print(f"\n📄 {template}")
        for category, missing in by_template[template]:
            print(f"\n   {category}:")
            for field in sorted(missing):
                print(f"      ❌ {field}")

    print("\n" + "=" * 80)
    print("❌ CRITICAL - Templates will fail at runtime!")
    print("=" * 80)
    print("\nAction required:")
    print("1. Add missing fields to context builders in src/rendering/context.py")
    print("2. OR remove field accesses from templates if not needed")
    print("3. Re-run this script to verify fixes")

    return False


def main():
    """Run the template audit."""
    print("Starting template field audit with runtime verification...\n")

    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    template_dir = project_root / "src" / "templates"

    if not template_dir.exists():
        print(f"❌ Template directory not found: {template_dir}")
        sys.exit(1)

    try:
        # 1. Extract template field accesses (static)
        print("Step 1: Scanning templates...")
        template_fields = extract_template_fields(template_dir)

        # 2. Build actual runtime context (dynamic)
        print("Step 2: Building runtime context...")
        runtime_context = build_runtime_context()

        # 3. Extract runtime field availability
        print("Step 3: Extracting runtime fields...")
        runtime_fields = extract_runtime_fields(runtime_context)

        # 4. Verify template fields against runtime
        print("Step 4: Verifying field accesses...\n")
        issues = verify_template_fields(template_fields, runtime_fields)

        # 5. Print results
        print_template_summary(template_fields)
        print_runtime_summary(runtime_fields)
        success = print_verification_results(issues)

        print()
        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
