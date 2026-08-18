#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Run the configuration wizard with ``python -m cli.wizard``.

The wizard used to be a single module, whose ``if __name__ == "__main__"``
block made that invocation work. A package ``__init__`` cannot be executed
that way, so the entry point lives here instead.
"""

from .api import run_wizard


if __name__ == "__main__":
    run_wizard()
