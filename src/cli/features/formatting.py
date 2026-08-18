# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Human-readable rendering of feature listings, details and search results."""

from .models import AVAILABLE_FEATURES
from .queries import get_feature_info, get_features_by_category, get_features_in_category


def list_all_features(verbose: bool = False) -> str:
    """
    Generate formatted list of all available features.

    Args:
        verbose: If True, include config file info

    Returns:
        Formatted string listing all features by category

    Example:
        >>> print(list_all_features())
        Available Feature Checks:

        CI/CD:
          dependabot              - Dependabot configuration detection
          github-actions          - GitHub Actions workflows
        ...
    """
    features_by_category = get_features_by_category()

    lines = ["Available Feature Checks:", ""]

    # Sort categories for consistent output
    category_order = sorted(features_by_category.keys())

    for category in category_order:
        lines.append(f"📁 {category}:")

        for feature_name, description in features_by_category[category]:
            # Format with padding for alignment
            lines.append(f"  • {feature_name:24} - {description}")

            # Add config file info if verbose
            if verbose:
                info = get_feature_info(feature_name)
                if info and info.config_file:
                    lines.append(f"    Config: {info.config_file}")

        lines.append("")  # Blank line between categories

    # Summary
    lines.append(
        f"Total: {len(AVAILABLE_FEATURES)} features across {len(category_order)} categories"
    )
    lines.append("")
    lines.append(
        "💡 Use --show-feature <name> to see detailed information about a specific feature"
    )

    return "\n".join(lines)


def show_feature_details(feature_name: str) -> str:
    """
    Generate detailed information display for a specific feature.

    Args:
        feature_name: Name of the feature to display

    Returns:
        Formatted string with complete feature details

    Example:
        >>> print(show_feature_details('dependabot'))
        Feature: dependabot
        Category: CI/CD
        Description: Dependabot configuration detection
        ...
    """
    info = get_feature_info(feature_name)

    if not info:
        return f"❌ Unknown feature: {feature_name}\n\nUse --list-features to see all available features."

    lines = []
    lines.append("=" * 70)
    lines.append(f"Feature: {info.name}")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"📁 Category: {info.category}")
    lines.append(f"📝 Description: {info.description}")
    lines.append("")

    if info.detection_method:
        lines.append("🔍 Detection Method:")
        lines.append(f"  {info.detection_method}")
        lines.append("")

    if info.config_file:
        lines.append("📄 Configuration File(s):")
        lines.append(f"  {info.config_file}")
        lines.append("")

    if info.config_example:
        lines.append("📋 Configuration Example:")
        lines.append("")
        # Indent example code
        for line in info.config_example.split("\n"):
            lines.append(f"  {line}")
        lines.append("")

    # Related features in same category
    related = get_features_in_category(info.category)
    related = [f for f in related if f != feature_name]
    if related:
        lines.append(f"🔗 Related Features in {info.category}:")
        for related_feature in related[:5]:  # Show max 5
            related_info = get_feature_info(related_feature)
            if related_info:
                lines.append(f"  • {related_feature:24} - {related_info.description}")
        if len(related) > 5:
            lines.append(f"  ... and {len(related) - 5} more")
        lines.append("")

    lines.append("💡 Tip: Use --list-features to see all available features")

    return "\n".join(lines)


def format_search_results(query: str, results: list[tuple[str, str, str]]) -> str:
    """
    Format search results for display.

    Args:
        query: The search query used
        results: List of (feature_name, description, category) tuples

    Returns:
        Formatted string with search results
    """
    if not results:
        lines = [
            f"No features found matching '{query}'",
            "",
            "💡 Tip: Use --list-features to see all available features",
        ]
        return "\n".join(lines)

    lines = [f"Found {len(results)} feature(s) matching '{query}':", ""]

    # Group by category
    by_category: dict[str, list[tuple[str, str]]] = {}
    for name, desc, cat in results:
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append((name, desc))

    for category in sorted(by_category.keys()):
        lines.append(f"📁 {category}:")
        for name, desc in by_category[category]:
            lines.append(f"  • {name:24} - {desc}")
        lines.append("")

    lines.append("💡 Use --show-feature <name> to see detailed information")

    return "\n".join(lines)


def format_feature_list_compact() -> str:
    """
    Generate compact single-line list of all features.

    Returns:
        Comma-separated list of feature names

    Example:
        >>> print(format_feature_list_compact())
        dependabot, github-actions, github2gerrit, jenkins, ...
    """
    feature_names = sorted(AVAILABLE_FEATURES.keys())
    return ", ".join(feature_names)
