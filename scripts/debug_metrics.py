#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Debug script to analyze organization metrics from HTML reports.
"""

import json
import re
import sys
from pathlib import Path


def extract_org_table(html_file):
    """Extract the Top Organizations table from an HTML report."""
    with open(html_file, encoding="utf-8") as f:
        content = f.read()

    # Find the Top Organizations section
    org_section_pattern = r"🏢 Top Organizations.*?</table>"
    match = re.search(org_section_pattern, content, re.DOTALL)

    if not match:
        print(f"Could not find Top Organizations table in {html_file}")
        return None

    table_html = match.group(0)

    # Extract table rows
    row_pattern = r"<tr>\s*<td>(\d+)</td>\s*<td>(.*?)</td>\s*<td>(\d+)</td>\s*<td>(\d+)</td>\s*<td>\+?(-?\d+)</td>\s*<td>(-?\d+)</td>"
    rows = re.findall(row_pattern, table_html, re.DOTALL)

    organizations = []
    for row in rows:
        rank, domain, contributors, commits, lines_added, lines_deleted = row
        organizations.append(
            {
                "rank": int(rank),
                "domain": domain.strip(),
                "contributors": int(contributors),
                "commits": int(commits),
                "lines_added": int(lines_added),
                "lines_deleted": int(lines_deleted),
            }
        )

    return organizations


def extract_contributor_table(html_file):
    """Extract the Top Contributors table from an HTML report."""
    with open(html_file, encoding="utf-8") as f:
        content = f.read()

    # Find the Top Contributors section
    contrib_section_pattern = r"👥 Top Contributors.*?</table>"
    match = re.search(contrib_section_pattern, content, re.DOTALL)

    if not match:
        print(f"Could not find Top Contributors table in {html_file}")
        return None

    table_html = match.group(0)

    # Extract table rows - look for rows with domain information
    row_pattern = r"<tr>\s*<td>(\d+)</td>\s*<td>(.*?)</td>\s*<td>(\d+)</td>\s*<td>\+?(-?\d+)</td>\s*<td>(-?\d+)</td>.*?<td>(.*?)</td>"
    rows = re.findall(row_pattern, table_html, re.DOTALL)

    contributors = []
    for row in rows:
        rank, name, commits, lines_added, lines_deleted, domain = row
        contributors.append(
            {
                "rank": int(rank),
                "name": name.strip(),
                "commits": int(commits),
                "lines_added": int(lines_added),
                "lines_deleted": int(lines_deleted),
                "domain": domain.strip(),
            }
        )

    return contributors


def compare_reports(production_file, test_file):
    """Compare production and test reports."""
    print("=" * 80)
    print("COMPARING REPORTS")
    print("=" * 80)

    # Extract organization tables
    print("\n📊 Extracting organization tables...")
    prod_orgs = extract_org_table(production_file)
    test_orgs = extract_org_table(test_file)

    if not prod_orgs or not test_orgs:
        print("ERROR: Could not extract organization tables")
        return

    print(f"  Production: {len(prod_orgs)} organizations")
    print(f"  Test:       {len(test_orgs)} organizations")

    # Compare est.tech specifically
    print("\n" + "=" * 80)
    print("🔍 ANALYZING est.tech")
    print("=" * 80)

    prod_est = next((o for o in prod_orgs if o["domain"] == "est.tech"), None)
    test_est = next((o for o in test_orgs if o["domain"] == "est.tech"), None)

    if prod_est:
        print("\nProduction est.tech:")
        print(f"  Rank:          {prod_est['rank']}")
        print(f"  Contributors:  {prod_est['contributors']}")
        print(f"  Commits:       {prod_est['commits']}")
        print(f"  Lines Added:   {prod_est['lines_added']:,}")
        print(f"  Lines Deleted: {prod_est['lines_deleted']:,}")
    else:
        print("\n❌ est.tech not found in production report!")

    if test_est:
        print("\nTest est.tech:")
        print(f"  Rank:          {test_est['rank']}")
        print(f"  Contributors:  {test_est['contributors']}")
        print(f"  Commits:       {test_est['commits']}")
        print(f"  Lines Added:   {test_est['lines_added']:,}")
        print(f"  Lines Deleted: {test_est['lines_deleted']:,}")
    else:
        print("\n❌ est.tech not found in test report!")

    if prod_est and test_est:
        print("\n📈 Differences:")
        print(f"  Contributors:  {test_est['contributors'] - prod_est['contributors']:+d}")
        print(f"  Commits:       {test_est['commits'] - prod_est['commits']:+d}")
        print(f"  Lines Added:   {test_est['lines_added'] - prod_est['lines_added']:+,}")
        print(f"  Lines Deleted: {test_est['lines_deleted'] - prod_est['lines_deleted']:+,}")

        if prod_est["lines_added"] > 0:
            ratio = test_est["lines_added"] / prod_est["lines_added"]
            print(f"\n  Lines Added Ratio: {ratio:.2f}x")

        if prod_est["lines_deleted"] > 0:
            ratio = test_est["lines_deleted"] / prod_est["lines_deleted"]
            print(f"  Lines Deleted Ratio: {ratio:.2f}x")

    # Extract and compare contributors
    print("\n" + "=" * 80)
    print("👥 ANALYZING CONTRIBUTORS FROM est.tech")
    print("=" * 80)

    prod_contribs = extract_contributor_table(production_file)
    test_contribs = extract_contributor_table(test_file)

    if prod_contribs and test_contribs:
        prod_est_contribs = [c for c in prod_contribs if c["domain"] == "est.tech"]
        test_est_contribs = [c for c in test_contribs if c["domain"] == "est.tech"]

        print(f"\nProduction: {len(prod_est_contribs)} est.tech contributors")
        print(f"Test:       {len(test_est_contribs)} est.tech contributors")

        # Show top 5 from each
        print("\nTop 5 Production est.tech contributors:")
        for i, contrib in enumerate(prod_est_contribs[:5], 1):
            print(
                f"  {i}. {contrib['name']}: {contrib['commits']} commits, "
                f"+{contrib['lines_added']:,}, -{contrib['lines_deleted']:,}"
            )

        print("\nTop 5 Test est.tech contributors:")
        for i, contrib in enumerate(test_est_contribs[:5], 1):
            print(
                f"  {i}. {contrib['name']}: {contrib['commits']} commits, "
                f"+{contrib['lines_added']:,}, -{contrib['lines_deleted']:,}"
            )

        # Calculate totals from contributors
        prod_total_added = sum(c["lines_added"] for c in prod_est_contribs)
        prod_total_deleted = sum(c["lines_deleted"] for c in prod_est_contribs)
        test_total_added = sum(c["lines_added"] for c in test_est_contribs)
        test_total_deleted = sum(c["lines_deleted"] for c in test_est_contribs)

        print("\n📊 Totals from summing contributors:")
        print(f"  Production: +{prod_total_added:,}, -{prod_total_deleted:,}")
        print(f"  Test:       +{test_total_added:,}, -{test_total_deleted:,}")

        if prod_est:
            print(
                f"\n  Org table (Production): +{prod_est['lines_added']:,}, -{prod_est['lines_deleted']:,}"
            )
        if test_est:
            print(
                f"  Org table (Test):       +{test_est['lines_added']:,}, -{test_est['lines_deleted']:,}"
            )


def analyze_json_data(json_file):
    """Analyze raw JSON data to understand the source of the discrepancy."""
    print("\n" + "=" * 80)
    print("🔍 ANALYZING RAW JSON DATA")
    print("=" * 80)

    with open(json_file, encoding="utf-8") as f:
        data = json.load(f)

    # Find est.tech organization
    organizations = data.get("organizations", [])
    est_tech = next((o for o in organizations if o.get("domain") == "est.tech"), None)

    if not est_tech:
        print("❌ est.tech not found in JSON data!")
        return

    print("\nOrganization Data:")
    print(f"  Domain: {est_tech.get('domain')}")
    print(f"  Contributors: {est_tech.get('contributor_count')}")

    # Check time windows
    for key in ["commits", "lines_added", "lines_removed", "lines_net"]:
        if key in est_tech:
            print(f"\n  {key}:")
            for window, value in est_tech[key].items():
                print(f"    {window}: {value:,}")

    # Sample some authors from est.tech
    authors = data.get("authors", [])
    est_tech_authors = [a for a in authors if a.get("domain") == "est.tech"]

    print(f"\n\n📊 Found {len(est_tech_authors)} authors from est.tech")

    if est_tech_authors:
        print("\nSample of top 5 authors by commits (last_365):")

        def _last_365(a):
            commits = a.get("commits", {})
            return commits.get("last_365", 0)

        sorted_authors = sorted(est_tech_authors, key=_last_365, reverse=True)[:5]

        for i, author in enumerate(sorted_authors, 1):
            name = author.get("name", "Unknown")
            email = author.get("email", "Unknown")
            commits = author.get("commits", {})
            lines_added = author.get("lines_added", {})
            lines_removed = author.get("lines_removed", {})

            print(f"\n  {i}. {name} ({email})")
            print(f"     Commits: {commits}")
            print(f"     Lines added: {lines_added}")
            print(f"     Lines removed: {lines_removed}")

    # Check repositories
    repositories = data.get("repositories", [])
    print(f"\n\n📦 Total repositories: {len(repositories)}")

    # Sample some repositories and their metrics
    print("\nSample of repositories with est.tech contributors:")
    repos_with_est_tech = []
    for repo in repositories[:10]:  # Check first 10 repos
        authors_in_repo = repo.get("authors", [])
        est_tech_in_repo = [a for a in authors_in_repo if a.get("domain") == "est.tech"]
        if est_tech_in_repo:
            repos_with_est_tech.append(
                {
                    "name": repo.get("gerrit_project", "Unknown"),
                    "est_tech_count": len(est_tech_in_repo),
                    "total_authors": len(authors_in_repo),
                }
            )

    for repo_info in repos_with_est_tech[:5]:
        print(
            f"  - {repo_info['name']}: {repo_info['est_tech_count']}/{repo_info['total_authors']} authors from est.tech"
        )

    # Check for duplicate counting
    print("\n\n🔎 Checking for duplicate counting issues...")

    # Sum up est.tech contributions from all repositories
    total_commits_from_repos = 0
    total_added_from_repos = 0
    total_removed_from_repos = 0

    for repo in repositories:
        for author in repo.get("authors", []):
            if author.get("domain") == "est.tech":
                # Use last_365 window for comparison
                commits_data = author.get("commits", {})
                total_commits_from_repos += commits_data.get("last_365", 0)
                added_data = author.get("lines_added", {})
                total_added_from_repos += added_data.get("last_365", 0)
                removed_data = author.get("lines_removed", {})
                total_removed_from_repos += removed_data.get("last_365", 0)

    print("\nSumming est.tech metrics from repository.authors:")
    print(f"  Commits: {total_commits_from_repos:,}")
    print(f"  Lines added: {total_added_from_repos:,}")
    print(f"  Lines removed: {total_removed_from_repos:,}")

    # Compare with organization totals
    org_commits_data = est_tech.get("commits", {})
    org_commits = org_commits_data.get("last_365", 0)
    org_added_data = est_tech.get("lines_added", {})
    org_added = org_added_data.get("last_365", 0)
    org_removed_data = est_tech.get("lines_removed", {})
    org_removed = org_removed_data.get("last_365", 0)

    print("\nOrganization totals (last_365):")
    print(f"  Commits: {org_commits:,}")
    print(f"  Lines added: {org_added:,}")
    print(f"  Lines removed: {org_removed:,}")

    if total_commits_from_repos != org_commits:
        print(f"\n⚠️  MISMATCH in commits: {total_commits_from_repos:,} vs {org_commits:,}")
        print(f"     Difference: {total_commits_from_repos - org_commits:,}")

    if total_added_from_repos != org_added:
        print(f"\n⚠️  MISMATCH in lines added: {total_added_from_repos:,} vs {org_added:,}")
        print(f"     Difference: {total_added_from_repos - org_added:,}")
        print(f"     Ratio: {total_added_from_repos / org_added if org_added > 0 else 0:.2f}x")

    if total_removed_from_repos != org_removed:
        print(f"\n⚠️  MISMATCH in lines removed: {total_removed_from_repos:,} vs {org_removed:,}")
        print(f"     Difference: {total_removed_from_repos - org_removed:,}")
        print(
            f"     Ratio: {total_removed_from_repos / org_removed if org_removed > 0 else 0:.2f}x"
        )


if __name__ == "__main__":
    production_file = Path("testing/onap-production-report.html")
    test_file = Path("testing/onap-report.html")
    test_json = Path("/tmp/reports/ONAP/report_raw.json")

    if not production_file.exists():
        print(f"ERROR: Production file not found: {production_file}")
        sys.exit(1)

    if not test_file.exists():
        print(f"ERROR: Test file not found: {test_file}")
        sys.exit(1)

    compare_reports(production_file, test_file)

    # Analyze JSON if available
    if test_json.exists():
        analyze_json_data(test_json)
    else:
        print(f"\n⚠️  JSON file not found: {test_json}")
        print("    Skipping JSON analysis")
