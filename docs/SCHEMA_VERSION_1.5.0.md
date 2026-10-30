<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Schema Version 1.5.0 - GitHub Native Project Support

> Schema version changelog for GitHub-native project support

**Version:** 1.5.0
**Previous Version:** 1.4.0
**Date:** January 2025
**Status:** ✅ Implemented

---

## Overview

Schema version 1.5.0 adds support for **GitHub-native projects** that do not have a Gerrit backend. This enhancement allows the lf-releng-project-reporting to analyze and report on projects hosted entirely on GitHub, while maintaining full backward compatibility with existing Gerrit-based projects.

---

## Key Changes

### 1. Project Type Detection

Added automatic project type detection based on configuration:

- **Gerrit projects**: Have `gerrit.host` configured
- **GitHub-native projects**: No `gerrit.host`, rely on `GITHUB_ORG` environment variable

### 2. Configuration Schema Changes

#### New Optional Fields

```yaml
gerrit:
  enabled: auto  # Auto-set based on host presence
  host: ""       # OPTIONAL for GitHub-native projects
```

#### Behavior Changes

- `gerrit.host` is now **optional** (was required in previous versions)
- `gerrit.enabled` is automatically set to `false` when `host` is empty
- GitHub organization is derived from `GITHUB_ORG` environment variable for GitHub-native projects

### 3. Rendering Context Enhancements

#### New Context Variables

Added to project context for templates:

```python
{
  "project_type": "github",  # or "gerrit"
  "terminology": {
    "repository": "Repository",        # or "Gerrit Project"
    "repositories": "Repositories",    # or "Gerrit Projects"
    "source_system": "GitHub",         # or "Gerrit"
  }
}
```

#### URL Construction

Repository URLs now built based on project type:

- **Gerrit**: `https://gerrit.onap.org/r/admin/repos/oom,general`
- **GitHub**: `https://github.com/opennetworkinglab/aether`

### 4. Template Updates

Updated terminology in all templates to use context variables:

**Before (hardcoded):**

```jinja2
## 📊 Gerrit Projects
| Gerrit Project | Commits | LOC |
```

**After (dynamic):**

```jinja2
## 📊 {{ project.terminology.repositories }}
| {{ project.terminology.repository }} | Commits | LOC |
```

---

## Data Structure Compatibility

### No Breaking Changes

The underlying data structure remains **100% compatible** with previous schema versions:

- Field names unchanged (`gerrit_project`, `gerrit_host`, `gerrit_url`)
- JSON schema structure identical
- Field semantics remain consistent

### Semantic Field Usage

For GitHub-native projects, existing fields are reused semantically:

| Field                | Gerrit Project           | GitHub Project  |
| -------------------- | ------------------------ | --------------- |
| `gerrit_project`     | Gerrit project path      | Repository name |
| `gerrit_host`        | Gerrit server            | GitHub org name |
| `gerrit_url`         | Gerrit admin URL         | GitHub repo URL |
| `gerrit_path_prefix` | Path prefix (e.g., "/r") | Empty or "/"    |

---

## PROJECTS_JSON Configuration

### Gerrit-Based Project (Existing)

```json
{
  "project": "ONAP",
  "slug": "onap",
  "gerrit": "gerrit.onap.org",
  "jenkins": "jenkins.onap.org",
  "github": "onap"
}
```

### GitHub-Native Project (New)

```json
{
  "project": "Aether",
  "slug": "aether",
  "github": "opennetworkinglab"
}
```

**Key Differences:**

- ✅ No `gerrit` field
- ✅ Required `github` field (GitHub org name)
- ✅ Optional `jenkins` field (if ci-management exists)

---

## Migration Guide

### For Existing Projects

**No action required.** All existing Gerrit-based projects continue to work unchanged.

### For New GitHub-Native Projects

1. Add project to `PROJECTS_JSON` with `github` field
2. Omit `gerrit` field
3. Run reporting tool normally
4. Reports will show "Repositories" instead of "Gerrit Projects"

### Example Workflow Update

