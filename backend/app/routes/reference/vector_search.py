"""Vector Search reference endpoints."""
import logging
from fastapi import APIRouter, Query, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.cache import ref_cache
from app.services.validators import validate_cloud, validate_vector_search_mode

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/vector-search/list", tags=["Vector Search"])
def list_vector_search_modes(db: Session = Depends(get_db)):
    cached = ref_cache.get("vector_search_list")
    if cached is not None:
        return cached

    try:
        query = text("""
            SELECT DISTINCT size_or_model as mode
            FROM lakemeter.sync_product_serverless_rates
            WHERE product = 'vector_search'
            ORDER BY mode
        """)
        modes = [r.mode for r in db.execute(query).fetchall()]

        response = {"success": True, "data": {"count": len(modes), "modes": modes}}
        ref_cache.set("vector_search_list", response)
        return response
    except Exception as e:
        logger.error(f"Error fetching Vector Search mode list: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}


@router.get("/vector-search/modes", tags=["Vector Search"])
def get_vector_search_modes(
    cloud: str = Query(..., description="Cloud provider (required): AWS, AZURE, GCP"),
    mode: str = Query(None, description="Filter by mode"),
    db: Session = Depends(get_db),
):
    error = validate_cloud(cloud)
    if error:
        return error

    if mode:
        error = validate_vector_search_mode(mode, cloud, db)
        if error:
            return error

    try:
        where_conditions = ["product = 'vector_search'", "cloud = :cloud"]
        params = {"cloud": cloud.upper()}

        if mode:
            where_conditions.append("size_or_model = :mode")
            params["mode"] = mode

        where_clause = "WHERE " + " AND ".join(where_conditions)

        query = text(f"""
            SELECT
                cloud, size_or_model as mode, dbu_rate, input_divisor,
                CASE
                    WHEN input_divisor::bigint = 2000000 THEN 2
                    WHEN input_divisor::bigint = 64000000 THEN 64
                    ELSE input_divisor::bigint / 1000000.0
                END as vector_capacity_millions
            FROM lakemeter.sync_product_serverless_rates
            {where_clause}
            ORDER BY cloud, mode
        """)
        results = db.execute(query, params).fetchall()

        modes_list = [
            {
                "cloud": r.cloud,
                "mode": r.mode,
                "dbu_per_hour": float(r.dbu_rate) if r.dbu_rate else None,
                "vector_capacity_millions": float(r.vector_capacity_millions),
                "description": f"{r.vector_capacity_millions}M vectors per pricing unit",
            }
            for r in results
        ]

        return {
            "success": True,
            "data": {
                "cloud_filter": cloud.upper(),
                "mode_filter": mode if mode else None,
                "count": len(modes_list),
                "modes": modes_list,
            },
        }
    except Exception as e:
        logger.error(f"Error fetching Vector Search modes: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}
