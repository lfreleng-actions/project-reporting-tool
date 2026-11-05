<!--
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# GitHub Pages Reporting System Setup Guide

This guide covers the complete setup and migration to the new GitHub Pages-based reporting system.

---

## 🎯 Overview

The reporting system publishes reports directly to GitHub Pages on this
repository. The `reporting-production.yaml` workflow deploys them as a
Pages artifact, authenticating with the built-in `GITHUB_TOKEN`, and
each project's report appears at `/<project-slug>/report.html`
relative to the Pages site root.

---

## 📋 Prerequisites

### Required Secrets

1. **CLASSIC_READ_ONLY_PAT_TOKEN** (Required)
   - Used for GitHub API queries (workflow status, repository info)
   - Permissions needed: `repo` (read-only), `workflow` (read)
   - Create at: <https://github.com/settings/tokens>

2. **LF_GERRIT_INFO_MASTER_SSH_KEY** (Optional)
   - SSH key for cloning `info-master` repository
   - Falls back to HTTPS if not provided
   - Format: Private SSH key

### Required Variables

1. **PROJECTS_JSON**
   - Array of project configurations
   - Format:

     ```json
     [
       {
         "project": "Project Name",
         "slug": "project-name",
         "gerrit": "gerrit.example.org",
         "jenkins": "jenkins.example.org",
         "github": "github-org-name"
       }
     ]
     ```

     **Required fields:**
     - `project`: Full project name
     - `slug`: Short identifier for artifact naming (lowercase, no spaces)
     - `gerrit`: Gerrit server hostname

---

## 🚀 Initial Setup

### Step 1: Enable GitHub Pages

1. Go to **Settings** → **Pages**
2. Under **Build and deployment** → **Source**, select **GitHub Actions**

The production workflow builds the whole site from the run's report
artifacts and deploys it with `actions/deploy-pages`. No branch holds
the site, so there is no `gh-pages` branch to create.

### Step 2: Allow Deployments to the `github-pages` Environment

GitHub creates the `github-pages` environment when you select
**GitHub Actions** as the source. By default it accepts deployments
only from the default branch. A manual run from another branch fails
at the **Deploy GitHub Pages** job until you add that branch under
**Settings** → **Environments** → **github-pages**.

### Step 3: Configure Repository Permissions

Each job in the workflow declares the permissions it needs, so the
default **Read repository contents and packages permissions** setting
under **Settings** → **Actions** → **General** → **Workflow
permissions** is sufficient. No job needs write access to the
repository contents.

### Step 4: Set Up Secrets and Variables

#### Add Secrets

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**

**CLASSIC_READ_ONLY_PAT_TOKEN:**

```text
Name: CLASSIC_READ_ONLY_PAT_TOKEN
Secret: ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```text

**LF_GERRIT_INFO_MASTER_SSH_KEY** (optional):

```text
Name: LF_GERRIT_INFO_MASTER_SSH_KEY
Secret: -----BEGIN OPENSSH PRIVATE KEY-----
        [your key content]
        -----END OPENSSH PRIVATE KEY-----
```text

#### Add Variables

1. Click **Variables** tab
2. Click **New repository variable**

**PROJECTS_JSON:**

```text
Name: PROJECTS_JSON
Value: [
  {
    "project": "ONAP",
    "gerrit": "gerrit.onap.org",
    "jenkins": "jenkins.onap.org",
    "github": "onap"
  },
  {
    "project": "O-RAN-SC",
    "gerrit": "gerrit.o-ran-sc.org",
    "jenkins": "jenkins.o-ran-sc.org",
    "github": "o-ran-sc"
  }
]
```text

**Slack Failure Notification Variables (Optional):**

To enable Slack notifications when production report generation
fails:

```text
Name: SLACK_CHANNEL_ID
Value: [Channel ID for your Slack channel, e.g. C0123456789]
```

**Slack Failure Notification Secret:**

```text
Name: SLACK_BOT_TOKEN
Secret: xoxb-[Your Slack bot token]
```

