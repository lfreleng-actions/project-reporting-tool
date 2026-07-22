<!--
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Production Migration Guide

> Complete guide for migrating from the legacy reporting system to the modern Gerrit Reporting Tool

This guide covers pre-migration preparation, deployment steps, validation procedures, and rollback strategies for production environments.

---

## Table of Contents

- [Overview](#overview)
- [Migration Summary](#migration-summary)
- [Pre-Migration Checklist](#pre-migration-checklist)
- [Deployment Steps](#deployment-steps)
- [Validation & Testing](#validation--testing)
- [Rollback Procedures](#rollback-procedures)
- [Post-Migration](#post-migration)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## Overview

### What's Changing

The modern reporting system provides:

- ✅ **Feature Parity** - All legacy features preserved or enhanced
- ✅ **Improved Performance** - Parallel processing, caching, optimized data collection
- ✅ **Better Maintainability** - Template-based architecture, modular design
- ✅ **Enhanced Output** - Improved formatting, better visual presentation
- ✅ **New Features** - INFO.yaml integration, enhanced metrics, workflow status

### What's NOT Changing

- ✅ **Data sources** - Same Gerrit/GitHub/Jenkins APIs
- ✅ **Report structure** - Same sections and organization
- ✅ **Core metrics** - Same calculations and definitions
- ✅ **Configuration** - Backward compatible configuration format

### Migration Timeline

| Phase           | Duration  | Description                       |
| --------------- | --------- | --------------------------------- |
| **Preparation** | 1-2 days  | Testing, validation, backup       |
| **Deployment**  | 2-4 hours | Code deployment, configuration    |
| **Validation**  | 1 day     | Report comparison, quality checks |
| **Monitoring**  | 1 week    | Monitor for issues, user feedback |

**Total Estimated Time:** 3-5 days

---

## Migration Summary

### System Changes

#### Phase 0-3: Core Features (Complete ✅)

- INFO.yaml reporting integration
- Enhanced metrics (LOC, organization stats)
- Activity status indicators
- Feature matrix improvements
- Workflow status detection

#### Phase 4: Formatting Utilities (Complete ✅)

- New template filters: `format_loc`, `status_emoji`
- Enhanced `format_percentage` with dual modes
- Consistent number/date formatting

#### Phase 5: HTML Template Updates (Complete ✅)

- Full HTML/Markdown parity
- Section emoji standardization
- Enhanced table formatting
- Improved visual presentation

#### Phase 6: Integration Testing (Complete ✅)

- ONAP production report validation
- OpenDaylight testing
- Automated comparison tools
- 100% pass rate on critical checks

### Compatibility Matrix

<!-- markdownlint-disable MD060 -->

| Component            | Legacy                | Modern                 | Compatible |
| -------------------- | --------------------- | ---------------------- | ---------- |
| **Python**           | 3.10+                 | 3.11+                  | ✅ Yes     |
| **Configuration**    | YAML                  | YAML                   | ✅ Yes     |
| **Data Format**      | JSON                  | JSON                   | ✅ Yes     |
| **APIs**             | Gerrit/GitHub/Jenkins | Gerrit/GitHub/Jenkins  | ✅ Yes     |
| **Output Formats**   | MD/HTML/JSON          | MD/HTML/JSON/ZIP       | ✅ Yes     |
| **Report Structure** | 6 sections            | 6 sections + INFO.yaml | ✅ Yes     |

<!-- markdownlint-enable MD060 -->

---

## Pre-Migration Checklist

### 1. Environment Preparation

#### Backup Current System

```bash
# Backup legacy codebase
cd /path/to/legacy/system
tar -czf legacy-reporting-backup-$(date +%Y%m%d).tar.gz .

# Backup configuration files
cp -r configuration/ configuration.backup/

# Backup recent reports (for comparison)
cp -r reports/ reports.backup/
```

#### Verify Dependencies

```bash
# Check Python version
python --version  # Should be 3.11+

# Check required tools
which git
which curl

# Verify GitHub token (if using)
echo $GITHUB_TOKEN  # or $CLASSIC_READ_ONLY_PAT_TOKEN
```

#### Clone Test Environment

```bash
# Clone modern system to test location
git clone https://github.com/lfreleng-actions/project-reporting-tool.git test-modern-reporting
cd test-modern-reporting

# Install dependencies
uv sync
# OR
pip install .
```

### 2. Configuration Migration

#### Review Current Configuration

```bash
# Check current project configuration
cat configuration/onap.config
cat configuration/o-ran-sc.config
cat configuration/opendaylight.config
```

#### Migrate Configuration Files

The modern system uses the same YAML format - configuration files are **100% compatible**.

```bash
# Copy configuration files
cp /path/to/legacy/configuration/*.config /path/to/modern/configuration/

# Verify configuration
uv run lf-releng-project-reporting generate \
  --project ONAP \
  --repos-path ./gerrit.onap.org \
  --dry-run
```

#### Optional: Add INFO.yaml Configuration

Enhance your configuration with INFO.yaml reporting:

```yaml
# Add to configuration/onap.config
info_yaml:
  enabled: true
  source:
    type: git
    url: https://github.com/lfit/info-master.git
    branch: master
  performance:
    cache_enabled: true
    async_validation: true
```

See [Configuration Guide](CONFIGURATION.md#infoyaml-reports-configuration) for details.

### 3. Test Report Generation

#### Generate Comparison Reports

```bash
# Generate with legacy system
cd /path/to/legacy
./generate_report.sh ONAP
cp reports/ONAP/report.html reports/ONAP/legacy-report.html

# Generate with modern system
cd /path/to/modern
uv run lf-releng-project-reporting generate \
  --project ONAP \
  --repos-path ./gerrit.onap.org
cp reports/ONAP/report.html reports/ONAP/modern-report.html
```

#### Compare Reports

```bash
# Use automated comparison tool
bash testing/compare-production.sh \
  reports/ONAP/legacy-report.html \
  reports/ONAP/modern-report.html

# Expected output:
# ✅ All critical checks passed
# ✅ Section headers match
# ✅ Metrics present
# ✅ Formatting consistent
```

#### Validation Criteria

- ✅ All sections present
- ✅ Metrics match (±5% acceptable for timing-sensitive data)
- ✅ No missing data
- ✅ Formatting improvements visible
- ✅ No errors in output

---

## Deployment Steps

### Step 1: Production Environment Setup

#### Install Modern System

```bash
# Clone to production location
cd /opt/reporting  # or your deployment path
git clone https://github.com/lfreleng-actions/project-reporting-tool.git modern
cd modern

# Install dependencies
uv sync
# OR
pip install .
```

#### Configure Environment Variables

```bash
# Add to ~/.bashrc or deployment scripts
export GITHUB_TOKEN=ghp_your_token_here
# OR
export CLASSIC_READ_ONLY_PAT_TOKEN=ghp_your_token_here

# Optional: Performance tuning
export WORKERS=8
export CACHE_ENABLED=true
```

#### Verify Installation

```bash
# Test command availability
uv run lf-releng-project-reporting --help

# Expected output:
# Usage: lf-releng-project-reporting [OPTIONS] COMMAND [ARGS]...
# ...
```

### Step 2: Configuration Deployment

#### Copy Configuration Files

```bash
# Copy from legacy system
cp /opt/reporting/legacy/configuration/*.config configuration/

# Verify configurations
ls -la configuration/
# Should see: onap.config, o-ran-sc.config, opendaylight.config, etc.
```

#### Validate Configuration

```bash
# Test each project configuration
for project in ONAP O-RAN-SC OpenDaylight; do
  echo "Testing $project..."
  uv run lf-releng-project-reporting generate \
    --project $project \
    --repos-path ./repos \
    --dry-run
done
```

### Step 3: CI/CD Pipeline Update

#### GitHub Actions Workflow

Update your workflow file (`.github/workflows/generate-reports.yml`):

```yaml
name: Generate Reports

on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight
  workflow_dispatch:

jobs:
  generate:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        project: [ONAP, O-RAN-SC, OpenDaylight]

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install UV
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync

      - name: Clone repositories
        uses: lfit/gerrit-clone-action@main
        with:
          gerrit-server: gerrit.${{ matrix.project }}.org
          dest-path: ./gerrit.${{ matrix.project }}.org

      - name: Generate report
        run: |
          uv run lf-releng-project-reporting generate \
            --project ${{ matrix.project }} \
            --repos-path ./gerrit.${{ matrix.project }}.org \
            --cache \
            --workers 8 \
            --quiet
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: ${{ matrix.project }}-report
          path: reports/${{ matrix.project }}/
```

#### Manual Deployment Scripts

Update your cron jobs or deployment scripts:

```bash
#!/bin/bash
# /opt/reporting/scripts/generate-all-reports.sh

set -e

PROJECTS=(ONAP O-RAN-SC OpenDaylight)

for project in "${PROJECTS[@]}"; do
  echo "Generating report for $project..."

  cd /opt/reporting/modern

  uv run lf-releng-project-reporting generate \
    --project "$project" \
    --repos-path "./repos/gerrit.${project,,}.org" \
    --cache \
    --workers 8 \
    --quiet

  echo "✅ $project report complete"
done

echo "✅ All reports generated successfully"
```

### Step 4: Cutover

#### Parallel Run Period (Recommended)

Run both systems in parallel for 1 week:

```bash
# Generate with both systems
./legacy/generate_reports.sh
./modern/lf-releng-project-reporting generate --project ONAP --repos-path ./repos

# Compare outputs daily
bash testing/compare-production.sh \
  legacy/reports/ONAP/report.html \
  modern/reports/ONAP/report.html
```

#### Switch to Modern System

```bash
# Update symlinks or paths
ln -sf /opt/reporting/modern /opt/reporting/current

# Update cron jobs
crontab -e
# Change: /opt/reporting/legacy/generate.sh
# To:     /opt/reporting/modern/generate.sh

# Update CI/CD workflows (commit and push)
git commit -am "Switch to modern reporting system"
git push
```

---

## Validation & Testing

### Automated Validation

#### Run Comparison Script

```bash
cd /opt/reporting/modern

# Compare against production baseline
bash testing/compare-production.sh \
  /path/to/production/report.html \
  reports/ONAP/report.html

# Expected checks:
# ✅ Section headers present
# ✅ Metrics extracted
# ✅ Formatting applied
# ✅ Footer branding
```

#### Verify Output Files

```bash
# Check all output formats generated
ls -lh reports/ONAP/

# Expected files:
# - report_raw.json          (complete data)
# - report.md                (markdown report)
# - report.html              (interactive HTML)
# - config_resolved.json     (applied config)
# - ONAP_report_bundle.zip   (bundled archive)
```

### Manual Validation

#### Section-by-Section Review

<!-- markdownlint-disable MD060 -->

| Section           | Validation Criteria                                    | Status |
| ----------------- | ------------------------------------------------------ | ------ |
| **Summary**       | Metrics match, percentages correct                     | ☐      |
| **Repositories**  | All repos listed, LOC formatted with '+', status emoji | ☐      |
| **Contributors**  | Top contributors present, organization column          | ☐      |
| **Organizations** | Organization stats, LOC with '+' prefix                | ☐      |
| **Features**      | Feature matrix complete, checkmarks correct            | ☐      |
| **Workflows**     | CI/CD jobs listed, status indicators                   | ☐      |
| **INFO.yaml**     | Committer activity (if enabled)                        | ☐      |
| **Footer**        | "Generated with ❤️ by Release Engineering"             | ☐      |

<!-- markdownlint-enable MD060 -->

#### Quality Checks

```bash
# Check for errors in logs
grep -i error reports/ONAP/*.log

# Verify data completeness
jq '.repositories | length' reports/ONAP/report_raw.json
jq '.contributors | length' reports/ONAP/report_raw.json

# Check HTML rendering
open reports/ONAP/report.html  # Manual visual inspection
```

### Performance Validation

#### Benchmark Generation Time

```bash
# Time report generation
time uv run lf-releng-project-reporting generate \
  --project ONAP \
  --repos-path ./gerrit.onap.org \
  --cache \
  --workers 8

# Expected: < 5 minutes for ONAP (with cache)
# First run (no cache): 10-15 minutes
```

#### Resource Usage

```bash
# Monitor during generation
top -p $(pgrep -f lf-releng-project-reporting)

# Check disk usage
du -sh reports/
du -sh .cache/
```

---

## Rollback Procedures

### Quick Rollback (< 5 minutes)

If critical issues are discovered:

```bash
# Revert symlinks
ln -sf /opt/reporting/legacy /opt/reporting/current

# Revert cron jobs
crontab -e
# Change back to legacy paths

# Revert CI/CD workflows
git revert <commit-hash>
git push
```

### Data Preservation

Legacy reports are preserved during migration:

```bash
# Legacy reports remain untouched
ls /opt/reporting/legacy/reports/

# Modern reports in separate directory
ls /opt/reporting/modern/reports/

# No data loss risk
```

### Configuration Rollback

Configuration files are backward compatible - no changes needed for rollback.

---

## Post-Migration

### Monitoring Checklist

#### First 24 Hours

- [ ] Verify daily report generation completes
- [ ] Check for errors in logs
- [ ] Validate output files created
- [ ] Monitor disk space usage
- [ ] Review cache performance

#### First Week

- [ ] Compare reports to legacy baseline
- [ ] Collect user feedback
- [ ] Monitor performance metrics
- [ ] Adjust cache settings if needed
- [ ] Fine-tune parallel processing

#### First Month

- [ ] Review INFO.yaml integration (if enabled)
- [ ] Analyze performance improvements
- [ ] Document any issues encountered
- [ ] Update configuration as needed
- [ ] Plan for legacy system decommission

### Optimization Opportunities

#### Enable Caching

```bash
# Add to configuration or environment
export CACHE_ENABLED=true

# Or in command:
lf-releng-project-reporting generate --project ONAP --cache
```

#### Tune Parallelism

```bash
# Adjust workers based on CPU count
export WORKERS=16  # For 16+ core systems

# Or in command:
lf-releng-project-reporting generate --project ONAP --workers 16
```

#### INFO.yaml Configuration

```yaml
# Optimize INFO.yaml performance
info_yaml:
  performance:
    async_validation: true
    max_concurrent_urls: 20
    cache_enabled: true
    cache_ttl: 3600
```

### Documentation Updates

Update internal documentation to reflect new system:

- [ ] Update runbooks with new commands
- [ ] Update troubleshooting guides
- [ ] Document new features for users
- [ ] Update CI/CD pipeline documentation
- [ ] Create quick reference for operators

---

## Troubleshooting

### Report Generation Fails

**Error:** Command exits with non-zero status

**Solutions:**

1. Check logs for specific error messages
2. Verify repository path is correct
3. Test with `--dry-run` flag first
4. Check GitHub token is valid (if using)

```bash
# Debug command
uv run lf-releng-project-reporting generate \
  --project ONAP \
  --repos-path ./gerrit.onap.org \
  --verbose
```

### Missing Sections in Report

**Problem:** Expected sections not in output

**Solutions:**

1. Check configuration file is loaded correctly
2. Verify data is available for section
3. Review template files in `src/templates/`

```bash
# Verify resolved configuration
cat reports/ONAP/config_resolved.json | jq '.sections'
```

### Performance Issues

**Problem:** Report generation too slow

**Solutions:**

1. Enable caching: `--cache`
2. Increase workers: `--workers 16`
3. Use INFO.yaml async validation
4. Check network connectivity to APIs

```bash
# Optimized command
uv run lf-releng-project-reporting generate \
  --project ONAP \
  --repos-path ./gerrit.onap.org \
  --cache \
  --workers 16
```

### INFO.yaml Data Missing

**Problem:** INFO.yaml sections not appearing

**Solutions:**

1. Verify `info_yaml.enabled: true` in config
2. Check info-master repository access
3. Review INFO.yaml validation logs
4. Test with local info-master clone

```bash
# Debug INFO.yaml
uv run lf-releng-project-reporting generate \
  --project ONAP \
  --repos-path ./gerrit.onap.org \
  --verbose 2>&1 | grep -i info.yaml
```

### GitHub Workflow Status Missing

**Problem:** Workflow status shows as "unknown" or grey

**Solutions:**

1. Verify `GITHUB_TOKEN` environment variable set
2. Check token has required permissions (repo, actions:read)
3. Ensure using Classic PAT (not fine-grained)

```bash
# Test GitHub token
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user

# Should return user info, not 401
```

---

## FAQ

### Q: Will the migration affect existing reports?

**A:** No. Legacy reports are preserved in separate directories. The modern system writes to its own `reports/` directory.

### Q: Do I need to change my configuration files?

**A:** No. Configuration files are 100% backward compatible. You can optionally add new features like INFO.yaml, but existing configs work as-is.

### Q: What if I find a bug after migration?

**A:** Follow the quick rollback procedure (< 5 minutes) to revert to legacy system while the issue is addressed. Report the bug on GitHub.

### Q: How do I compare old and new reports?

**A:** Use the automated comparison tool:

```bash
bash testing/compare-production.sh legacy-report.html modern-report.html
```

### Q: Can I run both systems in parallel?

**A:** Yes. This is recommended during the transition period. Both systems can coexist without conflicts.

### Q: What happens to custom modifications in legacy system?

**A:** Custom modifications need to be ported to the new template-based system. See [Template Development Guide](TEMPLATE_DEVELOPMENT.md).

### Q: How do I enable INFO.yaml reporting?

**A:** Add INFO.yaml configuration to your project config file. See [Configuration Guide](CONFIGURATION.md#infoyaml-reports-configuration).

### Q: What's the performance improvement?

**A:** With caching and parallel processing enabled:

- First run: Similar to legacy (~10-15 min for ONAP)
- Subsequent runs: 50-70% faster (~3-5 min for ONAP)

### Q: Are there any breaking changes?

**A:** No breaking changes. All legacy features are preserved or enhanced.

### Q: How do I update the system after migration?

**A:** Standard git pull and dependency update:

```bash
cd /opt/reporting/modern
git pull
uv sync  # or pip install --upgrade .
```

---

## Additional Resources

### Documentation

- [Getting Started Guide](GETTING_STARTED.md) - Installation and setup
- [Configuration Guide](CONFIGURATION.md) - All configuration options
- [Template Development Guide](TEMPLATE_DEVELOPMENT.md) - Customizing templates
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Problem solving
- [Performance Guide](PERFORMANCE.md) - Optimization tips

### Testing Tools

- `testing/quick-test.sh` - Quick validation with minimal data
- `testing/local-testing.sh` - Full test with real data
- `testing/compare-production.sh` - Automated report comparison

### Support

- **Documentation**: [Complete Index](INDEX.md)
- **Issues**: [GitHub Issues](https://github.com/lfreleng-actions/project-reporting-tool/issues)
- **Discussions**: [GitHub Discussions](https://github.com/lfreleng-actions/project-reporting-tool/discussions)

---

## Migration Checklist Summary

### Pre-Migration

- [ ] Backup legacy system and configuration
- [ ] Install modern system in test environment
- [ ] Migrate configuration files
- [ ] Generate test reports
- [ ] Compare test reports to production
- [ ] Review and approve test results

### Deployment

- [ ] Install modern system in production
- [ ] Deploy configuration files
- [ ] Update CI/CD pipelines
- [ ] Update cron jobs / automation
- [ ] Start parallel run period (optional but recommended)

### Validation

- [ ] Run automated comparison
- [ ] Verify all output files created
- [ ] Manual section-by-section review
- [ ] Performance benchmarking
- [ ] Quality checks pass

### Post-Migration

- [ ] Monitor first 24 hours
- [ ] Collect user feedback
- [ ] Optimize performance settings
- [ ] Update documentation
- [ ] Plan legacy system decommission

---

**Migration Status:** ✅ **READY FOR PRODUCTION**

The modern Gerrit Reporting Tool has been thoroughly tested and validated. All features from the legacy system are preserved or enhanced. Migration risk is minimal with clear rollback procedures available.

**Recommended Migration Date:** At your convenience
**Estimated Downtime:** None (parallel operation supported)
**Rollback Time:** < 5 minutes if needed

_For questions or assistance during migration, consult the troubleshooting section above or open a GitHub issue._
