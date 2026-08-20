# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Deterministic ranking of aggregated entities.

Sorts repositories, authors and organizations by a (possibly nested) metric
key with name-based tie-breaking so report output is stable across runs.
"""

from typing import Any


class AggregatorRankingMixin:
    """Metric-based sorting with deterministic tie-breaking."""

    def rank_entities(
        self,
        entities: list[dict[str, Any]],
        sort_key: str,
        reverse: bool = False,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Sort entities by a metric with deterministic tie-breaking.

        Primary sort by the specified metric, secondary sort by name for stability.
        Handles nested dictionary keys (e.g., "commits.last_365_days").
        """

        def get_sort_value(entity):
            """Extract sort value, handling nested keys."""
            if "." in sort_key:
                keys = sort_key.split(".")
                value = entity
                for key in keys:
                    value = value.get(key, 0) if isinstance(value, dict) else 0
            else:
                value = entity.get(sort_key, 0)

            # Handle None values with appropriate defaults based on the metric
            if value is None:
                if sort_key == "days_since_last_commit":
                    return 999999  # Very large number for very old/no commits
                else:
                    return 0  # Default for other metrics

            # Ensure numeric return value
            if not isinstance(value, (int, float)):
                return 0
            return value

        def get_name(entity):
            """Extract name for tie-breaking."""
            return (
                entity.get("name")
                or entity.get("gerrit_project")
                or entity.get("domain")
                or entity.get("email")
                or ""
            )

        # Sort with primary metric (reverse if specified) and secondary name (always ascending)
        if reverse:
            sorted_entities = sorted(entities, key=lambda x: (-get_sort_value(x), get_name(x)))
        else:
            sorted_entities = sorted(entities, key=lambda x: (get_sort_value(x), get_name(x)))

        if limit and limit > 0:
            return sorted_entities[:limit]

        return sorted_entities
