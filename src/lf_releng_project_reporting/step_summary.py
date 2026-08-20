# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
GitHub Step Summary configuration reporting.

Writes the resolved configuration for a project (thresholds, time windows and
enabled feature counts) into the GitHub Actions step summary.
"""

import logging
import os
from typing import Any


logger = logging.getLogger(__name__)


def write_config_to_step_summary(config: dict[str, Any], project: str) -> None:
    """Write configuration information to GitHub Step Summary."""
    step_summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if not step_summary_file:
        return

    try:
        thresholds = config.get("activity_thresholds", {})
        current_days = thresholds.get("current_days", "N/A")
        active_days = thresholds.get("active_days", "N/A")
        features = config.get("features", {})
        features_enabled = features.get("enabled", [])

        with open(step_summary_file, "a") as f:
            f.write(f"## 🔧 Configuration for {project}\n\n")
            f.write("| Setting | Value |\n")
            f.write("|---------|-------|\n")
            f.write(f"| Schema Version | {config.get('schema_version', 'N/A')} |\n")
            f.write(f"| Current Threshold | {current_days} days |\n")
            f.write(f"| Active Threshold | {active_days} days |\n")
            f.write(f"| Time Windows | {len(config.get('time_windows', {}))} |\n")
            f.write(f"| Features Enabled | {len(features_enabled)} |\n")
            f.write("\n")

    except Exception as e:
        logger.warning("Could not write config to step summary: %s", e)
