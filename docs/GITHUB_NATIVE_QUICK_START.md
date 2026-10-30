<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# GitHub Native Projects - Quick Start Guide

> Quick reference for adding and reporting on GitHub-native projects

**Feature:** GitHub-native project support
**Schema Version:** 1.5.0
**Status:** ✅ Available

---

## What Are GitHub Native Projects?

**GitHub-native projects** are projects hosted entirely on GitHub with no Gerrit backend.

**Examples:**

- Aether (opennetworkinglab org)
- Future LF projects starting on GitHub

**Comparison:**

<!-- markdownlint-disable MD060 -->

| Aspect        | Gerrit-Based                       | GitHub-Native           |
| ------------- | ---------------------------------- | ----------------------- |
| Source Code   | Gerrit (primary) + GitHub (mirror) | GitHub only             |
| Code Review   | Gerrit                             | GitHub Pull Requests    |
| Configuration | Has `gerrit` field                 | Has `github` field only |
| Terminology   | "Gerrit Projects"                  | "Repositories"          |
| INFO.yaml     | ✅ Supported                       | ❌ Not applicable       |

<!-- markdownlint-enable MD060 -->

---

## Quick Configuration

### Add to PROJECTS_JSON

**GitHub Variable (for workflows):**

```json
[
  {
    "project": "Aether",
    "slug": "aether",
    "github": "opennetworkinglab"
  }
]
```

**Key Points:**

- ✅ Include `github` field with organization name
- ❌ Omit `gerrit` field (or leave empty)
- ✅ Optional: Include `jenkins` if ci-management exists
- ✅ Use lowercase `slug` for URLs

### Add to Local Testing

**File:** `testing/projects.json`

```json
{
  "project": "Aether",
  "slug": "aether",
  "github": "opennetworkinglab"
}
```

---

## Generate Reports

### Production (GitHub Actions)

```yaml
# In PROJECTS_JSON variable
[
  {
    "project": "Aether",
    "slug": "aether",
    "github": "opennetworkinglab"
  }
]
```

**Workflow automatically:**

1. Sets `GITHUB_ORG=opennetworkinglab`
2. Detects project type (GitHub-native)
3. Generates report with "Repositories" terminology
4. Publishes to GitHub Pages

### Local Testing

```bash
# Install GitHub CLI (if not installed)
brew install gh  # macOS
# OR
sudo apt install gh  # Ubuntu

# Authenticate
gh auth login

# Generate report
cd testing
./local-testing.sh --project Aether
```

**Output:**

```text
testing/reports/Aether/
├── report.html              # Interactive report
├── report.md                # Markdown version
├── report_raw.json          # Complete data
└── config_resolved.json     # Applied config
```

---

## What You Get

### Report Sections

All standard sections included:

- ✅ **Global Summary** - Repository counts, activity status
- ✅ **Repositories** - All repos with metrics
- ✅ **Contributors** - Top contributors by commits
- ✅ **Organizations** - Contributor organization breakdown
- ✅ **Features** - CI/CD, documentation detection
- ✅ **Workflows** - GitHub Actions workflows
- ❌ **INFO.yaml** - Not applicable (Gerrit-specific)

### Terminology

| Section      | Shows                  |
| ------------ | ---------------------- |
| Summary      | "Total Repositories"   |
| Repositories | "Repository" column    |
| Links        | GitHub repository URLs |
| Metrics      | Standard git metrics   |

### Example Output

```markdown
## 📈 Global Summary

| Metric                | Count | Percentage |
| --------------------- | ----- | ---------- |
| Total Repositories    | 45    | 100%       |
| Current Repositories  | 38    | 84.4%      |
| Active Repositories   | 5     | 11.1%      |
| Inactive Repositories | 2     | 4.4%       |

## 📊 Repositories

<!-- markdownlint-disable MD060 -->

| Repository                                                          | Commits | LOC   | Contributors | Days Inactive | Status |
| ------------------------------------------------------------------- | ------- | ----- | ------------ | ------------- | ------ |
| [aether-onramp](https://github.com/opennetworkinglab/aether-onramp) | 1,234   | 45.6K | 12           | 5             | ✅     |

<!-- markdownlint-enable MD060 -->
```

---

## Configuration Reference

### Minimal Configuration

```json
{
  "project": "ProjectName",
  "slug": "project-slug",
  "github": "github-org-name"
}
```

### With Jenkins

```json
{
  "project": "ProjectName",
  "slug": "project-slug",
  "github": "github-org-name",
  "jenkins": "jenkins.example.org"
}
```

### Behind the Scenes

When you configure a GitHub-native project, the tool:

1. **Detects** project type (no `gerrit` field = GitHub-native)
2. **Sets** `gerrit.enabled = false` automatically
3. **Uses** `GITHUB_ORG` environment variable for org name
4. **Applies** "Repositories" terminology in templates
5. **Builds** GitHub URLs: `https://github.com/{org}/{repo}`

---

## Differences from Gerrit Projects

### What's the Same ✅

- Git metrics (commits, LOC, contributors)
- Activity status (current, active, inactive)
- Feature detection (CI/CD, docs, etc.)
- GitHub Actions workflow reporting
- Jenkins job attribution (if configured)
- Report formats (HTML, Markdown, JSON)
- Data structure (same JSON fields)

### What's Different 🔄

- Terminology: "Repositories" vs "Gerrit Projects"
- URLs: GitHub repos vs Gerrit admin pages
- Source: GitHub only vs Gerrit primary
- INFO.yaml: Not available vs available

