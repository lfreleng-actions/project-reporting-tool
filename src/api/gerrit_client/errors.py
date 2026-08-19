# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Gerrit API exception types.

Shared error classes raised by the Gerrit discovery, URL-building and
client layers.
"""


class GerritAPIError(Exception):
    """Base exception for Gerrit API errors."""

    pass


class GerritConnectionError(Exception):
    """Raised when connection to Gerrit server fails."""

    pass
