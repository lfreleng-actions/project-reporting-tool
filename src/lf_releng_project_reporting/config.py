# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Configuration management for the lf-releng-project-reporting package.

This module handles:
- Loading YAML configuration files
- Merging template and project configurations
- Validating configuration values
- Computing configuration digests
- Setting up time windows
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from .exceptions import ConfigurationError


logger = logging.getLogger(__name__)


def deep_merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Deep merge two dictionaries, with override taking precedence.

    Args:
        base: Base dictionary
        override: Override dictionary (takes precedence)

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


def load_yaml_config(config_path: Path) -> dict[str, Any]:
    """
    Load YAML configuration file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Parsed configuration dictionary

    Raises:
        ConfigurationError: If file cannot be loaded or parsed
    """
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
            if config is None:
                return {}
            if not isinstance(config, dict):
                raise ConfigurationError(
                    f"Configuration file must contain a YAML dictionary: {config_path}"
                )
            return config
    except FileNotFoundError as err:
        raise ConfigurationError(f"Configuration file not found: {config_path}") from err
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in configuration file {config_path}: {e}") from e
    except Exception as e:
        raise ConfigurationError(f"Error loading configuration file {config_path}: {e}") from e


def load_configuration(
    project: str, config_dir: Path | None = None, default_config_name: str | None = None
) -> dict[str, Any]:
    """
    Load and merge configuration files.

    Loads default configuration (default.yaml) and project-specific configuration,
    then merges them with project config taking precedence.

    Project-specific configurations are matched by the 'project' field in the YAML file,
    not by filename. This allows configuration files to have simple lowercase names
    (e.g., lfbroadband.yaml) while supporting project names with spaces and capitals
    (e.g., "LF Broadband").

    If no project-specific configuration exists, uses the default configuration.
    This allows the tool to work out-of-the-box for most projects without
    requiring custom configuration files.

    Args:
        project: Project name (matched against 'project' field in config files)
        config_dir: Directory containing configuration files (default: configuration)
        default_config_name: Default configuration file name (default: default.yaml)

    Returns:
        Merged configuration dictionary
    """
    # Ensure config_dir is a Path object (default: "configuration")
    config_dir = Path("configuration") if config_dir is None else Path(config_dir)

    if default_config_name is None:
        default_config_name = "default.yaml"

    # Load default configuration
    default_path = config_dir / default_config_name
    if not default_path.exists():
        logger.warning(f"Default configuration not found: {default_path}")
        default_config = {}
    else:
        default_config = load_yaml_config(default_path)
        logger.debug(f"Loaded default configuration from {default_path}")

    # Search for project-specific configuration by matching 'project' field
    project_config = None
    project_path = None

    # Try loading by filename first (with .yaml and .config extensions)
    project_lower = project.lower()
    for extension in [".yaml", ".config"]:
        candidate_path = config_dir / f"{project_lower}{extension}"
        if candidate_path.exists():
            try:
                project_config = load_yaml_config(candidate_path)
                project_path = candidate_path
                logger.debug(f"Loaded project configuration from {candidate_path}")
                break
            except Exception as e:
                logger.debug(f"Failed to load {candidate_path}: {e}")
                continue

    # If not found by filename, search for project-specific configuration by matching 'project' field
    if project_config is None and config_dir.exists() and config_dir.is_dir():
        # Files to skip (not project configurations)
        skip_files = {
            default_config_name,
            "organizational_domains.yaml",
            "README.md",
        }

        for config_file in config_dir.glob("*.yaml"):
            # Skip non-project configuration files
            if config_file.name in skip_files:
                continue
            # Skip test configuration files
            if config_file.name.startswith("test-"):
                continue

            try:
                candidate_config = load_yaml_config(config_file)
                # Check if this config has a 'project' field that matches
                if candidate_config.get("project") == project:
                    project_config = candidate_config
                    project_path = config_file
                    logger.debug(f"Found project configuration in {config_file}")
                    break
            except Exception as e:
                logger.debug(f"Skipping {config_file}: {e}")
                continue

    if project_config is None:
        # No project-specific config found, use defaults
        logger.info(
            f"No project-specific configuration found for '{project}' in {config_dir}, "
            f"using defaults from {default_config_name}"
        )
        merged_config = default_config.copy()
    else:
        # Merge: default config <- project config (project overrides defaults)
        merged_config = deep_merge_dicts(default_config, project_config)
        logger.debug(f"Loaded project configuration from {project_path}")

    # Ensure project name is set
    merged_config["project"] = project

    # Apply intelligent auto-derivation
    merged_config = apply_auto_derivation(merged_config)

    return merged_config