**Slack Notification Configuration:**

The production reports workflow sends Slack notifications to a
configured channel when any pipeline stage fails. Only failures
trigger a notification — successful runs stay silent.

1. Create a Slack app with `chat:write` and
   `chat:write.customize` scopes
2. Invite the bot to the target channel
3. Add `SLACK_BOT_TOKEN` secret with the bot's `xoxb-` token
4. Add `SLACK_CHANNEL_ID` variable with the target channel ID

The Slack message includes:

- Which pipeline stages failed (Secrets Validation, Matrix
  Build, Project Analysis, Pages Publishing, Pages Deployment)
- Which specific projects failed in the analysis matrix
- Status of each job (validate/analyze/publish/deploy)
- Direct link to the workflow run

---

## 🔄 Migration from Old System

### Step 1: Update Workflows

The old `reporting.yaml` workflow has been replaced with
**`reporting-production.yaml`**, which produces production reports on a
schedule.

The old workflow file has been renamed to `reporting.yaml.deprecated` and is no longer active.

### Step 2: Verify New Workflows

1. Navigate to **Actions** tab
2. You should see the new workflow: 📊 Production Reports

### Step 3: Switch from the `gh-pages` Branch

Repositories that published from a `gh-pages` branch before the
workflow moved to `actions/deploy-pages` need two one-off steps:

1. Right after merging the change, go to **Settings** → **Pages** →
   **Build and deployment** → **Source** and select **GitHub
   Actions**. Until then the **Deploy GitHub Pages** job fails and the
   previous site stays live.
2. Once the first deployment from GitHub Actions is live, delete the
   `gh-pages` branch. Nothing reads it any more.

---

## 📊 Workflow Details

### Production Reports Workflow

**File:** `.github/workflows/reporting-production.yaml`

**Triggers:**

- 🕐 **Schedule:** Monday at 7:00 AM UTC
- 🔧 **Manual:** workflow_dispatch

**What it does:**

1. Validates configuration and secrets
2. Clones all Gerrit repositories (parallel)
3. Clones `info-master` for committer data
4. Generates reports for each project
5. Uploads report artifacts with 90-day retention
6. Builds the site from this run's report artifacts, reusing the
   newest unexpired `reports-<slug>` artifact from an earlier run for
   any active project this run produced no report for
7. Deploys the site with `actions/deploy-pages`

The publish job reuses an earlier artifact only when it holds a
`report.html` and comes from a scheduled or dispatched run of
`reporting-production.yaml` on the default branch of this repository,
so a pull request, a fork or another workflow cannot place pages on
the production site. A project with no such artifact left within the
90-day retention drops off the site: the publish job logs a warning
naming it, and the workflow summary lists it as unavailable instead
of linking to it. When a GitHub API lookup for an earlier artifact
fails and leaves a project without a report, the publish job fails
instead, so the deploy job does not run and the previous deployment
stays live; re-run the workflow once the API recovers.

**Output Location:**

```text
https://<owner>.github.io/<repo>/production/<project-slug>/report.html
```text

---

## 🗂️ GitHub Pages Structure

```text
https://<owner>.github.io/<repo>/
├── index.html                          # Landing page
└── production/                         # Production reports
│   ├── index.html                      # Production report list
│   ├── onap/
│   │   ├── report.html
│   │   ├── report_raw.json
│   │   ├── report.md
│   │   └── metadata.json
│   ├── o-ran-sc/
│   │   ├── report.html
│   │   ├── report_raw.json
│   │   └── metadata.json
│   └── ...
```text

---

## 📦 Artifact Retention

### Production Workflow

| Artifact Type    | Retention | Purpose                        |
| ---------------- | --------- | ------------------------------ |
| Raw data (JSON)  | 90 days   | Meta-reporting, trend analysis |
| Complete reports | 90 days   | Full report package            |
| Clone manifests  | 90 days   | Repository tracking            |
| Clone logs       | 90 days   | Debugging                      |

---

## 🔧 Maintenance

### Manual Trigger

