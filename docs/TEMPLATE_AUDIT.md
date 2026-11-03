<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Template Audit Tool

**Location:** `scripts/audit_templates.py`
**Purpose:** Prevent template rendering errors by auditing field accesses

---

## Overview

The template audit script performs a comprehensive analysis of all Jinja2 templates to ensure they won't fail at runtime due to missing fields. It compares what templates expect against what the context builders actually provide.

This is essential for maintaining template correctness, especially after:

- Modifying templates
- Updating context builders
- Refactoring data structures
- Adding new features

---

## Usage

### Basic Usage

```bash
python scripts/audit_templates.py
```text

### Exit Codes

- `0` - Success (no critical issues)
- `1` - Failure (missing fields detected)

### CI/CD Integration

```yaml
# Add to GitHub Actions workflow
- name: Audit Templates
  run: python scripts/audit_templates.py
```text

---

## What It Does

### 1. Template Field Extraction

Scans all `.j2` files and extracts field accesses using patterns:

```python
# Detects patterns like:
summary.active_count
org.name
contributor.total_commits
repo.gerrit_project
```text

### 2. Context Analysis

Analyzes `src/lf_releng_project_reporting/rendering/context/` to extract:

- Top-level fields returned by each context builder
- Fields in list items (e.g., fields in each repository object)

### 3. Comparison

Compares template expectations against context reality:

- **Missing fields** → ❌ Will cause runtime errors
- **Extra fields** → ⚠️ Unused but safe

---

## Output Sections

### Section 1: Template Field Access Audit

Shows all field accesses found in each template:

```text
📄 html/sections/summary.html.j2
  summary:
    - active_count
    - current_count
    - repositories_analyzed
```text

### Section 2: Context Builder Analysis

Shows what each context builder provides:

```text
SUMMARY CONTEXT (_build_summary_context)

  Top-level fields (20):
    ✓ active_count
    ✓ current_count
    ✓ repositories_analyzed
```text

### Section 3: Field Mismatch Report

Identifies problems:

```text
❌ CONTRIBUTOR ITEMS

  MISSING (template expects but context doesn't provide):
     - total_lines_added
     - delta_loc

  ℹ️  EXTRA (context provides but template doesn't use):
     - email
```text

---

## Understanding Results

### ✅ No Issues

```text
✅ No critical issues found!
   All template expectations are met by context builders.
```text

**Action:** None required. Templates are safe.

---

### ⚠️ Extra Fields Only

```text
⚠️  ORGANIZATION ITEMS

  ℹ️  EXTRA (context provides but template doesn't use):
     - domain
     - net_lines
```text

**Action:** None required. Extra fields are safe—they're just not used by templates.

**Explanation:** Context builders often provide more data than templates use. This allows:

- Future template enhancements
- Optional features
- Data export in JSON format

---

### ❌ Missing Fields

```text
❌ CONTRIBUTOR ITEMS

  MISSING (template expects but context doesn't provide):
     - total_lines_added
     - delta_loc
```text

**Action:** **REQUIRED** - Fix immediately before deployment.

**Solutions:**

1. **Add field to context builder:**

   ```python
   # In src/lf_releng_project_reporting/rendering/context/
   def _build_contributors_context(self):
       # ...
       transformed = {
           "name": contrib.get("name"),
           "total_lines_added": lines_added,  # ← Add this
           "delta_loc": delta,                # ← Add this
       }
   ```

2. **OR remove field from template:**

   ```jinja
   {# Remove if not needed #}
   {{ contributor.total_lines_added }}
   ```

---

## Common Issues

### False Positives

Some fields appear as "MISSING" but are actually fine:

#### 1. Rendered Content Fields

```text
MISSING:
  - html
  - md
```text

**Explanation:** These are rendered content sections, not data fields. They're provided by the base template after sections are rendered.

**Action:** Ignore or add to `ignore_fields` in the script.

#### 2. Nested Access Patterns

```text
MISSING:
  - dependabot
  - g2g
```text

**Explanation:** Template accesses `repo_data.features.dependabot`, but script sees `features.dependabot`. The `features` object is provided in the item.

**Action:** Verify manually that the nested structure exists.

---

## Integration with Development Workflow

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running template audit..."
python scripts/audit_templates.py

if [ $? -ne 0 ]; then
    echo "❌ Template audit failed - commit aborted"
    echo "   Fix missing fields or update templates"
    exit 1
fi

