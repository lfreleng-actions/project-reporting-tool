# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Progress bar primitives backed by tqdm with a plain-text fallback."""

# This module renders progress indicators and status messages to the terminal
# (stderr); print() is the intended output sink here, not leftover debugging.
# aislop-ignore-file python-print-debug -- intentional user-facing CLI output

import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any


try:
    from tqdm import tqdm  # pyright: ignore[reportMissingModuleSource]

    TQDM_AVAILABLE = True
except ImportError:
    tqdm = None
    TQDM_AVAILABLE = False  # pyright: ignore[reportConstantRedefinition]


class ProgressIndicator:
    """
    Progress indicator for long-running operations.

    Provides a consistent interface for progress tracking that works
    with or without tqdm. Automatically falls back to simple text
    indicators if tqdm is not available.

    Example:
        >>> with ProgressIndicator(total=100, desc="Processing") as progress:
        ...     for i in range(100):
        ...         # Do work
        ...         progress.update(1)
    """

    def __init__(
        self,
        total: int | None = None,
        desc: str = "Progress",
        disable: bool = False,
        unit: str = "item",
        leave: bool = True,
    ):
        """
        Initialize progress indicator.

        Args:
            total: Total number of items to process
            desc: Description of the operation
            disable: Disable progress display (quiet mode)
            unit: Unit name for items (e.g., "repo", "file")
            leave: Leave progress bar visible after completion
        """
        self.total = total
        self.desc = desc
        self.disable = disable
        self.unit = unit
        self.leave = leave
        self.current = 0
        self.pbar = None
        self._start_time: float | None = None

    def __enter__(self):
        """Enter context manager."""
        if self.disable:
            return self

        self._start_time = time.time()

        if TQDM_AVAILABLE and tqdm is not None:
            # Use tqdm if available
            self.pbar = tqdm(
                total=self.total,
                desc=self.desc,
                unit=self.unit,
                leave=self.leave,
                file=sys.stderr,
            )
        else:
            # Simple text-based indicator
            if self.total:
                print(f"{self.desc}: 0/{self.total} (0.0%)", file=sys.stderr, end="", flush=True)
            else:
                print(f"{self.desc}: Starting...", file=sys.stderr, flush=True)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if self.disable or self._start_time is None:
            return

        if self.pbar:
            self.pbar.close()  # type: ignore[unreachable]
        else:
            # Complete simple indicator
            if self.total and self.leave:
                elapsed = time.time() - self._start_time
                print(
                    f"\r{self.desc}: {self.current}/{self.total} (100.0%) - {elapsed:.1f}s",
                    file=sys.stderr,
                )
            elif self.leave:
                print(file=sys.stderr)

    def update(self, n: int = 1):
        """
        Update progress by n items.

        Args:
            n: Number of items to increment by (default: 1)
        """
        self.current += n

        if self.disable:
            return

        if self.pbar:
            self.pbar.update(n)  # type: ignore[unreachable]
        else:
            # Update simple indicator
            if self.total:
                percent = (self.current / self.total) * 100
                print(
                    f"\r{self.desc}: {self.current}/{self.total} ({percent:.1f}%)",
                    file=sys.stderr,
                    end="",
                    flush=True,
                )

    def set_description(self, desc: str):
        """
        Update progress description.

        Args:
            desc: New description text
        """
        self.desc = desc

        if self.disable:
            return

        if self.pbar:
            self.pbar.set_description(desc)  # type: ignore[unreachable]
        else:
            print(
                f"\r{desc}: {self.current}/{self.total if self.total else '?'}",
                file=sys.stderr,
                end="",
                flush=True,
            )

    def set_postfix_str(self, s: str):
        """
        Set postfix string (additional info after progress bar).

        Args:
            s: Postfix string
        """
        if self.disable:
            return

        if self.pbar and hasattr(self.pbar, "set_postfix_str"):  # type: ignore[unreachable]
            self.pbar.set_postfix_str(s)  # type: ignore[unreachable]

    def write(self, msg: str):
        """
        Write message without disrupting progress bar.

        Args:
            msg: Message to write
        """
        if self.disable:
            return

        if self.pbar and hasattr(self.pbar, "write"):  # type: ignore[unreachable]
            self.pbar.write(msg, file=sys.stderr)  # type: ignore[unreachable]
        else:
            print(f"\n{msg}", file=sys.stderr)


@contextmanager
def progress_bar(
    iterable: Any | None = None,
    total: int | None = None,
    desc: str = "Progress",
    disable: bool = False,
    unit: str = "item",
    leave: bool = True,
) -> Iterator[ProgressIndicator]:
    """
    Context manager for progress bars.

    Convenience wrapper around ProgressIndicator that works like tqdm.

    Args:
        iterable: Iterable to wrap (optional)
        total: Total number of items (required if no iterable)
        desc: Description of the operation
        disable: Disable progress display
        unit: Unit name for items
        leave: Leave progress bar visible after completion

    Yields:
        ProgressIndicator instance or wrapped iterable

    Example:
        >>> with progress_bar(total=100, desc="Processing") as pbar:
        ...     for i in range(100):
        ...         # Do work
        ...         pbar.update(1)

        >>> # Or with an iterable
        >>> with progress_bar(my_list, desc="Processing") as items:
        ...     for item in items:
        ...         # Process item
        ...         pass
    """
    if iterable is not None:
        # Wrap iterable
        if total is None:
            try:
                total = len(iterable)
            except TypeError:
                total = None

        pbar = ProgressIndicator(total=total, desc=desc, disable=disable, unit=unit, leave=leave)
        with pbar:
            for item in iterable:
                yield item
                pbar.update(1)
    else:
        # Manual progress tracking
        pbar = ProgressIndicator(total=total, desc=desc, disable=disable, unit=unit, leave=leave)
        with pbar:
            yield pbar
