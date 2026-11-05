<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Job Attribution Test Fixtures

This directory contains test fixtures extracted from production report data for testing
the Jenkins job attribution logic.

## Purpose

These fixtures serve three purposes:

1. **Regression Protection** - Ensure changes to the job matching algorithm don't break
   existing functionality for projects like ONAP and OpenDaylight
2. **Feature Verification** - Define expected behavior for new patterns (like LF Broadband)
3. **Living Documentation** - Document the job naming patterns that are supported

## Data Source

Fixtures are extracted from actual production reports: the `report_raw.json` file in the
`raw-data-<slug>` workflow artifact that each `reporting-production.yaml` run uploads.

The extraction process pulls real job-to-project mappings from the report artifacts,
providing realistic test data that reflects actual usage patterns.

## Files

### `production_data.json`

The main fixture file containing:

- **`_metadata`** - Information about when and how fixtures were extracted
- **`onap`** - Known-working mappings from ONAP (prefix-based patterns)
- **`lfbroadband`** - Expected mappings for LF Broadband (suffix/infix patterns)
- **`job_naming_patterns`** - Documentation of supported patterns with examples
- **`negative_test_cases`** - Cases that should NOT match (prevent false positives)

## Job Naming Patterns

### Prefix-Based (ONAP, OpenDaylight)

```text
Pattern: {project-name}-{job-type}-{stream}
Example: aai-babel-maven-verify-master -> aai/babel
```

### Suffix with Underscore (LF Broadband)

```text
Pattern: {job-type}_{project-name}
Example: docker-publish_bbsim -> bbsim
```

### Infix Verify Pattern (LF Broadband)

```text
Pattern: verify_{project-name}_{job-type}
Example: verify_aaa_maven-test -> aaa
```

## Updating Fixtures

To update fixtures with new production data:

```bash
# Download raw-data artifacts from recent production runs (needs GITHUB_TOKEN)
bash .github/scripts/download-artifacts.sh reporting-production.yaml /tmp/raw-data 7

# Each run lands in /tmp/raw-data/run-<id>/raw-data-<slug>/report_raw.json,
# for example raw-data-onap and raw-data-lfbroadband

# Run extraction script (if available) or manually update production_data.json
```

## Test Coverage

The associated test file (`tests/unit/test_job_attribution.py`) uses these fixtures to run:

| Test Class                     | Description                | Expected Result        |
| ------------------------------ | -------------------------- | ---------------------- |
| `TestONAPPrefixMatching`       | Prefix-based pattern tests | All should pass        |
| `TestONAPProductionRegression` | ONAP production mappings   | All should pass        |
| `TestLFBroadbandPatterns`      | LF Broadband patterns      | Pass after enhancement |
| `TestNegativeCases`            | False positive prevention  | All should pass        |
| `TestScoreOrdering`            | Score priority tests       | All should pass        |
| `TestEdgeCases`                | Edge case handling         | All should pass        |

## Running Tests

```bash
# Run all job attribution tests
pytest tests/unit/test_job_attribution.py -v

# Run only regression tests (ONAP)
pytest tests/unit/test_job_attribution.py -v -k "ONAP"

# Run only LF Broadband tests
pytest tests/unit/test_job_attribution.py -v -k "LFBroadband"

# Run only negative tests
pytest tests/unit/test_job_attribution.py -v -k "Negative"
```

## Notes

- 3-level project paths (e.g., `dcaegen2/analytics/tca-gen2`) are currently excluded
  from fixtures as they require special handling
- The LF Broadband tests are expected to fail until the matching algorithm is enhanced
  to support suffix/infix patterns
- Fixture data should be updated periodically to reflect changes in production job naming
