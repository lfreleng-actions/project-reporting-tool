# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Clone strategy selection and reference repository management.

Contains the strategy deciding whether a shallow clone is safe and how
deep it should be, and the manager for the local bare reference
repositories used to accelerate clones.
"""

import hashlib
import logging
import shutil
import subprocess
import time
from pathlib import Path


logger = logging.getLogger(__name__)


class ShallowCloneStrategy:
    """
    Strategy for determining when and how to use shallow clones.

    Shallow clones are faster and use less disk space but have limitations
    for certain operations (e.g., full history analysis).
    """

    def __init__(self, default_depth: int = 1):
        """
        Initialize shallow clone strategy.

        Args:
            default_depth: Default depth for shallow clones
        """
        self.default_depth = default_depth

    def should_use_shallow(
        self,
        analysis_type: str = "basic",
        needs_history: bool = False,
        needs_branches: bool = False,
    ) -> bool:
        """
        Determine if shallow clone is appropriate.

        Args:
            analysis_type: Type of analysis to perform
            needs_history: Whether full history is needed
            needs_branches: Whether branch information is needed

        Returns:
            True if shallow clone is safe to use
        """
        # Don't use shallow if full history needed
        if needs_history:
            return False

        # Don't use shallow if branch analysis needed
        if needs_branches:
            return False

        # Safe for basic analysis (file structure, current state)
        if analysis_type in ("basic", "structure", "files", "current"):
            return True

        # Default to shallow for most cases
        return True

    def get_depth(self, analysis_type: str = "basic") -> int:
        """
        Get appropriate depth for shallow clone.

        Args:
            analysis_type: Type of analysis to perform

        Returns:
            Depth for shallow clone
        """
        # Deeper clones for certain analysis types
        depth_map = {
            "basic": 1,
            "structure": 1,
            "recent": 10,
            "commits": 50,
            "history": 100,
        }

        return depth_map.get(analysis_type, self.default_depth)


class ReferenceRepository:
    """
    Manage reference repositories for faster clones.

    Reference repositories store git objects locally and are referenced
    during clone operations to avoid re-downloading common objects.
    """

    def __init__(self, reference_dir: str = "./.git-references"):
        """
        Initialize reference repository manager.

        Args:
            reference_dir: Directory to store reference repositories
        """
        self.reference_dir = Path(reference_dir)
        self.reference_dir.mkdir(parents=True, exist_ok=True)

    def _get_reference_path(self, repo_url: str) -> Path:
        """
        Get path for reference repository.

        Args:
            repo_url: Repository URL

        Returns:
            Path to reference repository
        """
        url_hash = hashlib.sha256(repo_url.encode()).hexdigest()[:16]
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        return self.reference_dir / f"{repo_name}_{url_hash}"

    def has_reference(self, repo_url: str) -> bool:
        """
        Check if reference repository exists.

        Args:
            repo_url: Repository URL

        Returns:
            True if reference exists
        """
        ref_path = self._get_reference_path(repo_url)
        return ref_path.exists() and (ref_path / ".git").exists()

    def create_reference(self, repo_url: str, update: bool = False) -> Path | None:
        """
        Create or update reference repository.

        Args:
            repo_url: Repository URL
            update: Update existing reference if True

        Returns:
            Path to reference repository, or None on failure
        """
        ref_path = self._get_reference_path(repo_url)

        try:
            if ref_path.exists() and not update:
                return ref_path

            if ref_path.exists() and update:
                subprocess.run(
                    ["git", "fetch", "--all"],
                    cwd=ref_path,
                    check=True,
                    capture_output=True,
                    timeout=300,
                )
                return ref_path

            # Create new reference (bare clone)
            ref_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", "--bare", repo_url, str(ref_path)],
                check=True,
                capture_output=True,
                timeout=600,
            )

            return ref_path

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, Exception):
            # Reference creation failed, not critical
            return None

    def get_reference(self, repo_url: str, auto_create: bool = True) -> Path | None:
        """
        Get reference repository path.

        Args:
            repo_url: Repository URL
            auto_create: Create reference if it doesn't exist

        Returns:
            Path to reference repository, or None if not available
        """
        if self.has_reference(repo_url):
            return self._get_reference_path(repo_url)

        if auto_create:
            return self.create_reference(repo_url)

        return None

    def cleanup_old_references(self, max_age_days: int = 30) -> int:
        """
        Clean up old reference repositories.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of references cleaned up
        """
        if not self.reference_dir.exists():
            return 0

        count = 0
        now = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60

        for ref_path in self.reference_dir.iterdir():
            if not ref_path.is_dir():
                continue

            mtime = ref_path.stat().st_mtime
            age = now - mtime

            if age > max_age_seconds:
                try:
                    shutil.rmtree(ref_path)
                    count += 1
                # aislop-ignore-next-line silent-recovery -- best-effort cleanup; cause logged at debug
                except Exception:
                    logger.debug("Failed to remove stale reference %s", ref_path, exc_info=True)

        return count
