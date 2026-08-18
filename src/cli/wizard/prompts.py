# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Terminal prompt and message-printing helpers used by the wizard."""

# This module asks the user questions and prints the answers back to the
# terminal; print() is the intended output sink here, not leftover debugging.
# The wizard was previously one module whose __main__ block exempted it from
# this rule, so the exemption is now stated explicitly.
# aislop-ignore-file python-print-debug -- intentional user-facing CLI output

# =============================================================================
# WIZARD HELPERS
# =============================================================================


def prompt(question: str, default: str | None = None) -> str:
    """
    Prompt user for input with optional default.

    Args:
        question: Question to ask
        default: Default value if user presses Enter

    Returns:
        User's answer or default
    """
    prompt_text = f"{question} [{default}]: " if default else f"{question}: "

    answer = input(prompt_text).strip()
    return answer if answer else (default or "")


def confirm(question: str, default: bool = True) -> bool:
    """
    Ask yes/no question.

    Args:
        question: Question to ask
        default: Default answer

    Returns:
        True for yes, False for no
    """
    default_str = "Y/n" if default else "y/N"
    answer = input(f"{question} [{default_str}]: ").strip().lower()

    if not answer:
        return default

    return answer in ("y", "yes", "true", "1")


def select_option(question: str, options: list[tuple[str, str]], default: int = 0) -> str:
    """
    Present multiple choice selection.

    Args:
        question: Question to ask
        options: List of (value, description) tuples
        default: Index of default option

    Returns:
        Selected value
    """
    print(f"\n{question}")
    for i, (_value, description) in enumerate(options, 1):
        marker = "→" if i - 1 == default else " "
        print(f"  {marker} {i}. {description}")

    while True:
        answer = input(f"\nSelect [1-{len(options)}] or press Enter for default: ").strip()

        if not answer:
            return options[default][0]

        try:
            idx = int(answer) - 1
            if 0 <= idx < len(options):
                return options[idx][0]
            else:
                print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print(f"Please enter a number between 1 and {len(options)}")
            continue


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print(f"{'─' * 70}\n")


def print_success(message: str) -> None:
    """Print success message."""
    print(f"✅ {message}")


def print_warning(message: str) -> None:
    """Print warning message."""
    print(f"⚠️  {message}")


def print_error(message: str) -> None:
    """Print error message."""
    print(f"❌ {message}")


def print_info(message: str) -> None:
    """Print info message."""
    print(f"ℹ️  {message}")