echo "✅ Template audit passed"
```text

### Code Review Checklist

- [ ] Run `python scripts/audit_templates.py`
- [ ] Verify no new missing fields introduced
- [ ] Document any intentional extra fields
- [ ] Test with actual data if fields changed

### Before Production Deployment

```bash
# Verify templates are safe
python scripts/audit_templates.py || exit 1

# Run full test suite
pytest tests/

# Generate test report
python -m pytest tests/integration/test_rendering.py
```text

---

## Maintenance

### Updating the Script

When adding new context categories or field patterns:

```python
# In scripts/audit_templates.py

# Add new pattern
patterns = [
    (r'new_category\.(\w+)', 'new_category'),  # ← Add here
]

# Add new context builder
methods = {
    '_build_new_context': 'new_category',  # ← Add here
}

# Add category mapping
category_mapping = {
    'new_category': ('new_category', 'top_level'),  # ← Add here
}
```text

### Ignored Fields

Add fields to ignore (rendered content, not data):

```python
# Fields to ignore (these are rendered content, not data)
ignore_fields = {'html', 'md', 'count', 'percentage', 'state'}
```text

---

## Technical Details

### Pattern Matching

Uses regular expressions to find field accesses:

```python
r'summary\.(\w+)'      # Matches: summary.field_name
r'org\.(\w+)'          # Matches: org.field_name
r'contributor\.(\w+)' # Matches: contributor.field_name
```text

### Context Extraction

Parses `context.py` to find:

1. **Return dictionaries:**

   ```python
   return {
       "field1": value1,
       "field2": value2,
   }
   ```

2. **List item structures:**

   ```python
   items.append({
       "field_a": value_a,
       "field_b": value_b,
   })
   ```

### Limitations

1. **Dynamic field access** - Cannot detect:

   ```jinja
   {{ obj[variable_name] }}
   ```

2. **Computed fields** - Cannot verify:

   ```jinja
   {{ obj.field | filter }}
   ```

3. **Nested structures** - May report false positives for:

   ```jinja
   {{ obj.nested.deep.field }}
   ```

---

## Examples

### Example 1: Successful Audit

```bash
$ python scripts/audit_templates.py

Starting template field audit...

================================================================================
TEMPLATE FIELD ACCESS AUDIT
================================================================================

📄 html/sections/summary.html.j2
  summary:
    - active_count
    - repositories_analyzed

================================================================================
CONTEXT BUILDER ANALYSIS
================================================================================

SUMMARY:
  Top-level fields (20):
    ✓ active_count
    ✓ repositories_analyzed

================================================================================

✅ No critical issues found!
   Extra fields are safe - they're just unused.
```text

**Exit code:** 0

---

### Example 2: Missing Fields Detected

```bash
$ python scripts/audit_templates.py

Starting template field audit...

[... audit output ...]

================================================================================
❌ CONTRIBUTOR ITEMS
================================================================================

  MISSING (template expects but context doesn't provide):
     - total_lines_added

================================================================================
❌ CRITICAL ISSUES FOUND
================================================================================

Templates will fail at runtime!
Add missing fields to context builders in src/lf_releng_project_reporting/rendering/context/
```text

**Exit code:** 1

**Fix required before deployment!**

---

## Related Documentation

- [Template Development Guide](TEMPLATE_DEVELOPMENT.md)
- [Developer Guide](DEVELOPER_GUIDE.md)
- [Testing Guide](TESTING.md)

---

## Best Practices

1. **Run before commits** - Always audit after template changes
2. **Include in CI** - Fail builds on missing fields
3. **Document extras** - Comment why extra fields exist
4. **Test with data** - Verify with actual report generation
5. **Review carefully** - Some warnings are false positives

---

## Troubleshooting

### Script Reports Missing Fields But Templates Work

**Cause:** False positive due to:

- Nested field access
- Rendered content fields
- Dynamic lookups

**Solution:**

1. Verify manually that field exists in context
2. Add to `ignore_fields` if it's rendered content
3. Update pattern matching if it's a new pattern

### Script Doesn't Detect Actual Missing Field

**Cause:** Field accessed through variable or filter

**Solution:**

1. Check template manually
2. Test with actual data
3. Add explicit checks in integration tests

### Script Shows Too Many Extra Fields

**Cause:** Context provides comprehensive data for JSON export

**Solution:**

- This is expected and safe
- Extra fields allow future enhancements
- Only worry about MISSING fields

---

**Last Updated:** January 12, 2026
**Maintainer:** Release Engineering Team
