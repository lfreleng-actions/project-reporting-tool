<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2026 The Linux Foundation
-->

# Documentation

This directory documents the tool as it works today. Start at
[INDEX.md](INDEX.md), the single table of contents for every page here.

## Conventions

- **One page per topic.** Each feature, guide or reference has exactly
  one page. Before adding a page, check [INDEX.md](INDEX.md) for an
  existing one and extend that instead.
- **Edit in place.** When a change alters behaviour, update the page
  for that feature in the same pull request. Git history records what
  changed and when.
- **No dated status documents.** Do not add fix reports, completion
  summaries, implementation plans or changelogs for a single change.
  Put that context in the commit message and the pull request
  description, and move anything still true into the feature's page.
- **List every page in the index.** Add a new page to
  [INDEX.md](INDEX.md) in the same commit that creates it, and remove
  the entry when you delete the page.