def compute_config_digest(config: dict[str, Any]) -> str:
    """
    Compute SHA256 digest of configuration for caching purposes.

    Args:
        config: Configuration dictionary

    Returns:
        Hexadecimal digest string
    """
    config_json = json.dumps(config, sort_keys=True)
    return hashlib.sha256(config_json.encode()).hexdigest()


def setup_time_windows(config: dict[str, Any]) -> dict[str, datetime]:
    """
    Set up time windows from configuration.

    Converts time window configurations (e.g., "90d", "1y") into
    actual datetime objects for filtering.

    Supports two formats:
    - Simple: time_windows: {last_30: 30}
    - Dictionary: time_windows: {last_30: {days: 30}}

    Args:
        config: Configuration dictionary with time_windows section

    Returns:
        Dictionary mapping window names to datetime cutoff points
    """
    time_windows = {}
    now = datetime.now()

    if "time_windows" not in config:
        logger.warning("No time_windows defined in configuration, using defaults")
        return {
            "last_30": now - timedelta(days=30),
            "last_90": now - timedelta(days=90),
            "last_365": now - timedelta(days=365),
        }

    for window_name, window_config in config["time_windows"].items():
        # Support both simple integer format and dictionary format
        if isinstance(window_config, int):
            # Simple format: last_30: 30
            days = window_config
            time_windows[window_name] = now - timedelta(days=days)
        elif isinstance(window_config, dict) and "days" in window_config:
            # Dictionary format: last_30: {days: 30}
            days = window_config["days"]
            time_windows[window_name] = now - timedelta(days=days)
        else:
            logger.warning(f"Time window '{window_name}' invalid format, skipping")

    return time_windows


def validate_loaded_config(config: dict[str, Any]) -> None:
    """
    Validate loaded configuration has required fields.

    Args:
        config: Configuration dictionary to validate

    Raises:
        ConfigurationError: If required fields are missing or invalid
    """
    required_fields = ["project"]

    for field in required_fields:
        if field not in config:
            raise ConfigurationError(f"Required configuration field missing: {field}")

    # Validate time windows if present
    if "time_windows" in config:
        if not isinstance(config["time_windows"], dict):
            raise ConfigurationError("time_windows must be a dictionary")

        for window_name, window_config in config["time_windows"].items():
            if not isinstance(window_config, dict):
                raise ConfigurationError(f"Time window '{window_name}' must be a dictionary")
            if "days" not in window_config:
                raise ConfigurationError(f"Time window '{window_name}' missing 'days' field")
            if not isinstance(window_config["days"], int) or window_config["days"] <= 0:
                raise ConfigurationError(
                    f"Time window '{window_name}' days must be a positive integer"
                )

    # Validate activity thresholds if present
    if "activity_thresholds" in config and not isinstance(config["activity_thresholds"], dict):
        raise ConfigurationError("activity_thresholds must be a dictionary")

    logger.debug("Configuration validation passed")


