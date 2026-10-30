# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Pinned third-party assets loaded by HTML reports.

Reports load Simple-DataTables from jsDelivr. The version and its
Subresource Integrity hashes live together here so a bump changes one
place, and the browser refuses any file whose bytes differ from the
release that was reviewed. Dependabot does not track CDN URLs; see
docs/DATATABLES_IMPLEMENTATION.md for the manual bump procedure.
"""

DATATABLES_VERSION = "10.3.0"

_DATATABLES_BASE_URL = f"https://cdn.jsdelivr.net/npm/simple-datatables@{DATATABLES_VERSION}"

DATATABLES_CSS_URL = f"{_DATATABLES_BASE_URL}/dist/style.css"
DATATABLES_CSS_SRI = "sha384-CinX6s1UC1GpaQwL9eKshF7JhtC8H2xchDD0dWqlCgZ8t+GCCcjluxCgmsbVpdEh"

DATATABLES_JS_URL = f"{_DATATABLES_BASE_URL}/dist/umd/simple-datatables.js"
DATATABLES_JS_SRI = "sha384-OMR/OfeQC/fStE5yr0SBMKPPfMHctC+Ebr+QVzjdXw1FqbB0iBKgFkrAzvjhYByo"


def get_template_globals() -> dict[str, str]:
    """Return the asset URLs and hashes exposed to Jinja2 templates."""
    return {
        "DATATABLES_CSS_URL": DATATABLES_CSS_URL,
        "DATATABLES_CSS_SRI": DATATABLES_CSS_SRI,
        "DATATABLES_JS_URL": DATATABLES_JS_URL,
        "DATATABLES_JS_SRI": DATATABLES_JS_SRI,
    }
