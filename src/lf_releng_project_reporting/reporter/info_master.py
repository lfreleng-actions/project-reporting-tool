# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
info-master repository checkout lifecycle.

Clones the releng info-master repository into a temporary directory for
use as additional report context, and registers the ``atexit`` cleanup
that removes it again.
"""

import atexit
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from util.git import safe_git_command


class ReporterInfoMasterMixin:
    """Temporary info-master checkout management for the reporter."""

    # Assigned by RepositoryReporter.__init__; declared here for type checking.
    logger: logging.Logger
    api_stats: Any
    info_master_temp_dir: str | None

    def _cleanup_info_master_repo(self) -> None:
        """Clean up the temporary info-master repository directory."""
        if self.info_master_temp_dir and os.path.exists(self.info_master_temp_dir):
            try:
                self.logger.info(
                    f"Cleaning up info-master repository at {self.info_master_temp_dir}"
                )
                shutil.rmtree(self.info_master_temp_dir)
                self.logger.info("Successfully cleaned up info-master repository")
            except Exception as e:
                self.logger.warning(f"Failed to clean up info-master repository: {e}")

    def _clone_info_master_repo(self) -> Path | None:
        """
        Clone the info-master repository for additional context data.

        Returns the path to the cloned repository in a temporary directory,
        or None if cloning failed.
        """
        self.info_master_temp_dir = tempfile.mkdtemp(prefix="info-master-")
        info_master_path = Path(self.info_master_temp_dir) / "info-master"
        info_master_url = "https://gerrit.linuxfoundation.org/infra/releng/info-master"

        self.logger.info(
            f"Cloning info-master repository to temporary location: {info_master_path}"
        )
        success, output = safe_git_command(
            ["git", "clone", info_master_url, str(info_master_path)],
            Path(self.info_master_temp_dir),
            self.logger,
        )

        if success:
            if self.api_stats:
                self.api_stats.record_info_master(True)
            self.logger.debug("✅ Successfully cloned info-master repository")
            # Register cleanup handler
            atexit.register(self._cleanup_info_master_repo)
            return info_master_path
        else:
            error_msg = f"Clone failed: {output[:200]}" if output else "Clone failed"
            if self.api_stats:
                self.api_stats.record_info_master(False, error_msg)
            self.logger.error(f"❌ Failed to clone info-master repository: {output}")
            # Clean up the temp directory if clone failed
            if os.path.exists(self.info_master_temp_dir):
                shutil.rmtree(self.info_master_temp_dir)
            self.info_master_temp_dir = None
            return None
