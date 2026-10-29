<!--
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Reporting Workflow Setup

This document describes the setup and usage of the GitHub CI/CD reporting
workflow for analyzing Linux Foundation projects hosted on Gerrit servers.

## Overview

The reporting workflow (`reporting.yaml`) provides:

1. **Run automatically** every Monday at 7:00 AM UTC
2. **Support manual execution** via GitHub's workflow dispatch
3. **Process projects** in parallel using matrix jobs
4. **Clone entire Gerrit servers** using the `gerrit-clone-action`
5. **Perform analytics** on the downloaded repositories
6. **Generate comprehensive reports** with results and summaries

## Configuration

### GitHub Secrets: Required Tokens

The workflow requires **TWO separate GitHub Personal Access Tokens** for
different purposes:

#### 1. GitHub API Token (Classic PAT)

**Purpose**: Query workflow status and GitHub API data across all
organizations.

**Environment Variable Names**:

- **Default**: `GITHUB_TOKEN` (recommended for most users)
- **CI/Legacy**: `CLASSIC_READ_ONLY_PAT_TOKEN` (used in existing CI workflows)
- **Custom**: Can be configured via `--github-token-env` CLI option

**⚠️ IMPORTANT**: You **MUST use a Classic Personal Access Token**, not a
fine-grained token, because fine-grained tokens work with a single
organization and cannot span the Linux Foundation organizations
needed for cross-org reporting.

**Required Scopes**:

- `repo` (full repository access, or `public_repo` for public repositories only)
- `actions:read` (read GitHub Actions workflow runs and status)

**Quick Setup**:

1. Go to <https://github.com/settings/tokens>
2. Click "Generate new token" → "Generate new token (classic)"
3. Select scopes: `repo` and `actions:read`
4. Generate and copy the token
5. Go to your repository's **Settings** → **Secrets and variables** → **Actions**
6. Click "New repository secret"
7. Name: `GITHUB_TOKEN` (or `CLASSIC_READ_ONLY_PAT_TOKEN` for CI environments)
8. Value: Paste your token
9. Click "Add secret"

**Note**: The tool defaults to reading from `GITHUB_TOKEN`. If you need to use
a different environment variable name (e.g., for CI/CD compatibility), use the
`--github-token-env` option:

```bash
# Use default GITHUB_TOKEN
lf-releng-project-reporting generate --project my-project --repos-path ./repos

# Use custom environment variable for CI
lf-releng-project-reporting generate --project my-project --repos-path ./repos \
  --github-token-env CLASSIC_READ_ONLY_PAT_TOKEN
```

#### 2. GitHub Pages Setup

**Purpose**: Publish reports directly to GitHub Pages on this repository.

**No additional token needed** - Uses built-in `GITHUB_TOKEN` with appropriate permissions.

**Setup Steps**:

1. Go to **Settings** → **Pages**
2. Under **Source**, select:
   - **Deploy from a branch**
   - Branch: `gh-pages`
   - Folder: `/ (root)`
3. Click **Save**

