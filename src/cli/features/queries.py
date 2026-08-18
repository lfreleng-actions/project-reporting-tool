# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Lookup, filtering, search and counting helpers over the feature registry."""

from .models import AVAILABLE_FEATURES, FeatureInfo


def get_feature_info(feature_name: str) -> FeatureInfo | None:
    """
    Get complete information for a specific feature.

    Args:
        feature_name: Name of the feature

    Returns:
        FeatureInfo object or None if not found

    Example:
        >>> info = get_feature_info('dependabot')
        >>> print(info.description)
        Dependabot configuration detection
    """
    if feature_name not in AVAILABLE_FEATURES:
        return None

    data = AVAILABLE_FEATURES[feature_name]
    return FeatureInfo(
        name=feature_name,
        description=data[0],
        category=data[1],
        config_file=data[2] if len(data) > 2 else None,
        config_example=data[3] if len(data) > 3 else None,
        detection_method=data[4] if len(data) > 4 else None,
    )


def get_features_by_category() -> dict[str, list[tuple[str, str]]]:
    """
    Get features organized by category.

    Returns:
        Dictionary mapping category names to list of (feature_name, description) tuples

    Example:
        >>> features = get_features_by_category()
        >>> print(features['CI/CD'])
        [('dependabot', 'Dependabot configuration detection'), ...]
    """
    categories: dict[str, list[tuple[str, str]]] = {}

    for feature_name, feature_data in AVAILABLE_FEATURES.items():
        description = feature_data[0]
        category = feature_data[1]
        if category not in categories:
            categories[category] = []
        categories[category].append((feature_name, description))

    # Sort features within each category
    for category in categories:
        categories[category].sort(key=lambda x: x[0])

    return categories


def get_feature_description(feature_name: str) -> str:
    """
    Get description for a specific feature.

    Args:
        feature_name: Name of the feature

    Returns:
        Feature description or "Unknown feature" if not found

    Example:
        >>> desc = get_feature_description('dependabot')
        >>> print(desc)
        Dependabot configuration detection
    """
    info = get_feature_info(feature_name)
    return info.description if info else f"Unknown feature: {feature_name}"


def get_feature_category(feature_name: str) -> str:
    """
    Get category for a specific feature.

    Args:
        feature_name: Name of the feature

    Returns:
        Feature category or "Unknown" if not found

    Example:
        >>> category = get_feature_category('dependabot')
        >>> print(category)
        CI/CD
    """
    info = get_feature_info(feature_name)
    return info.category if info else "Unknown"


def get_features_in_category(category: str) -> list[str]:
    """
    Get all feature names in a specific category.

    Args:
        category: Category name

    Returns:
        List of feature names in the category

    Example:
        >>> features = get_features_in_category('CI/CD')
        >>> print(features)
        ['dependabot', 'github-actions', 'github2gerrit', 'jenkins']
    """
    features = [
        name for name, feature_data in AVAILABLE_FEATURES.items() if feature_data[1] == category
    ]
    return sorted(features)


def get_all_categories() -> list[str]:
    """
    Get list of all feature categories.

    Returns:
        Sorted list of category names

    Example:
        >>> categories = get_all_categories()
        >>> print(categories)
        ['Build & Package', 'CI/CD', 'Code Quality', 'Documentation', ...]
    """
    categories = {feature_data[1] for feature_data in AVAILABLE_FEATURES.values()}
    return sorted(categories)


def search_features(query: str, category: str | None = None) -> list[tuple[str, str, str]]:
    """
    Search for features matching a query string.

    Args:
        query: Search query (case-insensitive)
        category: Optional category to filter by

    Returns:
        List of (feature_name, description, category) tuples matching the query

    Example:
        >>> results = search_features('github')
        >>> for name, desc, cat in results:
        ...     print(f"{name}: {desc}")
        github-actions: GitHub Actions workflows
        github-mirror: GitHub mirror repository detection
        github2gerrit: GitHub to Gerrit workflow synchronization
    """
    query_lower = query.lower()
    results = []

    for feature_name, feature_data in AVAILABLE_FEATURES.items():
        description = feature_data[0]
        feature_category = feature_data[1]

        # Filter by category if specified
        if category and feature_category != category:
            continue

        # Search in feature name, description, and config file
        config_file = feature_data[2] if len(feature_data) > 2 else ""
        if (
            query_lower in feature_name.lower()
            or query_lower in description.lower()
            or (config_file and query_lower in config_file.lower())
        ):
            results.append((feature_name, description, feature_category))

    # Sort by relevance (exact match first, then alphabetically)
    results.sort(
        key=lambda x: (
            not x[0].lower().startswith(query_lower),  # Prefix matches first
            x[0],  # Then alphabetically
        )
    )

    return results


def get_feature_count() -> int:
    """
    Get total number of available features.

    Returns:
        Number of features

    Example:
        >>> count = get_feature_count()
        >>> print(f"Total features: {count}")
        Total features: 23
    """
    return len(AVAILABLE_FEATURES)


def get_category_count() -> int:
    """
    Get total number of categories.

    Returns:
        Number of categories

    Example:
        >>> count = get_category_count()
        >>> print(f"Total categories: {count}")
        Total categories: 6
    """
    return len(get_all_categories())
