<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Table of Contents Feature

**Automatic navigation for long HTML and Markdown reports**

---

## Overview

The Table of Contents (TOC) feature automatically generates a navigation menu
at the top of HTML and Markdown reports, providing quick access to all visible
sections. This is especially useful for reports with hundreds of rows across
multiple sections.

**Schema Version:** 1.2.0+

---

## Features

- ✅ **Automatic Generation** - TOC is built dynamically based on visible
  sections
- ✅ **Smart Detection** - Only includes sections with data
- ✅ **Configuration Aware** - Respects section enable/disable flags
- ✅ **Clean Formatting** - Plain text titles without emoji
- ✅ **Multi-Format Support** - Available in HTML and Markdown reports
- ✅ **Enabled by Default** - Works out of the box
- ✅ **Easy to Disable** - Single configuration flag

---

## Quick Start

### Default Behavior (Enabled)

By default, all reports generated with schema version 1.2.0+ include a table
of contents:

```bash
lf-releng-project-reporting generate --project my-project --repos-path ./repos
```

The generated `report.html` and `report.md` will include a TOC after the
header.

### Disable TOC

To disable the table of contents, add this to your project configuration:

```yaml
# configuration/my-project.yaml
render:
  table_of_contents: false
```

---

## Configuration

### Location

The TOC setting is in the `render` section of your configuration file:

```yaml
render:
  # Enable or disable table of contents in reports
  table_of_contents: true  # default: true
```

### Why in `render` and not `output.include_sections`?

The TOC is a **rendering feature** that affects how content is displayed, not
a **content section** itself. Therefore:

- `output.include_sections.*` - Controls which data sections to include
  (Contributors, Organizations, etc.)
- `render.table_of_contents` - Controls whether to show navigation for those
  sections

---

## How It Works

The TOC is generated intelligently based on:

1. **Configuration flags** - Is the section enabled in
   `output.include_sections`?
2. **Data availability** - Does the section have data to display?
3. **Template logic** - Does the section's template render?

### Example Logic Flow

```text
┌─────────────────────────────────────────────┐
│ For each potential section:                │
├─────────────────────────────────────────────┤
│ 1. Check config.include_sections.{section} │
│ 2. Check if data exists for section        │
│ 3. If BOTH true → Add to TOC               │
└─────────────────────────────────────────────┘
```

This ensures the TOC **exactly matches** what sections are actually rendered
in the report.

---

## Section Mapping

The TOC uses plain text titles (no emoji) for clean navigation:

<!-- markdownlint-disable MD013 -->

<!-- markdownlint-disable MD060 -->

| Section        | Config Key      | TOC Title                 | Report Heading            |
| -------------- | --------------- | ------------------------- | ------------------------- |
| Global Summary | `summary`       | Global Summary            | 📈 Global Summary         |
| Repositories   | `repositories`  | Gerrit Projects           | All Repositories          |
| Contributors   | `contributors`  | Top Contributors          | Top Contributors          |
| Organizations  | `organizations` | Top Organizations         | Top Organizations         |
| Features       | `features`      | Repository Feature Matrix | Repository Feature Matrix |
| Workflows      | `workflows`     | Deployed CI/CD Jobs       | Deployed CI/CD Jobs       |
| Orphaned Jobs  | `orphaned_jobs` | Orphaned Jenkins Jobs     | Orphaned Jenkins Jobs     |
| Time Windows   | N/A             | Time Windows              | Time Windows              |

<!-- markdownlint-enable MD060 -->

<!-- markdownlint-enable MD013 -->

---

## HTML Output

In HTML reports, the TOC appears as a navigation section after the header:

```html
<header class="page-header">
    <h1>ONAP</h1>
    <p>Generated: December 04, 2025 at 07:16 UTC</p>
    <p>Schema Version: 1.2.0</p>
</header>

<nav id="table-of-contents" class="toc report-section">
    <h2>Table of Contents</h2>
    <ul class="toc-list">
        <li class="toc-item"><a href="#summary">Global Summary</a></li>
        <li class="toc-item"><a href="#repositories">Gerrit Projects</a></li>
        <li class="toc-item"><a href="#contributors">Top Contributors</a></li>
        <!-- ... more sections ... -->
    </ul>
</nav>

<main id="main-content">
    <section id="summary">...</section>
    <!-- ... sections ... -->
</main>
```

### Styling

The TOC uses standard CSS classes that can be customized via your theme:

- `.toc` - Container for the TOC navigation
- `.toc-list` - The `<ul>` element containing links
- `.toc-item` - Each `<li>` item
- `.toc-link` - Each anchor link

---

## Markdown Output

In Markdown reports, the TOC appears as a bulleted list with anchor links:

```markdown
# ONAP

**Generated:** December 04, 2025 at 07:16 UTC
**Schema Version:** 1.2.0

---

## Table of Contents

- [Global Summary](#summary)
- [Gerrit Projects](#repositories)
- [Top Contributors](#contributors)
- [Top Organizations](#organizations)
- [Repository Feature Matrix](#features)
- [Deployed CI/CD Jobs](#workflows)

---

## Global Summary
...
```

---

## Examples

### Example 1: Full Report with TOC

Default configuration with all sections enabled:

```yaml
# configuration/my-project.yaml
project: my-project

output:
  include_sections:
    contributors: true
    organizations: true
    repositories: true
    features: true
    workflows: true
    orphaned_jobs: true

render:
  table_of_contents: true  # default, can omit
```

**Result:** TOC shows all 7-8 sections (depending on data availability)

---

### Example 2: Minimal Report with TOC

Only summary and repositories:

