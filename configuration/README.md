<!--
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Configuration Files

## Overview

This is the reporting tool's single configuration directory and the
default value of `--config-dir`. It holds:

- `default.yaml`: the base configuration merged under every project,
  and the template to copy when creating a project configuration
- `organizational_domains.yaml`: email domain extraction rules
- One file per project, such as `onap.yaml`

The built wheel ships `default.yaml` inside the package as
`lf_releng_project_reporting/templates/default.yaml`, so an installed
copy can recover it with `importlib.resources`.

## File Naming Convention

Configuration files should use **simple, lowercase names without spaces**:

- ✅ `lfbroadband.yaml`
- ✅ `onap.yaml`
- ✅ `opendaylight.yaml`
- ❌ `LF Broadband.yaml` (avoid spaces)
- ❌ `lf-broadband.yaml` (avoid hyphens)

## Project Identifier Matching

The configuration system matches projects by the `project` field **inside** the YAML file, not by the filename. This allows:

1. **Simple filenames**: Use lowercase, no spaces (e.g., `lfbroadband.yaml`)
2. **Flexible project names**: Support spaces and capitals in the project identifier (e.g., `project: LF Broadband`)

### Example

**File:** `configuration/lfbroadband.yaml`

```yaml
project: LF Broadband  # This is the identifier used for matching

gerrit:
  enabled: true
  host: "gerrit.lfbroadband.org"
```

When the tool runs with `--project "LF Broadband"`, it will:

1. Scan all `.yaml` files in this directory
2. Parse each file and check the `project` field
3. Load `lfbroadband.yaml` because `project: LF Broadband` matches

## Special Configuration Files

The following files are **NOT** project configurations and are skipped during project matching:

- `default.yaml` - Default settings inherited by all projects
- `organizational_domains.yaml` - Domain extraction rules
- `test-*.yaml` - Test configurations
- `README.md` - This file

## Configuration Hierarchy

1. **default.yaml** - Loaded first, provides baseline configuration
2. **Project-specific config** - Merged with defaults, overrides default values
3. **Runtime arguments** - Command-line arguments override both

## Creating a New Project Configuration

1. **Create the file** with a simple lowercase name:

   ```bash
   touch configuration/myproject.yaml
   ```

2. **Set the project identifier** at the top:

   ```yaml
   project: My Project Name
   ```

3. **Override only what you need**:

   ```yaml
   project: My Project

   jenkins:
     enabled: true
     host: "jenkins.myproject.org"
     allow_http_fallback: true  # If needed for SSL issues
   ```

4. **Test the configuration**:

   ```bash
   python -m lf_releng_project_reporting.main --project "My Project" --validate-only
   ```

## Common Configuration Options

### Jenkins with HTTP Fallback

For Jenkins servers with SSL certificate issues:

```yaml
jenkins:
  enabled: true
  host: "jenkins.example.org"
  allow_http_fallback: true  # Enable HTTP fallback for SSL issues
```

⚠️ **Security Warning**: Only enable `allow_http_fallback` for trusted internal servers.

### Custom Gerrit Configuration

```yaml
gerrit:
  enabled: true
  host: "gerrit.example.org"
  base_url: "https://gerrit.example.org/custom-path"
  timeout: 60.0
```

### JJB Attribution

For custom Jenkins Job Builder configurations:

```yaml
jjb_attribution:
  enabled: true
  url: "https://gerrit.example.org/ci-management"
  branch: master
  cache_dir: /tmp
```

### G2G (GitHub2Gerrit) Custom Workflow Detection

To customize which workflow files are checked for GitHub2Gerrit synchronization:

```yaml
features:
  enabled:
    - g2g

  g2g:
    workflow_files:
      - "github2gerrit.yaml"
      - "call-github2gerrit.yaml"
      - "sync-to-gerrit.yaml"        # Custom workflow name
      - "custom-gerrit-mirror.yaml"  # Another custom name
```

**Default Behavior**: If not specified, the tool checks for `github2gerrit.yaml` and `call-github2gerrit.yaml`.

**Custom Configuration**: Projects can specify their own workflow filenames. If **any** of the listed workflows exist in `.github/workflows/`, the G2G feature is marked as present (✅) in the report.

## Validation

All configuration files are validated against the schema. To check if a configuration is valid:

```bash
python -m lf_releng_project_reporting.main --project "Your Project" --validate-only
```

## See Also

- `default.yaml` - Default configuration with all available options
- `organizational_domains.yaml` - Email domain extraction rules
- [Configuration Schema Documentation](../docs/configuration-schema.md)
