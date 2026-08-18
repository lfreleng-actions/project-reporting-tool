# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Emoji-prefixed status messages for user-facing operation feedback."""

# This module renders progress indicators and status messages to the terminal
# (stderr); print() is the intended output sink here, not leftover debugging.
# aislop-ignore-file python-print-debug -- intentional user-facing CLI output

import sys


class OperationFeedback:
    """
    Provides user-friendly feedback messages for operations.

    Shows status messages with emoji indicators for better UX.
    Respects quiet mode when enabled.

    Example:
        >>> feedback = OperationFeedback(quiet=False)
        >>> feedback.start("Analyzing repositories")
        >>> feedback.info("Found 42 repositories")
        >>> feedback.success("Analysis complete")
    """

    def __init__(self, quiet: bool = False):
        """
        Initialize operation feedback.

        Args:
            quiet: Suppress informational messages (errors still shown)
        """
        self.quiet = quiet

    def start(self, message: str):
        """
        Show operation start message.

        Args:
            message: Operation description
        """
        if not self.quiet:
            print(f"🚀 {message}...", file=sys.stderr)

    def info(self, message: str):
        """
        Show informational message.

        Args:
            message: Information to display
        """
        if not self.quiet:
            print(f"ℹ️  {message}", file=sys.stderr)

    def success(self, message: str):
        """
        Show success message.

        Args:
            message: Success message
        """
        if not self.quiet:
            print(f"✅ {message}", file=sys.stderr)

    def warning(self, message: str):
        """
        Show warning message.

        Args:
            message: Warning message
        """
        # Warnings shown even in quiet mode
        print(f"⚠️  {message}", file=sys.stderr)

    def error(self, message: str):
        """
        Show error message.

        Args:
            message: Error message
        """
        # Errors always shown
        print(f"❌ {message}", file=sys.stderr)

    def step(self, step_num: int, total_steps: int, message: str):
        """
        Show step progress in a multi-step operation.

        Args:
            step_num: Current step number (1-based)
            total_steps: Total number of steps
            message: Step description
        """
        if not self.quiet:
            print(f"📍 Step {step_num}/{total_steps}: {message}...", file=sys.stderr)

    def discovery(self, message: str):
        """
        Show discovery/search operation message.

        Args:
            message: Discovery message
        """
        if not self.quiet:
            print(f"🔍 {message}...", file=sys.stderr)

    def processing(self, message: str):
        """
        Show processing operation message.

        Args:
            message: Processing message
        """
        if not self.quiet:
            print(f"⚙️  {message}...", file=sys.stderr)

    def writing(self, message: str):
        """
        Show file writing operation message.

        Args:
            message: Writing message
        """
        if not self.quiet:
            print(f"💾 {message}...", file=sys.stderr)

    def analyzing(self, message: str):
        """
        Show analysis operation message.

        Args:
            message: Analysis message
        """
        if not self.quiet:
            print(f"📊 {message}...", file=sys.stderr)
