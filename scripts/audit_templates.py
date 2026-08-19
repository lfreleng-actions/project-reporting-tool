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

import sys
from pathlib import Path


# Allow importing the sibling helper modules that live alongside this script
sys.path.insert(0, str(Path(__file__).parent))

from template_audit_analysis import (
    build_runtime_context,
    extract_runtime_fields,
    extract_template_fields,
    verify_template_fields,
)
from template_audit_reporting import (
    print_runtime_summary,
    print_template_summary,
    print_verification_results,
)


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
