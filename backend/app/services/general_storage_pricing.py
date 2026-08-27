"""Canonical usage conversion for Databricks Default Storage."""
import math


GENERAL_STORAGE_SKU = "DATABRICKS_STORAGE"
GENERAL_STORAGE_UNITS = {"gb", "tb"}
GB_PER_TB = 1024
STORED_DATA_DSU_PER_GB_MONTH = 1.0
GENERAL_STORAGE_OPERATION_DSU_RATES = {
    "aws": {
        "tier_1_per_thousand": 0.2174,
        "tier_2_per_thousand": 0.0174,
    },
    "azure": {
        "tier_1_per_thousand": 0.3535,
        "tier_2_per_thousand": 0.0226,
    },
    "gcp": {
        "tier_1_per_thousand": 0.2174,
        "tier_2_per_thousand": 0.0174,
    },
}


def _non_negative_number(value, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")
    if number < 0:
        raise ValueError(
            f"{field_name} must be greater than or equal to 0"
        )
    return number


def get_general_storage_operation_dsu_rates(cloud: str) -> dict:
    """Return official Tier 1 and Tier 2 DSU multipliers for a cloud."""
    normalized_cloud = (cloud or "").strip().lower()
    rates = GENERAL_STORAGE_OPERATION_DSU_RATES.get(normalized_cloud)
    if rates is None:
        raise ValueError("cloud must be one of: aws, azure, gcp")
    return dict(rates)


def calculate_general_storage_usage(
    quantity: float,
    unit: str,
    cloud: str = "aws",
    tier_1_operations_thousands: float = 0,
    tier_2_operations_thousands: float = 0,
) -> dict:
    """Convert stored data and API operations into monthly DSUs."""
    value = _non_negative_number(quantity, "quantity")
    tier_1_operations = _non_negative_number(
        tier_1_operations_thousands,
        "tier_1_operations_thousands",
    )
    tier_2_operations = _non_negative_number(
        tier_2_operations_thousands,
        "tier_2_operations_thousands",
    )

    normalized_unit = (unit or "").strip().lower()
    if normalized_unit not in GENERAL_STORAGE_UNITS:
        raise ValueError("unit must be one of: gb, tb")

    operation_rates = get_general_storage_operation_dsu_rates(cloud)
    billable_gb = value * GB_PER_TB if normalized_unit == "tb" else value
    stored_data_dsu = billable_gb * STORED_DATA_DSU_PER_GB_MONTH
    tier_1_dsu = (
        tier_1_operations
        * operation_rates["tier_1_per_thousand"]
    )
    tier_2_dsu = (
        tier_2_operations
        * operation_rates["tier_2_per_thousand"]
    )
    return {
        "quantity": value,
        "unit": normalized_unit,
        "billable_gb_months": billable_gb,
        "tier_1_operations_thousands": tier_1_operations,
        "tier_2_operations_thousands": tier_2_operations,
        "dsu_rates": {
            "stored_data_per_gb_month": STORED_DATA_DSU_PER_GB_MONTH,
            **operation_rates,
        },
        "stored_data_dsu": stored_data_dsu,
        "tier_1_operations_dsu": tier_1_dsu,
        "tier_2_operations_dsu": tier_2_dsu,
        "total_dsu": stored_data_dsu + tier_1_dsu + tier_2_dsu,
    }