def save_resolved_config(config: dict[str, Any], output_path: Path) -> None:
    """
    Save resolved/merged configuration to file.

    Args:
        config: Configuration dictionary to save
        output_path: Path where to save the configuration
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Saved resolved configuration to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save configuration to {output_path}: {e}")


def apply_auto_derivation(config: dict[str, Any]) -> dict[str, Any]:
    """
    Apply intelligent auto-derivation of configuration values.

    Auto-derives:
    - github_org from gerrit.host (e.g., gerrit.onap.org -> onap) for Gerrit projects
    - github_org from environment variable for GitHub-native projects
    - info_yaml.clone_url (uses standard LF location)
    - gerrit.enabled based on gerrit.host presence

    Args:
        config: Configuration dictionary

    Returns:
        Configuration with auto-derived values
    """
    # Get Gerrit host if available
    gerrit_host = config.get("gerrit", {}).get("host", "")

    # Auto-set gerrit.enabled based on host presence
    if "gerrit" not in config:
        config["gerrit"] = {}

    if gerrit_host:
        # Gerrit is available - ensure it's enabled
        config["gerrit"]["enabled"] = config.get("gerrit", {}).get("enabled", True)

        # Auto-derive GitHub organization from Gerrit host for mirrored projects
        if not config.get("extensions", {}).get("github_api", {}).get("github_org"):
            # Extract org name from gerrit.{org}.org pattern
            # Examples: gerrit.onap.org -> onap, gerrit.o-ran-sc.org -> o-ran-sc
            parts = gerrit_host.split(".")
            if len(parts) >= 2 and parts[0] == "gerrit":
                github_org = parts[1]
                logger.debug(
                    f"Auto-derived github_org '{github_org}' from Gerrit host '{gerrit_host}'"
                )

                # Ensure extensions.github_api structure exists
                if "extensions" not in config:
                    config["extensions"] = {}
                if "github_api" not in config["extensions"]:
                    config["extensions"]["github_api"] = {}

                config["extensions"]["github_api"]["github_org"] = github_org
                config["_github_org_auto_derived"] = True
    else:
        # No Gerrit host - disable Gerrit integration
        config["gerrit"]["enabled"] = False
        logger.debug(
            "No gerrit.host configured - Gerrit integration disabled (GitHub-native project)"
        )

        # For GitHub-native projects, github_org comes from GITHUB_ORG environment variable
        # which is set by the workflow from PROJECTS_JSON matrix.github field
        # The environment variable is read by util/github_org.py determine_github_org()
        import os

        github_org_env = os.environ.get("GITHUB_ORG", "")
        if github_org_env and not config.get("extensions", {}).get("github_api", {}).get(
            "github_org"
        ):
            logger.debug(f"Using GitHub org from environment: {github_org_env}")
            if "extensions" not in config:
                config["extensions"] = {}
            if "github_api" not in config["extensions"]:
                config["extensions"]["github_api"] = {}
            config["extensions"]["github_api"]["github_org"] = github_org_env
            config["_github_org_from_env"] = True

    # Auto-derive info_yaml.clone_url (always use standard LF location)
    if "info_yaml" not in config:
        config["info_yaml"] = {}

    if not config["info_yaml"].get("clone_url"):
        standard_info_yaml_url = "https://gerrit.linuxfoundation.org/infra/releng/info-master"
        config["info_yaml"]["clone_url"] = standard_info_yaml_url
        logger.debug(f"Auto-derived info_yaml.clone_url: {standard_info_yaml_url}")

    return config


def write_config_to_step_summary(config: dict[str, Any]) -> None:
    """
    Write configuration to GitHub Actions step summary.

    This writes a formatted version of the configuration to the
    GITHUB_STEP_SUMMARY file for visibility in GitHub Actions.

    Args:
        config: Configuration dictionary to write
    """
    import os

    step_summary = os.getenv("GITHUB_STEP_SUMMARY")
    if not step_summary:
        return

    try:
        with open(step_summary, "a") as f:
            f.write("\n## 📋 Configuration\n\n")
            f.write("```yaml\n")
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            f.write("```\n")
    except Exception as e:
        logger.warning(f"Failed to write configuration to step summary: {e}")