4. Create the `gh-pages` branch (if it doesn't exist):

   ```bash
   git checkout --orphan gh-pages
   git rm -rf .
   mkdir -p production pr-preview
   echo "Reports coming soon" > index.html
   git add .
   git commit -m "chore: initialize gh-pages branch"
   git push origin gh-pages
   git checkout main
   ```

5. Configure repository permissions:
   - Go to **Settings** → **Actions** → **General**
   - Under **Workflow permissions**, select **Read and write permissions**
   - Enable **Allow GitHub Actions to create and approve pull requests**
   - Click **Save**

For detailed setup instructions, see:
**[GitHub Pages Setup Guide](docs/GITHUB_PAGES_SETUP.md)**

### GitHub Variable: PROJECTS_JSON

The workflow requires a GitHub repository variable called `PROJECTS_JSON` that
contains a **base64-encoded** JSON array of project configurations.

> **⚠️ IMPORTANT:** The JSON must be base64-encoded before storing as a
> variable/secret. This prevents console log redaction issues caused by raw
> JSON content appearing in workflow logs.

#### JSON Structure (before encoding)

```json
[
  {
    "project": "O-RAN-SC",
    "slug": "oran",
    "gerrit": "gerrit.o-ran-sc.org",
    "jenkins": "jenkins.o-ran-sc.org",
    "github": "o-ran-sc"
  },
  {
    "project": "ONAP",
    "slug": "onap",
    "gerrit": "gerrit.onap.org",
    "jenkins": "jenkins.onap.org",
    "github": "onap"
  }
]
```

#### Encoding the JSON

To encode your `projects.json` file:

```bash
# Encode the JSON file to base64
cat projects.json | base64

# Or on macOS (to avoid line wrapping):
cat projects.json | base64 -b 0

# Store the output as your PROJECTS_JSON variable/secret value
```

To decode and verify:

```bash
# Decode and pretty-print to verify
echo "YOUR_BASE64_STRING" | base64 -d | jq .
```

**Required Fields:**

- `project`: Full project name (can contain spaces and capitals)
- `slug`: Short, lowercase identifier used for artifact naming (no spaces)
- `gerrit`: Gerrit server hostname

**Optional Fields:**

- `jenkins`: Jenkins server hostname
- `github`: GitHub organization name
- `jjb_attribution`: JJB repository configuration (for Opendaylight)

#### Setting up the Variable

1. Create your `projects.json` file with the JSON structure above
2. Encode it: `cat projects.json | base64`
3. Go to your repository's **Settings** → **Secrets and variables** →
   **Actions**
4. Click **Variables** tab (for previews) or **Secrets** tab (for production)
5. Click **New repository variable** or **New repository secret**
6. Name: `PROJECTS_JSON`
7. Value: Paste the **base64-encoded** string (not the raw JSON)

> **Note:** The production workflow uses `secrets.PROJECTS_JSON` while the
> preview workflow uses `vars.PROJECTS_JSON`. Both must be base64-encoded.

## Workflow Structure

### Production Workflow (`reporting-production.yaml`)

Scheduled to run every Monday at 7:00 AM UTC, or can be triggered manually.

**Jobs:**

1. **verify**: Validates configuration, secrets, and `PROJECTS_JSON`
2. **analyze**: Clones repositories, generates reports (parallel processing)
3. **publish**: Publishes reports to GitHub Pages at `/production/`
4. **summary**: Generates workflow summary and statistics

### Preview Report Workflow (`reporting-pr-preview.yaml`)

Runs automatically on pull requests that modify reporting code.

**Jobs:**

1. **verify**: Validates configuration (limited to 2 projects)
2. **analyze**: Generates preview reports for first 2 projects
3. **publish-preview**: Publishes to GitHub Pages at `/pr-preview/<pr-number>/`
4. **summary**: Comments on PR with preview links

### Security Features

- **Hardened runners** using `step-security/harden-runner`
- **Minimal permissions** with explicit permission grants
- **Input validation** to prevent configuration errors

## Report Generation

The workflow uses the `lf-releng-project-reporting` CLI to generate comprehensive repository analysis reports:

```bash
uv run lf-releng-project-reporting generate \
  --project "$project" \
  --repos-path "./gerrit-server-clone" \
  --config-dir "./configuration" \
  --output-dir "./reports" \
  --verbose
```

### What Gets Analyzed

The reporting tool automatically analyzes:

- **Git Activity**: Commit history, lines of code, contributor metrics
- **CI/CD Status**: Jenkins builds, GitHub Actions workflows
- **Feature Detection**: Dependabot, pre-commit hooks, documentation
- **Contributors**: Author and organization analysis
- **Repository Health**: Activity status, aging, maintenance indicators

### Analysis Output

The tool generates multiple report formats:

- **JSON** (`report_raw.json`): Complete dataset for further processing
- **Markdown** (`report.md`): Human-readable text report
- **HTML** (`report.html`): Interactive report with sortable tables
- **ZIP Bundle**: Complete package with all formats

### Customization

To customize the analysis:

1. **Configuration**: Edit files in `configuration/` directory
   - `template.config`: Default settings for all projects
   - `<project>.config`: Project-specific overrides

2. **Time Windows**: Adjust analysis periods in project config:

   ```yaml
   time_windows:
     last_30_days: 30
     last_365_days: 365
   ```

3. **Features**: Enable/disable feature detection in config:

   ```yaml
   features:
     enabled:
       - dependabot
       - pre-commit
       - readthedocs
   ```

For detailed configuration options, see Configuration Guide.

## Artifacts

The workflow generates the following artifacts:

- **Clone manifests**: JSON files with repository clone results
- **Analysis outputs**: Per-project analysis results in JSON format
- **GitHub Step Summaries**: Rich markdown summaries including:
  - Repository structure analysis with disk usage
  - Clone statistics and largest repositories
  - Detailed analysis results from the Python script

Artifacts have a 30-day retention period and are available for download from
the workflow run page.

## Manual Execution

To run the workflow manually:

1. Go to **Actions** tab in your repository
2. Select **📊 Project Reports** workflow
3. Click **Run workflow**
4. Click **Run workflow** button (uses the current branch)

## Monitoring

The workflow includes comprehensive logging and error handling:

- **Input validation**: Ensures `PROJECTS_JSON` is properly formatted
- **Clone monitoring**: Tracks success/failure rates for repository cloning
- **Structure analysis**: Validates cloned data and provides disk usage metrics
- **Error reporting**: Clear error messages and status indicators
- **Timeout protection**: Jobs have reasonable timeout limits

## Customization

## Adding New Projects

1. Add the new project to your `projects.json` file
2. Re-encode the file: `cat projects.json | base64`
3. Update the `PROJECTS_JSON` variable/secret with the new base64-encoded value
4. The workflow will automatically include the new project in the next run
5. Verify the project appears in the workflow summary
6. Check the GitHub Pages site for the new project report

## Migration from Legacy System

If you're migrating from the old system that used a separate artifacts
repository:

**Key changes:**

- No longer requires `GERRIT_REPORTS_PAT_TOKEN`
- Reports published to GitHub Pages on this repository
- Separate production and Preview report workflows
- Enhanced artifact retention for meta-reporting
- See [GitHub Pages Setup Guide](docs/GITHUB_PAGES_SETUP.md) for migration steps

### Modifying Clone Behavior

Edit the `gerrit-clone-action` parameters in the workflow:

- `threads`: Number of concurrent clone operations
- `clone-timeout`: Timeout per repository clone
- `skip-archived`: Whether to skip archived repositories
- `depth`: Create shallow clones with specified depth

### Changing the Schedule

Change the `cron` expression in the workflow file:

```yaml
schedule:
  # Run every Monday at 7:00 AM UTC
  - cron: '0 7 * * 1'
```text
## Troubleshooting

### Common Issues

1. **Missing PROJECTS_JSON**: Ensure the repository variable/secret exists properly
2. **Invalid base64**: Ensure the value is properly base64-encoded
   - Verify with: `echo "YOUR_VALUE" | base64 -d | jq .`
3. **Invalid JSON**: Check JSON syntax using online tools after decoding
4. **Gerrit connectivity**: Check that Gerrit servers are accessible
5. **Permission errors**: Verify repository permissions and secrets
6. **Grey workflow status in reports**: Check your GitHub token environment variable
   (`GITHUB_TOKEN` by default, or `CLASSIC_READ_ONLY_PAT_TOKEN` for CI) exists
   and is a Classic PAT with required scopes: `repo` and `actions:read`
7. **Report publishing failures**: Check `GERRIT_REPORTS_PAT_TOKEN` exists and has
   Contents: Read and write permissions for `lfreleng-actions/project-reporting-artifacts`

### Debugging

1. Check the workflow logs in the Actions tab
2. Review the GitHub Step Summary for detailed information
3. Download and examine the generated artifacts
4. Test the reporting tool locally:
   ```bash
   # Install dependencies from the checkout
   uv sync

   # Run a test report
   uv run lf-releng-project-reporting generate \
     --project test-project \
     --repos-path ./test-repos \
     --dry-run
   ```

5. For GitHub API issues, see GitHub Token Requirements
6. For configuration issues, see Configuration Guide
7. For general troubleshooting, see [Troubleshooting Guide](docs/TROUBLESHOOTING.md)

## Further Documentation

For more detailed information:

- **Quick Start Guide** - Get started in 5 minutes
- **CLI Guide** - Complete CLI reference
- **Configuration Guide** - Configuration options
- **[CI/CD Integration](docs/CI_CD_INTEGRATION.md)** - GitHub Actions setup
- **Performance Guide** - Optimization tips
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Documentation Index](docs/INDEX.md)** - Complete documentation hub

## Future Enhancements

Planned improvements for the reporting workflow include:

- **Historical tracking** and trend analysis across report runs
- **Custom notification systems** for significant changes
- **Enhanced dashboard** with interactive visualizations
- **Integration with external tools** and databases
- **Automated remediation** suggestions for inactive repositories
