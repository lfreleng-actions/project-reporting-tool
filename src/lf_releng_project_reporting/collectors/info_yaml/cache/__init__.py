# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Advanced caching module for INFO.yaml data.

Provides multi-level caching with TTL (time-to-live), LRU eviction,
and persistent storage support for parsed INFO.yaml data, URL validation
results, and enrichment data.
"""

import hashlib
import json
import logging
import pickle
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, TypeVar

from .memory import LRUCache
from .models import CacheEntry, T
from .multilevel import MultiLevelCache, create_info_yaml_cache
from .persistent import PersistentCache


logger = logging.getLogger(__name__)


__all__ = [
    "Any",
    "CacheEntry",
    "Generic",
    "LRUCache",
    "MultiLevelCache",
    "Path",
    "PersistentCache",
    "T",
    "TypeVar",
    "create_info_yaml_cache",
    "dataclass",
    "hashlib",
    "json",
    "logger",
    "logging",
    "pickle",
    "time",
]
