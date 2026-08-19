# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Public entry points for running the wizard and generating config from templates."""

from pathlib import Path

import yaml

from .configuration import ConfigurationWizard
from .models import FULL_TEMPLATE, MINIMAL_TEMPLATE, STANDARD_TEMPLATE


# =============================================================================
# PUBLIC API
# =============================================================================


def run_wizard(output_path: str | None = None) -> str:
    """
    Run the interactive configuration wizard.

    Args:
        output_path: Optional path to save configuration

    Returns:
        Path to created configuration file
    """
    wizard = ConfigurationWizard()
    return wizard.run(output_path)


def create_config_from_template(
    project: str,
    template: str = "standard",
    output_path: str | None = None,
) -> str:
    """
    Create configuration file from template without interactive prompts.

    Args:
        project: Project name
        template: Template type (minimal, standard, full)
        output_path: Optional path to save configuration

    Returns:
        Path to created configuration file
    """
    # Select template
    if template == "minimal":
        config = MINIMAL_TEMPLATE.copy()
    elif template == "standard":
        config = STANDARD_TEMPLATE.copy()
    elif template == "full":
        config = FULL_TEMPLATE.copy()
    else:
        raise ValueError(f"Unknown template: {template}")

    # Set project name
    config["project"] = project

    # Determine output path
    if not output_path:
        output_path = f"config/{project}.yaml"

    # Create parent directory if needed
    config_path = Path(output_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Save configuration
    with open(config_path, "w") as f:
        yaml.dump(
            config,
            f,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
        )

    return str(config_path)
