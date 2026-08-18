# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Console output for the template field audit.

Formats the template, runtime and verification summaries printed by
``scripts/audit_templates.py``.
"""

from collections import defaultdict


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
