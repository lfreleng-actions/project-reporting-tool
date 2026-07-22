<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Getting Started Guide

**Get up and running with the Repository Reporting System in 5 minutes!**

---

## 📋 Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** (supports 3.11, 3.12, 3.13, 3.14)
- **Git** installed
- **Repositories** cloned locally (the repos you want to analyze)

**Optional:**

- GitHub Personal Access Token (for GitHub API features)
- Gerrit credentials (for Gerrit API features)

---

## 🚀 Quick Start (3 Steps)

### Step 1: Install

Choose your preferred method:

#### Using UV (Recommended - Faster)

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the tool
uv sync

# Verify installation
uv run lf-releng-project-reporting --version
```

#### Using pip

```bash
# Install from source
pip install .

# Verify installation
lf-releng-project-reporting --version
```

### Step 2: Setup Configuration

**Interactive wizard** (easiest for first-time users):

```bash
lf-releng-project-reporting init --project my-project
```

Follow the prompts:

- Repository path: `./repos` (or your path)
- Output directory: `./reports`
- Other options: Press Enter for defaults

**Or use a template** (quick setup):

```bash
lf-releng-project-reporting init --project my-project --template standard
```

This creates `config/my-project.yaml` with sensible defaults.

### Step 3: Generate Your First Report

```bash
lf-releng-project-reporting generate \
  --project my-project \
  --repos-path ./repos
```

**Done!** Your reports are in `reports/my-project/`

---

## 📊 What You Get

After generation, you'll find:

```text
reports/my-project/
├── report_raw.json           # Complete data (canonical)
├── report.md                 # Markdown report (readable)
├── report.html               # Interactive HTML (sortable)
├── config_resolved.json      # Configuration used
└── my-project_report_bundle.zip  # Everything bundled
```

**Open `report.html` in your browser** for an interactive experience!

---

## 🎯 Common First-Time Scenarios

### Scenario 1: Analyze One Repository

```bash
# Create directory for repo
mkdir repos
cd repos
git clone https://github.com/example/my-repo.git
cd ..

# Generate report
lf-releng-project-reporting generate \
  --project my-repo \
  --repos-path ./repos
```

### Scenario 2: Analyze Multiple Repositories

```bash
# Clone multiple repos
mkdir repos
cd repos
git clone https://github.com/example/repo1.git
git clone https://github.com/example/repo2.git
git clone https://github.com/example/repo3.git
cd ..

# Generate combined report
lf-releng-project-reporting generate \
  --project my-organization \
  --repos-path ./repos
```

### Scenario 3: Test with Sample Configuration

```bash
# Create sample config
lf-releng-project-reporting init --project sample --template standard

# Preview configuration (dry run)
lf-releng-project-reporting generate \
  --project sample \
  --repos-path ./repos \
  --dry-run

# Generate if looks good
lf-releng-project-reporting generate \
  --project sample \
  --repos-path ./repos
```

### Scenario 4: Quick Analysis (Skip Features)

```bash
# Quick analysis with minimal output
lf-releng-project-reporting generate \
  --project quick-test \
  --repos-path ./repos \
  --quiet
```

---

## ⚙️ Basic Configuration

Your `config/my-project.yaml` controls report generation:

```yaml
# Minimal configuration
project: my-project

# Time windows for analysis
time_windows:
  last_365:
    days: 365
    label: "Last Year"
  last_3_years:
    days: 1095
    label: "Last 3 Years"
```

**See [Configuration Guide](CONFIGURATION.md) for complete options.**

---

## 🎨 Customizing Your Report

### Add GitHub API Integration

```yaml
# config/my-project.yaml
github_api:
  enabled: true
  token: ghp_your_token_here  # Or use environment variable
```

```bash
# Or pass via environment
export GITHUB_TOKEN=ghp_your_token_here
lf-releng-project-reporting generate --project my-project --repos-path ./repos
```

### Enable INFO.yaml Reports

```yaml
# config/my-project.yaml
info_yaml:
  enabled: true
  source:
    type: "git"
    url: "https://gerrit.linuxfoundation.org/infra/releng/info-master"
```

### Optimize Performance

```yaml
# config/my-project.yaml
performance:
  parallel_processing:
    enabled: true
    max_workers: 8
  caching:
    enabled: true
```

```bash
# Or use command-line flags
lf-releng-project-reporting generate \
  --project my-project \
  --repos-path ./repos \
  --cache \
  --workers 8
```

---

## 🔍 Verifying Your Setup

### Check Configuration

```bash
# Show resolved configuration
lf-releng-project-reporting config show --project my-project

# Validate without generating
lf-releng-project-reporting generate \
  --project my-project \
  --repos-path ./repos \
  --dry-run
```

### Check Available Features

```bash
# List all features the tool can detect
lf-releng-project-reporting list-features

# Check features in your repos
lf-releng-project-reporting generate \
  --project my-project \
  --repos-path ./repos \
  --dry-run \
  --verbose
```

### View Help

```bash
# General help
lf-releng-project-reporting --help

