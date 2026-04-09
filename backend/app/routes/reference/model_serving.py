"""Model Serving reference endpoints."""
import json
import logging
import os
from pathlib import Path
from fastapi import APIRouter, Query, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.cache import ref_cache
from app.services.validators import validate_cloud

logger = logging.getLogger(__name__)
router = APIRouter()

# Load descriptions from pricing bundle for human-readable names
_GPU_DESCRIPTIONS: dict = {}
try:
    _bundle_path = Path(__file__).resolve().parents[2] / "static" / "pricing" / "model-serving-rates.json"
    if _bundle_path.exists():
        with open(_bundle_path) as f:
            for key, val in json.load(f).items():
                # key format: "cloud:gpu_type"
                parts = key.split(":", 1)
                if len(parts) == 2:
                    _GPU_DESCRIPTIONS[key] = val.get("description", "")
except Exception:
    pass


def _gpu_display_name(gpu_type: str, cloud: str) -> str:
    """Build a human-readable name for a GPU type."""
    # Try pricing bundle description first
    desc = _GPU_DESCRIPTIONS.get(f"{cloud.lower()}:{gpu_type}", "")
    if desc:
        return desc
    # Fallback: humanize the key
    name = gpu_type.replace("_", " ").replace("gpu ", "GPU ").title()
    if gpu_type == "cpu":
        return "CPU"
    return name


@router.get("/model-serving/gpu-types", tags=["Model Serving"])
def get_model_serving_gpu_types(
    cloud: str = Query(..., description="Cloud provider: AWS, AZURE, GCP (required)"),
    db: Session = Depends(get_db),
):
    error = validate_cloud(cloud)
    if error:
        return error

    cached = ref_cache.get("model_serving_gpu_types", cloud=cloud)
    if cached is not None:
        return cached

    try:
        query = text("""
            SELECT size_or_model as gpu_type, dbu_rate
            FROM lakemeter.sync_product_serverless_rates
            WHERE product = 'model_serving' AND cloud = :cloud
            ORDER BY size_or_model
        """)
        results = db.execute(query, {"cloud": cloud.upper()}).fetchall()

        response = {
            "success": True,
            "data": {
                "cloud": cloud.upper(),
                "count": len(results),
                "gpu_types": [
                    {
                        "gpu_type": r.gpu_type,
                        "name": _gpu_display_name(r.gpu_type, cloud),
                        "dbu_rate": float(r.dbu_rate) if r.dbu_rate else None,
                    }
                    for r in results
                ],
                "scale_out_presets": {
                    "small": {"concurrency": 4, "dbu_multiplier": 4, "range": "4"},
                    "medium": {"concurrency": 12, "dbu_multiplier": 12, "range": "8-16"},
                    "large": {"concurrency": 40, "dbu_multiplier": 40, "range": "16-64"},
                },
                "custom_scale_out": {
                    "min": 4,
                    "step": 4,
                    "note": "Custom concurrency must be a multiple of 4 (4, 8, 12, 16, ...)",
                },
            },
        }
        ref_cache.set("model_serving_gpu_types", response, cloud=cloud)
        return response
    except Exception as e:
        logger.error(f"Error fetching Model Serving GPU types: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}
