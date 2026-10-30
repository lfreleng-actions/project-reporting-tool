<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# 📚 Documentation Index

**Complete guide to the Repository Reporting System**

---

## 🚀 Start Here

New to the tool? Begin with these essentials:

| Document                                  | Description                            | Time   |
| ----------------------------------------- | -------------------------------------- | ------ |
| [**Getting Started**](GETTING_STARTED.md) | Install and generate your first report | 5 min  |
| [**Commands**](COMMANDS.md)               | Complete command reference             | 10 min |
| [**FAQ**](FAQ.md)                         | Frequently asked questions             | 5 min  |

---

## 📖 Core Documentation

### User Guides

| Document                                  | Description                                                 |
| ----------------------------------------- | ----------------------------------------------------------- |
| [**Getting Started**](GETTING_STARTED.md) | Installation, setup, and first report                       |
| [**Commands**](COMMANDS.md)               | Complete command-line reference                             |
| [**FAQ**](FAQ.md)                         | Common questions and answers                                |
| [**Configuration**](CONFIGURATION.md)     | All configuration options (including GitHub API, INFO.yaml) |
| [**Usage Examples**](USAGE_EXAMPLES.md)   | Real-world usage scenarios and patterns                     |
| [**Troubleshooting**](TROUBLESHOOTING.md) | Problem solving and debugging                               |

### Advanced Topics

| Document                                            | Description                                    |
| --------------------------------------------------- | ---------------------------------------------- |
| [**Performance**](PERFORMANCE.md)                   | Optimization, caching, and parallel processing |
| [**CI/CD Integration**](CI_CD_INTEGRATION.md)       | GitHub Actions, GitLab CI, and automation      |
| [**Deployment**](DEPLOYMENT.md)                     | Production deployment and operations           |
| [**Feature Discovery**](FEATURE_DISCOVERY_GUIDE.md) | Understanding feature detection                |

### Developer Documentation

| Document                                            | Description                                   |
| --------------------------------------------------- | --------------------------------------------- |
| [**Developer Guide**](DEVELOPER_GUIDE.md)           | Architecture, API reference, and contributing |
| [**Template Development**](TEMPLATE_DEVELOPMENT.md) | Customizing Jinja2 templates                  |
| [**Testing**](TESTING.md)                           | Test suite documentation                      |
| [**Migration Guide**](MIGRATION_GUIDE.md)           | Production migration from legacy system       |

---

## 📂 Documentation by Topic

### 🎯 Getting Started

- [Getting Started Guide](GETTING_STARTED.md) - Complete setup walkthrough
- [Commands](COMMANDS.md) - Quick reference and full command docs
- [FAQ](FAQ.md) - Common questions

### ⚙️ Configuration

- [Configuration Guide](CONFIGURATION.md) - Comprehensive configuration reference
  - Basic configuration
  - GitHub API authentication
  - INFO.yaml reports
  - Performance tuning
  - Advanced options
- [Configuration Merging](CONFIGURATION_MERGING.md) - How project configs inherit and override defaults
  - Deep merge behavior
  - Minimal configuration files
  - Override patterns
  - Real-world examples

### 📊 Features

- [Usage Examples](USAGE_EXAMPLES.md) - How to use all features
  - Basic reports
  - INFO.yaml reports
  - GitHub API integration
  - Performance optimization
  - CI/CD examples
- [Feature Discovery Guide](FEATURE_DISCOVERY_GUIDE.md) - Feature detection system

### ⚡ Performance & Operations

- [Performance Guide](PERFORMANCE.md) - Optimization strategies
  - Caching
  - Parallel processing
  - Memory optimization
  - Scaling
- [Deployment Guide](DEPLOYMENT.md) - Production operations
  - Installation
  - Configuration management
  - Monitoring
  - Maintenance
- [CI/CD Integration](CI_CD_INTEGRATION.md) - Automation
  - GitHub Actions
  - GitLab CI
  - Jenkins
  - Scheduled reports

