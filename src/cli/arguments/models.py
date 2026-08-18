# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Enumerations describing supported output formats and verbosity levels."""

from enum import Enum


class OutputFormat(Enum):
    """Supported output formats."""

    JSON = "json"
    MARKDOWN = "md"
    HTML = "html"
    ALL = "all"

    def __str__(self):
        return self.value


class VerbosityLevel(Enum):
    """Verbosity levels for logging."""

    QUIET = 0
    NORMAL = 1
    VERBOSE = 2
    DEBUG = 3
    TRACE = 4
