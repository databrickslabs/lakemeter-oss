"""DBSQL warehouse reference endpoints."""
import logging
from fastapi import APIRouter, Query, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.cache import ref_cache
from app.services.validators import (
    validate_cloud,
    validate_region,
    validate_warehouse_type,
    validate_warehouse_size,
    validate_pricing_tier,
    validate_payment_option,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/dbsql/warehouse-types", tags=["DBSQL"])
def get_dbsql_warehouse_types():
    warehouse_types = ["CLASSIC", "PRO", "SERVERLESS"]
    return {
        "success": True,
        "data": {"count": len(warehouse_types), "warehouse_types": warehouse_types},
    }


@router.get("/dbsql/warehouse-sizes", tags=["DBSQL"])
def get_dbsql_warehouse_sizes(
    cloud: str = Query(..., description="Cloud provider: AWS, AZURE, GCP (required)"),
    warehouse_type: str = Query(None, description="Filter by warehouse type: CLASSIC, PRO, SERVERLESS"),
    warehouse_size: str = Query(None, description="Filter by warehouse size"),
    min_vcpus: int = Query(None, ge=1),
    max_vcpus: int = Query(None, ge=1),
    min_memory_gb: float = Query(None, ge=0),
    max_memory_gb: float = Query(None, ge=0),
    min_dbu_rate: float = Query(None, ge=0),
    max_dbu_rate: float = Query(None, ge=0),
    db: Session = Depends(get_db),
):
    error = validate_cloud(cloud)
    if error:
        return error

    if warehouse_type:
        error = validate_warehouse_type(warehouse_type)
        if error:
            return error

    if warehouse_size:
        type_to_validate = warehouse_type if warehouse_type else "CLASSIC"
        error = validate_warehouse_size(cloud, type_to_validate, warehouse_size, db)
        if error:
            return error

    try:
        query = text("""
            WITH hardware_data AS (
                SELECT
                    rates.cloud, rates.warehouse_type, rates.warehouse_size, rates.dbu_per_hour,
                    COALESCE(config.driver_count, pro_config.driver_count) as driver_count,
                    COALESCE(config.worker_count, pro_config.worker_count) as worker_count,
                    COALESCE(config.driver_instance_type, pro_config.driver_instance_type) as driver_instance_type,
                    COALESCE(config.worker_instance_type, pro_config.worker_instance_type) as worker_instance_type,
                    CASE WHEN UPPER(rates.warehouse_type) = 'SERVERLESS' THEN TRUE ELSE FALSE END as is_estimated,
                    CASE UPPER(rates.warehouse_size)
                        WHEN '2X-SMALL' THEN 1 WHEN 'X-SMALL' THEN 2 WHEN 'SMALL' THEN 3
                        WHEN 'MEDIUM' THEN 4 WHEN 'LARGE' THEN 5 WHEN 'X-LARGE' THEN 6
                        WHEN '2X-LARGE' THEN 7 WHEN '3X-LARGE' THEN 8 WHEN '4X-LARGE' THEN 9
                        ELSE 10
                    END as size_order
                FROM lakemeter.sync_product_dbsql_rates rates
                LEFT JOIN lakemeter.sync_ref_dbsql_warehouse_config config
                    ON rates.cloud = config.cloud
                    AND rates.warehouse_type = config.warehouse_type
                    AND rates.warehouse_size = config.warehouse_size
                LEFT JOIN lakemeter.sync_ref_dbsql_warehouse_config pro_config
                    ON rates.cloud = pro_config.cloud
                    AND pro_config.warehouse_type = 'pro'
                    AND rates.warehouse_size = pro_config.warehouse_size
                WHERE UPPER(rates.cloud) = UPPER(:cloud)
            )
            SELECT
                hd.*, di.vcpus as driver_vcpus, di.memory_gb as driver_memory_gb,
                wi.vcpus as worker_vcpus, wi.memory_gb as worker_memory_gb
            FROM hardware_data hd
            LEFT JOIN lakemeter.sync_ref_instance_dbu_rates di
                ON hd.cloud = di.cloud AND hd.driver_instance_type = di.instance_type
            LEFT JOIN lakemeter.sync_ref_instance_dbu_rates wi
                ON hd.cloud = wi.cloud AND hd.worker_instance_type = wi.instance_type
            ORDER BY hd.size_order, hd.warehouse_type
        """)
        results = db.execute(query, {"cloud": cloud.upper()}).fetchall()

        sizes = []
        for r in results:
            total_worker_vcpus = (r.worker_vcpus * r.worker_count) if r.worker_vcpus and r.worker_count else None
            total_worker_memory_gb = (r.worker_memory_gb * r.worker_count) if r.worker_memory_gb and r.worker_count else None

            if warehouse_type and r.warehouse_type.upper() != warehouse_type.upper():
                continue
            if warehouse_size and r.warehouse_size.upper() != warehouse_size.upper():
                continue
            if min_vcpus is not None and (total_worker_vcpus is None or total_worker_vcpus < min_vcpus):
                continue
            if max_vcpus is not None and (total_worker_vcpus is None or total_worker_vcpus > max_vcpus):
                continue
            if min_memory_gb is not None and (total_worker_memory_gb is None or total_worker_memory_gb < min_memory_gb):
                continue
            if max_memory_gb is not None and (total_worker_memory_gb is None or total_worker_memory_gb > max_memory_gb):
                continue
            if min_dbu_rate is not None and (r.dbu_per_hour is None or float(r.dbu_per_hour) < min_dbu_rate):
                continue
            if max_dbu_rate is not None and (r.dbu_per_hour is None or float(r.dbu_per_hour) > max_dbu_rate):
                continue

            driver_instance_display = r.driver_instance_type
            worker_instance_display = r.worker_instance_type
            if r.is_estimated:
                if driver_instance_display:
                    driver_instance_display = f"{driver_instance_display} (estimated)"
                if worker_instance_display:
                    worker_instance_display = f"{worker_instance_display} (estimated)"

            sizes.append({
                "warehouse_size": r.warehouse_size,
                "warehouse_type": r.warehouse_type,
                "dbu_per_hour": float(r.dbu_per_hour) if r.dbu_per_hour else None,
                "hardware": {
                    "driver_count": r.driver_count,
                    "worker_count": r.worker_count,
                    "driver_instance_type": driver_instance_display,
                    "worker_instance_type": worker_instance_display,
                    "driver_vcpus": r.driver_vcpus,
                    "driver_memory_gb": float(r.driver_memory_gb) if r.driver_memory_gb else None,
                    "worker_vcpus_each": r.worker_vcpus,
                    "worker_memory_gb_each": float(r.worker_memory_gb) if r.worker_memory_gb else None,
                    "total_worker_vcpus": total_worker_vcpus,
                    "total_worker_memory_gb": float(total_worker_memory_gb) if total_worker_memory_gb else None,
                },
                "is_estimated": r.is_estimated,
            })

        filters = {}
        if warehouse_type:
            filters["warehouse_type"] = warehouse_type.upper()
        if warehouse_size:
            filters["warehouse_size"] = warehouse_size
        if min_vcpus is not None:
            filters["min_vcpus"] = min_vcpus
        if max_vcpus is not None:
            filters["max_vcpus"] = max_vcpus
        if min_memory_gb is not None:
            filters["min_memory_gb"] = min_memory_gb
        if max_memory_gb is not None:
            filters["max_memory_gb"] = max_memory_gb
        if min_dbu_rate is not None:
            filters["min_dbu_rate"] = min_dbu_rate
        if max_dbu_rate is not None:
            filters["max_dbu_rate"] = max_dbu_rate

        return {
            "success": True,
            "data": {
                "cloud": cloud.upper(),
                "filters": filters if filters else None,
                "count": len(sizes),
                "sizes": sizes,
            },
        }
    except Exception as e:
        logger.error(f"Error fetching DBSQL warehouse sizes: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}


@router.get("/dbsql/warehouse-vm-costs", tags=["DBSQL"])
def get_dbsql_warehouse_vm_costs(
    cloud: str = Query(..., description="Cloud provider: AWS, AZURE, GCP (required)"),
    region: str = Query(..., description="Region code (required)"),
    warehouse_type: str = Query(..., description="Warehouse type: CLASSIC, PRO (required)"),
    warehouse_size: str = Query(..., description="Warehouse size (required)"),
    pricing_tier: str = Query(None, description="Filter by pricing tier"),
    payment_option: str = Query(None, description="Filter by payment option"),
    db: Session = Depends(get_db),
):
    error = validate_cloud(cloud)
    if error:
        return error

    # Only CLASSIC and PRO have VM costs
    valid_types = ["CLASSIC", "PRO"]
    if warehouse_type.upper() not in valid_types:
        return {
            "success": False,
            "error": {
                "code": "INVALID_WAREHOUSE_TYPE",
                "message": f"Invalid warehouse type '{warehouse_type}'. This endpoint only supports CLASSIC and PRO. SERVERLESS warehouses have no VM costs.",
                "field": "warehouse_type",
                "allowed_values": valid_types,
            },
        }

    error = validate_region(cloud, region, db)
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

    try:
        config_query = text("""
            SELECT driver_instance_type, worker_instance_type, worker_count
            FROM lakemeter.sync_ref_dbsql_warehouse_config
            WHERE cloud = :cloud
                AND UPPER(warehouse_type) = UPPER(:warehouse_type)
                AND UPPER(warehouse_size) = UPPER(:warehouse_size)
        """)
        config = db.execute(config_query, {
            "cloud": cloud.upper(), "warehouse_type": warehouse_type, "warehouse_size": warehouse_size
        }).fetchone()

        if not config:
            error = validate_warehouse_size(cloud, warehouse_type, warehouse_size, db)
            if error:
                return error

        driver_instance = config.driver_instance_type
        worker_instance = config.worker_instance_type
        worker_count = config.worker_count

        where_conditions = ["cloud = :cloud", "region = :region", "instance_type = :instance_type"]
        if pricing_tier:
            where_conditions.append("pricing_tier = :pricing_tier")
        if payment_option:
            where_conditions.append("payment_option = :payment_option")
        where_clause = " AND ".join(where_conditions)

        vm_query = text(f"""
            SELECT pricing_tier, payment_option, cost_per_hour
            FROM lakemeter.sync_pricing_vm_costs
            WHERE {where_clause}
            ORDER BY
                CASE pricing_tier
                    WHEN 'on_demand' THEN 1 WHEN 'spot' THEN 2
                    WHEN 'reserved_1y' THEN 3 WHEN 'reserved_3y' THEN 4
                END, payment_option
        """)

        driver_params = {"cloud": cloud.upper(), "region": region, "instance_type": driver_instance}
        if pricing_tier:
            driver_params["pricing_tier"] = pricing_tier
        if payment_option:
            driver_params["payment_option"] = payment_option
        driver_costs = db.execute(vm_query, driver_params).fetchall()

        worker_params = {"cloud": cloud.upper(), "region": region, "instance_type": worker_instance}
        if pricing_tier:
            worker_params["pricing_tier"] = pricing_tier
        if payment_option:
            worker_params["payment_option"] = payment_option
        worker_costs = db.execute(vm_query, worker_params).fetchall()

        response_data = {
            "cloud": cloud.upper(),
            "region": region,
            "warehouse_type": warehouse_type.upper(),
            "warehouse_size": warehouse_size,
        }
        if pricing_tier:
            response_data["filter_pricing_tier"] = pricing_tier
        if payment_option:
            response_data["filter_payment_option"] = payment_option

        response_data["driver"] = {
            "instance_type": driver_instance,
            "vm_costs": [
                {"pricing_tier": d.pricing_tier, "payment_option": d.payment_option, "cost_per_hour": float(d.cost_per_hour) if d.cost_per_hour else None}
                for d in driver_costs
            ],
        }
        response_data["workers"] = {
            "instance_type": worker_instance,
            "worker_count": worker_count,
            "individual_worker_vm_costs": [
                {"pricing_tier": w.pricing_tier, "payment_option": w.payment_option, "cost_per_hour": float(w.cost_per_hour) if w.cost_per_hour else None}
                for w in worker_costs
            ],
            "total_worker_vm_costs": [
                {"pricing_tier": w.pricing_tier, "payment_option": w.payment_option, "cost_per_hour": float(w.cost_per_hour) * worker_count if w.cost_per_hour else None}
                for w in worker_costs
            ],
        }

        return {"success": True, "data": response_data}
    except Exception as e:
        logger.error(f"Error fetching DBSQL warehouse VM costs: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}


@router.get("/dbsql/warehouse-hardware", tags=["DBSQL"])
def get_dbsql_warehouse_hardware(
    cloud: str = Query(..., description="Cloud provider: AWS, AZURE, GCP (required)"),
    warehouse_type: str = Query(..., description="Warehouse type: CLASSIC, PRO (required)"),
    warehouse_size: str = Query(..., description="Warehouse size (required)"),
    db: Session = Depends(get_db),
):
    error = validate_cloud(cloud)
    if error:
        return error

    valid_types = ["CLASSIC", "PRO"]
    if warehouse_type.upper() not in valid_types:
        return {
            "success": False,
            "error": {
                "code": "INVALID_WAREHOUSE_TYPE",
                "message": f"Invalid warehouse type '{warehouse_type}'. This endpoint only supports CLASSIC and PRO. SERVERLESS warehouses have no hardware specs.",
                "field": "warehouse_type",
                "allowed_values": valid_types,
            },
        }

    try:
        query = text("""
            SELECT
                wc.cloud, wc.warehouse_type, wc.warehouse_size,
                wc.driver_count, wc.driver_instance_type,
                di.vcpus as driver_vcpus, di.memory_gb as driver_memory_gb,
                wc.worker_count, wc.worker_instance_type,
                wi.vcpus as worker_vcpus, wi.memory_gb as worker_memory_gb
            FROM lakemeter.sync_ref_dbsql_warehouse_config wc
            LEFT JOIN lakemeter.sync_ref_instance_dbu_rates di
                ON wc.cloud = di.cloud AND wc.driver_instance_type = di.instance_type
            LEFT JOIN lakemeter.sync_ref_instance_dbu_rates wi
                ON wc.cloud = wi.cloud AND wc.worker_instance_type = wi.instance_type
            WHERE wc.cloud = :cloud
                AND UPPER(wc.warehouse_type) = UPPER(:warehouse_type)
                AND UPPER(wc.warehouse_size) = UPPER(:warehouse_size)
        """)
        config = db.execute(query, {
            "cloud": cloud.upper(), "warehouse_type": warehouse_type, "warehouse_size": warehouse_size
        }).fetchone()

        if not config:
            error = validate_warehouse_size(cloud, warehouse_type, warehouse_size, db)
            if error:
                return error

        return {
            "success": True,
            "data": {
                "cloud": config.cloud,
                "warehouse_type": config.warehouse_type,
                "warehouse_size": config.warehouse_size,
                "driver": {
                    "count": config.driver_count,
                    "instance_type": config.driver_instance_type,
                    "vcpus": config.driver_vcpus,
                    "memory_gb": float(config.driver_memory_gb) if config.driver_memory_gb else None,
                },
                "workers": {
                    "count": config.worker_count,
                    "instance_type": config.worker_instance_type,
                    "vcpus_per_worker": config.worker_vcpus,
                    "memory_gb_per_worker": float(config.worker_memory_gb) if config.worker_memory_gb else None,
                    "total_vcpus": config.worker_vcpus * config.worker_count if config.worker_vcpus else None,
                    "total_memory_gb": float(config.worker_memory_gb) * config.worker_count if config.worker_memory_gb else None,
                },
            },
        }
    except Exception as e:
        logger.error(f"Error fetching DBSQL warehouse config: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}
