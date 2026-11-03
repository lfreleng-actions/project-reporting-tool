<!--
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Quick Reference Guide - GitHub Pages Reporting System

Fast reference for common tasks and operations.

---

## 🚀 Common Tasks

### View Production Reports

```text
https://<owner>.github.io/<repo>/production/
```text

### Manually Trigger Production Report

1. Go to **Actions** → **📊 Production Reports**
2. Click **Run workflow**
3. Select branch → **Run workflow**

---

## 🔑 Required Secrets

<!-- markdownlint-disable MD060 -->

| Secret                          | Required    | Purpose                   |
| ------------------------------- | ----------- | ------------------------- |
| `CLASSIC_READ_ONLY_PAT_TOKEN`   | ✅ Yes      | GitHub API access         |
| `LF_GERRIT_INFO_MASTER_SSH_KEY` | ⚠️ Optional | SSH clone for info-master |

<!-- markdownlint-enable MD060 -->

---

## 📋 Required Variables

| Variable        | Format     | Example   |
| --------------- | ---------- | --------- |
| `PROJECTS_JSON` | JSON array | See below |

**PROJECTS_JSON Format:**

```json
[
  {
    "project": "Project Name",
    "slug": "project-name",
    "gerrit": "gerrit.example.org",
    "jenkins": "jenkins.example.org",
    "github": "github-org"
  }
]
```

**Required:** `project`, `slug`, `gerrit`
**Optional:** `jenkins`, `github`, `jjb_attribution`

```text

---

## 📊 Workflows

### Production Reports (`reporting-production.yaml`)

- **Schedule:** Monday 7:00 AM UTC
- **Trigger:** Manual via workflow_dispatch
- **Output:** `/production/<project-slug>/`
- **Artifacts:** 90-day retention
- **Projects:** All configured projects

---

## 🗂️ GitHub Pages Structure

```text
/                              # Root landing page
└── production/                # Production reports
    ├── index.html            # Report listing
    └── <project-slug>/
        ├── report.html       # Interactive report
        ├── report_raw.json   # Raw data
        ├── report.md         # Markdown report
        └── metadata.json     # Generation metadata
```text

---

## 🔧 Setup Quick Steps

### 1. Enable GitHub Pages

```bash
# Settings → Pages → Build and deployment
# Source: GitHub Actions
```text

The workflow deploys the site with `actions/deploy-pages`; no
`gh-pages` branch is needed.

### 2. Set Permissions

```bash
# Settings → Actions → General
# Read repository contents and packages permissions is enough;
# each job declares the permissions it needs
```text

---

## 📦 Artifacts

### Production Workflow

| Artifact                   | Contents         | Retention |
| -------------------------- | ---------------- | --------- |
| `raw-data-<project>`       | JSON data files  | 90 days   |
| `reports-<project>`        | All report files | 90 days   |
| `clone-manifest-<project>` | Clone tracking   | 90 days   |
| `clone-log-<project>`      | Clone logs       | 90 days   |

---

## 🐛 Troubleshooting

### Reports Not Showing

```bash
# Check the publish job log for projects dropped from the site
# Actions → Select run → Build GitHub Pages site

# Check GitHub Pages status
# Settings → Pages → Check deployment status
```text

### Workflow Failing

```bash
# Check workflow logs
# Actions → Select failed run → Review logs

# Verify secrets exist
# Settings → Secrets and variables → Actions

# Validate PROJECTS_JSON
echo '${{ vars.PROJECTS_JSON }}' | jq .
```text

---

## 📥 Download Historical Data

```bash
# Set token
export GITHUB_TOKEN=ghp_...

# Download last 90 days
.github/scripts/download-artifacts.sh \
  reporting-production.yaml \
  ./historical-data \
  90
```text

---

## 🔄 Adding New Project

1. Edit `PROJECTS_JSON` variable:

```json
{
  "project": "New Project",
  "gerrit": "gerrit.newproject.org",
  "jenkins": "jenkins.newproject.org",
  "github": "newproject-org"
}
```text

2. Save variable

3. Next workflow run will include it

---

## 📞 Quick Links

| Resource        | Link                                                      |
| --------------- | --------------------------------------------------------- |
| **Setup Guide** | [GITHUB_PAGES_SETUP.md](GITHUB_PAGES_SETUP.md)            |
| **Migration**   | [MIGRATION_CHECKLIST.md](MIGRATION_CHECKLIST.md)          |
| **Scripts**     | [.github/scripts/README.md](../.github/scripts/README.md) |
| **Main Docs**   | [README.md](../README.md)                                 |

---

## 🆘 Emergency Contacts

- **Issues:** GitHub Issues tab
- **Documentation:** `/docs` directory
- **Workflow Logs:** Actions tab

---

## 💡 Tips

- ✅ Production runs Monday 7am UTC
- ✅ Artifacts retained 90 days
- ✅ Use download script for meta-reporting
- ✅ Download the `github-pages` artifact to inspect the deployed site

---

**Version:** 2.0
**Updated:** 2025-01-XX
