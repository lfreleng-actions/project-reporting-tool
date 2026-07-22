<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Testing GitHub Native Project Support

> Quick start guide for testing the GitHub-native project implementation

**Feature:** GitHub-native project support
**Schema Version:** 1.5.0
**Test Project:** Aether (opennetworkinglab)

---

## Prerequisites

### Required Tools

```bash
# Python environment
python --version  # 3.11+
uv --version      # Latest

# GitHub CLI (required for GitHub project cloning)
gh --version      # 2.0+

# Git
git --version     # 2.0+
```

### Install GitHub CLI

**macOS:**

```bash
brew install gh
```

**Ubuntu/Debian:**

```bash
sudo apt install gh
```

**Other platforms:** <https://cli.github.com/>

### Authentication

**Option 1: GitHub CLI Login**

```bash
gh auth login
# Follow interactive prompts
```

**Option 2: Environment Token**

```bash
export GITHUB_TOKEN="ghp_your_token_here"
# OR
export CLASSIC_READ_ONLY_PAT_TOKEN="ghp_your_token_here"
```

**Verify:**

```bash
gh auth status
# Should show: ✓ Logged in to github.com
```

---

## Quick Test

### 1. Test Aether Project

```bash
cd test-lf-releng-project-reporting/testing
./local-testing.sh --project Aether
```

**Expected output:**

```text
[INFO] Testing lf-releng-project-reporting locally
[INFO] Step 1/3: Cloning Repositories
[INFO] Cloning Aether repositories from GitHub org opennetworkinglab...
[INFO] Found 45 repositories in opennetworkinglab
[SUCCESS] Aether repositories cloned: 45 succeeded, 0 failed

[INFO] Step 2/3: Generating Reports
[INFO] Generating Aether report...
[SUCCESS] Aether report generated successfully

[INFO] Step 3/3: Copying Reports
[SUCCESS] Reports copied successfully
```

### 2. Verify Generated Report

```bash
cd testing/reports/Aether

# Check files exist
ls -lh
# Expected:
# - report.html
# - report.md
# - report_raw.json
# - config_resolved.json

# Open HTML report
open report.html  # macOS
# OR
xdg-open report.html  # Linux
```

### 3. Check Report Content

**In the HTML report, verify:**

- [ ] Title shows "Aether" project name
- [ ] Summary section header: "📈 Global Summary"
- [ ] Summary table shows "Total Repositories" (NOT "Total Gerrit Projects")
- [ ] Repositories section header: "📊 Repositories" (NOT "📊 Gerrit Projects")
- [ ] Column header: "Repository" (NOT "Gerrit Project")
- [ ] Repository links point to GitHub: `https://github.com/opennetworkinglab/{repo}`
- [ ] All metrics present: Commits, LOC, Contributors, Days Inactive, etc.

---

## Detailed Testing

### Test 1: Schema Version

```bash
# Check schema version in generated report
jq '.schema_version' testing/reports/Aether/report_raw.json
# Expected: "1.5.0"
```

### Test 2: Project Type Detection

```bash
# Check configuration
jq '.gerrit.enabled' testing/reports/Aether/config_resolved.json
# Expected: false

jq '.extensions.github_api.github_org' testing/reports/Aether/config_resolved.json
# Expected: "opennetworkinglab"
```

### Test 3: Repository Data Structure

```bash
# Check first repository structure
jq '.repositories[0] | keys' testing/reports/Aether/report_raw.json
# Should include: gerrit_project, gerrit_host, gerrit_url, etc.
# (Field names unchanged for backward compatibility)

# Check repository URL format
jq '.repositories[0].gerrit_url' testing/reports/Aether/report_raw.json
# Expected: "https://github.com/opennetworkinglab/{repo_name}"
```

### Test 4: Terminology in Markdown

```bash
# Check terminology in markdown report
grep "Repositories" testing/reports/Aether/report.md
# Should find: "Total Repositories", "Current Repositories", etc.

grep "Gerrit Project" testing/reports/Aether/report.md
# Should find: NOTHING (should use "Repository" instead)
```

### Test 5: Backward Compatibility

```bash
# Test existing Gerrit project still works
cd testing
./local-testing.sh --project ONAP

# Check ONAP report uses Gerrit terminology
grep "Gerrit Projects" testing/reports/ONAP/report.md
# Should find: "Total Gerrit Projects", etc.
```

---

## Test Both Project Types Together

```bash
# Run all projects (Gerrit + GitHub)
cd testing
./local-testing.sh

# Verify both report types generated
ls -d reports/*/
# Expected:
# - reports/Aether/    (GitHub-native)
# - reports/ONAP/      (Gerrit-based)
# - reports/Opendaylight/  (Gerrit-based)
# etc.

# Compare terminology
echo "=== Aether (GitHub) ==="
grep -h "Total.*Repositories\|Total.*Projects" reports/Aether/report.md

echo "=== ONAP (Gerrit) ==="
grep -h "Total.*Repositories\|Total.*Projects" reports/ONAP/report.md
```

---

## Validation Checklist

### Configuration ✅

- [ ] Schema version is 1.5.0 in all configs
- [ ] `gerrit.enabled` auto-set to false for GitHub projects
- [ ] GitHub org derived from `GITHUB_ORG` environment variable
- [ ] Gerrit projects still have `gerrit.enabled = true`

### Templates ✅

- [ ] Run template audit: `python scripts/audit_templates.py`
- [ ] All templates pass validation
- [ ] No undefined variable errors
- [ ] Terminology variables work in all templates

### Data Structure ✅

- [ ] JSON schema unchanged (field names identical)
- [ ] Repository objects have all required fields
- [ ] URLs constructed correctly for both types
- [ ] No breaking changes to data format

