<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# DataTables Usage Guide

This guide explains how to use DataTables features in the reporting
system's HTML templates.

## Overview

The reporting system integrates
[Simple-DataTables](https://github.com/fiduswriter/Simple-DataTables),
a lightweight JavaScript library that adds sorting, searching, and
pagination to HTML tables.

## Quick Start

### Enable DataTables on a Table

Add the `dt-enabled` class to any table:

```jinja2
<table class="dt-enabled">
    <thead>
        <tr>
            <th>Column 1</th>
            <th>Column 2</th>
        </tr>
    </thead>
    <tbody>
        <!-- table rows -->
    </tbody>
</table>
```

This enables all DataTables features (sorting, searching, pagination)
using global configuration defaults.

### Disable Specific Features

Use additional CSS classes to disable features:

```jinja2
{#- Sorting only (no search or pagination) -#}
<table class="dt-enabled dt-no-search dt-no-pagination">
    ...
</table>

{#- No search, but keep sorting and pagination -#}
<table class="dt-enabled dt-no-search">
    ...
</table>
```

## CSS Classes Reference

| Class              | Purpose                         |
| ------------------ | ------------------------------- |
| `dt-enabled`       | Enable DataTables on this table |
| `dt-no-search`     | Disable search feature          |
| `dt-no-pagination` | Disable pagination feature      |
| `dt-no-sort`       | Disable sorting feature         |

## Using with data_table Component

The `data_table.html.j2` component supports DataTables through
parameters:

```jinja2
{% set columns = [
    {'key': 'name', 'label': 'Name'},
    {'key': 'count', 'label': 'Count', 'format': 'number'}
] %}
{% set rows = my_data %}

{#- Full DataTables features -#}
{% include 'html/components/data_table.html.j2' %}

{#- Disable specific features -#}
{% include 'html/components/data_table.html.j2'
    with enable_search=false, enable_pagination=false %}

{#- Completely disable DataTables -#}
{% include 'html/components/data_table.html.j2'
    with enable_datatables=false %}
```

### Component Parameters

- `enable_datatables` (bool): Enable/disable DataTables entirely
  (default: from config)
- `enable_search` (bool): Enable/disable search (default: from config)
- `enable_pagination` (bool): Enable/disable pagination
  (default: from config)
- `enable_sorting` (bool): Enable/disable sorting
  (default: from config)

## Configuration

DataTables behavior is controlled in `configuration/default.yaml`:

```yaml
html_tables:
  # Global enable/disable
  sortable: true

  # Feature defaults
  searchable: true
  pagination: true

  # Pagination settings
  entries_per_page: 20
  page_size_options: [20, 50, 100, 200]

  # Performance optimization
  min_rows_for_sorting: 3
```

The `min_rows_for_sorting` setting skips DataTables for tables with
fewer rows (default: 3).

## Performance Considerations

### Automatic Skipping

DataTables is skipped for tables with fewer than `min_rows_for_sorting`
rows (default: 3). This avoids overhead for small tables.

### Large Tables

For tables with 1000+ rows, DataTables performs well but consider:

1. **Disable features you don't need**: If users won't search, disable
   search
2. **Use appropriate page sizes**: Smaller page sizes improve rendering
3. **Consider server-side processing**: For 10k+ rows (future
   enhancement)

## Recommended Settings by Table Type

Based on UX best practices:

<!-- markdownlint-disable MD060 -->

| Table Type           | Search | Sort | Pagination | Rationale                                        |
| -------------------- | ------ | ---- | ---------- | ------------------------------------------------ |
| **All Repositories** | ✅     | ✅   | ✅         | Large dataset, users need to find specific repos |
| **Contributors**     | ✅     | ✅   | ✅         | Large dataset, users search by name              |
| **Organizations**    | ❌     | ✅   | ❌         | Small dataset, fits on one page                  |
| **Feature Matrix**   | ❌     | ✅   | ❌         | Comparison table, users want to see all at once  |
| **CI/CD Jobs**       | ❌     | ✅   | ❌         | Visual scanning preferred                        |
| **Summary Stats**    | ❌     | ❌   | ❌         | Small metadata table                             |

<!-- markdownlint-enable MD060 -->

## Examples from Templates

### Repositories (Full Features)

```jinja2
<table class="dt-enabled">
    <thead>
        <tr>
            <th>Gerrit Project</th>
            <th>Commits</th>
            <th>Contributors</th>
        </tr>
    </thead>
    <tbody>
        {% for repo in repositories.all %}
        <tr>
            <td>{{ repo.gerrit_project }}</td>
            <td>{{ repo.total_commits }}</td>
            <td>{{ repo.unique_contributors }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
```

### Feature Matrix (Sorting Only)

```jinja2
<table class="dt-enabled dt-no-search dt-no-pagination">
    <thead>
        <tr>
            <th>Gerrit Project</th>
            <th>Dependabot</th>
            <th>Pre-commit</th>
        </tr>
    </thead>
    <tbody>
        {% for repo in features.matrix %}
        <tr>
            <td>{{ repo.repo_name }}</td>
            <td>{{ '✅' if repo.features.dependabot else '❌' }}</td>
            <td>{{ '✅' if repo.features.pre_commit else '❌' }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
```

## Accessibility

DataTables maintains keyboard navigation and screen reader
compatibility:

- **Tab navigation**: Navigate through controls
- **Arrow keys**: Move through pagination
- **Enter/Space**: Activate controls
- **ARIA labels**: Announced by screen readers

## Print Support

DataTables controls (search, pagination) are hidden when printing,
ensuring clean printouts.

## Browser Support

Simple-DataTables supports all modern browsers:

- Chrome/Edge (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)

## Troubleshooting

### DataTables Not Appearing

1. Check that `html_tables.sortable: true` in configuration
2. Verify table has `dt-enabled` class
3. Ensure table has enough rows (>= `min_rows_for_sorting`)
4. Check browser console for JavaScript errors

### Features Not Disabled

Verify you're using the correct CSS classes:

- `dt-no-search` (not `no-search`)
- `dt-no-pagination` (not `no-pagination`)
- `dt-no-sort` (not `no-sort`)

### Styling Issues

1. Ensure theme CSS is loaded correctly
2. Check for custom CSS conflicts
3. Verify DataTables CSS is loaded from CDN

## Advanced Usage

### Using the Helper Macro

For complete control, use the `datatables_classes` helper macro:

```jinja2
{% import 'html/components/datatables_support.html.j2' as dt %}

<table class="{{ dt.datatables_classes(
    enable_search=false,
    enable_pagination=false,
    base_classes='my-custom-table'
) }}">
    ...
</table>
```

This generates:
`my-custom-table dt-enabled dt-no-search dt-no-pagination`

## Further Reading

- [Simple-DataTables
  Documentation](https://github.com/fiduswriter/Simple-DataTables)
- [DataTables Integration
  Proposal](DATATABLES_INTEGRATION_PROPOSAL.md)
- [Template Development Guide](../README.md)
