"""DBU pricing reference endpoints."""
import logging
from fastapi import APIRouter, Query, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.cache import ref_cache
from app.services.validators import (
    validate_cloud,
    validate_region,
    validate_tier,
    validate_product_type,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/pricing/product-types", tags=["Pricing - DBU Rates"])
def list_product_types(
    cloud: str = Query(..., description="Cloud provider (required): AWS, AZURE, GCP"),
    region: str = Query(..., description="Region code (required)"),
    tier: str = Query(..., description="Pricing tier (required): STANDARD, PREMIUM, ENTERPRISE"),
    db: Session = Depends(get_db),
):
    error = validate_cloud(cloud)
    if error:
        return error
    error = validate_region(cloud, region, db)
    if error:
        return error
    error = validate_tier(cloud, tier, db)
    if error:
        return error

    cached = ref_cache.get("product_types", cloud=cloud, region=region, tier=tier)
    if cached is not None:
        return cached

    try:
        query = text("""
            SELECT DISTINCT product_type
            FROM lakemeter.sync_pricing_dbu_rates
            WHERE cloud = :cloud AND region = :region AND tier = :tier
            ORDER BY product_type
        """)
        product_types = [r.product_type for r in db.execute(
            query, {"cloud": cloud.upper(), "region": region, "tier": tier.upper()}
        ).fetchall()]

        response = {
            "success": True,
            "data": {
                "cloud": cloud.upper(),
                "region": region,
                "tier": tier.upper(),
                "count": len(product_types),
                "product_types": product_types,
            },
        }
        ref_cache.set("product_types", response, cloud=cloud, region=region, tier=tier)
        return response
    except Exception as e:
        logger.error(f"Error fetching product types: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}


@router.get("/pricing/dbu-rates", tags=["Pricing - DBU Rates"])
def get_dbu_rates(
    cloud: str = Query(..., description="Cloud provider (required): AWS, AZURE, GCP"),
    region: str = Query(..., description="Region code (required)"),
    tier: str = Query(..., description="Pricing tier (required): STANDARD, PREMIUM, ENTERPRISE"),
    product_type: str = Query(None, description="Filter by product type"),
    db: Session = Depends(get_db),
):
    error = validate_cloud(cloud)
    if error:
        return error
    error = validate_region(cloud, region, db)
    if error:
        return error
    error = validate_tier(cloud, tier, db)
    if error:
        return error

    if product_type:
        error = validate_product_type(cloud, region, product_type, db)
        if error:
            return error

    try:
        where_conditions = ["cloud = :cloud", "region = :region", "tier = :tier"]
        params = {"cloud": cloud.upper(), "region": region, "tier": tier.upper()}

        if product_type:
            where_conditions.append("product_type = :product_type")
            params["product_type"] = product_type.upper()

        where_clause = "WHERE " + " AND ".join(where_conditions)

        query = text(f"""
            SELECT sku_name, product_type, cloud, region, tier, price_per_dbu
            FROM lakemeter.sync_pricing_dbu_rates
            {where_clause}
            ORDER BY product_type, sku_name
        """)
        results = db.execute(query, params).fetchall()

        dbu_rates = [
            {
                "sku_name": r.sku_name,
                "product_type": r.product_type,
                "cloud": r.cloud,
                "region": r.region,
                "tier": r.tier,
                "price_per_dbu": float(r.price_per_dbu) if r.price_per_dbu else None,
            }
            for r in results
        ]

        return {
            "success": True,
            "data": {
                "cloud": cloud.upper(),
                "region": region,
                "tier": tier.upper(),
                "product_type_filter": product_type.upper() if product_type else None,
                "count": len(dbu_rates),
                "dbu_rates": dbu_rates,
            },
        }
    except Exception as e:
        logger.error(f"Error fetching DBU rates: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}
