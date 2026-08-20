# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Render context builder for preparing data for template rendering.

This module provides the RenderContext class which transforms raw report data
into a structured context suitable for Jinja2 templates. It handles data
extraction, formatting, and organization.

Phase: 8 - Renderer Modernization (Fixed for actual data schema)
"""

import logging

from .base import RenderContext


# Defined here (rather than in a submodule) so the logger keeps its original
# "rendering.context" name now that this module has become a package.
logger = logging.getLogger(__name__)

# Keep introspection and serialized references on the historical public path.
RenderContext.__module__ = __name__

__all__ = [
    "RenderContext",
    "logger",
]
