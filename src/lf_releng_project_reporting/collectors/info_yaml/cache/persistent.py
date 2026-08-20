# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
On-disk persistent cache level.

Level 2 of the cache stack: serialises values to hashed filenames under a
cache directory using either JSON or pickle.
"""

import hashlib
import json
import logging
import pickle
from pathlib import Path
from typing import Any


class PersistentCache:
    """
    Persistent cache that stores data to disk.

    Provides persistent storage for cache data across program runs,
    with support for JSON and pickle serialization.
    """

    def __init__(
        self,
        cache_dir: Path,
        format: str = "json",
        compression: bool = False,
    ):
        """
        Initialize the persistent cache.

        Args:
            cache_dir: Directory for cache files
            format: Serialization format ('json' or 'pickle')
            compression: Enable compression (not yet implemented)
        """
        self.cache_dir = Path(cache_dir)
        self.format = format
        self.compression = compression

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(f"PersistentCache initialized: dir={cache_dir}, format={format}")

    def get(self, key: str) -> Any | None:
        """
        Get a value from persistent storage.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        cache_file = self._get_cache_file(key)

        if not cache_file.exists():
            return None

        try:
            if self.format == "json":
                with open(cache_file) as f:
                    return json.load(f)
            elif self.format == "pickle":
                # Defense in depth: never unpickle a file that resolves
                # outside the cache directory (e.g. via a symlink).
                resolved = cache_file.resolve()
                if self.cache_dir.resolve() not in resolved.parents:
                    self.logger.warning(
                        "Refusing to load cache file outside cache directory: %s",
                        cache_file,
                    )
                    return None
                with open(resolved, "rb") as f:
                    # aislop-ignore-next-line pickle-load -- path-contained cache file written by this tool
                    return pickle.load(f)
            else:
                self.logger.error(f"Unknown format: {self.format}")
                return None
        except Exception as e:
            self.logger.warning(f"Failed to load cache file {cache_file}: {e}")
            return None

    def set(self, key: str, value: Any) -> bool:
        """
        Set a value in persistent storage.

        Args:
            key: Cache key
            value: Value to cache

        Returns:
            True if successful, False otherwise
        """
        cache_file = self._get_cache_file(key)

        try:
            if self.format == "json":
                with open(cache_file, "w") as f:
                    json.dump(value, f, indent=2)
            elif self.format == "pickle":
                with open(cache_file, "wb") as f:
                    pickle.dump(value, f)
            else:
                self.logger.error(f"Unknown format: {self.format}")
                return False

            return True
        except Exception as e:
            self.logger.warning(f"Failed to save cache file {cache_file}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete a value from persistent storage.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        cache_file = self._get_cache_file(key)

        if cache_file.exists():
            try:
                cache_file.unlink()
                return True
            except Exception as e:
                self.logger.warning(f"Failed to delete cache file {cache_file}: {e}")
                return False

        return False

    def clear(self) -> int:
        """
        Clear all cache files.

        Returns:
            Number of files deleted
        """
        count = 0
        for cache_file in self.cache_dir.glob("*"):
            if cache_file.is_file():
                try:
                    cache_file.unlink()
                    count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to delete {cache_file}: {e}")

        self.logger.info(f"Cleared {count} cache files")
        return count

    def _get_cache_file(self, key: str) -> Path:
        """
        Get the cache file path for a key.

        Args:
            key: Cache key

        Returns:
            Path to cache file
        """
        # Hash the key to create a safe filename
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]

        extension = "json" if self.format == "json" else "pkl"
        return self.cache_dir / f"{key_hash}.{extension}"
