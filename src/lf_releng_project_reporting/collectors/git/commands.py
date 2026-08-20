# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Low-level Git command and date parsing helpers."""

import datetime
import logging
import subprocess
from pathlib import Path


def safe_git_command(cmd: list[str], cwd: Path | None, logger: logging.Logger) -> tuple[bool, str]:
    """
    Execute a git command safely with error handling.

    Returns:
        (success: bool, output_or_error: str)
    """
    try:
        git_result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        return (
            git_result.returncode == 0,
            git_result.stdout.strip() or git_result.stderr.strip(),
        )
    except subprocess.CalledProcessError as e:
        logger.warning(f"Git command failed in {cwd}: {' '.join(cmd)} - {e.stderr}")
        return False, e.stderr
    except subprocess.TimeoutExpired:
        logger.error(f"Git command timed out in {cwd}: {' '.join(cmd)}")
        return False, "Command timed out"
    except Exception as e:
        logger.error(f"Unexpected error running git command in {cwd}: {e}")
        return False, str(e)


def parse_git_iso_date(date_str: str) -> datetime.datetime:
    """
    Parse git's --date=iso format into a datetime object.

    Git ISO format: "2013-03-25 16:50:06 +0100"
    Python fromisoformat expects: "2013-03-25T16:50:06+01:00"

    Args:
        date_str: Date string from git in ISO format

    Returns:
        datetime object with timezone information

    Raises:
        ValueError: If the date string cannot be parsed
    """
    # Replace first space with 'T' to separate date and time
    date_str = date_str.replace(" ", "T", 1)

    if "+" in date_str or date_str.count("-") > 2:
        # Split at the timezone offset
        if "+" in date_str:
            parts = date_str.rsplit("+", 1)
            tz_sign = "+"
        else:
            # Find the last '-' which is the timezone indicator
            # (date already has 2 dashes, so count > 2 means timezone)
            parts = date_str.rsplit("-", 1)
            tz_sign = "-"

        if len(parts) == 2 and len(parts[1]) == 4:
            # Format timezone: "0100" -> "01:00"
            tz_offset = parts[1]
            formatted_tz = f"{tz_offset[:2]}:{tz_offset[2:]}"
            date_str = f"{parts[0]}{tz_sign}{formatted_tz}"

    return datetime.datetime.fromisoformat(date_str)