### Functionality ✅

- [ ] Aether repositories clone successfully
- [ ] Report generation completes without errors
- [ ] All sections render correctly
- [ ] Statistics calculated properly
- [ ] Links work in HTML report

### Backward Compatibility ✅

- [ ] Existing Gerrit projects (ONAP, ODL) still work
- [ ] Gerrit projects show "Gerrit Project" terminology
- [ ] GitHub projects show "Repository" terminology
- [ ] No regressions in existing functionality

---

## Common Issues & Solutions

### Issue: `gh: command not found`

**Solution:**

```bash
# Install GitHub CLI
brew install gh  # macOS
# OR
sudo apt install gh  # Ubuntu
```

### Issue: `gh auth status` fails

**Solution:**

```bash
# Login to GitHub CLI
gh auth login

# OR set token
export GITHUB_TOKEN="your_token_here"
```

### Issue: No repositories found for Aether

**Solution:**

```bash
# Verify org exists and is accessible
gh repo list opennetworkinglab --limit 5

# Check authentication
gh auth status

# Verify org name in projects.json
jq '.[] | select(.project == "Aether")' testing/projects.json
```

### Issue: Report shows "Gerrit Project" for Aether

**Diagnosis:**

```bash
# Check configuration
jq '.gerrit.enabled' testing/reports/Aether/config_resolved.json

# Check project type detection
jq '.gerrit.host' testing/reports/Aether/config_resolved.json
# Should be empty for GitHub projects
```

**Solution:**

- Ensure `gerrit` field is NOT in Aether's projects.json entry
- Only `github` field should be present

### Issue: Clone fails with rate limit

**Solution:**

```bash
# Use authenticated token
export GITHUB_TOKEN="ghp_your_token_here"

# Check rate limit status
gh api rate_limit
```

---

## Manual Verification Steps

### 1. Visual Inspection

**Open HTML report in browser:**

```bash
open testing/reports/Aether/report.html
```

**Check:**

- [ ] Page title: "Aether - Repository Analysis Report"
- [ ] Table of contents present
- [ ] Summary section readable
- [ ] Repositories table sortable
- [ ] Links clickable and point to GitHub
- [ ] No broken images or CSS
- [ ] Responsive design works

### 2. Data Accuracy

**Compare with GitHub directly:**

```bash
# Count repos in org
gh repo list opennetworkinglab --limit 1000 | wc -l

# Compare with report
jq '.summaries.all_repositories | length' testing/reports/Aether/report_raw.json
```

**Check metrics:**

```bash
# Pick a known repository
gh repo view opennetworkinglab/aether-onramp

# Verify commits, contributors in report match reality
jq '.repositories[] | select(.gerrit_project == "aether-onramp")' \
  testing/reports/Aether/report_raw.json
```

### 3. Cross-Project Comparison

**Compare Aether (GitHub) with ONAP (Gerrit):**

```bash
# Structure should be identical
diff \
  <(jq '.repositories[0] | keys | sort' testing/reports/Aether/report_raw.json) \
  <(jq '.repositories[0] | keys | sort' testing/reports/ONAP/report_raw.json)
# Expected: No differences in keys
```

---

## Performance Testing

### Clone Performance

```bash
# Time the clone operation
time ./local-testing.sh --project Aether

# Expected: ~2-5 minutes for ~45 repos
# Depends on: network speed, repo sizes
```

### Report Generation Performance

```bash
# Check generation time in logs
grep "Generated in" testing/reports/Aether/*.log

# Should be comparable to Gerrit projects
```

---

## Next Steps After Testing

### If All Tests Pass ✅

1. Document any findings
2. Create summary report
3. Prepare for production deployment
4. Update production documentation

### Production Deployment Steps

1. Port changes to `lf-releng-project-reporting` (production repo)
2. Update production `PROJECTS_JSON` variable
3. Add Aether to preview workflow first
4. Monitor preview reports
5. Deploy to production workflow
6. Announce new capability

---

## Support

### Documentation

- [Implementation Plan](docs/GITHUB_NATIVE_IMPLEMENTATION_PLAN.md)
- [Implementation Summary](docs/GITHUB_NATIVE_IMPLEMENTATION_SUMMARY.md)
- [Schema Version 1.5.0](docs/SCHEMA_VERSION_1.5.0.md)

### Debugging

**Enable verbose logging:**

```bash
cd testing
VERBOSE=1 ./local-testing.sh --project Aether
```

**Check logs:**

```bash
ls -lh testing/reports/Aether/*.log
tail -n 100 testing/reports/Aether/*.log
```

**Validate JSON:**

```bash
jq empty testing/reports/Aether/report_raw.json
# No output = valid JSON
```

---

## Success Criteria

All checkboxes must be ✅ before considering implementation complete:

### Core Functionality

- [ ] Aether repositories clone successfully
- [ ] Report generates without errors
- [ ] All sections render correctly
- [ ] Metrics are accurate

### Terminology

- [ ] GitHub projects show "Repositories"
- [ ] Gerrit projects show "Gerrit Projects"
- [ ] URLs point to correct locations
- [ ] No hardcoded "Gerrit" references for GitHub projects

### Compatibility

- [ ] Schema version is 1.5.0
- [ ] Existing projects unchanged
- [ ] JSON structure identical
- [ ] No breaking changes

### Quality

- [ ] Template audit passes
- [ ] No errors in logs
- [ ] Performance acceptable
- [ ] Documentation complete

---

**Last Updated:** 2025-01-XX
**Status:** Ready for Testing
**Schema Version:** 1.5.0
