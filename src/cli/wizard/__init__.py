#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Configuration Wizard - Interactive Setup for Repository Reports

This module provides an interactive configuration wizard that helps users
create valid configuration files for their first report generation.

Features:
- Interactive prompts for all configuration options
- Template-based configuration generation
- Validation during setup
- Smart defaults based on environment
- Example configurations for common use cases
- Pre-flight checks before saving
"""

from .api import create_config_from_template, run_wizard
from .configuration import ConfigurationWizard
from .models import FULL_TEMPLATE, MINIMAL_TEMPLATE, STANDARD_TEMPLATE
from .prompts import (
    confirm,
    print_error,
    print_info,
    print_section,
    print_success,
    print_warning,
    prompt,
    select_option,
)


__all__ = [
    "MINIMAL_TEMPLATE",
    "STANDARD_TEMPLATE",
    "FULL_TEMPLATE",
    "prompt",
    "confirm",
    "select_option",
    "print_section",
    "print_success",
    "print_warning",
    "print_error",
    "print_info",
    "ConfigurationWizard",
    "run_wizard",
    "create_config_from_template",
]
