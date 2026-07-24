#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Validation script for JJB Attribution job-group expansion.

This script tests the JJB Attribution module to ensure job-groups are properly
expanded from global-jjb definitions. It provides detailed reporting on job
resolution rates and identifies any unresolved template variables.

Usage:
    python3 scripts/validate_jjb_job_groups.py

Environment Variables:
    CI_MGMT_URL: URL to ci-management repository (default: ONAP)
    CI_MGMT_BRANCH: Branch to use (default: master)
"""

import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jjb_attribution import JJBAttribution, JJBRepoManager


def test_job_group_expansion():
    """Test that job-groups are properly loaded and expanded."""
    print("=" * 80)
    print("JJB Attribution Job-Group Expansion Validation")
    print("=" * 80)
    print()

    # Initialize repository manager
    print("Step 1: Ensuring repositories are available...")
    repo_mgr = JJBRepoManager(cache_dir=Path("/tmp"))

    ci_mgmt_url = "https://gerrit.onap.org/r/ci-management"
    ci_mgmt_path, global_jjb_path = repo_mgr.ensure_repos(ci_mgmt_url, "master")

    print(f"✅ ci-management: {ci_mgmt_path}")
    print(f"✅ global-jjb: {global_jjb_path}")
    print()

    # Initialize JJB Attribution
    print("Step 2: Loading JJB templates and job-groups...")
    jjb = JJBAttribution(ci_mgmt_path, global_jjb_path)
    jjb.load_templates()

    summary = jjb.get_project_summary()
    print(f"✅ Loaded {summary['gerrit_projects']} Gerrit projects")
    print(f"✅ Total job templates: {len(jjb._templates)}")
    print(f"✅ Total job groups: {len(jjb._job_groups)}")
    print(f"✅ Total jobs: {summary['total_jobs']}")
    print()

    # Show sample job-groups
    print("Step 3: Sample job-groups loaded:")
    sample_groups = list(jjb._job_groups.items())[:8]
    for group_name, jobs in sample_groups:
        print(f"  • {group_name}")
        print(f"    └─> {jobs}")
    print()

    # Test specific projects that use job-groups
    print("Step 4: Testing job-group expansion on specific projects:")
    print("-" * 80)

    test_projects = [
        ("portal-ng/bff", "Uses gerrit-docker-jobs and gerrit-release-jobs"),
        ("portal-ng/ui", "Uses gerrit-docker-jobs and gerrit-release-jobs"),
        ("portal-ng/history", "Uses gerrit-docker-jobs and gerrit-release-jobs"),
        ("portal-ng/preferences", "Uses gerrit-docker-jobs and gerrit-release-jobs"),
        ("dcaegen2/collectors/restconf", "Uses maven jobs"),
        ("ccsdk/apps", "Uses multiple job groups"),
        ("integration", "Complex multi-stream project"),
        ("sdc", "Large project with many jobs"),
    ]

    total_projects = 0
    total_jobs = 0
    total_resolved = 0
    fully_resolved_projects = 0

    for project, description in test_projects:
        result = _report_project_expansion(jjb, project, description)
        if result is None:
            continue
        num_jobs, num_resolved, fully_resolved = result
        total_projects += 1
        total_jobs += num_jobs
        total_resolved += num_resolved
        if fully_resolved:
            fully_resolved_projects += 1

    return _print_expansion_summary(
        total_projects, total_jobs, total_resolved, fully_resolved_projects
    )


def _report_project_expansion(jjb, project, description):
    """Report job-group expansion for one project.

    Returns ``(num_jobs, num_resolved, fully_resolved)`` or None when the
    project has no JJB definition.
    """
    jobs = jjb.parse_project_jobs(project)
    resolved = [j for j in jobs if "{" not in j]
    unresolved = [j for j in jobs if "{" in j]

    if not jobs:
        print(f"⚠️  {project:40s} - No JJB definition found")
        return None

    percentage = (len(resolved) / len(jobs) * 100) if jobs else 0

    if percentage == 100:
        status = "✅"
    elif percentage >= 80:
        status = "⚠️ "
    else:
        status = "❌"

    print(f"{status} {project:40s} {len(resolved):3d}/{len(jobs):3d} ({percentage:5.1f}%)")
    print(f"    {description}")

    # Show sample resolved jobs
    if resolved:
        samples = resolved[:3]
        for sample in samples:
            print(f"      ✓ {sample}")
        if len(resolved) > 3:
            print(f"      ... and {len(resolved) - 3} more")

    # Show unresolved (if any)
    if unresolved:
        samples = unresolved[:2]
        for sample in samples:
            print(f"      ✗ {sample}")
        if len(unresolved) > 2:
            print(f"      ... and {len(unresolved) - 2} more unresolved")

    print()

    return len(jobs), len(resolved), percentage == 100


def _print_expansion_summary(total_projects, total_jobs, total_resolved, fully_resolved_projects):
    """Print the final validation summary and return the process exit code."""
    print("=" * 80)
    print("Summary:")
    print("=" * 80)
    if not total_projects or not total_jobs:
        print("❌ VALIDATION FAILED - No JJB job definitions were found")
        print(f"   Projects tested: {total_projects}, jobs found: {total_jobs}")
        return 1
    print(f"Projects tested: {total_projects}")
    print(
        f"Fully resolved projects: {fully_resolved_projects} ({fully_resolved_projects / total_projects * 100:.1f}%)"
    )
    print(f"Total jobs found: {total_jobs}")
    print(f"Resolved jobs: {total_resolved} ({total_resolved / total_jobs * 100:.1f}%)")
    print(
        f"Unresolved jobs: {total_jobs - total_resolved} ({(total_jobs - total_resolved) / total_jobs * 100:.1f}%)"
    )
    print()

    # Explanation of unresolved jobs
    if total_resolved < total_jobs:
        print("Note about unresolved jobs:")
        print("  Some jobs contain template variables that require additional context")
        print("  to resolve (e.g., {mvn-version}, {subproject}). These are edge cases")
        print("  where the JJB definitions use advanced templating that goes beyond")
        print("  standard job-group expansion.")
        print()

    # Success criteria
    success_rate = total_resolved / total_jobs * 100 if total_jobs else 0
    if success_rate >= 85:
        print("✅ VALIDATION PASSED - Job-group expansion is working well!")
        print(f"   Achievement: {success_rate:.1f}% job resolution rate")
        return 0

    print("⚠️  VALIDATION WARNING - Job resolution rate below target")
    print(f"   Current: {success_rate:.1f}%, Target: 85%+")
    return 1


if __name__ == "__main__":
    try:
        exit_code = test_job_group_expansion()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
