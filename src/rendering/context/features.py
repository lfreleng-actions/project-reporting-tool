# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Repository feature matrix context builder.

Holds the ``RenderContext`` method that turns per-repository feature
detection results into the feature matrix rendered by a report.
"""

from typing import Any

from .shared import ContextMixinBase


class FeaturesContextMixin(ContextMixinBase):
    """Feature matrix section of the render context."""

    def _build_features_context(self) -> dict[str, Any]:
        """Build features detection context."""
        repositories = self.data.get("repositories", [])

        if not repositories:
            return {
                "has_features": False,
                "features_list": [],
                "matrix": [],
                "feature_count": 0,
                "repositories_count": 0,
            }

        features_set = set()
        for repo in repositories:
            repo_features = repo.get("features", {})
            features_set.update(repo_features.keys())

        features_list = sorted(features_set)

        matrix = []
        for repo in repositories:
            repo_features = repo.get("features", {})

            project_types = repo_features.get("project_types", {})
            if isinstance(project_types, dict):
                primary_type = project_types.get("primary_type")
                detected_types = project_types.get("detected_types", project_types.get("types", []))
            else:
                primary_type = None
                detected_types = []

            # Separate primary type from other types
            if primary_type and detected_types:
                other_types = [t for t in detected_types if t != primary_type]
            else:
                other_types = []

            # Display values
            primary_type_display = primary_type if primary_type else "N/A"
            other_types_display = other_types if other_types else []

            # Determine status based on activity
            activity_status = repo.get("activity_status", "unknown")
            if activity_status == "current":
                status = "✅"
            elif activity_status == "active":
                status = "☑️"
            else:
                status = "🛑"

            # Normalize feature names for template (strip has_ prefix)
            normalized_features = {}
            for feature in features_list:
                if isinstance(repo_features.get(feature), dict):
                    feature_entry = repo_features.get(feature, {})
                    feature_value = feature_entry.get("present", False)
                else:
                    feature_value = bool(repo_features.get(feature, False))

                # Normalize the feature name (strip has_ prefix if present)
                normalized_name = (
                    feature.replace("has_", "") if feature.startswith("has_") else feature
                )
                normalized_features[normalized_name] = feature_value

            matrix.append(
                {
                    "repo_name": repo.get("gerrit_project", "Unknown"),
                    "primary_type": primary_type_display,
                    "other_types": other_types_display,
                    "status": status,
                    "features": normalized_features,
                }
            )

        return {
            "has_features": len(features_list) > 0,
            "features_list": features_list,
            "matrix": matrix,
            "feature_count": len(features_list),
            "repositories_count": len(repositories),
        }