To manually trigger a production report:

1. Go to **Actions** tab
2. Select **📊 Production Reports**
3. Click **Run workflow**
4. Choose branch (usually `main`)
5. Click **Run workflow**

### Viewing Reports

**Production Reports:**

```text
https://<owner>.github.io/<repo>/production/
```text

### Downloading Artifacts for Meta-Reporting

Use the provided script to download historical artifact data:

```bash
# Set your GitHub token
export GITHUB_TOKEN=ghp_...

# Download artifacts from last 90 days
.github/scripts/download-artifacts.sh \
  reporting-production.yaml \
  ./meta-report-data \
  90
```text

This downloads all raw JSON data files which can be used to generate:

- Migration progress tracking
- Jenkins job → GitHub Actions transition metrics
- Repository activity trends
- Historical comparisons

---

## 🐛 Troubleshooting

### Reports Not Appearing

**Check GitHub Pages Status:**

1. Go to **Settings** → **Pages**
2. Verify **Source** is set to **GitHub Actions**
3. Check for deployment status

**Check Workflow Status:**

1. Go to **Actions** tab
2. Check if workflows completed successfully
3. Review logs for errors

**Check the Deployed Site:**

1. Open the workflow run and download the `github-pages` artifact
   from the **Build GitHub Pages site** job
2. Check the publish job log for warnings about projects dropped from
   the site

### Missing Secrets Error

```text
Error: CLASSIC_READ_ONLY_PAT_TOKEN secret is not set
```text

**Solution:**

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Verify secret exists and is spelled correctly
3. Regenerate token if expired

### Clone Failures

If repository cloning fails:

1. **Check Gerrit server accessibility**
2. **Verify SSH key** (if using SSH)
3. **Check workflow timeout settings**
4. Review clone logs in artifacts

---

## 📈 Monitoring

### Key Metrics to Track

1. **Workflow Success Rate**
   - Monitor in Actions tab
   - Set up notifications for failures

2. **Artifact Storage Usage**
   - Check Settings → Actions → Storage
   - Adjust retention if needed

3. **Report Generation Time**
   - Review workflow run durations
   - Optimize if exceeding 60 minutes

4. **GitHub Pages Deployment**
   - Monitor Pages deployments
   - Check for build errors

---

## 🔐 Security Considerations

### Token Permissions

**CLASSIC_READ_ONLY_PAT_TOKEN:**

- ✅ Use fine-grained token when possible
- ✅ Limit to specific repositories
- ✅ Set expiration date
- ✅ Use read-only permissions only

**Built-in GITHUB_TOKEN:**

- ✅ Automatically scoped to repository
- ✅ Expires after workflow run
- ✅ No manual token management needed

### SSH Keys

**LF_GERRIT_INFO_MASTER_SSH_KEY:**

- ✅ Use dedicated deployment key
- ✅ Limit to read-only access
- ✅ Rotate periodically
- ✅ Monitor usage

---

## 🎯 Best Practices

### Production Reports

1. **Schedule appropriately**
   - Monday 7am UTC catches weekend activity
   - Avoid peak hours

2. **Monitor failures**
   - Set up notifications
   - Review logs regularly

3. **Archive old reports**
   - Download artifacts before retention expires
   - Store externally for long-term analysis

### Artifacts

1. **Download raw data regularly**
   - Use download script
   - Build historical dataset

2. **Monitor storage usage**
   - Adjust retention if needed
   - Archive important runs externally

---

## 📚 Additional Resources

- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [GitHub Actions Permissions](https://docs.github.com/en/actions/security-guides/automatic-token-authentication)
- [Workflow Artifacts](https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts)

---

## 🆘 Getting Help

If you encounter issues:

1. Check this documentation
2. Review workflow logs in Actions tab
3. Check GitHub Pages deployment status
4. Verify all secrets and variables are set
5. Open an issue with:
   - Workflow run link
   - Error messages
   - Steps to reproduce

---

**Last Updated:** 2025-01-XX

**Migration Status:** ✅ Ready for production use