### What's Not Included ❌

- Gerrit-specific metrics (changes, reviews)
- INFO.yaml project metadata
- Gerrit API data
- Cross-project Gerrit references

---

## Common Use Cases

### 1. New Project Starting on GitHub

```json
{
  "project": "NewProject",
  "slug": "newproject",
  "github": "myorg"
}
```

**Use when:**

- Project starts fresh on GitHub
- No Gerrit infrastructure
- Pure GitHub workflow

### 2. Project Migrated from Gerrit

```json
{
  "project": "MigratedProject",
  "slug": "migrated",
  "github": "myorg",
  "jenkins": "jenkins.example.org"
}
```

**Use when:**

- Moved from Gerrit to GitHub
- Still using Jenkins (via ci-management)
- Want GitHub-style reporting

### 3. Mixed Organization

```json
[
  {
    "project": "LegacyProject",
    "slug": "legacy",
    "gerrit": "gerrit.example.org",
    "jenkins": "jenkins.example.org"
  },
  {
    "project": "ModernProject",
    "slug": "modern",
    "github": "myorg"
  }
]
```

**Use when:**

- Organization has both types
- Gradual migration ongoing
- Need unified reporting

---

## Troubleshooting

### Issue: Report shows "Gerrit Projects" for GitHub project

**Check:**

```bash
jq '.gerrit.enabled' reports/ProjectName/config_resolved.json
```

**Should be:** `false`

**Fix:** Remove `gerrit` field from PROJECTS_JSON

---

### Issue: No repositories found

**Check:**

```bash
gh repo list your-org --limit 5
```

**Fix:**

- Verify org name correct
- Check GitHub authentication
- Ensure token has permissions

---

### Issue: Clone fails

**Check:**

```bash
gh auth status
```

**Fix:**

```bash
gh auth login
# OR
export GITHUB_TOKEN="your_token_here"
```

---

## Best Practices

### Naming

✅ **Do:**

- Use descriptive project names
- Use lowercase slugs
- Match org name exactly

❌ **Don't:**

- Use spaces in slugs
- Guess org names
- Mix case in slugs

### Configuration

✅ **Do:**

- Test locally first
- Verify org accessibility
- Document any special setup

❌ **Don't:**

- Add `gerrit` field for GitHub projects
- Forget authentication
- Skip validation

### Workflow

✅ **Do:**

- Start with preview reports
- Monitor first production run
- Document findings

❌ **Don't:**

- Deploy to production untested
- Ignore errors
- Skip documentation

---

## Examples

### Aether Project

**Configuration:**

```json
{
  "project": "Aether",
  "slug": "aether",
  "github": "opennetworkinglab"
}
```

**Command:**

```bash
./local-testing.sh --project Aether
```

**Result:**

- 45 repositories analyzed
- "Repositories" terminology
- GitHub URLs in report
- Standard git metrics

### Custom Organization

**Configuration:**

```json
{
  "project": "MyProject",
  "slug": "myproject",
  "github": "my-github-org",
  "jenkins": "jenkins.myproject.org"
}
```

**Features:**

- GitHub repository analysis
- Jenkins job attribution
- Custom project name
- Full metrics coverage

---

## Migration Guide

### From Gerrit to GitHub

**Before (Gerrit):**

```json
{
  "project": "MyProject",
  "slug": "myproject",
  "gerrit": "gerrit.example.org",
  "jenkins": "jenkins.example.org",
  "github": "myorg"
}
```

**After (GitHub-native):**

```json
{
  "project": "MyProject",
  "slug": "myproject",
  "github": "myorg",
  "jenkins": "jenkins.example.org"
}
```

**Steps:**

1. Remove `gerrit` field
2. Keep `github` field
3. Optionally keep `jenkins`
4. Update in PROJECTS_JSON
5. Generate new report
6. Verify terminology changed

---

## FAQ

### Can I have both Gerrit and GitHub projects?

**Yes!** The tool supports both in the same run. It auto-detects project type from configuration.

### Will existing Gerrit projects break?

**No!** Full backward compatibility. Gerrit projects work exactly as before.

### Do field names change in the data?

**No!** JSON structure unchanged. Field names identical for compatibility.

### Can I customize the terminology?

**No.** Terminology auto-set based on project type (Gerrit vs GitHub).

### Does INFO.yaml work for GitHub projects?

**No.** INFO.yaml is Gerrit-specific and not available for GitHub projects.

### Can I mix Gerrit and GitHub in one project?

**Sort of.** If `gerrit` field exists, project treated as Gerrit-based (with GitHub as optional mirror).

---

## Related Documentation

- [Schema Version 1.5.0](SCHEMA_VERSION_1.5.0.md) - Version details
- [Testing Guide](TESTING_GITHUB_NATIVE.md) - Test procedures
- [Configuration Guide](CONFIGURATION.md) - Full config reference

---

## Support

### Get Help

1. Check [Troubleshooting](#troubleshooting) section above
2. Review [Testing Guide](TESTING_GITHUB_NATIVE.md)
3. Verify GitHub authentication
4. Check logs in `reports/{project}/`
5. Open issue with details

### Report Issues

Include:

- Project configuration (sanitized)
- Error messages
- Log snippets
- Steps to reproduce

---

**Last Updated:** 2025-01-XX
**Schema Version:** 1.5.0
**Status:** ✅ Production Ready