```yaml
# configuration/minimal-project.yaml
project: minimal-project

output:
  include_sections:
    contributors: false
    organizations: false
    repositories: true
    features: false
    workflows: false
    orphaned_jobs: false

render:
  table_of_contents: true
```

**Result:** TOC shows only 2 sections (Global Summary, Gerrit Projects)

---

### Example 3: Disable TOC

For single-page or short reports:

```yaml
# configuration/short-project.yaml
project: short-project

render:
  table_of_contents: false
```

**Result:** No TOC is generated

---

## Migration Guide

### Upgrading to Schema 1.2.0

Projects using schema version 1.1.0 or earlier should update:

```yaml
# Old configuration
schema_version: "1.1.0"

# New configuration
schema_version: "1.2.0"
```

**Behavior change:** TOC will now appear by default. To maintain previous
behavior (no TOC):

```yaml
schema_version: "1.2.0"

render:
  table_of_contents: false  # Explicitly disable
```

### No Changes Required for Most Projects

Since `table_of_contents: true` is the default, most projects do not need to
update their configuration files. Simply update the schema version and the TOC
will automatically appear.

---

## Accessibility

The TOC improves report accessibility:

- **Keyboard Navigation** - All TOC links are keyboard accessible
- **Screen Readers** - Semantic HTML5 `<nav>` element used
- **Skip Links** - Works alongside existing skip-to-content links
- **Clear Labels** - Plain text without emoji for clarity

---

## Performance

The TOC has minimal performance impact:

- **Build Time** - ~1-5ms added to context generation
- **HTML Size** - ~200-500 bytes per TOC entry
- **Browser Rendering** - Negligible (simple list of links)

For reports with 1000+ repositories, the TOC is especially valuable as it
allows instant navigation without scrolling through hundreds of table rows.

---

## Troubleshooting

### TOC Not Appearing

**Problem:** TOC is not showing in generated reports.

**Solutions:**

1. Check schema version is 1.2.0 or higher:

   ```yaml
   schema_version: "1.2.0"
   ```

2. Verify TOC is not explicitly disabled:

   ```yaml
   render:
     table_of_contents: true  # Should be true or omitted
   ```

3. Ensure at least one section has data to display

---

### TOC Shows Unexpected Sections

**Problem:** TOC includes sections that should be disabled.

**Solution:** Verify section is disabled in configuration:

```yaml
output:
  include_sections:
    contributors: false  # Should be false to exclude
```

---

### TOC Links Not Working

**Problem:** Clicking TOC links does not navigate to sections (HTML only).

**Cause:** Section IDs might have been modified in custom templates.

**Solution:** Ensure section IDs match the TOC anchors:

| TOC Anchor       | Required Section ID            |
| ---------------- | ------------------------------ |
| `#summary`       | `<section id="summary">`       |
| `#repositories`  | `<section id="repositories">`  |
| `#contributors`  | `<section id="contributors">`  |
| `#organizations` | `<section id="organizations">` |
| `#features`      | `<section id="features">`      |
| `#workflows`     | `<section id="workflows">`     |
| `#orphaned-jobs` | `<section id="orphaned-jobs">` |
| `#time-windows`  | `<section id="time-windows">`  |

---

## Advanced Customization

### Custom Styling (HTML)

Override TOC styles in your custom theme:

```css
/* themes/custom/theme.css */

.toc {
    background-color: #f5f5f5;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 1rem;
    margin: 2rem 0;
}

.toc-list {
    list-style-type: none;
    padding-left: 0;
}

.toc-item {
    padding: 0.25rem 0;
}

.toc-link {
    color: #0066cc;
    text-decoration: none;
    font-weight: 500;
}

.toc-link:hover {
    text-decoration: underline;
}
```

---

## FAQs

### Q: Can I customize TOC section titles?

**A:** Not without modifying templates. The TOC titles are defined in the
context builder (`src/lf_releng_project_reporting/rendering/context/`) and
match standard section names.

### Q: Can I reorder sections in the TOC?

**A:** The TOC order matches the report section order, which is fixed in the
base template. Custom ordering would require template modifications.

### Q: Does TOC work with custom sections?

**A:** Custom sections need to be added to both:

1. The TOC context builder (`_build_toc_context()` method)
2. The base template (include the section and assign it an ID)

### Q: Can I have a TOC in JSON output?

**A:** No. JSON output is data-only. The TOC is a presentation feature for
human-readable formats (HTML/Markdown).

### Q: Will TOC appear in GitHub Pages?

**A:** Yes! The TOC is part of the generated HTML, so it will appear in
GitHub Pages deployments.

---

## Related Documentation

- [Configuration Guide](CONFIGURATION.md) - Full configuration options
- [Configuration Merging](CONFIGURATION_MERGING.md) - How defaults and
  overrides work
- [Developer Guide](DEVELOPER_GUIDE.md) - Extending templates and context
  builders

---

## Changelog

### Version 1.2.0 (2025-12-06)

- ✨ **New Feature:** Table of Contents for HTML and Markdown reports
- 📝 Schema version bumped to 1.2.0
- ⚙️ New configuration option: `render.table_of_contents` (default: `true`)
- 🎨 New template components: `table_of_contents.html.j2` and
  `table_of_contents.md.j2`
- 🧠 Smart section detection based on config and data availability

---

## Support

For questions or issues with the Table of Contents feature:

1. Verify schema version is 1.2.0+
2. Check configuration syntax
3. Review this documentation
4. File an issue with:
   - Configuration file
   - Generated report (HTML/MD)
   - Expected vs. actual TOC

---

*Generated by Repository Reporting System*
*Schema Version: 1.2.0*
