# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Feature Discovery Module

Provides functionality to list and describe available feature checks.
This allows users to discover what features the reporting system can detect.

Phase 9: CLI & UX Improvements
Phase 13: Enhanced Feature Discovery
"""

from .formatting import (
    format_feature_list_compact,
    format_search_results,
    list_all_features,
    show_feature_details,
)
from .models import AVAILABLE_FEATURES, FeatureInfo
from .queries import (
    get_all_categories,
    get_category_count,
    get_feature_category,
    get_feature_count,
    get_feature_description,
    get_feature_info,
    get_features_by_category,
    get_features_in_category,
    search_features,
)


__all__ = [
    "AVAILABLE_FEATURES",
    "FeatureInfo",
    "get_feature_info",
    "get_features_by_category",
    "list_all_features",
    "show_feature_details",
    "get_feature_description",
    "get_feature_category",
    "get_features_in_category",
    "get_all_categories",
    "search_features",
    "format_search_results",
    "format_feature_list_compact",
    "get_feature_count",
    "get_category_count",
]
