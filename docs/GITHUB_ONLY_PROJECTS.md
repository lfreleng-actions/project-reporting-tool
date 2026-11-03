<!--
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# GitHub-Only Projects Support

## Overview

The lf-releng-project-reporting now supports GitHub-only projects (projects without a Gerrit server) by leveraging the `gerrit-clone-action` v0.1.13, which includes multi-threaded GitHub repository cloning capabilities.

## What Changed

### 1. Workflow Updates (`reporting-production.yaml`)

#### Project Validation

- **Before**: Required all projects to have `gerrit` field
- **After**: Projects must have either `gerrit` OR `github` field (or both)

#### Clone Steps

- **Added**: Conditional clone step for GitHub-only projects
- **Modified**: Existing Gerrit clone step now only runs when `matrix.gerrit != ''`
- **GitHub Clone**: Uses `gerrit-clone-action` with GitHub-specific options:
  - `source-type: github`
  - `host: github.com/<org>`
  - `github-token: ${{ secrets.CLASSIC_READ_ONLY_PAT_TOKEN }}`
  - `threads: 8` (faster than Gerrit's default 4)
  - No Gerrit-specific options like `move-conflicting`

#### Report Generation

- **Dynamic Path**: Automatically selects correct repos path:
  - Gerrit projects: `./${{ matrix.gerrit }}`
  - GitHub-only projects: `./${{ matrix.github }}`

#### Error Handling

- **Enhanced**: Separate error messages for Gerrit vs GitHub clone failures
- **Metadata**: Failure reports include appropriate source field

#### Artifacts

- **Path Resolution**: Clone manifests and logs use correct path based on project type

### 2. Local Testing Script (`testing/local-testing.sh`)

#### `clone_github_project()` Function Rewrite

- **Before**: Single-threaded cloning using `git clone` in a loop (~10 minutes for large orgs)
- **After**: Multi-threaded cloning using `gerrit-clone clone` CLI (~2-3 minutes)

**Old Approach:**

```bash
# Sequential cloning (slow)
while IFS= read -r repo_name; do
    git clone "https://github.com/${github_org}/${repo_name}.git" "${clone_dir}/${repo_name}"
done
```

**New Approach:**

```bash
# Multi-threaded cloning (fast)
gerrit-clone clone \
    --host "github.com/${github_org}" \
    --source-type github \
    --threads 8 \
    --https
```

### 3. Version Updates

- **gerrit-clone-action**: Updated from `v0.1.12` to `v0.1.13` in both:
  - `reporting-production.yaml`
  - `reporting-previews.yaml`

## Project Configuration

### GitHub-Only Project Example (Aether)

```json
{
  "project": "Aether",
  "slug": "aether",
  "github": "opennetworkinglab",
  "jenkins": "jenkins.aetherproject.org",
  "jenkins_user": "username",
  "jenkins_token": "api_token_here"
}
```

**Key Points:**

- No `gerrit` field required
- `github` field specifies the GitHub organization
- Jenkins authentication supported via `jenkins_user` and `jenkins_token`

### Hybrid Project Example (OpenDaylight)

```json
{
  "project": "Opendaylight",
  "slug": "odl",
  "gerrit": "git.opendaylight.org",
  "github": "opendaylight",
  "jenkins": "jenkins.opendaylight.org"
}
```

**Key Points:**

- Has both `gerrit` and `github` fields
- Gerrit takes priority for cloning
- GitHub org used for additional API queries

## Technical Details

### GitHub Clone Options

The following `gerrit-clone clone` options are used for GitHub projects:

| Option             | Value              | Purpose                                          |
| ------------------ | ------------------ | ------------------------------------------------ |
| `--host`           | `github.com/<org>` | Auto-detects as GitHub source                    |
| `--source-type`    | `github`           | Explicit source type (optional, auto-detected)   |
| `--github-token`   | Token from secrets | Authentication for private repos and rate limits |
| `--output-path`    | `.`                | Clone to current directory                       |
| `--skip-archived`  | `true`             | Skip archived repositories                       |
| `--threads`        | `8`                | Parallel clone threads (vs 4 for Gerrit)         |
| `--clone-timeout`  | `600`              | 10 minute timeout per repo                       |
| `--retry-attempts` | `5`                | Retry failed clones                              |
| `--https`          | `true`             | Use HTTPS instead of SSH                         |

### Options NOT Used for GitHub

The following Gerrit-specific options are NOT applicable to GitHub projects:

- `--move-conflicting`: GitHub has flat structure, no nested repos
- `--allow-nested-git`: Same reason
- `--nested-protection`: Same reason
- `--port`: GitHub uses standard ports
- `--ssh-user`: Uses HTTPS, not SSH
- `--discovery-method`: Always uses `github_api`

### Directory Structure

#### Gerrit Projects

```text
./gerrit.example.org/
├── parent-project/
│   └── child-project/  # Nested structure possible
├── another-project/
└── clone-manifest.json
```

#### GitHub-Only Projects

```text
./github-org/
├── repo1/  # Flat structure
├── repo2/
├── repo3/
└── clone-manifest.json
```

## Performance Improvements

### Aether Project Clone Time

- **Old Method** (single-threaded): ~10 minutes
- **New Method** (8 threads): ~2-3 minutes
- **Improvement**: ~70% faster

### Parallelization Benefits

- Multiple repositories cloned simultaneously
- Automatic retry and error handling
- Progress tracking and logging
- Clone manifest generation

## Authentication

### GitHub Token Requirements

GitHub cloning requires a Personal Access Token (PAT) with:

- **Minimum Scope**: `public_repo` (for public repositories)
- **Recommended Scope**: `repo` (for private repositories)
- **Environment Variable**: `CLASSIC_READ_ONLY_PAT_TOKEN` or `GITHUB_TOKEN`

### Jenkins Authentication

Projects can specify Jenkins credentials directly in `projects.json`:

```json
{
  "jenkins_user": "username",
  "jenkins_token": "api_token"
}
```

These are exported as `JENKINS_USER` and `JENKINS_API_TOKEN` environment variables.

## Workflow Execution

### GitHub-Only Project Flow

1. **Verify Job**: Validates project configuration, ensures `github` field exists
2. **Analyze Job**:
   - Skips Gerrit clone step (conditional: `if: matrix.gerrit != ''`)
   - Executes GitHub clone step (conditional: `if: matrix.gerrit == '' && matrix.github != ''`)
   - Clones repositories to `./<github-org>/`
   - Generates reports using GitHub org path
3. **Publish Job**: Publishes reports to GitHub Pages
4. **Summary Job**: Sends notifications

### Clone Status Checking

```bash
# Determine which clone step ran and check its outcome
if [ -n "${{ matrix.gerrit }}" ]; then
  # Gerrit project
  if [ "${{ steps.clone-gerrit.outcome }}" != "success" ]; then
    echo "CLONE_FAILED=true" >> "$GITHUB_ENV"
  fi
elif [ -n "${{ matrix.github }}" ]; then
  # GitHub-only project
  if [ "${{ steps.clone-github.outcome }}" != "success" ]; then
    echo "CLONE_FAILED=true" >> "$GITHUB_ENV"
  fi
fi
```

## Troubleshooting

### Common Issues

#### 1. GitHub Rate Limiting

**Symptom**: Clone fails with "API rate limit exceeded"
**Solution**: Ensure `CLASSIC_READ_ONLY_PAT_TOKEN` is set and valid

#### 2. Authentication Required

**Symptom**: "GitHub organization unavailable or inaccessible"
**Solution**: Check token has access to the organization

#### 3. Wrong Directory Path

**Symptom**: Reports fail to generate
**Solution**: Verify project has either `gerrit` or `github` field set

### Debug Commands

Local testing with verbose output:

```bash
cd testing
./local-testing.sh --project Aether -vv
```

Check clone manifest:

```bash
cat /tmp/opennetworkinglab/clone-manifest.json | jq .
```

Verify gerrit-clone version:

```bash
gerrit-clone --version
```

## Migration Guide

### Adding a GitHub-Only Project

1. Add project to `PROJECTS_JSON` secret:

   ```json
   {
     "project": "ProjectName",
     "slug": "shortname",
     "github": "github-org-name",
     "jenkins": "jenkins.example.org"  // optional
   }
   ```

2. Ensure `CLASSIC_READ_ONLY_PAT_TOKEN` secret has access to the organization

3. For Jenkins authentication, add credentials:

   ```json
   {
     "jenkins_user": "username",
     "jenkins_token": "token"
   }
   ```

4. Run workflow - it will automatically detect GitHub-only configuration

### Converting Gerrit Project to Hybrid

Simply add `github` field to existing configuration:

```json
{
  "project": "ExistingProject",
  "slug": "existing",
  "gerrit": "gerrit.example.org",
  "github": "github-org",  // ADD THIS
  "jenkins": "jenkins.example.org"
}
```

The Gerrit clone will still take priority, but GitHub API queries will use the org name.

## Report Titles

Reports automatically display the correct title based on project type:

### GitHub-Only Projects

```text
📊 GitHub Project Analysis Report: Aether
```

### Gerrit Projects

```text
📊 Gerrit Project Analysis Report: ONAP
```

### Implementation

The templates dynamically detect the project type from the configuration:

```jinja2
{% if project.project_type == 'github' %}GitHub{% else %}Gerrit{% endif %} Project Analysis Report
```

This applies to both HTML and Markdown reports:

- **HTML**: Page title (`<title>` tag) and main heading (`<h1>`)
- **Markdown**: Main heading (`#`)

The `project_type` is automatically detected in `src/lf_releng_project_reporting/rendering/context/`:

- If `gerrit.host` is configured → `"gerrit"`
- Otherwise → `"github"`

## References

- [gerrit-clone-action v0.1.13](https://github.com/lfit/releng-lftools/tree/main/gerrit-clone-action)
- [gerrit-clone CLI documentation](https://github.com/lfit/releng-lftools)
- [GitHub Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