### 🐛 Troubleshooting

- [Troubleshooting Guide](TROUBLESHOOTING.md) - Problem solving
  - Common issues
  - Error messages
  - Performance problems
  - GitHub API issues
  - INFO.yaml issues
  - Debug mode

### 👨‍💻 Development

- [Developer Guide](DEVELOPER_GUIDE.md) - For contributors
  - Architecture overview
  - API reference
  - INFO.yaml API
  - Extension points
  - Contribution guidelines
- [Template Development Guide](TEMPLATE_DEVELOPMENT.md) - Template customization
  - Template architecture
  - Available filters
  - Creating custom templates
  - Component system
  - Best practices
- [Testing Guide](TESTING.md) - Test suite
  - Running tests
  - Writing tests
  - Test coverage
- [Migration Guide](MIGRATION_GUIDE.md) - Production deployment
  - Pre-migration checklist
  - Deployment steps
  - Validation procedures
  - Rollback strategies

---

## 🔍 Quick Navigation

**Looking for...?**

- **First time using the tool?** → [Getting Started](GETTING_STARTED.md)
- **Command syntax?** → [Commands](COMMANDS.md)
- **Configuration options?** → [Configuration](CONFIGURATION.md)
- **Minimal project configs?** → [Configuration Merging](CONFIGURATION_MERGING.md)
- **GitHub token setup?** → [Configuration > GitHub API](CONFIGURATION.md#github-api-authentication)
- **INFO.yaml reports?** → [Usage Examples > INFO.yaml](USAGE_EXAMPLES.md#infoyaml-reports)
- **Common problems?** → [Troubleshooting](TROUBLESHOOTING.md)
- **Performance issues?** → [Performance](PERFORMANCE.md)
- **CI/CD setup?** → [CI/CD Integration](CI_CD_INTEGRATION.md)
- **Customizing templates?** → [Template Development](TEMPLATE_DEVELOPMENT.md)
- **Migrating to production?** → [Migration Guide](MIGRATION_GUIDE.md)
- **Contributing?** → [Developer Guide](DEVELOPER_GUIDE.md)
- **Running tests?** → [Testing](TESTING.md)

---

## 📊 Report Types

The tool generates multiple report types:

### Standard Reports

- **Git Analytics** - Commit activity, contributors, LOC changes
- **Feature Detection** - CI/CD, docs, security, dependencies
- **Contributor Intelligence** - Author analysis, organization mapping

### INFO.yaml Reports

- **Committer INFO.yaml Report** - Project metadata with activity-colored committers
- **Lifecycle State Summary** - Project distribution by lifecycle state

**Configuration:** [Configuration > INFO.yaml](CONFIGURATION.md#infoyaml-reports-configuration)
**Usage:** [Usage Examples > INFO.yaml](USAGE_EXAMPLES.md#infoyaml-reports)
**API:** [Developer Guide > INFO.yaml](DEVELOPER_GUIDE.md#infoyaml-report-type)

---

## 🎓 Learning Paths

### Beginner (Day 1)

1. [Getting Started](GETTING_STARTED.md) - Installation and first report
2. [Commands](COMMANDS.md) - Basic command usage
3. [FAQ](FAQ.md) - Common questions
4. [Usage Examples](USAGE_EXAMPLES.md) - See real-world scenarios

### Intermediate (Week 1)

1. [Configuration](CONFIGURATION.md) - Customize your setup
2. [Performance](PERFORMANCE.md) - Optimize generation
3. [CI/CD Integration](CI_CD_INTEGRATION.md) - Automate reports
4. [Troubleshooting](TROUBLESHOOTING.md) - Solve common issues

### Advanced (Month 1)

1. [Deployment](DEPLOYMENT.md) - Production operations
2. [Template Development](TEMPLATE_DEVELOPMENT.md) - Customize templates
3. [Migration Guide](MIGRATION_GUIDE.md) - Migrate legacy systems
4. [Developer Guide](DEVELOPER_GUIDE.md) - Understand architecture
5. [Testing](TESTING.md) - Run and write tests
6. Contribute improvements!

---

## 🆘 Getting Help

### Self-Service Resources

1. **Check [FAQ](FAQ.md)** - Most questions answered here
2. **Search [Troubleshooting](TROUBLESHOOTING.md)** - Common issues solved
3. **Review [Commands](COMMANDS.md)** - Full command reference
4. **Read [Configuration](CONFIGURATION.md)** - All options documented

### Need More Help?

- **GitHub Issues:** Report bugs or request features
- **Discussions:** Ask questions, share tips
- **Documentation:** All guides in this directory

---

## 📝 Documentation Standards

All documentation follows these standards:

- **Format:** Markdown (.md)
- **License:** Apache-2.0 (header in every file)
- **Style:** Clear, concise, example-driven
- **Structure:** Consistent headings and organization
- **Links:** Relative paths, verified regularly
- **Examples:** Syntax highlighted, tested when possible
- **One page per topic:** Update the existing page for a feature in
  place; do not add dated status reports. See [README](README.md).

---

## 🗂️ Complete File List

This index is the single table of contents for `docs/`. Add new pages
here when you create them.

### User Documentation

| File                                                  | Topic                                    |
| ----------------------------------------------------- | ---------------------------------------- |
| [GETTING_STARTED.md](GETTING_STARTED.md)              | Installation and first report            |
| [COMMANDS.md](COMMANDS.md)                            | Command-line reference                   |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md)              | GitHub Pages reporting quick reference   |
| [FAQ.md](FAQ.md)                                      | Frequently asked questions               |
| [CONFIGURATION.md](CONFIGURATION.md)                  | Configuration reference                  |
| [CONFIGURATION_MERGING.md](CONFIGURATION_MERGING.md)  | Configuration inheritance and overrides  |
| [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md)                | Real-world usage patterns                |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md)              | Problem solving guide                    |

### Features

| File                                                                 | Topic                               |
| -------------------------------------------------------------------- | ----------------------------------- |
| [FEATURE_DISCOVERY_GUIDE.md](FEATURE_DISCOVERY_GUIDE.md)             | Feature detection system            |
| [TABLE_OF_CONTENTS.md](TABLE_OF_CONTENTS.md)                         | Report table of contents            |
| [DATATABLES_USAGE.md](DATATABLES_USAGE.md)                           | Sortable, searchable HTML tables    |
| [INFO_YAML_REPORTING.md](INFO_YAML_REPORTING.md)                     | INFO.yaml committer reporting       |
| [INFO_YAML_QUICK_REF.md](INFO_YAML_QUICK_REF.md)                     | INFO.yaml reporting quick reference |
| [INFO_YAML_SERVER_FILTERING.md](INFO_YAML_SERVER_FILTERING.md)       | INFO.yaml server filtering          |
| [GITHUB_NATIVE_QUICK_START.md](GITHUB_NATIVE_QUICK_START.md)         | GitHub-native projects              |
| [GITHUB_ONLY_PROJECTS.md](GITHUB_ONLY_PROJECTS.md)                   | GitHub-only projects                |
| [SCHEMA_VERSION_1.5.0.md](SCHEMA_VERSION_1.5.0.md)                   | Project schema 1.5.0                |
| [GITHUB_TOKEN_ENV.md](GITHUB_TOKEN_ENV.md)                           | GitHub token environment variable   |
| [features/GITHUB_TOKEN_ENV_VAR.md](features/GITHUB_TOKEN_ENV_VAR.md) | GitHub token variable summary       |
| [features/G2G_REGEX_PATTERNS.md](features/G2G_REGEX_PATTERNS.md)     | G2G workflow detection patterns     |
| [features/G2G_PATTERN_FLOW.md](features/G2G_PATTERN_FLOW.md)         | G2G pattern matching flow           |
| [HTTP_FALLBACK_GUIDE.md](HTTP_FALLBACK_GUIDE.md)                     | Jenkins HTTP fallback               |
| [GITHUB_LANGUAGE_COMPARISON.md](GITHUB_LANGUAGE_COMPARISON.md)       | GitHub language comparison tool     |

### Operations and Deployment

| File                                                      | Topic                                  |
| --------------------------------------------------------- | -------------------------------------- |
| [PERFORMANCE.md](PERFORMANCE.md)                          | Optimization and scaling               |
| [CI_CD_INTEGRATION.md](CI_CD_INTEGRATION.md)              | Automation and workflows               |
| [DEPLOYMENT.md](DEPLOYMENT.md)                            | Production operations                  |
| [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)                  | Production migration guide             |
| [GITHUB_PAGES_SETUP.md](GITHUB_PAGES_SETUP.md)            | GitHub Pages publishing                |
| [TABLE_COMPARISON.md](TABLE_COMPARISON.md)                | Production and new system tables       |

### Developer Documentation

| File                                                                     | Topic                            |
| ------------------------------------------------------------------------ | -------------------------------- |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)                                 | Architecture and API reference   |
| [TEMPLATE_DEVELOPMENT.md](TEMPLATE_DEVELOPMENT.md)                       | Template customization guide     |
| [TEMPLATE_AUDIT.md](TEMPLATE_AUDIT.md)                                   | Template field audit tool        |
| [DATATABLES_IMPLEMENTATION.md](DATATABLES_IMPLEMENTATION.md)             | DataTables integration internals |
| [guides/THEME_CREATION.md](guides/THEME_CREATION.md)                     | Building HTML report themes      |
| [guides/CONCURRENCY_CONFIG.md](guides/CONCURRENCY_CONFIG.md)             | Concurrency configuration        |
| [concurrency/model.md](concurrency/model.md)                             | Concurrency model                |
| [concurrency/performance_tuning.md](concurrency/performance_tuning.md)   | Concurrency performance tuning   |
| [concurrency/troubleshooting.md](concurrency/troubleshooting.md)         | Concurrency troubleshooting      |
| [concurrency/thread_safety_audit.md](concurrency/thread_safety_audit.md) | Thread safety audit              |

### Testing

| File                                                                               | Topic                              |
| ---------------------------------------------------------------------------------- | ---------------------------------- |
| [TESTING.md](TESTING.md)                                                           | Test suite documentation           |
| [TESTING_GITHUB_NATIVE.md](TESTING_GITHUB_NATIVE.md)                               | Testing GitHub-native projects     |
| [testing/TEST_PREREQUISITES.md](testing/TEST_PREREQUISITES.md)                     | Test prerequisites and environment |
| [testing/TEST_WRITING_GUIDE.md](testing/TEST_WRITING_GUIDE.md)                     | Writing tests                      |
| [testing/PARALLEL_EXECUTION.md](testing/PARALLEL_EXECUTION.md)                     | Parallel test execution            |
| [testing/PARALLEL_EXECUTION_QUICK_REF.md](testing/PARALLEL_EXECUTION_QUICK_REF.md) | Parallel execution quick reference |
| [testing/PROPERTY_TESTING_OVERVIEW.md](testing/PROPERTY_TESTING_OVERVIEW.md)       | Property-based testing             |
| [testing/ENHANCED_ERRORS_GUIDE.md](testing/ENHANCED_ERRORS_GUIDE.md)               | Enhanced error messages            |

### Navigation

| File                     | Topic                         |
| ------------------------ | ----------------------------- |
| [INDEX.md](INDEX.md)     | This file                     |
| [README.md](README.md)   | Documentation conventions     |

---

**Ready to start?** → [Getting Started Guide](GETTING_STARTED.md)

**Need help?** → [FAQ](FAQ.md) | [Troubleshooting](TROUBLESHOOTING.md)

**Contributing?** → [Developer Guide](DEVELOPER_GUIDE.md)
