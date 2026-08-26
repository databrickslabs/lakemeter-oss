"""Canonical AI Runtime accelerator profiles and usage calculations."""
import math


AI_RUNTIME_SKU = "MODEL_TRAINING"

# Databricks publishes AWS US East list prices of $2.50/A10 GPU-hour and
# $7.00/H100 GPU-hour, and Azure US East prices of $4.90/A10 GPU-hour and
# $7.00/H100 GPU-hour. MODEL_TRAINING is $0.65/DBU in those regions, so the
# ratios below preserve the SKU-rate calculation used throughout Lakemeter.
AI_RUNTIME_ACCELERATORS = {
    "aws": {
        "GPU_1xA10": {
            "display_name": "1x A10 (24 GB)",
            "gpu_count": 1,
            "dbu_per_gpu_hour": 50 / 13,
        },
        "GPU_1xH100": {
            "display_name": "1x H100 (80 GB)",
            "gpu_count": 1,
            "dbu_per_gpu_hour": 140 / 13,
        },
        "GPU_8xH100": {
            "display_name": "8x H100 (640 GB total)",
            "gpu_count": 8,
            "dbu_per_gpu_hour": 140 / 13,
        },
    },
    "azure": {
        "GPU_1xA10": {
            "display_name": "1x A10 (24 GB)",
            "gpu_count": 1,
            "dbu_per_gpu_hour": 98 / 13,
        },
        "GPU_1xH100": {
            "display_name": "1x H100 (80 GB)",
            "gpu_count": 1,
            "dbu_per_gpu_hour": 140 / 13,
        },
        "GPU_8xH100": {
            "display_name": "8x H100 (640 GB total)",
            "gpu_count": 8,
            "dbu_per_gpu_hour": 140 / 13,
        },
    },
}

def get_ai_runtime_accelerator(cloud: str, accelerator_type: str) -> dict:
    """Return one supported accelerator profile."""
    cloud_key = (cloud or "").strip().lower()
    requested_accelerator = (accelerator_type or "").strip()
    cloud_profiles = AI_RUNTIME_ACCELERATORS.get(cloud_key)
    if cloud_profiles is None:
        raise ValueError("AI Runtime is currently supported on AWS and Azure")
    accelerator_key = next(
        (
            key
            for key in cloud_profiles
            if key.upper() == requested_accelerator.upper()
        ),
        None,
    )
    profile = cloud_profiles.get(accelerator_key)
    if profile is None:
        allowed = ", ".join(cloud_profiles)
        raise ValueError(
            f"accelerator_type must be one of: {allowed}"
        )
    return {
        "accelerator_type": accelerator_key,
        **profile,
    }
def calculate_ai_runtime_usage(
    cloud: str,
    accelerator_type: str,
    runtime_hours: float,
) -> dict:
    """Calculate GPU-hours and MODEL_TRAINING DBUs for one month."""
    try:
        hours = float(runtime_hours)
    except (TypeError, ValueError) as exc:
        raise ValueError("runtime_hours must be a number") from exc
    if not math.isfinite(hours):
        raise ValueError("runtime_hours must be finite")
    if hours < 0:
        raise ValueError("runtime_hours must be greater than or equal to 0")

    profile = get_ai_runtime_accelerator(cloud, accelerator_type)
    monthly_gpu_hours = hours * profile["gpu_count"]
    dbu_per_node_hour = (
        profile["gpu_count"] * profile["dbu_per_gpu_hour"]
    )
    return {
        **profile,
        "runtime_hours": hours,
        "monthly_gpu_hours": monthly_gpu_hours,
        "dbu_per_node_hour": dbu_per_node_hour,
        "monthly_dbus": hours * dbu_per_node_hour,
    }