# Command-specific help
lf-releng-project-reporting generate --help
lf-releng-project-reporting init --help
lf-releng-project-reporting config --help
```

---

## 🚦 Next Steps

Now that you have your first report:

### 1. **Explore Your Report**

- Open `report.html` in a browser
- Sort tables by clicking column headers
- Review feature detection results
- Check contributor statistics

### 2. **Refine Configuration**

- Add GitHub token for API features
- Customize time windows
- Configure feature detection
- Set up caching for faster runs

### 3. **Learn More**

- [Usage Examples](USAGE_EXAMPLES.md) - Real-world scenarios
- [Configuration Guide](CONFIGURATION.md) - All configuration options
- [Commands Reference](COMMANDS.md) - Complete command documentation
- [FAQ](FAQ.md) - Common questions answered

### 4. **Automate**

- [CI/CD Integration](CI_CD_INTEGRATION.md) - GitHub Actions setup
- Schedule regular report generation
- Distribute reports automatically

---

## 💡 Quick Tips

### Speed Up Generation

```bash
# Enable caching (60-70% faster on subsequent runs)
lf-releng-project-reporting generate --project my-project --repos-path ./repos --cache

# Use parallel processing
lf-releng-project-reporting generate --project my-project --repos-path ./repos --workers 8

# Combine both
lf-releng-project-reporting generate \
  --project my-project \
  --repos-path ./repos \
  --cache \
  --workers 8
```

### Quiet Mode for Production

```bash
# Minimal output (good for automation)
lf-releng-project-reporting generate \
  --project my-project \
  --repos-path ./repos \
  --quiet
```

### Verbose Mode for Debugging

```bash
# Detailed output (troubleshooting)
lf-releng-project-reporting generate \
  --project my-project \
  --repos-path ./repos \
  --verbose
```

### Generate Specific Format

```bash
# HTML only
lf-releng-project-reporting generate \
  --project my-project \
  --repos-path ./repos \
  --output-format html

# JSON only
lf-releng-project-reporting generate \
  --project my-project \
  --repos-path ./repos \
  --output-format json
```

---

## ❓ Troubleshooting

### "Command not found: lf-releng-project-reporting"

**Using UV:**

```bash
uv run lf-releng-project-reporting --help
```

**Using pip:** Ensure installed correctly:

```bash
pip install -e .
```

### "No repositories found"

Check your repository path:

```bash
ls -la ./repos  # Should show .git directories
```

### "Configuration file not found"

Create configuration first:

```bash
lf-releng-project-reporting init --project my-project
```

### Reports Take Too Long

Enable caching and parallel processing:

```bash
lf-releng-project-reporting generate \
  --project my-project \
  --repos-path ./repos \
  --cache \
  --workers auto
```

### Need More Help?

- [FAQ](FAQ.md) - Frequently asked questions
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues
- [GitHub Issues](https://github.com/lfreleng-actions/project-reporting-tool/issues) - Report bugs

---

## 🎓 Learning Path

### Beginner Path (Today)

1. ✅ Install the tool (you are here!)
2. ✅ Generate first report
3. 📖 Read [Usage Examples](USAGE_EXAMPLES.md)
4. 📖 Review [FAQ](FAQ.md)

### Intermediate Path (This Week)

1. 📖 Study [Configuration Guide](CONFIGURATION.md)
2. 🔧 Customize your configuration
3. 🚀 Set up [CI/CD Integration](CI_CD_INTEGRATION.md)
4. ⚡ Enable [Performance Optimization](PERFORMANCE.md)

### Advanced Path (This Month)

1. 📖 Read [Developer Guide](DEVELOPER_GUIDE.md)
2. 🛠️ Create custom templates
3. 🔌 Extend with plugins
4. 🤝 Contribute improvements

---

## 📚 Documentation Index

Quick links to all documentation:

| Category            | Document                                  | Description                |
| ------------------- | ----------------------------------------- | -------------------------- |
| **Getting Started** | [Getting Started](GETTING_STARTED.md)     | You are here!              |
| **Reference**       | [Commands](COMMANDS.md)                   | Complete command reference |
|                     | [FAQ](FAQ.md)                             | Common questions           |
|                     | [Configuration](CONFIGURATION.md)         | All configuration options  |
| **Usage**           | [Usage Examples](USAGE_EXAMPLES.md)       | Real-world scenarios       |
|                     | [Performance](PERFORMANCE.md)             | Optimization guide         |
|                     | [CI/CD Integration](CI_CD_INTEGRATION.md) | Automation setup           |
| **Support**         | [Troubleshooting](TROUBLESHOOTING.md)     | Problem solving            |
| **Development**     | [Developer Guide](DEVELOPER_GUIDE.md)     | Architecture & API         |
|                     | [Testing](TESTING.md)                     | Test suite documentation   |

---

## 🎉 Success

You've successfully:

- ✅ Installed the reporting tool
- ✅ Generated your first report
- ✅ Learned the basics

**Ready for more?** Check out [Usage Examples](USAGE_EXAMPLES.md) for advanced scenarios!

---

**Version:** 1.0
**Last Updated:** 2025-01-XX
**Status:** Production Ready
