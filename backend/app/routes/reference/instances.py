"""Instance types and VM pricing reference endpoints."""
import logging
from fastapi import APIRouter, Query, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.cache import ref_cache
from app.services.validators import (
    validate_cloud,
    validate_region,
    validate_instance_type,
    validate_instance_family,
    validate_pricing_tier,
    validate_payment_option,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/instances/families", tags=["Compute - Instance Types"])
def get_instance_families(db: Session = Depends(get_db)):
    cached = ref_cache.get("instance_families")
    if cached is not None:
        return cached

    try:
        query = text("""
            SELECT DISTINCT instance_family
            FROM lakemeter.sync_ref_instance_dbu_rates
            ORDER BY instance_family
        """)
        result = db.execute(query)
        results = result.fetchall()

        response = {
            "success": True,
            "data": {
                "count": len(results),
                "instance_families": [r.instance_family for r in results],
            },
        }
        ref_cache.set("instance_families", response)
        return response
    except Exception as e:
        logger.error(f"Error fetching instance families: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}


@router.get("/instances/types", tags=["Compute - Instance Types"])
def get_instance_types(
    cloud: str = Query(..., description="Cloud provider: AWS, AZURE, GCP (required)"),
    region: str = Query(..., description="Region code (required, filters by region availability)"),
    instance_family: str = Query(None, description="Filter by instance family"),
    min_vcpus: int = Query(None, ge=1),
    max_vcpus: int = Query(None, ge=1),
    min_memory_gb: float = Query(None, ge=0),
    max_memory_gb: float = Query(None, ge=0),
    min_dbu_rate: float = Query(None, ge=0),
    max_dbu_rate: float = Query(None, ge=0),
    limit: int = Query(1000, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    error = validate_cloud(cloud)
    if error:
        return error

    try:
        error = validate_region(cloud, region, db)
        if error:
            return error

        if instance_family:
            error = validate_instance_family(instance_family, db)
            if error:
                return error

        where_conditions = ["r.cloud = :cloud", "v.region = :region"]
        params = {"cloud": cloud.upper(), "region": region, "limit": limit, "offset": offset}

        join_clause = "INNER JOIN lakemeter.sync_pricing_vm_costs v ON r.cloud = v.cloud AND r.instance_type = v.instance_type"

        if instance_family:
            where_conditions.append("r.instance_family = :instance_family")
            params["instance_family"] = instance_family
        if min_vcpus is not None:
            where_conditions.append("r.vcpus >= :min_vcpus")
            params["min_vcpus"] = min_vcpus
        if max_vcpus is not None:
            where_conditions.append("r.vcpus <= :max_vcpus")
            params["max_vcpus"] = max_vcpus
        if min_memory_gb is not None:
            where_conditions.append("r.memory_gb >= :min_memory_gb")
            params["min_memory_gb"] = min_memory_gb
        if max_memory_gb is not None:
            where_conditions.append("r.memory_gb <= :max_memory_gb")
            params["max_memory_gb"] = max_memory_gb
        if min_dbu_rate is not None:
            where_conditions.append("r.dbu_rate >= :min_dbu_rate")
            params["min_dbu_rate"] = min_dbu_rate
        if max_dbu_rate is not None:
            where_conditions.append("r.dbu_rate <= :max_dbu_rate")
            params["max_dbu_rate"] = max_dbu_rate

        where_clause = " AND ".join(where_conditions)
        count_query = text(f"""
            SELECT COUNT(DISTINCT r.instance_type) as total
            FROM lakemeter.sync_ref_instance_dbu_rates r
            {join_clause}
            WHERE {where_clause}
        """)
        total_count = db.execute(count_query, params).scalar()

        query = text(f"""
            SELECT DISTINCT
                r.instance_type, r.vcpus, r.memory_gb, r.instance_family, r.dbu_rate
            FROM lakemeter.sync_ref_instance_dbu_rates r
            {join_clause}
            WHERE {where_clause}
            ORDER BY r.instance_type
            LIMIT :limit OFFSET :offset
        """)
        results = db.execute(query, params).fetchall()

        filters_applied = {}
        if instance_family:
            filters_applied["instance_family"] = instance_family
        if min_vcpus is not None:
            filters_applied["min_vcpus"] = min_vcpus
        if max_vcpus is not None:
            filters_applied["max_vcpus"] = max_vcpus
        if min_memory_gb is not None:
            filters_applied["min_memory_gb"] = min_memory_gb
        if max_memory_gb is not None:
            filters_applied["max_memory_gb"] = max_memory_gb
        if min_dbu_rate is not None:
            filters_applied["min_dbu_rate"] = min_dbu_rate
        if max_dbu_rate is not None:
            filters_applied["max_dbu_rate"] = max_dbu_rate

        return {
            "success": True,
            "data": {
                "cloud": cloud.upper(),
                "region": region,
                "filters": filters_applied if filters_applied else None,
                "total": total_count,
                "count": len(results),
                "limit": limit,
                "offset": offset,
                "has_more": (offset + len(results)) < total_count,
                "instance_types": [
                    {
                        "instance_type": r.instance_type,
                        "vcpus": r.vcpus,
                        "memory_gb": float(r.memory_gb),
                        "instance_family": r.instance_family,
                        "dbu_rate": float(r.dbu_rate),
                    }
                    for r in results
                ],
            },
        }
    except Exception as e:
        logger.error(f"Error fetching instance types: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}


@router.get("/instances/vm-costs", tags=["Compute - Instance Types"])
def get_instance_vm_costs(
    cloud: str = Query(..., description="Cloud provider: AWS, AZURE, GCP (required)"),
    region: str = Query(..., description="Region code (required)"),
    instance_type: str = Query(..., description="Instance type (required)"),
    pricing_tier: str = Query(None, description="Filter by pricing tier"),
    payment_option: str = Query(None, description="Filter by payment option"),
    db: Session = Depends(get_db),
):
    error = validate_cloud(cloud)
    if error:
        return error

    if pricing_tier:
        error = validate_pricing_tier(pricing_tier)
        if error:
            return error

    if payment_option:
        error = validate_payment_option(payment_option)
        if error:
            return error

    # Check cache first (keyed by all params to avoid stale filtered results)
    cache_key = f"vm_costs:{cloud}:{region}:{instance_type}:{pricing_tier}:{payment_option}"
    cached = ref_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        error = validate_region(cloud, region, db)
        if error:
            return error

        error = validate_instance_type(cloud, instance_type, db)
        if error:
            return error

        # Get instance specs
        specs_query = text("""
            SELECT vcpus, memory_gb, dbu_rate, instance_family
            FROM lakemeter.sync_ref_instance_dbu_rates
            WHERE cloud = :cloud AND instance_type = :instance_type
        """)
        specs_row = db.execute(specs_query, {"cloud": cloud.upper(), "instance_type": instance_type}).fetchone()
        instance_specs = {
            "vcpus": specs_row.vcpus,
            "memory_gb": float(specs_row.memory_gb),
            "dbu_rate": float(specs_row.dbu_rate),
            "instance_family": specs_row.instance_family,
        } if specs_row else None

        where_conditions = ["cloud = :cloud", "region = :region", "instance_type = :instance_type"]
        params = {"cloud": cloud.upper(), "region": region, "instance_type": instance_type}

        if pricing_tier:
            where_conditions.append("pricing_tier = :pricing_tier")
            params["pricing_tier"] = pricing_tier
        if payment_option:
            where_conditions.append("payment_option = :payment_option")
            params["payment_option"] = payment_option

        where_clause = " AND ".join(where_conditions)

        query = text(f"""
            SELECT pricing_tier, payment_option, cost_per_hour
            FROM lakemeter.sync_pricing_vm_costs
            WHERE {where_clause}
            ORDER BY
                CASE
                    WHEN pricing_tier = 'on_demand' THEN 1
                    WHEN pricing_tier = 'spot' THEN 2
                    WHEN pricing_tier = 'reserved_1y' THEN 3
                    WHEN pricing_tier = 'reserved_3y' THEN 4
                    ELSE 5
                END,
                CASE payment_option
                    WHEN 'NA' THEN 1
                    WHEN 'no_upfront' THEN 2
                    WHEN 'partial_upfront' THEN 3
                    WHEN 'all_upfront' THEN 4
                    ELSE 5
                END
        """)
        results = db.execute(query, params).fetchall()

        if not results:
            return {
                "success": False,
                "error": {
                    "code": "NO_PRICING_DATA",
                    "message": f"No VM pricing data found for {instance_type} in {cloud.upper()} {region} with the specified filters.",
                    "field": "instance_type",
                },
            }

        response_data = {
            "cloud": cloud.upper(),
            "region": region,
            "instance_type": instance_type,
            "instance_specs": instance_specs,
        }
        if pricing_tier:
            response_data["filter_pricing_tier"] = pricing_tier
        if payment_option:
            response_data["filter_payment_option"] = payment_option

        response_data["pricing_options"] = [
            {
                "pricing_tier": r.pricing_tier,
                "payment_option": r.payment_option,
                "cost_per_hour": float(r.cost_per_hour),
            }
            for r in results
        ]

        response = {"success": True, "data": response_data}
        ref_cache.set(cache_key, response)
        return response
    except Exception as e:
        logger.error(f"Error fetching instance VM costs: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}


@router.get("/instances/vm-pricing-options", tags=["Compute - Instance Types"])
def get_vm_pricing_options(
    cloud: str = Query(None, description="Filter by cloud provider"),
    db: Session = Depends(get_db),
):
    if cloud:
        error = validate_cloud(cloud)
        if error:
            return error

    cached = ref_cache.get("vm_pricing_options", cloud=cloud)
    if cached is not None:
        return cached

    try:
        if cloud:
            query = text("""
                SELECT DISTINCT
                    pricing_tier, payment_option,
                    CASE pricing_tier
                        WHEN 'on_demand' THEN 1 WHEN 'spot' THEN 2
                        WHEN 'reserved_1y' THEN 3 WHEN 'reserved_3y' THEN 4 ELSE 5
                    END as tier_order,
                    CASE payment_option
                        WHEN 'NA' THEN 1 WHEN 'no_upfront' THEN 2
                        WHEN 'partial_upfront' THEN 3 WHEN 'all_upfront' THEN 4 ELSE 5
                    END as option_order
                FROM lakemeter.sync_pricing_vm_costs
                WHERE cloud = :cloud
                ORDER BY tier_order, option_order
            """)
            results = db.execute(query, {"cloud": cloud.upper()}).fetchall()

            response = {
                "success": True,
                "data": {
                    "cloud": cloud.upper(),
                    "count": len(results),
                    "pricing_options": [
                        {"pricing_tier": r.pricing_tier, "payment_option": r.payment_option}
                        for r in results
                    ],
                },
            }
        else:
            query = text("""
                SELECT DISTINCT
                    cloud, pricing_tier, payment_option,
                    CASE pricing_tier
                        WHEN 'on_demand' THEN 1 WHEN 'spot' THEN 2
                        WHEN 'reserved_1y' THEN 3 WHEN 'reserved_3y' THEN 4 ELSE 5
                    END as tier_order,
                    CASE payment_option
                        WHEN 'NA' THEN 1 WHEN 'no_upfront' THEN 2
                        WHEN 'partial_upfront' THEN 3 WHEN 'all_upfront' THEN 4 ELSE 5
                    END as option_order
                FROM lakemeter.sync_pricing_vm_costs
                ORDER BY cloud, tier_order, option_order
            """)
            results = db.execute(query).fetchall()

            by_cloud = {}
            for r in results:
                if r.cloud not in by_cloud:
                    by_cloud[r.cloud] = []
                by_cloud[r.cloud].append(
                    {"pricing_tier": r.pricing_tier, "payment_option": r.payment_option}
                )

            response = {
                "success": True,
                "data": {"total_combinations": len(results), "by_cloud": by_cloud},
            }

        ref_cache.set("vm_pricing_options", response, cloud=cloud)
        return response
    except Exception as e:
        logger.error(f"Error fetching VM pricing options: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}
