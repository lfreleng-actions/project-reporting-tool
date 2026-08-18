# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Process-wide metrics collector singleton and convenience wrappers."""

from .collector import MetricsCollector


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

# Global metrics collector instance
_global_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """
    Get global metrics collector instance.

    Returns:
        MetricsCollector instance
    """
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector


def reset_metrics_collector():
    """Reset global metrics collector."""
    global _global_collector
    if _global_collector:
        _global_collector.finalize()
    _global_collector = MetricsCollector()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def time_operation(name: str, **metadata):
    """
    Time an operation using global collector.

    Args:
        name: Operation name
        **metadata: Additional metadata

    Returns:
        Context manager
    """
    return get_metrics_collector().time_operation(name, **metadata)


def record_api_call(api_name: str, duration: float, cached: bool = False, failed: bool = False):
    """
    Record an API call using global collector.

    Args:
        api_name: Name of the API
        duration: Call duration
        cached: Whether cached
        failed: Whether failed
    """
    get_metrics_collector().record_api_call(api_name, duration, cached, failed)


def print_performance_summary(verbose: bool = False):
    """
    Print performance summary using global collector.

    Args:
        verbose: Include detailed breakdown
    """
    get_metrics_collector().print_summary(verbose)


def print_debug_metrics():
    """Print debug metrics using global collector."""
    get_metrics_collector().print_debug_metrics()
