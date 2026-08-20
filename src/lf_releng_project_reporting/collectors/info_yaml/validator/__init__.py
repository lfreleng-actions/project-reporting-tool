# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
URL validator module.

Provides HTTP URL validation with caching, retries, and exponential backoff
for validating issue tracker URLs from INFO.yaml files.

Supports both synchronous and asynchronous validation for optimal performance.
"""

import asyncio
import logging
import time

import httpx

from .functions import (
    validate_url,
    validate_urls,
    validate_urls_async,
    validate_urls_sync,
)
from .validator import URLValidator


logger = logging.getLogger(__name__)

# Keep introspection and serialized references on the historical public path.
URLValidator.__module__ = __name__

__all__ = [
    "URLValidator",
    "asyncio",
    "httpx",
    "logger",
    "logging",
    "time",
    "validate_url",
    "validate_urls",
    "validate_urls_async",
    "validate_urls_sync",
]
