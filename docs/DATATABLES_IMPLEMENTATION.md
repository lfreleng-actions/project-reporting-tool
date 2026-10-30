<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# DataTables Implementation

## Overview

This document describes how the HTML reports integrate the
Simple-DataTables library to add sorting, searching, and pagination to
tables. For template authors' usage, see the
[DataTables Usage Guide](DATATABLES_USAGE.md).

## Components

### 1. DataTables Support Macro Template

**File**: `src/templates/html/components/datatables_support.html.j2`

Reusable Jinja2 macros for DataTables integration:

- `datatables_css(config)`: Injects the pinned Simple-DataTables CSS
  from the CDN, with Subresource Integrity
- `datatables_js(config)`: Injects JavaScript library and
  initialization code
- `datatables_classes(config, ...)`: Helper macro to generate CSS class
  strings

Each macro takes the report configuration as an explicit argument,
because an imported Jinja2 macro does not see its caller's variables.

**Key Features**:

- Conditional loading based on configuration
- Per-table feature control via CSS classes
- Performance optimization (skips small tables)
- Configurable labels and pagination options

### 2. Base Template

**File**: `src/templates/html/base.html.j2`

The main HTML template wires in DataTables support:

- Import datatables_support macros
- Inject CSS in `<head>` section
- Inject JavaScript before `</body>` tag

### 3. Theme CSS

**Files**:

- `src/themes/default/theme.css`
- `src/themes/dark/theme.css`
- `src/themes/minimal/theme.css`

Each theme styles the DataTables controls:

- Search input styling
- Pagination controls
- Sorting indicators
- Mobile responsive layouts
- Print-friendly styles

### 4. Data Table Component

**File**: `src/templates/html/components/data_table.html.j2`

The data table component accepts these DataTables parameters and
generates the matching CSS classes through the helper macro:

- `enable_datatables`
- `enable_search`
- `enable_pagination`
- `enable_sorting`

### 5. Section Templates

Section templates enable DataTables with the features suited to each
table:

- **Repositories** (`repositories.html.j2`): Full features (sort,
  search, pagination)
- **Contributors** (`contributors.html.j2`): Full features
- **Organizations** (`organizations.html.j2`): Sort only
- **Features** (`features.html.j2`): Sort only
- **Workflows** (`workflows.html.j2`): Sort only
- **Orphaned Jobs** (`orphaned_jobs.html.j2`): Sort only

### 6. Configuration Context

**File**: `src/rendering/context/sections.py`

The template context carries the `html_tables` configuration:

- `sortable`: Global enable/disable
- `searchable`: Default search setting
- `pagination`: Default pagination setting
- `entries_per_page`: Default page size
- `page_size_options`: Available page sizes
- `min_rows_for_sorting`: Performance threshold

### 7. Tests

**File**: `tests/test_datatables_integration.py`

Integration tests verify:

- Macro file exists
- Theme CSS includes DataTables styles
- Base template imports and uses macros
- Section templates use correct CSS classes
- Component supports DataTables parameters

## CSS Class System

### CSS Classes

| Class              | Purpose                    |
| ------------------ | -------------------------- |
| `dt-enabled`       | Enable DataTables on table |
| `dt-no-search`     | Disable search feature     |
| `dt-no-pagination` | Disable pagination feature |
| `dt-no-sort`       | Disable sorting feature    |

### Usage Examples

```jinja2
<!-- Full features -->
<table class="dt-enabled">

<!-- Sort only -->
<table class="dt-enabled dt-no-search dt-no-pagination">

<!-- No DataTables -->
<table>
```

## Configuration

DataTables is configured in `configuration/default.yaml`:

```yaml
html_tables:
  sortable: true
  searchable: true
  pagination: true
  entries_per_page: 20
  page_size_options: [20, 50, 100, 200]
  min_rows_for_sorting: 3
```

## Architecture

```text
┌─────────────────────────────────────────────┐
│ configuration/default.yaml                  │
│ - html_tables configuration                 │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ src/rendering/context/sections.py           │
│ - Builds config context with html_tables    │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ src/templates/html/base.html.j2             │
│ - Imports datatables_support macros         │
│ - Calls datatables_css() in <head>          │
│ - Calls datatables_js() before </body>      │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ Section Templates                           │
│ - Use dt-enabled class on tables            │
│ - Add dt-no-* classes to disable features   │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ Simple-DataTables Library                   │
│ - Initializes tables with dt-enabled class  │
│ - Respects per-table feature flags          │
│ - Skips tables < min_rows_for_sorting       │
└─────────────────────────────────────────────┘
```

## Table Feature Matrix

The templates apply these features to each table type:

<!-- markdownlint-disable MD060 -->

| Table          | Search | Sort | Pagination | Rationale       |
| -------------- | ------ | ---- | ---------- | --------------- |
| Repositories   | ✅     | ✅   | ✅         | Large dataset   |
| Contributors   | ✅     | ✅   | ✅         | Large dataset   |
| Organizations  | ❌     | ✅   | ❌         | Small dataset   |
| Feature Matrix | ❌     | ✅   | ❌         | Comparison view |
| CI/CD Jobs     | ❌     | ✅   | ❌         | Visual scan     |
| Orphaned Jobs  | ❌     | ✅   | ❌         | Small dataset   |
| Summary Stats  | ❌     | ❌   | ❌         | Metadata only   |

<!-- markdownlint-enable MD060 -->

## Pinned CDN Assets

Reports load Simple-DataTables from jsDelivr at an exact version, and
each `<link>` and `<script>` tag carries an `integrity` hash and
`crossorigin="anonymous"`. The browser refuses a file whose bytes do
not match the hash, so a compromised or changed CDN file cannot alter
a published report. `src/rendering/assets.py` holds the version, URLs
and hashes; `TemplateRenderer` exposes them to templates as Jinja2
globals.

### Bumping the version

Dependabot does not track CDN URLs, so bump the library by hand:

1. Set `DATATABLES_VERSION` in `src/rendering/assets.py` to the new
   release.
2. Download the release from npm and compute both hashes from the
   package contents:

   ```bash
   npm pack simple-datatables@<version>
   tar xzf simple-datatables-<version>.tgz
   for f in package/dist/style.css package/dist/umd/simple-datatables.js; do
     echo "$f sha384-$(openssl dgst -sha384 -binary "$f" | base64 -w0)"
   done
   ```

3. Confirm jsDelivr serves the same bytes, for example
   `curl -sL https://cdn.jsdelivr.net/npm/simple-datatables@<version>/dist/style.css | openssl dgst -sha384 -binary | base64 -w0`.
4. Update `DATATABLES_CSS_SRI` and `DATATABLES_JS_SRI`, then render a
   report and check the tables still sort, search and paginate.

## Performance Characteristics

- **Library Size**: Simple-DataTables is ~30KB minified (loaded from CDN)
- **Initialization**: < 100ms for tables with 1000 rows
- **Memory**: Minimal overhead, client-side only
- **Automatic Skipping**: Tables with < 3 rows skip DataTables entirely

## Browser Compatibility

Supported browsers:

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Accessibility

- Keyboard navigation fully supported
- ARIA labels for screen readers
- Semantic HTML maintained
- Focus management for controls

## Known Limitations

1. **Client-side only**: Not suitable for extremely large datasets
   (10k+ rows)
2. **CDN dependency**: Requires internet connection for library loading
3. **JavaScript required**: Gracefully degrades to plain table if JS
   disabled

## References

- [Simple-DataTables
  GitHub](https://github.com/fiduswriter/Simple-DataTables)
- [DataTables Usage Guide](DATATABLES_USAGE.md)
