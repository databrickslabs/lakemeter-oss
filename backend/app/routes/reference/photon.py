"""Photon multiplier reference endpoints."""
import logging
from fastapi import APIRouter, Query, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.cache import ref_cache
from app.services.validators import validate_cloud, validate_photon_sku_type

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/photon/list", tags=["Photon Multipliers"])
def list_photon_sku_types(
    cloud: str = Query(..., description="Cloud provider (required): AWS, AZURE, GCP"),
    db: Session = Depends(get_db),
):
    error = validate_cloud(cloud)
    if error:
        return error

    cached = ref_cache.get("photon_list", cloud=cloud)
    if cached is not None:
        return cached

    try:
        query = text("""
            SELECT DISTINCT sku_type
            FROM lakemeter.sync_ref_dbu_multipliers
            WHERE feature = 'photon' AND cloud = :cloud
            ORDER BY sku_type
        """)
        sku_types = [r.sku_type for r in db.execute(query, {"cloud": cloud.upper()}).fetchall()]

        response = {
            "success": True,
            "data": {"cloud": cloud.upper(), "count": len(sku_types), "sku_types": sku_types},
        }
        ref_cache.set("photon_list", response, cloud=cloud)
        return response
    except Exception as e:
        logger.error(f"Error fetching Photon SKU types: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}


@router.get("/photon/multipliers", tags=["Photon Multipliers"])
def get_photon_multipliers(
    cloud: str = Query(..., description="Cloud provider (required): AWS, AZURE, GCP"),
    sku_type: str = Query(None, description="Filter by SKU type"),
    db: Session = Depends(get_db),
):
    error = validate_cloud(cloud)
    if error:
        return error

    if sku_type:
        error = validate_photon_sku_type(cloud, sku_type, db)
        if error:
            return error

    cached = ref_cache.get("photon_multipliers", cloud=cloud, sku_type=sku_type)
    if cached is not None:
        return cached

    try:
        where_conditions = ["feature = 'photon'", "cloud = :cloud"]
        params = {"cloud": cloud.upper()}

        if sku_type:
            where_conditions.append("sku_type = :sku_type")
            params["sku_type"] = sku_type

        where_clause = "WHERE " + " AND ".join(where_conditions)

        query = text(f"""
            SELECT cloud, feature, multiplier, sku_type, category
            FROM lakemeter.sync_ref_dbu_multipliers
            {where_clause}
            ORDER BY sku_type, category
        """)
        results = db.execute(query, params).fetchall()

        multipliers = [
            {
                "cloud": r.cloud,
                "sku_type": r.sku_type,
                "category": r.category,
                "multiplier": float(r.multiplier),
            }
            for r in results
        ]

        response = {
            "success": True,
            "data": {
                "cloud_filter": cloud.upper(),
                "sku_type_filter": sku_type if sku_type else None,
                "count": len(multipliers),
                "multipliers": multipliers,
            },
        }
        ref_cache.set("photon_multipliers", response, cloud=cloud, sku_type=sku_type)
        return response
    except Exception as e:
        logger.error(f"Error fetching Photon multipliers: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}
