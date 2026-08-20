# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Data aggregator for repository metrics.

This module provides the DataAggregator class for aggregating repository
metrics into global summaries including:
- Repository classification (current/active/inactive)
- Author and organization rollups
- Top/least active repository identification
- Contributor leaderboards
- Activity status distribution analysis
"""

from .aggregator import DataAggregator


# Keep introspection and serialized references on the historical public path.
DataAggregator.__module__ = __name__

__all__ = ["DataAggregator"]
