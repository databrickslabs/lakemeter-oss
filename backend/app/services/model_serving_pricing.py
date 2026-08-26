"""Shared Model Serving capacity and DBU calculations."""

GPU_CONCURRENCY_PER_REPLICA = 4


def is_gpu_workload_type(workload_type: str | None) -> bool:
    """Return whether a Model Serving workload type uses GPU replicas."""
    normalized = (workload_type or "cpu").strip().lower()
    return not normalized.startswith("cpu")


def get_billing_capacity_units(
    workload_type: str | None,
    concurrency: int,
) -> float:
    """Convert provisioned concurrency to the units billed by the DBU rate.

    Databricks provisions one GPU replica for every four concurrency units.
    CPU rates continue to be charged per concurrency unit.
    """
    if is_gpu_workload_type(workload_type):
        return concurrency / GPU_CONCURRENCY_PER_REPLICA
    return float(concurrency)


def calculate_model_serving_dbu_per_hour(
    dbu_rate: float,
    workload_type: str | None,
    concurrency: int,
) -> float:
    """Calculate Model Serving DBU/hour from the rate and capacity."""
    return dbu_rate * get_billing_capacity_units(workload_type, concurrency)
