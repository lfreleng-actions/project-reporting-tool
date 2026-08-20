#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Repository Reporter - Main Orchestration Module

This module contains the RepositoryReporter class which orchestrates the entire
repository analysis workflow, including:
- Repository discovery and scanning
- Git data collection coordination
- Feature detection coordination
- Data aggregation
- Report rendering and output generation

The RepositoryReporter acts as the main controller that ties together all the
subsystems (collectors, aggregators, renderers) to produce comprehensive
repository analysis reports.
"""

from lf_releng_project_reporting.aggregators import DataAggregator
from lf_releng_project_reporting.collectors import GitDataCollector, INFOYamlCollector
from lf_releng_project_reporting.features import FeatureRegistry
from rendering.renderer import ModernReportRenderer

from .reporter import RepositoryReporter


# Preserve the original class identity and constructor patch points after moving
# the implementation into the package's private ``reporter`` module.
RepositoryReporter.__module__ = __name__

__all__ = [
    "DataAggregator",
    "FeatureRegistry",
    "GitDataCollector",
    "INFOYamlCollector",
    "ModernReportRenderer",
    "RepositoryReporter",
]
