"""Cloud regions and tiers reference endpoints."""
import logging
from fastapi import APIRouter, Query, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.cache import ref_cache
from app.services.validators import validate_cloud

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/regions", tags=["Cloud & Regions"])
def get_regions(
    cloud: str = Query(None, description="Cloud provider: AWS, AZURE, GCP"),
    db: Session = Depends(get_db),
):
    if cloud:
        error = validate_cloud(cloud)
        if error:
            return error

    cache_key = ref_cache.get("regions", cloud=cloud)
    if cache_key is not None:
        return cache_key

    try:
        if cloud:
            query = text("""
                SELECT DISTINCT region_code, sku_region as region_name
                FROM lakemeter.sync_ref_sku_region_map
                WHERE cloud = :cloud
                ORDER BY sku_region
            """)
            result = db.execute(query, {"cloud": cloud.upper()})
            results = result.fetchall()

            response = {
                "success": True,
                "data": {
                    "cloud": cloud.upper(),
                    "count": len(results),
                    "regions": [
                        {"region_code": r.region_code, "sku_region": r.region_name}
                        for r in results
                    ],
                },
            }
        else:
            query = text("""
                SELECT DISTINCT cloud, region_code, sku_region as region_name
                FROM lakemeter.sync_ref_sku_region_map
                ORDER BY cloud, sku_region
            """)
            result = db.execute(query)
            results = result.fetchall()

            by_cloud = {}
            for r in results:
                if r.cloud not in by_cloud:
                    by_cloud[r.cloud] = []
                by_cloud[r.cloud].append(
                    {"region_code": r.region_code, "sku_region": r.region_name}
                )

            response = {"success": True, "data": by_cloud}

        ref_cache.set("regions", response, cloud=cloud)
        return response
    except Exception as e:
        logger.error(f"Error fetching regions: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}


@router.get("/tiers", tags=["Cloud & Regions"])
def get_tiers(
    cloud: str = Query(None, description="Cloud provider: AWS, AZURE, GCP"),
    db: Session = Depends(get_db),
):
    if cloud:
        error = validate_cloud(cloud)
        if error:
            return error

    cached = ref_cache.get("tiers", cloud=cloud)
    if cached is not None:
        return cached

    try:
        if cloud:
            query = text("""
                SELECT tier, display_name
                FROM lakemeter.ref_cloud_tiers
                WHERE cloud = :cloud
                ORDER BY
                    CASE tier
                        WHEN 'STANDARD' THEN 1
                        WHEN 'PREMIUM' THEN 2
                        WHEN 'ENTERPRISE' THEN 3
                    END
            """)
            result = db.execute(query, {"cloud": cloud.upper()})
            results = result.fetchall()

            response = {
                "success": True,
                "data": {
                    "cloud": cloud.upper(),
                    "count": len(results),
                    "tiers": [
                        {"tier": r.tier, "display_name": r.display_name}
                        for r in results
                    ],
                },
            }
        else:
            query = text("""
                SELECT cloud, tier, display_name
                FROM lakemeter.ref_cloud_tiers
                ORDER BY cloud,
                    CASE tier
                        WHEN 'STANDARD' THEN 1
                        WHEN 'PREMIUM' THEN 2
                        WHEN 'ENTERPRISE' THEN 3
                    END
            """)
            result = db.execute(query)
            results = result.fetchall()

            by_cloud = {}
            for r in results:
                if r.cloud not in by_cloud:
                    by_cloud[r.cloud] = []
                by_cloud[r.cloud].append(
                    {"tier": r.tier, "display_name": r.display_name}
                )

            response = {"success": True, "data": by_cloud}

        ref_cache.set("tiers", response, cloud=cloud)
        return response
    except Exception as e:
        logger.error(f"Error fetching tiers: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}
