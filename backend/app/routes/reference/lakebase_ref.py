"""Lakebase reference endpoints."""
from fastapi import APIRouter, Query

from app.services.lakebase_pricing import LAKEBASE_AUTOSCALE_CU_VALUES, LAKEBASE_MAX_AUTOSCALE_SPREAD_CU

router = APIRouter()

_DOCUMENTED_MAX_CONNECTIONS = {
    0.5: 105,
    1: 218,
    2: 443,
    3: 668,
    4: 894,
    5: 1119,
    6: 1344,
    7: 1570,
    8: 1795,
    9: 2020,
    10: 2246,
    12: 2696,
    14: 3147,
    16: 3597,
}


def _max_connections_for_cu(cu: float) -> int:
    if cu in _DOCUMENTED_MAX_CONNECTIONS:
        return _DOCUMENTED_MAX_CONNECTIONS[cu]
    return 3993


LAKEBASE_FIXED_CU_VALUES = [80, 96, 112]

AUTOSCALE_SIZES = [
    {
        "cu": cu,
        "ram_gb": cu * 2,
        "max_connections": _max_connections_for_cu(cu),
        "type": "autoscale",
    }
    for cu in LAKEBASE_AUTOSCALE_CU_VALUES
]

FIXED_SIZES = [
    {"cu": cu, "ram_gb": cu * 2, "max_connections": 3993, "type": "fixed"}
    for cu in LAKEBASE_FIXED_CU_VALUES
]

VALID_CU_SIZES = [s["cu"] for s in AUTOSCALE_SIZES + FIXED_SIZES]

DBU_PER_CU_HOUR = {
    "AWS": {"PREMIUM": 0.230, "ENTERPRISE": 0.213},
    "AZURE": {"PREMIUM": 1.0, "ENTERPRISE": 1.0, "STANDARD": 1.0},
    "GCP": {"PREMIUM": 1.0, "ENTERPRISE": 1.0},
}


@router.get("/lakebase/list", tags=["Lakebase"])
def list_lakebase_sizes():
    return {
        "success": True,
        "data": {
            "total_sizes": len(VALID_CU_SIZES),
            "all_cu_values": VALID_CU_SIZES,
            "autoscale_sizes": AUTOSCALE_SIZES,
            "fixed_sizes": FIXED_SIZES,
            "dbu_per_cu_hour": DBU_PER_CU_HOUR,
            "notes": {
                "ram": "Each CU allocates approximately 2 GB RAM",
                "autoscale": f"Autoscaling supported for 0.5-64 CU. Range constraint: max - min <= {int(LAKEBASE_MAX_AUTOSCALE_SPREAD_CU)} CU. Supports scale-to-zero.",
                "fixed": "Larger fixed-size computes use the documented 80, 96, and 112 CU sizes and do not support autoscaling.",
            },
        },
    }


@router.get("/lakebase/calculate", tags=["Lakebase"])
def calculate_lakebase_dbu(
    cu_size: float = Query(..., description="Compute Unit size (required): 0.5 to 112"),
    cloud: str = Query(..., description="Cloud provider (required): AWS, AZURE, GCP"),
    tier: str = Query(..., description="Pricing tier (required): PREMIUM, ENTERPRISE"),
    read_replicas: int = Query(0, ge=0, description="Number of read replicas (0 = primary only)"),
):
    if cu_size not in VALID_CU_SIZES:
        return {
            "success": False,
            "error": {
                "code": "INVALID_CU_SIZE",
                "message": f"Invalid CU size '{cu_size}'. See /api/v1/lakebase/list for valid values.",
                "field": "cu_size",
                "allowed_values": VALID_CU_SIZES,
            },
        }

    cloud_upper = cloud.upper()
    if cloud_upper not in ["AWS", "AZURE", "GCP"]:
        return {
            "success": False,
            "error": {
                "code": "INVALID_CLOUD",
                "message": f"Invalid cloud '{cloud}'. Must be AWS, AZURE, or GCP.",
                "field": "cloud",
                "allowed_values": ["AWS", "AZURE", "GCP"],
            },
        }

    tier_upper = tier.upper()
    cloud_rates = DBU_PER_CU_HOUR.get(cloud_upper, {})
    if tier_upper not in cloud_rates:
        return {
            "success": False,
            "error": {
                "code": "INVALID_TIER",
                "message": f"Invalid tier '{tier}' for cloud '{cloud_upper}'. Must be one of: {list(cloud_rates.keys())}",
                "field": "tier",
                "allowed_values": list(cloud_rates.keys()),
            },
        }

    dbu_per_cu_hour = cloud_rates[tier_upper]
    total_computes = 1 + read_replicas
    dbu_per_hour_per_compute = cu_size * dbu_per_cu_hour
    total_dbu_per_hour = dbu_per_hour_per_compute * total_computes
    cu_spec_type = "autoscale" if cu_size <= 32 else "fixed"
    ram_gb = int(cu_size * 2)

    return {
        "success": True,
        "data": {
            "cu_size": cu_size,
            "cu_type": cu_spec_type,
            "ram_gb": ram_gb,
            "cloud": cloud_upper,
            "tier": tier_upper,
            "read_replicas": read_replicas,
            "total_computes": total_computes,
            "dbu_per_cu_hour": dbu_per_cu_hour,
            "dbu_per_hour_per_compute": round(dbu_per_hour_per_compute, 6),
            "total_dbu_per_hour": round(total_dbu_per_hour, 6),
            "calculation": f"{cu_size} CU × {dbu_per_cu_hour} DBU/CU-hr × {total_computes} compute(s) = {round(total_dbu_per_hour, 6)} DBU/hour",
            "description": f"Lakebase {cu_spec_type} compute with {cu_size} CU (~{ram_gb} GB RAM) and {read_replicas} read replica(s)",
        },
    }
