# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Shared declarations for the RenderContext section mixins.

The mixins in this package are composed by ``RenderContext`` (see
``base.py``). Because each mixin lives in its own module, type checkers
cannot see the attributes set in ``RenderContext.__init__`` nor the
builder methods implemented by sibling mixins. This base class declares
both, purely for typing: the method declarations are guarded by
``TYPE_CHECKING`` so they never exist at runtime and never shadow the
real implementations resolved through the MRO.
"""

from typing import TYPE_CHECKING, Any


class ContextMixinBase:
    """Type-only base shared by every RenderContext section mixin."""

    # Assigned in RenderContext.__init__; declared here for type checkers only.
    data: dict[str, Any]
    config: dict[str, Any]

    if TYPE_CHECKING:
        # Implemented by sibling mixins; resolved via RenderContext's MRO.
        def _detect_project_type(self) -> str: ...

        def _build_repository_url(
            self, project_name: str, host: str, path_prefix: str, project_type: str
        ) -> str: ...

        def _build_repositories_context(self) -> dict[str, Any]: ...

        def _build_contributors_context(self) -> dict[str, Any]: ...

        def _build_organizations_context(self) -> dict[str, Any]: ...

        def _build_features_context(self) -> dict[str, Any]: ...

        def _build_workflows_context(self) -> dict[str, Any]: ...

        def _build_orphaned_jobs_context(self) -> dict[str, Any]: ...

        def _build_unattributed_jobs_context(self) -> dict[str, Any]: ...

        def _build_time_windows_context(self) -> list[dict[str, Any]]: ...
