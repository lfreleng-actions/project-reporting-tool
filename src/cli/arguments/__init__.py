# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Enhanced Argument Parser

Provides improved command-line argument parsing with:
- Better help text and examples
- New features (--list-features, --dry-run, --output-format)
- Verbose/quiet modes
- Validation and error handling

Phase 9: CLI & UX Improvements
"""

from .models import OutputFormat, VerbosityLevel
from .options import (
    get_log_level,
    get_output_formats,
    get_verbosity_level,
    is_special_mode,
    is_wizard_mode,
    should_generate_zip,
)
from .parser import create_argument_parser, parse_arguments
from .validators import validate_arguments


__all__ = [
    "create_argument_parser",
    "parse_arguments",
    "validate_arguments",
    "get_verbosity_level",
    "get_log_level",
    "get_output_formats",
    "should_generate_zip",
    "is_special_mode",
    "is_wizard_mode",
    "OutputFormat",
    "VerbosityLevel",
]
