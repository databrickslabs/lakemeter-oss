"""Shared serverless performance-mode pricing rules."""

ALL_PURPOSE_WORKLOAD = "ALL_PURPOSE"
PERFORMANCE_MODE = "performance"


def normalize_serverless_mode(
    workload_type: str | None,
    serverless_mode: str | None,
) -> str:
    """Return the billable serverless mode for a workload.

    Serverless interactive notebooks do not support Standard mode, so
    All-Purpose Serverless is always billed as Performance Optimized.
    Jobs and Lakeflow Pipelines continue to honor the selected mode.
    """
    if (workload_type or "").strip().upper() == ALL_PURPOSE_WORKLOAD:
        return PERFORMANCE_MODE
    return (serverless_mode or "standard").strip().lower()


def get_serverless_mode_multiplier(
    workload_type: str | None,
    serverless_mode: str | None,
) -> float:
    """Return the DBU multiplier for a serverless performance mode."""
    normalized_mode = normalize_serverless_mode(workload_type, serverless_mode)
    return 2.0 if normalized_mode == PERFORMANCE_MODE else 1.0