```yaml
# GitHub Actions workflow matrix
matrix:
  include:
    # Existing Gerrit project
    - project: "ONAP"
      slug: "onap"
      gerrit: "gerrit.onap.org"
      jenkins: "jenkins.onap.org"
      github: "onap"

    # New GitHub-native project
    - project: "Aether"
      slug: "aether"
      gerrit: ""  # Empty or omit
      jenkins: ""
      github: "opennetworkinglab"
```

---

## Implementation Details

### Files Modified

**Configuration & Validation:**

- `src/config/validator.py` - Bumped schema version to 1.5.0
- `src/lf_releng_project_reporting/main.py` - Updated SCHEMA_VERSION constant
- `configuration/default.yaml` - Updated schema_version

**Core Logic:**

- `src/lf_releng_project_reporting/config.py` - Enhanced auto-derivation logic
- `src/rendering/context.py` - Added project type detection and terminology

**Templates (4 files):**

- `src/templates/markdown/sections/summary.md.j2`
- `src/templates/markdown/sections/repositories.md.j2`
- `src/templates/html/sections/summary.html.j2`
- `src/templates/html/sections/repositories.html.j2`

**Testing:**

- `testing/projects.json` - Added Aether configuration
- `testing/local-testing.sh` - Added GitHub cloning support

---

## Validation & Testing

### Schema Version Check

```python
from config.validator import ConfigValidator

validator = ConfigValidator()
assert validator.CURRENT_SCHEMA_VERSION == "1.5.0"
assert "1.5.0" in validator.COMPATIBLE_SCHEMA_VERSIONS
```

### Template Audit

```bash
python scripts/audit_templates.py
# Should pass with no errors
```

### Integration Test

```bash
# Test GitHub-native project
cd testing
./local-testing.sh --project Aether

# Verify output
ls reports/Aether/
# Should contain: report.html, report.md, report_raw.json
```

---

## Backward Compatibility

### Guaranteed Compatibility

✅ **Data Structure**: No changes to JSON schema
✅ **Field Names**: All existing fields preserved
✅ **API**: No breaking changes
✅ **Templates**: Backward compatible (variables work for both types)
✅ **Existing Projects**: Continue to work unchanged

### Compatibility Matrix

<!-- markdownlint-disable MD060 -->

| Version       | Gerrit Projects | GitHub Projects  | Notes           |
| ------------- | --------------- | ---------------- | --------------- |
| 1.0.0 - 1.4.0 | ✅ Supported    | ❌ Not supported | Original schema |
| 1.5.0         | ✅ Supported    | ✅ Supported     | New capability  |

<!-- markdownlint-enable MD060 -->

---

## Known Limitations

### INFO.yaml Reporting

INFO.yaml data remains Gerrit-centric and is **not applicable** to GitHub-native projects:

- INFO.yaml data filtered by `gerrit_server`
- GitHub-native projects will not have INFO.yaml entries
- This is **expected behavior** and documented

### Jenkins Integration

Jenkins job attribution works for both project types:

- Gerrit projects: Standard JJB attribution
- GitHub projects: Can reference Gerrit ci-management repo
- Requires ci-management repository URL in configuration

---

## Future Enhancements

Potential future additions (not in 1.5.0):

- [ ] GitHub-specific metrics (PRs, Issues, Stars)
- [ ] Enhanced GitHub Actions workflow reporting
- [ ] GitHub org auto-discovery (list all repos via API)
- [ ] GitHub-native INFO.yaml equivalent
- [ ] Mixed project type support in single report

---

## References

- [Configuration Guide](CONFIGURATION.md)
- [Template Development](TEMPLATE_DEVELOPMENT.md)

---

## Version History

| Version | Date    | Description                   |
| ------- | ------- | ----------------------------- |
| 1.5.0   | 2025-01 | GitHub-native project support |
| 1.4.0   | 2024-12 | Previous version              |
| 1.3.0   | 2024-11 | Total LOC metrics             |
| 1.2.0   | 2024-10 | Table of contents             |
| 1.1.0   | 2024-09 | Enhanced features             |
| 1.0.0   | 2024-08 | Initial schema                |

---

**Document Status:** ✅ Complete
**Schema Status:** ✅ Implemented
**Last Updated:** 2025-01-XX
