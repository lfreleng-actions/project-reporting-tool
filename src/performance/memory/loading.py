# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Deferred and streamed data access helpers.

Provides lazy proxies and their manager for deferring expensive loads, and
a stream processor for handling large files without loading them entirely
into memory.
"""

import logging
import threading
from collections.abc import Callable, Generator, Iterator
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class LazyProxy:
    """Proxy object for lazy-loaded data."""

    def __init__(self, loader: Callable[[], Any], name: str = ""):
        """
        Initialize lazy proxy.

        Args:
            loader: Function to load the actual object
            name: Name for debugging
        """
        self._loader = loader
        self._name = name
        self._loaded = False
        self._value = None
        self._lock = threading.Lock()

    def _load(self) -> Any:
        """Load the actual value."""
        with self._lock:
            if not self._loaded:
                logger.debug(f"Lazy loading: {self._name}")
                self._value = self._loader()
                self._loaded = True
            return self._value

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to loaded object."""
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        return getattr(self._load(), name)

    def __getitem__(self, key: Any) -> Any:
        """Proxy item access to loaded object."""
        return self._load()[key]

    def __len__(self) -> int:
        """Proxy length to loaded object."""
        return len(self._load())

    def __iter__(self) -> Iterator[Any]:
        """Proxy iteration to loaded object."""
        return iter(self._load())

    def __repr__(self) -> str:
        """String representation."""
        if self._loaded:
            return f"LazyProxy({self._name}, loaded)"
        return f"LazyProxy({self._name}, not loaded)"


class LazyLoader:
    """Lazy loading manager for deferred data access."""

    def __init__(self):
        """Initialize lazy loader."""
        self._proxies: dict[str, LazyProxy] = {}
        self._load_count = 0
        self._lock = threading.Lock()

    def create_lazy(
        self,
        loader: Callable[[], Any],
        name: str = "",
    ) -> LazyProxy:
        """
        Create a lazy-loaded proxy.

        Args:
            loader: Function to load the data
            name: Name for debugging

        Returns:
            Lazy proxy object
        """
        with self._lock:
            if not name:
                name = f"lazy_{len(self._proxies)}"

            proxy = LazyProxy(loader, name)
            self._proxies[name] = proxy

            logger.debug(f"Created lazy proxy: {name}")
            return proxy

    def load_all(self) -> int:
        """
        Force load all lazy proxies.

        Returns:
            Number of proxies loaded
        """
        loaded = 0
        for proxy in self._proxies.values():
            if not proxy._loaded:
                proxy._load()
                loaded += 1

        return loaded

    def clear(self) -> None:
        """Clear all lazy proxies."""
        with self._lock:
            self._proxies.clear()
            self._load_count = 0

    def get_stats(self) -> dict[str, Any]:
        """Get lazy loading statistics."""
        loaded = sum(1 for p in self._proxies.values() if p._loaded)
        return {
            "total_proxies": len(self._proxies),
            "loaded_proxies": loaded,
            "unloaded_proxies": len(self._proxies) - loaded,
            "load_ratio": loaded / len(self._proxies) if self._proxies else 0,
        }


class StreamProcessor:
    """Stream processor for handling large files."""

    def __init__(
        self,
        chunk_size: int = 8192,
        buffer_size: int = 65536,
    ):
        """
        Initialize stream processor.

        Args:
            chunk_size: Size of each read chunk in bytes
            buffer_size: Buffer size for buffered reading
        """
        self.chunk_size = chunk_size
        self.buffer_size = buffer_size
        self._read_count = 0
        self._bytes_read = 0

    def read_file_chunks(
        self,
        file_path: str | Path,
        encoding: str = "utf-8",
    ) -> Generator[str, None, None]:
        """
        Read file in chunks.

        Args:
            file_path: Path to file
            encoding: Text encoding

        Yields:
            File chunks
        """
        file_path = Path(file_path)

        with open(file_path, encoding=encoding, buffering=self.buffer_size) as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break

                self._read_count += 1
                self._bytes_read += len(chunk.encode(encoding))
                yield chunk

    def read_lines(
        self,
        file_path: str | Path,
        encoding: str = "utf-8",
    ) -> Generator[str, None, None]:
        """
        Read file line by line.

        Args:
            file_path: Path to file
            encoding: Text encoding

        Yields:
            File lines
        """
        file_path = Path(file_path)

        with open(file_path, encoding=encoding, buffering=self.buffer_size) as f:
            for line in f:
                self._read_count += 1
                self._bytes_read += len(line.encode(encoding))
                yield line

    def process_large_file(
        self,
        file_path: str | Path,
        processor: Callable[[str], Any],
        encoding: str = "utf-8",
        line_mode: bool = True,
    ) -> list[Any]:
        """
        Process large file without loading entirely into memory.

        Args:
            file_path: Path to file
            processor: Function to process each chunk/line
            encoding: Text encoding
            line_mode: Process line-by-line vs chunk-by-chunk

        Returns:
            List of processed results
        """
        results = []

        if line_mode:
            for line in self.read_lines(file_path, encoding):
                result = processor(line)
                if result is not None:
                    results.append(result)
        else:
            for chunk in self.read_file_chunks(file_path, encoding):
                result = processor(chunk)
                if result is not None:
                    results.append(result)

        return results

    def should_stream(self, file_path: str | Path, threshold_mb: float = 10) -> bool:
        """
        Check if file should be streamed.

        Args:
            file_path: Path to file
            threshold_mb: Size threshold in MB

        Returns:
            True if file should be streamed
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return False

        size_mb = file_path.stat().st_size / (1024 * 1024)
        return size_mb >= threshold_mb

    def get_stats(self) -> dict[str, Any]:
        """Get streaming statistics."""
        return {
            "read_count": self._read_count,
            "bytes_read": self._bytes_read,
            "mb_read": self._bytes_read / (1024 * 1024),
        }
