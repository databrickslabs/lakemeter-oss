"""Lakebase reference endpoints."""
from fastapi import APIRouter, Query

router = APIRouter()

AUTOSCALE_SIZES = [
    {"cu": 0.5, "ram_gb": 1, "max_connections": 104, "type": "autoscale"},
    {"cu": 1, "ram_gb": 2, "max_connections": 209, "type": "autoscale"},
    {"cu": 2, "ram_gb": 4, "max_connections": 419, "type": "autoscale"},
    {"cu": 3, "ram_gb": 6, "max_connections": 629, "type": "autoscale"},
    {"cu": 4, "ram_gb": 8, "max_connections": 839, "type": "autoscale"},
    {"cu": 5, "ram_gb": 10, "max_connections": 1049, "type": "autoscale"},
    {"cu": 6, "ram_gb": 12, "max_connections": 1258, "type": "autoscale"},
    {"cu": 7, "ram_gb": 14, "max_connections": 1468, "type": "autoscale"},
    {"cu": 8, "ram_gb": 16, "max_connections": 1678, "type": "autoscale"},
    {"cu": 9, "ram_gb": 18, "max_connections": 1888, "type": "autoscale"},
    {"cu": 10, "ram_gb": 20, "max_connections": 2098, "type": "autoscale"},
    {"cu": 12, "ram_gb": 24, "max_connections": 2517, "type": "autoscale"},
    {"cu": 14, "ram_gb": 28, "max_connections": 2937, "type": "autoscale"},
    {"cu": 16, "ram_gb": 32, "max_connections": 3357, "type": "autoscale"},
    {"cu": 24, "ram_gb": 48, "max_connections": 4000, "type": "autoscale"},
    {"cu": 28, "ram_gb": 56, "max_connections": 4000, "type": "autoscale"},
    {"cu": 32, "ram_gb": 64, "max_connections": 4000, "type": "autoscale"},
]

FIXED_SIZES = [
    {"cu": 36, "ram_gb": 72, "max_connections": 4000, "type": "fixed"},
    {"cu": 40, "ram_gb": 80, "max_connections": 4000, "type": "fixed"},
    {"cu": 44, "ram_gb": 88, "max_connections": 4000, "type": "fixed"},
    {"cu": 48, "ram_gb": 96, "max_connections": 4000, "type": "fixed"},
    {"cu": 52, "ram_gb": 104, "max_connections": 4000, "type": "fixed"},
    {"cu": 56, "ram_gb": 112, "max_connections": 4000, "type": "fixed"},
    {"cu": 60, "ram_gb": 120, "max_connections": 4000, "type": "fixed"},
    {"cu": 64, "ram_gb": 128, "max_connections": 4000, "type": "fixed"},
    {"cu": 72, "ram_gb": 144, "max_connections": 4000, "type": "fixed"},
    {"cu": 80, "ram_gb": 160, "max_connections": 4000, "type": "fixed"},
    {"cu": 88, "ram_gb": 176, "max_connections": 4000, "type": "fixed"},
    {"cu": 96, "ram_gb": 192, "max_connections": 4000, "type": "fixed"},
    {"cu": 104, "ram_gb": 208, "max_connections": 4000, "type": "fixed"},
    {"cu": 112, "ram_gb": 224, "max_connections": 4000, "type": "fixed"},
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
                "autoscale": "Autoscaling supported for 0.5-32 CU. Range constraint: max - min <= 8 CU. Supports scale-to-zero.",
                "fixed": "Fixed-size computes (36-112 CU) do not support autoscaling.",
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
