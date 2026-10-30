# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Cache key generation helpers.

Builds stable, human-readable-prefixed cache keys for repository metadata,
git operations, API responses and analysis results.
"""

import hashlib
import json
from typing import Any


class CacheKey:
    """Utilities for generating cache keys."""

    @staticmethod
    def repository(repo_url: str, ref: str | None = None) -> str:
        """Generate key for repository metadata."""
        key = f"repo:{repo_url}"
        if ref:
            key += f":{ref}"
        return CacheKey._hash(key)

    @staticmethod
    def git_operation(repo_url: str, operation: str, params: dict[str, Any] | None = None) -> str:
        """Generate key for git operation result."""
        key = f"git:{repo_url}:{operation}"
        if params:
            # Sort params for consistent keys
            param_str = json.dumps(params, sort_keys=True)
            key += f":{param_str}"
        return CacheKey._hash(key)

    @staticmethod
    def api_response(endpoint: str, params: dict[str, Any] | None = None) -> str:
        """Generate key for API response."""
        key = f"api:{endpoint}"
        if params:
            param_str = json.dumps(params, sort_keys=True)
            key += f":{param_str}"
        return CacheKey._hash(key)

    @staticmethod
    def analysis_result(
        repo_url: str, analysis_type: str, config: dict[str, Any] | None = None
    ) -> str:
        """Generate key for analysis result."""
        key = f"analysis:{repo_url}:{analysis_type}"
        if config:
            config_str = json.dumps(config, sort_keys=True)
            key += f":{config_str}"
        return CacheKey._hash(key)

    @staticmethod
    def _hash(key: str) -> str:
        """Hash key to reasonable length."""
        # Keep first part human-readable, hash the rest
        parts = key.split(":", 2)
        if len(parts) > 2:
            prefix = ":".join(parts[:2])
            suffix = hashlib.sha256(parts[2].encode()).hexdigest()[:16]
            return f"{prefix}:{suffix}"
        return key
