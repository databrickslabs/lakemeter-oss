import logging
import math
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import (
    init_engine, 
    start_token_refresh, 
    stop_token_refresh, 
    check_database_exists,
    database_health,
    get_async_db
)
from validators import (
    validate_cloud,
    validate_region,
    validate_instance_family,
    validate_instance_type,
    get_instance_info,
    validate_warehouse_size,
    validate_warehouse_type,
    validate_pricing_tier,
    validate_payment_option,
    validate_pricing_payment_combination,
    validate_fmapi_databricks_rate_type,
    validate_fmapi_databricks_model,
    validate_fmapi_proprietary_provider,
    validate_fmapi_proprietary_model,
    validate_fmapi_proprietary_endpoint_type,
    validate_fmapi_proprietary_context_length,
    validate_fmapi_proprietary_rate_type,
    validate_vector_search_mode,
    validate_lakebase_cu_size,
    validate_lakebase_num_nodes,
    validate_photon_sku_type,
    validate_product_type,
    validate_tier
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management with OAuth token refresh"""
    # Startup
    if check_database_exists():
        init_engine()
        await start_token_refresh()
        logger.info("✅ Application started with Lakebase connection and OAuth")
    else:
        logger.warning("⚠️ Lakebase database not found - endpoints may not work")
    
    yield
    
    # Shutdown
    await stop_token_refresh()
    logger.info("Application shutdown complete")

app = FastAPI(
    title="Lakemeter API",
    version="1.0.0",
    description="Cost calculator API with OAuth authentication",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "System",
            "description": "Health checks and system status"
        },
        {
            "name": "Cloud & Regions",
            "description": "Cloud providers, regions, and pricing tiers"
        },
        {
            "name": "Compute - Instance Types",
            "description": "Instance types, families, and VM pricing"
        },
        {
            "name": "Salesforce",
            "description": "Salesforce accounts, opportunities, and use cases"
        },
        {
            "name": "Cost Calculation",
            "description": "Calculate costs for various workload types (JOBS, DBSQL, DLT, etc.)"
        }
    ]
)

# Global exception handler to ensure all errors return JSON
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return JSON"""
    import traceback
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc),
                "type": type(exc).__name__,
                "traceback": traceback.format_exc(),
                "path": str(request.url)
            }
        }
    )

# Helper function to determine SKU type from workload configuration
def get_sku_type(
    workload_type: str,
    serverless_enabled: bool = False,
    photon_enabled: bool = False,
    dlt_edition: str = None,
    dbsql_warehouse_type: str = None,
    fmapi_provider: str = None
) -> str:
    """
    Determine the SKU product type based on workload configuration.
    Maps workload_type + configuration to the product_type used for DBU pricing.
    
    Based on database logic in sync_ref_workload_types and v_line_items_with_costs view.
    """
    workload_upper = workload_type.upper()
    
    if workload_upper == 'JOBS':
        if serverless_enabled:
            return 'JOBS_SERVERLESS_COMPUTE'
        elif photon_enabled:
            return 'JOBS_COMPUTE_(PHOTON)'
        else:
            return 'JOBS_COMPUTE'
    
    elif workload_upper == 'ALL_PURPOSE':
        if serverless_enabled:
            return 'INTERACTIVE_SERVERLESS_COMPUTE'
        elif photon_enabled:
            return 'ALL_PURPOSE_COMPUTE_(PHOTON)'
        else:
            return 'ALL_PURPOSE_COMPUTE'
    
    elif workload_upper == 'DLT':
        if serverless_enabled:
            return 'DELTA_LIVE_TABLES_SERVERLESS'
        else:
            edition = (dlt_edition or 'CORE').upper()
            base = f'DLT_{edition}_COMPUTE'
            if photon_enabled:
                return f'{base}_(PHOTON)'
            else:
                return base
    
    elif workload_upper == 'DBSQL':
        warehouse_type_upper = (dbsql_warehouse_type or 'CLASSIC').upper()
        if warehouse_type_upper == 'SERVERLESS':
            return 'SERVERLESS_SQL_COMPUTE'
        elif warehouse_type_upper == 'PRO':
            return 'SQL_PRO_COMPUTE'
        else:
            return 'SQL_COMPUTE'
    
    elif workload_upper == 'VECTOR_SEARCH':
        return 'VECTOR_SEARCH_ENDPOINT'
    
    elif workload_upper == 'MODEL_SERVING':
        return 'SERVERLESS_REAL_TIME_INFERENCE'
    
    elif workload_upper == 'FMAPI_DATABRICKS':
        return 'SERVERLESS_REAL_TIME_INFERENCE'
    
    elif workload_upper == 'FMAPI_PROPRIETARY':
        if fmapi_provider:
            return f'{fmapi_provider.upper()}_MODEL_SERVING'
        else:
            return 'MODEL_SERVING'  # Fallback
    
    elif workload_upper == 'LAKEBASE':
        return 'DATABASE_SERVERLESS_COMPUTE'
    
    else:
        return 'JOBS_COMPUTE'  # Default fallback

@app.get("/", tags=["System"])
def root():
    return {
        "message": "Lakemeter API with OAuth", 
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health", tags=["System"])
async def health():
    """Health check endpoint"""
    db_exists = check_database_exists()
    db_healthy = await database_health() if db_exists else False
    
    return {
        "status": "healthy" if (db_exists and db_healthy) else "degraded",
        "database_exists": db_exists,
        "database_healthy": db_healthy
    }

@app.get("/debug/headers", tags=["System"])
async def debug_headers(request: Request):
    """
    Debug endpoint to see what headers and auth info the app receives.
    Helps diagnose authentication issues with Databricks Apps.
    """
    headers_dict = dict(request.headers)
    
    # Check for common Databricks App authentication headers
    auth_info = {
        "authorization_header": headers_dict.get("authorization", "Not present"),
        "x_forwarded_user": headers_dict.get("x-forwarded-user", "Not present"),
        "x_forwarded_email": headers_dict.get("x-forwarded-email", "Not present"),
        "x_forwarded_access_token": headers_dict.get("x-forwarded-access-token", "Not present"),
        "all_x_forwarded_headers": {k: v for k, v in headers_dict.items() if k.startswith("x-forwarded")}
    }
    
    return {
        "message": "Debug info - authentication headers received by the app",
        "auth_info": auth_info,
        "all_headers": headers_dict
    }

@app.get("/api/v1/regions", tags=["Cloud & Regions"])
async def get_regions(
    cloud: str = Query(None, description="Cloud provider: AWS, AZURE, GCP"),
    db: AsyncSession = Depends(get_async_db)
):
    """Get available regions for a cloud provider or all clouds"""
    
    # Validate cloud parameter
    if cloud:
        error = await validate_cloud(cloud)
        if error:
            return error
    
    try:
        if cloud:
            # Single cloud
            query = text("""
                SELECT DISTINCT region_code, sku_region as region_name
            FROM lakemeter.sync_ref_sku_region_map
                WHERE cloud = :cloud
                ORDER BY sku_region
            """)
            result = await db.execute(query, {"cloud": cloud.upper()})
            results = result.fetchall()
            
            return {
                "success": True,
                "data": {
                    "cloud": cloud.upper(),
                    "count": len(results),
                    "regions": [
                        {
                            "region_code": r.region_code,
                            "sku_region": r.region_name
                        }
                        for r in results
                    ]
                }
            }
        else:
            # All clouds
            query = text("""
                SELECT DISTINCT cloud, region_code, sku_region as region_name
            FROM lakemeter.sync_ref_sku_region_map
                ORDER BY cloud, sku_region
            """)
            result = await db.execute(query)
            results = result.fetchall()
            
            # Group by cloud
            by_cloud = {}
            for r in results:
                if r.cloud not in by_cloud:
                    by_cloud[r.cloud] = []
                by_cloud[r.cloud].append({
                    "region_code": r.region_code,
                    "sku_region": r.region_name
                })
            
            return {
                "success": True,
                "data": by_cloud
            }
    except Exception as e:
        logger.error(f"Error fetching regions: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }

@app.get("/api/v1/tiers", tags=["Cloud & Regions"])
async def get_tiers(
    cloud: str = Query(None, description="Cloud provider: AWS, AZURE, GCP"),
    db: AsyncSession = Depends(get_async_db)
):
    """Get available pricing tiers, optionally filtered by cloud"""
    
    # Validate cloud if provided
    if cloud:
        error = await validate_cloud(cloud)
        if error:
            return error
    
    try:
        if cloud:
            # Get tiers for specific cloud
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
            result = await db.execute(query, {"cloud": cloud.upper()})
            results = result.fetchall()
            
            return {
                "success": True,
                "data": {
                    "cloud": cloud.upper(),
                    "count": len(results),
                    "tiers": [
                        {
                            "tier": r.tier,
                            "display_name": r.display_name
                        }
                        for r in results
                    ]
                }
            }
        else:
            # Get all tiers grouped by cloud
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
            result = await db.execute(query)
            results = result.fetchall()
            
            # Group by cloud
            by_cloud = {}
            for r in results:
                if r.cloud not in by_cloud:
                    by_cloud[r.cloud] = []
                by_cloud[r.cloud].append({
                    "tier": r.tier,
                    "display_name": r.display_name
                })
            
            return {
                "success": True,
                "data": by_cloud
            }
    except Exception as e:
        logger.error(f"Error fetching tiers: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }

@app.get("/api/v1/instances/families", tags=["Compute - Instance Types"])
async def get_instance_families(
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get available instance families (global, not cloud-specific).
    Returns: ["Compute Optimized", "Memory Optimized", "Storage Optimized", "General Purpose", "GPU"]
    """
    try:
        query = text("""
            SELECT DISTINCT instance_family
            FROM lakemeter.sync_ref_instance_dbu_rates
            ORDER BY instance_family
        """)
        result = await db.execute(query)
        results = result.fetchall()
        
        return {
            "success": True,
            "data": {
                "count": len(results),
                "instance_families": [r.instance_family for r in results]
            }
        }
    except Exception as e:
        logger.error(f"Error fetching instance families: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }

@app.get("/api/v1/instances/types", tags=["Compute - Instance Types"])
async def get_instance_types(
    cloud: str = Query(..., description="Cloud provider: AWS, AZURE, GCP (required)"),
    region: str = Query(..., description="Region code (required) - e.g., us-east-1, eu-west-2"),
    instance_family: str = Query(None, description="Filter by instance family (e.g., 'Compute Optimized', 'Memory Optimized')"),
    min_vcpus: int = Query(None, ge=1, description="Minimum number of vCPUs"),
    max_vcpus: int = Query(None, ge=1, description="Maximum number of vCPUs"),
    min_memory_gb: float = Query(None, ge=0, description="Minimum memory in GB"),
    max_memory_gb: float = Query(None, ge=0, description="Maximum memory in GB"),
    min_dbu_rate: float = Query(None, ge=0, description="Minimum DBU rate per hour"),
    max_dbu_rate: float = Query(None, ge=0, description="Maximum DBU rate per hour"),
    limit: int = Query(1000, ge=1, le=1000, description="Number of results per page (max 1000)"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get available instance types with vCPU, memory, DBU rate for a specific cloud and region.
    Supports filtering by instance family, vCPU range, and memory range.
    Only returns instances that have pricing data available in the specified region.
    """
    # Validate cloud
    error = await validate_cloud(cloud)
    if error:
        return error
    
    try:
        # Validate region
        error = await validate_region(cloud, region, db)
        if error:
            return error
        
        # Validate instance_family if provided
        if instance_family:
            error = await validate_instance_family(instance_family, db)
            if error:
                return error
        
        # Build dynamic WHERE clause for filters
        where_conditions = ["r.cloud = :cloud", "v.region = :region"]
        params = {"cloud": cloud.upper(), "region": region, "limit": limit, "offset": offset}
        
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
        
        # Count query
        count_query = text(f"""
            SELECT COUNT(DISTINCT r.instance_type) as total
            FROM lakemeter.sync_ref_instance_dbu_rates r
            INNER JOIN lakemeter.sync_pricing_vm_costs v
                ON r.cloud = v.cloud 
                AND r.instance_type = v.instance_type
            WHERE {where_clause}
        """)
        count_result = await db.execute(count_query, params)
        total_count = count_result.scalar()
        
        # Data query
        query = text(f"""
            SELECT DISTINCT
                r.instance_type,
                r.vcpus,
                r.memory_gb,
                r.instance_family,
                r.dbu_rate
            FROM lakemeter.sync_ref_instance_dbu_rates r
            INNER JOIN lakemeter.sync_pricing_vm_costs v
                ON r.cloud = v.cloud 
                AND r.instance_type = v.instance_type
            WHERE {where_clause}
            ORDER BY r.instance_type
            LIMIT :limit OFFSET :offset
        """)
        result = await db.execute(query, params)
        
        results = result.fetchall()
        
        # Build filters applied info
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
                        "dbu_rate": float(r.dbu_rate)
                    }
                    for r in results
                ]
            }
        }
    except Exception as e:
        logger.error(f"Error fetching instance types: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }

@app.get("/api/v1/instances/vm-costs", tags=["Compute - Instance Types"])
async def get_instance_vm_costs(
    cloud: str = Query(..., description="Cloud provider: AWS, AZURE, GCP (required)"),
    region: str = Query(..., description="Region code (required) - e.g., us-east-1, eu-west-2"),
    instance_type: str = Query(..., description="Instance type (required) - e.g., c5.4xlarge, Standard_D4s_v3, n2-standard-8"),
    pricing_tier: str = Query(None, description="Filter by pricing tier: on_demand, spot, reserved_1y, reserved_3y (optional)"),
    payment_option: str = Query(None, description="Filter by payment option: NA, no_upfront, partial_upfront, all_upfront (optional)"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get VM pricing for a specific instance type in a specific cloud and region.
    Optionally filter by pricing_tier and/or payment_option.
    Returns all available pricing tiers (on_demand, spot, reserved options with different upfront payments).
    """
    # Validate cloud
    error = await validate_cloud(cloud)
    if error:
        return error
    
    # Validate pricing_tier if provided
    if pricing_tier:
        error = validate_pricing_tier(pricing_tier)
        if error:
            return error
    
    # Validate payment_option if provided
    if payment_option:
        error = validate_payment_option(payment_option)
        if error:
            return error
    
    try:
        # Validate region
        error = await validate_region(cloud, region, db)
        if error:
            return error
        
        # Validate instance type and get info
        error = await validate_instance_type(cloud, instance_type, db)
        if error:
            return error
        
        instance_specs = await get_instance_info(cloud, instance_type, db)
        
        # Build WHERE clause with optional filters
        where_conditions = [
            "cloud = :cloud",
            "region = :region",
            "instance_type = :instance_type"
        ]
        params = {
            "cloud": cloud.upper(),
            "region": region,
            "instance_type": instance_type
        }
        
        if pricing_tier:
            where_conditions.append("pricing_tier = :pricing_tier")
            params["pricing_tier"] = pricing_tier
        
        if payment_option:
            where_conditions.append("payment_option = :payment_option")
            params["payment_option"] = payment_option
        
        where_clause = " AND ".join(where_conditions)
        
        # Get VM costs for this instance in this region
        query = text(f"""
            SELECT 
                pricing_tier,
                payment_option,
                cost_per_hour
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
        result = await db.execute(query, params)
        results = result.fetchall()
        
        if not results:
            return {
                "success": False,
                "error": {
                    "code": "NO_PRICING_DATA",
                    "message": f"No VM pricing data found for {instance_type} in {cloud.upper()} {region} with the specified filters.",
                    "field": "instance_type"
                }
            }
        
        response_data = {
            "cloud": cloud.upper(),
            "region": region,
            "instance_type": instance_type,
            "instance_specs": instance_specs
        }
        
        # Add filters to response if applied
        if pricing_tier:
            response_data["filter_pricing_tier"] = pricing_tier
        if payment_option:
            response_data["filter_payment_option"] = payment_option
        
        response_data["pricing_options"] = [
            {
                "pricing_tier": r.pricing_tier,
                "payment_option": r.payment_option,
                "cost_per_hour": float(r.cost_per_hour)
            }
            for r in results
        ]
        
        return {
            "success": True,
            "data": response_data
        }
    except Exception as e:
        logger.error(f"Error fetching instance VM costs: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }

@app.get("/api/v1/instances/vm-pricing-options", tags=["Compute - Instance Types"])
async def get_vm_pricing_options(
    cloud: str = Query(None, description="Optional: Filter by cloud provider (AWS, AZURE, GCP)"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get all distinct VM pricing options (pricing_tier + payment_option).
    Optional cloud filter to get options for a specific cloud.
    Shows the differences between AWS (granular upfront options) vs Azure/GCP (simple reserved).
    """
    # Validate cloud if provided
    if cloud:
        error = await validate_cloud(cloud)
        if error:
            return error
    
    try:
        if cloud:
            # Filter by specific cloud
            query = text("""
                SELECT DISTINCT 
                    pricing_tier,
                    payment_option,
                    CASE pricing_tier
                        WHEN 'on_demand' THEN 1
                        WHEN 'spot' THEN 2
                        WHEN 'reserved_1y' THEN 3
                        WHEN 'reserved_3y' THEN 4
                        ELSE 5
                    END as tier_order,
                    CASE payment_option
                        WHEN 'NA' THEN 1
                        WHEN 'no_upfront' THEN 2
                        WHEN 'partial_upfront' THEN 3
                        WHEN 'all_upfront' THEN 4
                        ELSE 5
                    END as option_order
                FROM lakemeter.sync_pricing_vm_costs
                WHERE cloud = :cloud
                ORDER BY tier_order, option_order
            """)
            result = await db.execute(query, {"cloud": cloud.upper()})
            results = result.fetchall()
            
            return {
                "success": True,
                "data": {
                    "cloud": cloud.upper(),
                    "count": len(results),
                    "pricing_options": [
                        {
                            "pricing_tier": r.pricing_tier,
                            "payment_option": r.payment_option
                        }
                        for r in results
                    ]
                }
            }
        else:
            # Get all clouds
            query = text("""
                SELECT DISTINCT 
                    cloud,
                    pricing_tier,
                    payment_option,
                    CASE pricing_tier
                        WHEN 'on_demand' THEN 1
                        WHEN 'spot' THEN 2
                        WHEN 'reserved_1y' THEN 3
                        WHEN 'reserved_3y' THEN 4
                        ELSE 5
                    END as tier_order,
                    CASE payment_option
                        WHEN 'NA' THEN 1
                        WHEN 'no_upfront' THEN 2
                        WHEN 'partial_upfront' THEN 3
                        WHEN 'all_upfront' THEN 4
                        ELSE 5
                    END as option_order
                FROM lakemeter.sync_pricing_vm_costs
                ORDER BY cloud, tier_order, option_order
            """)
            result = await db.execute(query)
            results = result.fetchall()
            
            # Group by cloud
            by_cloud = {}
            for r in results:
                if r.cloud not in by_cloud:
                    by_cloud[r.cloud] = []
                by_cloud[r.cloud].append({
                    "pricing_tier": r.pricing_tier,
                    "payment_option": r.payment_option
                })
            
            return {
                "success": True,
                "data": {
                    "total_combinations": len(results),
                    "by_cloud": by_cloud
                }
            }
    except Exception as e:
        logger.error(f"Error fetching VM pricing options: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }

@app.get("/api/v1/dbsql/warehouse-types", tags=["DBSQL"])
async def get_dbsql_warehouse_types(
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get available DBSQL warehouse types.
    Returns: CLASSIC, PRO, SERVERLESS
    """
    try:
        # Warehouse types are fixed values
        warehouse_types = ["CLASSIC", "PRO", "SERVERLESS"]
        
        return {
            "success": True,
            "data": {
                "count": len(warehouse_types),
                "warehouse_types": warehouse_types
            }
        }
    except Exception as e:
        logger.error(f"Error fetching DBSQL warehouse types: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }

@app.get("/api/v1/dbsql/warehouse-sizes", tags=["DBSQL"])
async def get_dbsql_warehouse_sizes(
    cloud: str = Query(..., description="Cloud provider: AWS, AZURE, GCP (required)"),
    warehouse_type: str = Query(None, description="Filter by warehouse type: CLASSIC, PRO, SERVERLESS (optional, case-insensitive)"),
    warehouse_size: str = Query(None, description="Filter by warehouse size (e.g., 'Medium', 'X-Small') (optional, case-insensitive)"),
    min_vcpus: int = Query(None, ge=1, description="Minimum total worker vCPUs"),
    max_vcpus: int = Query(None, ge=1, description="Maximum total worker vCPUs"),
    min_memory_gb: float = Query(None, ge=0, description="Minimum total worker memory in GB"),
    max_memory_gb: float = Query(None, ge=0, description="Maximum total worker memory in GB"),
    min_dbu_rate: float = Query(None, ge=0, description="Minimum DBU per hour"),
    max_dbu_rate: float = Query(None, ge=0, description="Maximum DBU per hour"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get all DBSQL warehouse sizes with hardware specifications and computing power.
    Supports filtering by warehouse type, warehouse size, vCPU range, memory range, and DBU rate range.
    
    **Computing Power:**
    - `total_worker_vcpus`: Sum of all worker vCPUs (driver excluded)
    - `total_worker_memory_gb`: Sum of all worker memory (driver excluded)
    - Driver resources are separate and do NOT affect totals
    
    **Serverless Estimation:**
    - SERVERLESS warehouses use PRO hardware specifications
    - Marked with `is_estimated: true`
    - Actual serverless compute is managed by Databricks
    
    **Filters:**
    - `warehouse_type`: CLASSIC, PRO, SERVERLESS (optional, validated)
    - `warehouse_size`: Exact match (optional, validated against available sizes)
    - `min_vcpus`, `max_vcpus`: Filter by total worker vCPUs range
    - `min_memory_gb`, `max_memory_gb`: Filter by total worker memory range
    - `min_dbu_rate`, `max_dbu_rate`: Filter by DBU per hour range
    
    **Example Requests:**
    - `/api/v1/dbsql/warehouse-sizes?cloud=AWS` - Get all AWS warehouses
    - `/api/v1/dbsql/warehouse-sizes?cloud=AWS&warehouse_type=SERVERLESS` - Get only SERVERLESS warehouses
    - `/api/v1/dbsql/warehouse-sizes?cloud=AWS&warehouse_size=Medium` - Get Medium size only
    - `/api/v1/dbsql/warehouse-sizes?cloud=AWS&warehouse_type=PRO&warehouse_size=Large` - Get PRO Large
    - `/api/v1/dbsql/warehouse-sizes?cloud=AWS&min_vcpus=32&max_vcpus=128` - Get warehouses with 32-128 total worker vCPUs
    - `/api/v1/dbsql/warehouse-sizes?cloud=AWS&min_dbu_rate=10&max_dbu_rate=50` - Get warehouses with 10-50 DBU/hour
    
    **Example Response:**
    ```json
    {
      "warehouse_size": "Medium",
      "warehouse_type": "PRO",
      "dbu_per_hour": 24,
      "hardware": {
        "driver_count": 1,
        "worker_count": 8,
        "driver_instance_type": "i3.8xlarge",
        "worker_instance_type": "i3.2xlarge",
        "driver_vcpus": 64,
        "driver_memory_gb": 488,
        "worker_vcpus_each": 8,
        "worker_memory_gb_each": 61,
        "total_worker_vcpus": 64,
        "total_worker_memory_gb": 488
      },
      "is_estimated": false
    }
    ```
    """
    # Validate cloud
    error = await validate_cloud(cloud)
    if error:
        return error
    
    # Validate warehouse_type if provided
    if warehouse_type:
        error = await validate_warehouse_type(warehouse_type, db)
        if error:
            return error
    
    # Validate warehouse_size if provided
    # Note: We need to check all warehouse types if warehouse_type not specified
    if warehouse_size:
        # Get a valid warehouse_type to validate against (use the first available)
        type_to_validate = warehouse_type if warehouse_type else "CLASSIC"
        error = await validate_warehouse_size(cloud, type_to_validate, warehouse_size, db)
        if error:
            return error
    
    try:
        query = text("""
            WITH hardware_data AS (
                SELECT 
                    rates.cloud,
                    rates.warehouse_type,
                    rates.warehouse_size,
                    rates.dbu_per_hour,
                    COALESCE(
                        config.driver_count,
                        pro_config.driver_count
                    ) as driver_count,
                    COALESCE(
                        config.worker_count,
                        pro_config.worker_count
                    ) as worker_count,
                    COALESCE(
                        config.driver_instance_type,
                        pro_config.driver_instance_type
                    ) as driver_instance_type,
                    COALESCE(
                        config.worker_instance_type,
                        pro_config.worker_instance_type
                    ) as worker_instance_type,
                    CASE 
                        WHEN UPPER(rates.warehouse_type) = 'SERVERLESS' THEN TRUE
                        ELSE FALSE
                    END as is_estimated,
                    CASE UPPER(rates.warehouse_size)
                        WHEN '2X-SMALL' THEN 1
                        WHEN 'X-SMALL' THEN 2
                        WHEN 'SMALL' THEN 3
                        WHEN 'MEDIUM' THEN 4
                        WHEN 'LARGE' THEN 5
                        WHEN 'X-LARGE' THEN 6
                        WHEN '2X-LARGE' THEN 7
                        WHEN '3X-LARGE' THEN 8
                        WHEN '4X-LARGE' THEN 9
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
                hd.cloud,
                hd.warehouse_type,
                hd.warehouse_size,
                hd.dbu_per_hour,
                hd.driver_count,
                hd.worker_count,
                hd.driver_instance_type,
                hd.worker_instance_type,
                hd.is_estimated,
                hd.size_order,
                di.vcpus as driver_vcpus,
                di.memory_gb as driver_memory_gb,
                wi.vcpus as worker_vcpus,
                wi.memory_gb as worker_memory_gb
            FROM hardware_data hd
            LEFT JOIN lakemeter.sync_ref_instance_dbu_rates di
                ON hd.cloud = di.cloud
                AND hd.driver_instance_type = di.instance_type
            LEFT JOIN lakemeter.sync_ref_instance_dbu_rates wi
                ON hd.cloud = wi.cloud
                AND hd.worker_instance_type = wi.instance_type
            ORDER BY hd.size_order, hd.warehouse_type
        """)
        
        result = await db.execute(query, {"cloud": cloud.upper()})
        results = result.fetchall()
        
        # Build response with hardware details and apply filters
        sizes = []
        for r in results:
            # Calculate total worker resources (driver NOT included)
            total_worker_vcpus = (r.worker_vcpus * r.worker_count) if r.worker_vcpus and r.worker_count else None
            total_worker_memory_gb = (r.worker_memory_gb * r.worker_count) if r.worker_memory_gb and r.worker_count else None
            
            # Apply filters
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
            
            # Add (estimated) suffix for serverless instance types
            driver_instance_display = r.driver_instance_type
            worker_instance_display = r.worker_instance_type
            if r.is_estimated:
                if driver_instance_display:
                    driver_instance_display = f"{driver_instance_display} (estimated)"
                if worker_instance_display:
                    worker_instance_display = f"{worker_instance_display} (estimated)"
            
            size_data = {
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
                    "total_worker_memory_gb": float(total_worker_memory_gb) if total_worker_memory_gb else None
                },
                "is_estimated": r.is_estimated
            }
            sizes.append(size_data)
        
        # Build filters object for response
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
                "sizes": sizes
            }
        }
    except Exception as e:
        logger.error(f"Error fetching DBSQL warehouse sizes: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }

@app.get("/api/v1/dbsql/warehouse-vm-costs", tags=["DBSQL"])
async def get_dbsql_warehouse_vm_costs(
    cloud: str = Query(..., description="Cloud provider: AWS, AZURE, GCP (required)"),
    region: str = Query(..., description="Region code - e.g., us-east-1, eu-west-2 (required)"),
    warehouse_type: str = Query(..., description="Warehouse type: CLASSIC, PRO (required)"),
    warehouse_size: str = Query(..., description="Warehouse size: X-Small, Small, Medium, etc. (case-insensitive, required)"),
    pricing_tier: str = Query(None, description="Filter by pricing tier: on_demand, spot, reserved_1y, reserved_3y (optional)"),
    payment_option: str = Query(None, description="Filter by payment option: NA, no_upfront, partial_upfront, all_upfront (optional)"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get DBSQL warehouse VM costs for driver and workers.
    Returns driver VM cost, individual worker VM cost, and total worker VM costs.
    Only supports CLASSIC and PRO warehouses (SERVERLESS has no VM costs).
    Optionally filter by pricing_tier and/or payment_option.
    """
    # Validate cloud
    error = await validate_cloud(cloud)
    if error:
        return error
    
    # Validate region
    region_query = text("""
        SELECT region_code 
        FROM lakemeter.sync_ref_sku_region_map 
        WHERE cloud = :cloud AND region_code = :region
    """)
    region_result = await db.execute(region_query, {"cloud": cloud.upper(), "region": region})
    if not region_result.fetchone():
        # Get valid regions
        valid_regions_query = text("""
            SELECT region_code 
            FROM lakemeter.sync_ref_sku_region_map 
            WHERE cloud = :cloud 
            ORDER BY region_code
        """)
        valid_result = await db.execute(valid_regions_query, {"cloud": cloud.upper()})
        valid_regions = [r.region_code for r in valid_result.fetchall()]
        
        return {
            "success": False,
            "error": {
                "code": "INVALID_REGION",
                "message": f"Invalid region '{region}' for {cloud.upper()}. Must be one of: {', '.join(valid_regions[:5])}{'...' if len(valid_regions) > 5 else ''}",
                "field": "region",
                "allowed_values": valid_regions
            }
        }
    
    # Validate warehouse_type (only CLASSIC and PRO have VM costs)
    valid_types = ["CLASSIC", "PRO"]
    if warehouse_type.upper() not in valid_types:
        return {
            "success": False,
            "error": {
                "code": "INVALID_WAREHOUSE_TYPE",
                "message": f"Invalid warehouse type '{warehouse_type}'. This endpoint only supports CLASSIC and PRO. SERVERLESS warehouses have no VM costs.",
                "field": "warehouse_type",
                "allowed_values": valid_types
            }
        }
    
    # Validate pricing_tier if provided
    if pricing_tier:
        error = validate_pricing_tier(pricing_tier)
        if error:
            return error
    
    # Validate payment_option if provided
    if payment_option:
        error = validate_payment_option(payment_option)
        if error:
            return error
    
    try:
        # First, get the warehouse configuration (instance types and counts)
        config_query = text("""
            SELECT 
                driver_instance_type,
                worker_instance_type,
                worker_count
            FROM lakemeter.sync_ref_dbsql_warehouse_config
            WHERE cloud = :cloud
                AND UPPER(warehouse_type) = UPPER(:warehouse_type)
                AND UPPER(warehouse_size) = UPPER(:warehouse_size)
        """)
        config_result = await db.execute(config_query, {
            "cloud": cloud.upper(),
            "warehouse_type": warehouse_type,
            "warehouse_size": warehouse_size
        })
        config = config_result.fetchone()
        
        if not config:
            # Use modular validation function
            error = await validate_warehouse_size(cloud, warehouse_type, warehouse_size, db)
            if error:
                return error
        
        driver_instance = config.driver_instance_type
        worker_instance = config.worker_instance_type
        worker_count = config.worker_count
        
        # Build WHERE clause with optional filters
        where_conditions = [
            "cloud = :cloud",
            "region = :region",
            "instance_type = :instance_type"
        ]
        
        if pricing_tier:
            where_conditions.append("pricing_tier = :pricing_tier")
        
        if payment_option:
            where_conditions.append("payment_option = :payment_option")
        
        where_clause = " AND ".join(where_conditions)
        
        # Get VM costs for driver instance
        driver_costs_query = text(f"""
            SELECT 
                pricing_tier,
                payment_option,
                cost_per_hour
            FROM lakemeter.sync_pricing_vm_costs
            WHERE {where_clause}
            ORDER BY 
                CASE pricing_tier
                    WHEN 'on_demand' THEN 1
                    WHEN 'spot' THEN 2
                    WHEN 'reserved_1y' THEN 3
                    WHEN 'reserved_3y' THEN 4
                END,
                payment_option
        """)
        
        driver_params = {
            "cloud": cloud.upper(),
            "region": region,
            "instance_type": driver_instance
        }
        if pricing_tier:
            driver_params["pricing_tier"] = pricing_tier
        if payment_option:
            driver_params["payment_option"] = payment_option
        
        driver_result = await db.execute(driver_costs_query, driver_params)
        driver_costs = driver_result.fetchall()
        
        # Get VM costs for worker instance
        worker_params = {
            "cloud": cloud.upper(),
            "region": region,
            "instance_type": worker_instance
        }
        if pricing_tier:
            worker_params["pricing_tier"] = pricing_tier
        if payment_option:
            worker_params["payment_option"] = payment_option
        
        worker_result = await db.execute(driver_costs_query, worker_params)
        worker_costs = worker_result.fetchall()
        
        response_data = {
            "cloud": cloud.upper(),
            "region": region,
            "warehouse_type": warehouse_type.upper(),
            "warehouse_size": warehouse_size
        }
        
        # Add filters to response if applied
        if pricing_tier:
            response_data["filter_pricing_tier"] = pricing_tier
        if payment_option:
            response_data["filter_payment_option"] = payment_option
        
        response_data["driver"] = {
            "instance_type": driver_instance,
            "vm_costs": [
                {
                    "pricing_tier": d.pricing_tier,
                    "payment_option": d.payment_option,
                    "cost_per_hour": float(d.cost_per_hour) if d.cost_per_hour else None
                }
                for d in driver_costs
            ]
        }
        
        response_data["workers"] = {
            "instance_type": worker_instance,
            "worker_count": worker_count,
            "individual_worker_vm_costs": [
                {
                    "pricing_tier": w.pricing_tier,
                    "payment_option": w.payment_option,
                    "cost_per_hour": float(w.cost_per_hour) if w.cost_per_hour else None
                }
                for w in worker_costs
            ],
            "total_worker_vm_costs": [
                {
                    "pricing_tier": w.pricing_tier,
                    "payment_option": w.payment_option,
                    "cost_per_hour": float(w.cost_per_hour) * worker_count if w.cost_per_hour else None
                }
                for w in worker_costs
            ]
        }
        
        return {
            "success": True,
            "data": response_data
        }
    except Exception as e:
        logger.error(f"Error fetching DBSQL warehouse VM costs: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }

@app.get("/api/v1/dbsql/warehouse-hardware", tags=["DBSQL"])
async def get_dbsql_warehouse_hardware(
    cloud: str = Query(..., description="Cloud provider: AWS, AZURE, GCP (required)"),
    warehouse_type: str = Query(..., description="Warehouse type: CLASSIC, PRO (required)"),
    warehouse_size: str = Query(..., description="Warehouse size: X-Small, Small, Medium, etc. (case-insensitive, required)"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get DBSQL warehouse hardware specifications (driver/worker instance types, vCPU, memory).
    Only supports CLASSIC and PRO warehouses. SERVERLESS warehouses have no instance types.
    All parameters are case-insensitive.
    """
    # Validate cloud
    error = await validate_cloud(cloud)
    if error:
        return error
    
    # Validate warehouse_type (only CLASSIC and PRO have instance hardware)
    valid_types = ["CLASSIC", "PRO"]
    if warehouse_type.upper() not in valid_types:
        return {
            "success": False,
            "error": {
                "code": "INVALID_WAREHOUSE_TYPE",
                "message": f"Invalid warehouse type '{warehouse_type}'. This endpoint only supports CLASSIC and PRO (warehouses with instance types). SERVERLESS warehouses have no hardware specs.",
                "field": "warehouse_type",
                "allowed_values": valid_types
            }
        }
    
    try:
        # Query with full hardware details (no pricing)
        query = text("""
            SELECT 
                wc.cloud,
                wc.warehouse_type,
                wc.warehouse_size,
                wc.driver_count,
                wc.driver_instance_type,
                di.vcpus as driver_vcpus,
                di.memory_gb as driver_memory_gb,
                wc.worker_count,
                wc.worker_instance_type,
                wi.vcpus as worker_vcpus,
                wi.memory_gb as worker_memory_gb
            FROM lakemeter.sync_ref_dbsql_warehouse_config wc
            -- Join driver instance specs
            LEFT JOIN lakemeter.sync_ref_instance_dbu_rates di
                ON wc.cloud = di.cloud 
                AND wc.driver_instance_type = di.instance_type
            -- Join worker instance specs
            LEFT JOIN lakemeter.sync_ref_instance_dbu_rates wi
                ON wc.cloud = wi.cloud 
                AND wc.worker_instance_type = wi.instance_type
            WHERE wc.cloud = :cloud
                AND UPPER(wc.warehouse_type) = UPPER(:warehouse_type)
                AND UPPER(wc.warehouse_size) = UPPER(:warehouse_size)
        """)
        result = await db.execute(query, {
            "cloud": cloud.upper(),
            "warehouse_type": warehouse_type,
            "warehouse_size": warehouse_size
        })
        config = result.fetchone()
        
        if not config:
            # Use modular validation function
            error = await validate_warehouse_size(cloud, warehouse_type, warehouse_size, db)
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
                    "memory_gb": float(config.driver_memory_gb) if config.driver_memory_gb else None
                },
                "workers": {
                    "count": config.worker_count,
                    "instance_type": config.worker_instance_type,
                    "vcpus_per_worker": config.worker_vcpus,
                    "memory_gb_per_worker": float(config.worker_memory_gb) if config.worker_memory_gb else None,
                    "total_vcpus": config.worker_vcpus * config.worker_count if config.worker_vcpus else None,
                    "total_memory_gb": float(config.worker_memory_gb) * config.worker_count if config.worker_memory_gb else None
                }
            }
        }
    except Exception as e:
        logger.error(f"Error fetching DBSQL warehouse config: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }

@app.get("/api/v1/dlt/editions", tags=["DLT"])
async def get_dlt_editions(
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get available DLT editions.
    Returns: CORE, PRO, ADVANCED
    """
    try:
        # DLT editions are fixed values
        editions = ["CORE", "PRO", "ADVANCED"]
        
        return {
            "success": True,
            "data": {
                "count": len(editions),
                "editions": editions
            }
        }
    except Exception as e:
        logger.error(f"Error fetching DLT editions: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }

@app.get("/api/v1/vector-search/list", tags=["Vector Search"])
async def list_vector_search_modes(
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get a simple list of all available Vector Search modes.
    Modes are the same across all clouds (AWS, AZURE, GCP).
    Useful for populating dropdowns or validation.
    """
    try:
        query = text("""
            SELECT DISTINCT
                size_or_model as mode
            FROM lakemeter.sync_product_serverless_rates
            WHERE product = 'vector_search'
            ORDER BY mode
        """)
        result = await db.execute(query)
        modes = [r.mode for r in result.fetchall()]
        
        return {
            "success": True,
            "data": {
                "count": len(modes),
                "modes": modes
            }
        }
    except Exception as e:
        logger.error(f"Error fetching Vector Search mode list: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }


@app.get("/api/v1/vector-search/modes", tags=["Vector Search"])
async def get_vector_search_modes(
    cloud: str = Query(..., description="Cloud provider (required): AWS, AZURE, GCP"),
    mode: str = Query(None, description="Filter by mode (optional). Use /list endpoint to see available modes."),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get Vector Search modes (standard, storage_optimized) with their pricing.
    
    **Cloud is REQUIRED** - Must specify one of: AWS, AZURE, GCP
    
    **Discovery Endpoint:**
    - `/api/v1/vector-search/list` - Get all available modes by cloud
    
    **Vector Capacity:**
    - The input_divisor represents how many million vectors per pricing unit
    - Standard mode: typically 2M vectors per unit
    - Storage-optimized mode: typically 64M vectors per unit
    
    **Pricing Display:**
    - Shows dbu_per_hour for the specified vector capacity
    
    **Example Requests:**
    - `/api/v1/vector-search/modes?cloud=AWS` - Get all modes for AWS
    - `/api/v1/vector-search/modes?cloud=AWS&mode=standard` - Get specific mode for AWS
    """
    # Validate cloud (required)
    error = await validate_cloud(cloud)
    if error:
        return error
    
    # Validate mode if provided
    if mode:
        error = await validate_vector_search_mode(mode, cloud, db)
        if error:
            return error
    
    try:
        # Build WHERE clause
        where_conditions = ["product = 'vector_search'", "cloud = :cloud"]
        params = {"cloud": cloud.upper()}
        
        if mode:
            where_conditions.append("size_or_model = :mode")
            params["mode"] = mode
        
        where_clause = "WHERE " + " AND ".join(where_conditions)
        
        query = text(f"""
            SELECT 
                cloud,
                size_or_model as mode,
                dbu_rate,
                input_divisor,
                CASE 
                    WHEN input_divisor = 2000000 THEN 2
                    WHEN input_divisor = 64000000 THEN 64
                    ELSE input_divisor / 1000000.0
                END as vector_capacity_millions
            FROM lakemeter.sync_product_serverless_rates
            {where_clause}
            ORDER BY cloud, mode
        """)
        result = await db.execute(query, params)
        results = result.fetchall()
        
        # Format results
        modes = []
        for r in results:
            modes.append({
                "cloud": r.cloud,
                "mode": r.mode,
                "dbu_per_hour": float(r.dbu_rate) if r.dbu_rate else None,
                "vector_capacity_millions": float(r.vector_capacity_millions),
                "description": f"{r.vector_capacity_millions}M vectors per pricing unit"
            })
        
        return {
            "success": True,
            "data": {
                "cloud_filter": cloud.upper(),
                "mode_filter": mode if mode else None,
                "count": len(modes),
                "modes": modes
            }
        }
    except Exception as e:
        logger.error(f"Error fetching Vector Search modes: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }


@app.get("/api/v1/lakebase/list", tags=["Lakebase"])
async def list_lakebase_sizes():
    """
    Get a simple list of all available Lakebase CU (Compute Unit) sizes.
    CU sizes are the same across all clouds (AWS, AZURE, GCP).
    Useful for populating dropdowns or validation.
    
    **Available CU sizes:** 1, 2, 4, 8
    """
    # Hardcoded CU sizes for Lakebase
    cu_sizes = [1, 2, 4, 8]
    
    return {
        "success": True,
        "data": {
            "count": len(cu_sizes),
            "cu_sizes": cu_sizes,
            "description": "Compute Units (CU) available for Lakebase. 1 CU = 1 DBU per hour."
        }
    }


@app.get("/api/v1/lakebase/calculate", tags=["Lakebase"])
async def calculate_lakebase_dbu(
    cu_size: int = Query(..., description="Compute Unit size (required): 1, 2, 4, or 8"),
    num_nodes: int = Query(..., description="Number of nodes (required): 1 to 3")
):
    """
    Calculate Lakebase DBU usage based on CU size and number of nodes.
    
    **CU size is REQUIRED** - Must be one of: 1, 2, 4, 8
    **Number of nodes is REQUIRED** - Must be between 1 and 3
    
    **Simple Formula (no database lookup, no cloud difference):**
    - Total DBU per hour = CU size × Number of nodes
    - 1 CU = 1 DBU per hour
    - Same calculation for all clouds (AWS, AZURE, GCP)
    
    **Discovery Endpoint:**
    - `/api/v1/lakebase/list` - Get all available CU sizes
    
    **Example Calculations:**
    - CU=2, Nodes=2 → 2 × 2 = 4 DBU/hour
    - CU=4, Nodes=3 → 4 × 3 = 12 DBU/hour
    - CU=8, Nodes=1 → 8 × 1 = 8 DBU/hour
    """
    # Validate CU size
    valid_cu_sizes = [1, 2, 4, 8]
    if cu_size not in valid_cu_sizes:
        return {
            "success": False,
            "error": {
                "code": "INVALID_CU_SIZE",
                "message": f"Invalid CU size '{cu_size}'. Must be one of: {', '.join(map(str, valid_cu_sizes))}",
                "field": "cu_size",
                "allowed_values": valid_cu_sizes
            }
        }
    
    # Validate number of nodes
    if num_nodes < 1 or num_nodes > 3:
        return {
            "success": False,
            "error": {
                "code": "INVALID_NUM_NODES",
                "message": f"Invalid number of nodes '{num_nodes}'. Must be between 1 and 3.",
                "field": "num_nodes",
                "allowed_values": [1, 2, 3]
            }
        }
    
    # Simple calculation: Total DBU/hour = CU size × Number of nodes
    # No database lookup needed - 1 CU always equals 1 DBU per hour
    # Same for all clouds
    total_dbu_per_hour = cu_size * num_nodes
    
    return {
        "success": True,
        "data": {
            "cu_size": cu_size,
            "num_nodes": num_nodes,
            "total_dbu_per_hour": total_dbu_per_hour,
            "calculation": f"{cu_size} CU × {num_nodes} nodes = {total_dbu_per_hour} DBU/hour",
            "description": f"Lakebase instance with {cu_size} CU and {num_nodes} node(s)",
            "note": "1 CU = 1 DBU per hour (same across all clouds)"
        }
    }


@app.get("/api/v1/photon/list", tags=["Photon Multipliers"])
async def list_photon_sku_types(
    cloud: str = Query(..., description="Cloud provider (required): AWS, AZURE, GCP"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get a list of all available SKU types that have Photon multipliers for a specific cloud.
    Useful for populating dropdowns or validation.
    """
    # Validate cloud (required)
    error = await validate_cloud(cloud)
    if error:
        return error
    
    try:
        query = text("""
            SELECT DISTINCT
                sku_type
            FROM lakemeter.sync_ref_dbu_multipliers
            WHERE feature = 'photon' AND cloud = :cloud
            ORDER BY sku_type
        """)
        result = await db.execute(query, {"cloud": cloud.upper()})
        sku_types = [r.sku_type for r in result.fetchall()]
        
        return {
            "success": True,
            "data": {
                "cloud": cloud.upper(),
                "count": len(sku_types),
                "sku_types": sku_types
            }
        }
    except Exception as e:
        logger.error(f"Error fetching Photon SKU types: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }


@app.get("/api/v1/photon/multipliers", tags=["Photon Multipliers"])
async def get_photon_multipliers(
    cloud: str = Query(..., description="Cloud provider (required): AWS, AZURE, GCP"),
    sku_type: str = Query(None, description="Filter by SKU type (optional). Use /list endpoint to see available types."),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get Photon multipliers for different cloud providers and SKU types.
    
    **Cloud is REQUIRED** - Must specify one of: AWS, AZURE, GCP
    **SKU type is OPTIONAL** - Filter by specific SKU type (validated per cloud)
    
    **Discovery Endpoint:**
    - `/api/v1/photon/list?cloud=<cloud>` - Get all available SKU types for a cloud
    
    **Photon Multiplier:**
    - Multiplier applied to DBU rates when Photon is enabled
    - Different multipliers for different SKU types and categories
    
    **Example Requests:**
    - `/api/v1/photon/multipliers?cloud=AWS` - All Photon multipliers for AWS
    - `/api/v1/photon/multipliers?cloud=AWS&sku_type=jobs` - Photon multiplier for AWS jobs
    """
    # Validate cloud (required)
    error = await validate_cloud(cloud)
    if error:
        return error
    
    # Validate sku_type if provided
    if sku_type:
        error = await validate_photon_sku_type(cloud, sku_type, db)
        if error:
            return error
    
    try:
        # Build WHERE clause
        where_conditions = ["feature = 'photon'", "cloud = :cloud"]
        params = {"cloud": cloud.upper()}
        
        if sku_type:
            where_conditions.append("sku_type = :sku_type")
            params["sku_type"] = sku_type
        
        where_clause = "WHERE " + " AND ".join(where_conditions)
        
        query = text(f"""
            SELECT 
                cloud,
                feature,
                multiplier,
                sku_type,
                category
            FROM lakemeter.sync_ref_dbu_multipliers
            {where_clause}
            ORDER BY sku_type, category
        """)
        result = await db.execute(query, params)
        results = result.fetchall()
        
        # Format results
        multipliers = []
        for r in results:
            multipliers.append({
                "cloud": r.cloud,
                "sku_type": r.sku_type,
                "category": r.category,
                "multiplier": float(r.multiplier)
            })
        
        return {
            "success": True,
            "data": {
                "cloud_filter": cloud.upper(),
                "sku_type_filter": sku_type if sku_type else None,
                "count": len(multipliers),
                "multipliers": multipliers
            }
        }
    except Exception as e:
        logger.error(f"Error fetching Photon multipliers: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }


@app.get("/api/v1/serverless/modes", tags=["Serverless Multipliers"])
async def get_serverless_modes():
    """
    Get serverless mode multipliers (hardcoded).
    
    **Available Modes:**
    - standard: multiplier = 1 (default performance)
    - performance: multiplier = 2 (enhanced performance)
    
    **Serverless Mode Multiplier:**
    - Multiplier applied to DBU rates for serverless workloads (Jobs, DLT, etc.)
    - Standard mode has no additional cost (1x)
    - Performance mode costs 2x more for enhanced performance
    
    **Example Usage:**
    - Standard serverless job: Base DBU rate × 1
    - Performance serverless job: Base DBU rate × 2
    """
    # Hardcoded serverless mode multipliers
    modes = [
        {
            "mode": "standard",
            "multiplier": 1,
            "description": "Standard performance (default)"
        },
        {
            "mode": "performance",
            "multiplier": 2,
            "description": "Enhanced performance (2x cost)"
        }
    ]
    
    return {
        "success": True,
        "data": {
            "count": len(modes),
            "modes": modes,
            "note": "Serverless mode multipliers are the same across all clouds"
        }
    }


@app.get("/api/v1/pricing/product-types", tags=["Pricing - DBU Rates"])
async def list_product_types(
    cloud: str = Query(..., description="Cloud provider (required): AWS, AZURE, GCP"),
    region: str = Query(..., description="Region code (required) - e.g., us-east-1, eu-west-2, eastasia"),
    tier: str = Query(..., description="Pricing tier (required): STANDARD, PREMIUM, ENTERPRISE (Note: Azure does not support ENTERPRISE)"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get a list of all available product types that have DBU pricing for a specific cloud, region, and tier.
    Useful for populating dropdowns or validation.
    
    **Note:** Azure does not support ENTERPRISE tier.
    """
    # Validate cloud (required)
    error = await validate_cloud(cloud)
    if error:
        return error
    
    # Validate region (required)
    error = await validate_region(cloud, region, db)
    if error:
        return error
    
    # Validate tier (required) - dynamically checks valid tiers for this cloud
    error = await validate_tier(cloud, tier, db)
    if error:
        return error
    
    try:
        query = text("""
            SELECT DISTINCT
                product_type
            FROM lakemeter.sync_pricing_dbu_rates
            WHERE cloud = :cloud AND region = :region AND tier = :tier
            ORDER BY product_type
        """)
        result = await db.execute(query, {"cloud": cloud.upper(), "region": region, "tier": tier.upper()})
        product_types = [r.product_type for r in result.fetchall()]
        
        return {
            "success": True,
            "data": {
                "cloud": cloud.upper(),
                "region": region,
                "tier": tier.upper(),
                "count": len(product_types),
                "product_types": product_types
            }
        }
    except Exception as e:
        logger.error(f"Error fetching product types: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }


@app.get("/api/v1/pricing/dbu-rates", tags=["Pricing - DBU Rates"])
async def get_dbu_rates(
    cloud: str = Query(..., description="Cloud provider (required): AWS, AZURE, GCP"),
    region: str = Query(..., description="Region code (required) - e.g., us-east-1, eu-west-2, eastasia"),
    tier: str = Query(..., description="Pricing tier (required): STANDARD, PREMIUM, ENTERPRISE (Note: Azure does not support ENTERPRISE)"),
    product_type: str = Query(None, description="Filter by product type (optional)"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get base DBU pricing rates ($/DBU) for different product types.
    
    **Cloud is REQUIRED** - Must specify one of: AWS, AZURE, GCP
    **Region is REQUIRED** - Must specify a valid region code for the cloud (e.g., us-east-1, eu-west-2, eastasia)
    **Tier is REQUIRED** - Must specify: STANDARD, PREMIUM, or ENTERPRISE (Note: Azure does not support ENTERPRISE tier)
    **Product type is OPTIONAL** - Filter by specific product type
    
    **Discovery Endpoints:**
    - `/api/v1/regions?cloud=<cloud>` - Get available regions for a cloud
    - `/api/v1/tiers?cloud=<cloud>` - Get available tiers for a cloud
    - `/api/v1/pricing/product-types?cloud=<cloud>&region=<region>&tier=<tier>` - Get available product types
    
    **DBU Pricing:**
    - Base price per DBU for different product types and tiers
    - Varies by cloud, region, tier, and product type
    - Used to convert DBU usage to dollar costs
    
    **Example Requests:**
    - `/api/v1/pricing/dbu-rates?cloud=AWS&region=us-east-1&tier=STANDARD` - All rates for STANDARD tier
    - `/api/v1/pricing/dbu-rates?cloud=AWS&region=us-east-1&tier=PREMIUM&product_type=JOBS` - Jobs rate only
    """
    # Validate cloud (required)
    error = await validate_cloud(cloud)
    if error:
        return error
    
    # Validate region (required)
    error = await validate_region(cloud, region, db)
    if error:
        return error
    
    # Validate tier (required) - dynamically checks valid tiers for this cloud
    error = await validate_tier(cloud, tier, db)
    if error:
        return error
    
    # Validate product_type if provided
    if product_type:
        error = await validate_product_type(cloud, region, product_type, db)
        if error:
            return error
    
    try:
        # Build WHERE clause
        where_conditions = ["cloud = :cloud", "region = :region", "tier = :tier"]
        params = {"cloud": cloud.upper(), "region": region, "tier": tier.upper()}
        
        if product_type:
            where_conditions.append("product_type = :product_type")
            params["product_type"] = product_type.upper()
        
        where_clause = "WHERE " + " AND ".join(where_conditions)
        
        query = text(f"""
            SELECT 
                sku_name,
                product_type,
                cloud,
                region,
                tier,
                price_per_dbu
            FROM lakemeter.sync_pricing_dbu_rates
            {where_clause}
            ORDER BY product_type, sku_name
        """)
        result = await db.execute(query, params)
        results = result.fetchall()
        
        # Format results
        dbu_rates = []
        for r in results:
            dbu_rates.append({
                "sku_name": r.sku_name,
                "product_type": r.product_type,
                "cloud": r.cloud,
                "region": r.region,
                "tier": r.tier,
                "price_per_dbu": float(r.price_per_dbu) if r.price_per_dbu else None
            })
        
        return {
            "success": True,
            "data": {
                "cloud": cloud.upper(),
                "region": region,
                "tier": tier.upper(),
                "product_type_filter": product_type.upper() if product_type else None,
                "count": len(dbu_rates),
                "dbu_rates": dbu_rates
            }
        }
    except Exception as e:
        logger.error(f"Error fetching DBU rates: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }


@app.get("/api/v1/model-serving/gpu-types", tags=["Model Serving"])
async def get_model_serving_gpu_types(
    cloud: str = Query(..., description="Cloud provider: AWS, AZURE, GCP (required)"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get available GPU types for Model Serving in a specific cloud with their DBU rates.
    Returns cloud-specific GPU types like cpu, gpu_small_t4 (AWS), gpu_medium_a10g_1x (AWS/AZURE), gpu_medium_g2_standard_8 (GCP), etc.
    """
    # Validate cloud
    error = await validate_cloud(cloud)
    if error:
        return error
    
    try:
        query = text("""
            SELECT 
                size_or_model as gpu_type,
                dbu_rate
            FROM lakemeter.sync_product_serverless_rates
            WHERE product = 'model_serving'
                AND cloud = :cloud
            ORDER BY size_or_model
        """)
        result = await db.execute(query, {"cloud": cloud.upper()})
        results = result.fetchall()
        
        return {
            "success": True,
            "data": {
                "cloud": cloud.upper(),
                "count": len(results),
                "gpu_types": [
                    {
                        "gpu_type": r.gpu_type,
                        "dbu_rate": float(r.dbu_rate) if r.dbu_rate else None
                    }
                    for r in results
                ]
            }
        }
    except Exception as e:
        logger.error(f"Error fetching Model Serving GPU types: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }

@app.get("/api/v1/fmapi/databricks-models/list", tags=["FMAPI - Databricks"])
async def list_fmapi_databricks_models(
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get a simple list of all available Databricks FMAPI model names.
    Useful for populating dropdowns or validation.
    """
    try:
        query = text("""
            SELECT DISTINCT model
            FROM lakemeter.sync_product_fmapi_databricks
            ORDER BY model
        """)
        result = await db.execute(query)
        models = [r.model for r in result.fetchall()]
        
        return {
            "success": True,
            "data": {
                "count": len(models),
                "models": models
            }
        }
    except Exception as e:
        logger.error(f"Error fetching Databricks FMAPI model list: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }


@app.get("/api/v1/fmapi/databricks-models", tags=["FMAPI - Databricks"])
async def get_fmapi_databricks_models(
    model: str = Query(..., description="Model name (required). Use /list endpoint to see available models."),
    cloud: str = Query(None, description="Filter by cloud: AWS, AZURE, GCP (optional)"),
    rate_type: str = Query(None, description="Filter by rate type (optional). Valid values depend on the model."),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get available Databricks FMAPI models with their pricing information.
    
    **Model is REQUIRED** - Must specify a valid Databricks model name
    
    **Discovery Endpoints:**
    1. Get list of all available models:
       - `/api/v1/fmapi/databricks-models/list`
    
    **Dynamic Validation:**
    - Model (required) → must be a valid Databricks FMAPI model
    - Rate type (optional) → validated against available rate types for the specific model
    
    **Pricing Display:**
    - For hourly rates (provisioned): shows dbu_per_hour
    - For token-based rates: shows dbu_per_1M_tokens
    
    **Example Requests:**
    - `/api/v1/fmapi/databricks-models?model=llama-3-1-70b` - Get all pricing for this model
    - `/api/v1/fmapi/databricks-models?model=llama-3-1-70b&cloud=AWS` - Filter by cloud
    - `/api/v1/fmapi/databricks-models?model=mixtral-8x7b&rate_type=input_token` - Filter by rate type
    """
    # Validate model (required)
    error = await validate_fmapi_databricks_model(model, db)
    if error:
        return error
    
    # Validate cloud if provided
    if cloud:
        error = await validate_cloud(cloud)
        if error:
            return error
    
    # Validate rate_type if provided (dynamic validation based on model)
    if rate_type:
        error = await validate_fmapi_databricks_rate_type(model, rate_type, db)
        if error:
            return error
    
    try:
        # Build WHERE clause
        where_conditions = []
        params = {}
        
        # Model is required, always add it
        where_conditions.append("model = :model")
        params["model"] = model
        
        if cloud:
            where_conditions.append("cloud = :cloud")
            params["cloud"] = cloud.upper()
        
        if rate_type:
            where_conditions.append("rate_type = :rate_type")
            params["rate_type"] = rate_type
        
        where_clause = "WHERE " + " AND ".join(where_conditions)
        
        query = text(f"""
            SELECT 
                cloud,
                model,
                rate_type,
                dbu_rate,
                input_divisor,
                is_hourly
            FROM lakemeter.sync_product_fmapi_databricks
            {where_clause}
            ORDER BY cloud, model, rate_type
        """)
        result = await db.execute(query, params)
        results = result.fetchall()
        
        # Group by cloud and model
        models = {}
        for r in results:
            key = f"{r.cloud}:{r.model}"
            if key not in models:
                models[key] = {
                    "cloud": r.cloud,
                    "model": r.model,
                    "pricing": []
                }
            
            pricing_entry = {
                "rate_type": r.rate_type
            }
            
            # If hourly, show dbu_per_hour; if token-based, show dbu_per_1M_tokens
            if r.is_hourly:
                pricing_entry["dbu_per_hour"] = float(r.dbu_rate) if r.dbu_rate else None
            elif r.input_divisor == 1000000:
                pricing_entry["dbu_per_1M_tokens"] = float(r.dbu_rate) if r.dbu_rate else None
            else:
                # Fallback
                pricing_entry["dbu_rate"] = float(r.dbu_rate) if r.dbu_rate else None
                pricing_entry["input_divisor"] = float(r.input_divisor) if r.input_divisor else None
            
            models[key]["pricing"].append(pricing_entry)
        
        return {
            "success": True,
            "data": {
                "model_filter": model,
                "cloud_filter": cloud.upper() if cloud else None,
                "rate_type_filter": rate_type if rate_type else None,
                "count": len(models),
                "models": list(models.values())
            }
        }
    except Exception as e:
        logger.error(f"Error fetching FMAPI Databricks models: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }

@app.get("/api/v1/fmapi/proprietary-models/list", tags=["FMAPI - Proprietary"])
async def list_fmapi_proprietary_models(
    provider: str = Query(..., description="Provider (required): openai, anthropic, google"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get a list of all available proprietary FMAPI model names for a specific provider.
    Useful for populating dropdowns or validation.
    
    **Provider is REQUIRED** - Must specify one of: openai, anthropic, google
    """
    # Validate provider (required)
    error = await validate_fmapi_proprietary_provider(provider, db)
    if error:
        return error
    
    try:
        query = text("""
            SELECT DISTINCT model
            FROM lakemeter.sync_product_fmapi_proprietary
            WHERE provider = :provider
            ORDER BY model
        """)
        result = await db.execute(query, {"provider": provider.lower()})
        models = [r.model for r in result.fetchall()]
        
        return {
            "success": True,
            "data": {
                "provider": provider,
                "count": len(models),
                "models": models
            }
        }
    except Exception as e:
        logger.error(f"Error fetching proprietary FMAPI model list: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }


@app.get("/api/v1/fmapi/proprietary-models/options", tags=["FMAPI - Proprietary"])
async def get_fmapi_proprietary_model_options(
    provider: str = Query(..., description="Provider (required): openai, anthropic, google"),
    model: str = Query(..., description="Model name (required)"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get available context_length and rate_type options for a specific provider and model.
    Useful for populating dropdowns or validation.
    """
    # Validate provider
    error = await validate_fmapi_proprietary_provider(provider, db)
    if error:
        return error
    
    # Validate model for this provider
    error = await validate_fmapi_proprietary_model(model, provider, db)
    if error:
        return error
    
    try:
        query = text("""
            SELECT DISTINCT 
                context_length,
                rate_type,
                endpoint_type
            FROM lakemeter.sync_product_fmapi_proprietary
            WHERE provider = :provider AND model = :model
            ORDER BY endpoint_type, context_length, rate_type
        """)
        result = await db.execute(query, {
            "provider": provider.lower(),
            "model": model
        })
        results = result.fetchall()
        
        # Extract unique values
        context_lengths = sorted(list(set([r.context_length for r in results])))
        rate_types = sorted(list(set([r.rate_type for r in results])))
        endpoint_types = sorted(list(set([r.endpoint_type for r in results])))
        
        return {
            "success": True,
            "data": {
                "provider": provider,
                "model": model,
                "available_context_lengths": context_lengths,
                "available_rate_types": rate_types,
                "available_endpoint_types": endpoint_types
            }
        }
    except Exception as e:
        logger.error(f"Error fetching proprietary FMAPI model options: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }


@app.get("/api/v1/fmapi/proprietary-models", tags=["FMAPI - Proprietary"])
async def get_fmapi_proprietary_models(
    provider: str = Query(..., description="Provider (required): openai, anthropic, google"),
    cloud: str = Query(None, description="Filter by cloud: AWS, AZURE, GCP (optional)"),
    model: str = Query(None, description="Filter by model name (optional). Use /list endpoint to see available models for this provider."),
    endpoint_type: str = Query(None, description="Filter by endpoint type (optional). Valid values depend on provider and model."),
    context_length: str = Query(None, description="Filter by context length (optional). Valid values depend on provider, model, and endpoint_type."),
    rate_type: str = Query(None, description="Filter by rate type (optional). Valid values depend on provider, model, endpoint_type, and context_length."),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get available proprietary FMAPI models (OpenAI, Anthropic, Google) with their pricing.
    
    **Provider is REQUIRED** - Must specify one of: openai, anthropic, google
    
    **Discovery Endpoints:**
    1. Get available models for a provider:
       - `/api/v1/fmapi/proprietary-models/list?provider=<provider>`
    
    2. Get available options (endpoint_type, context_length, rate_type) for a specific model:
       - `/api/v1/fmapi/proprietary-models/options?provider=<provider>&model=<model>`
    
    **Dynamic Validation Hierarchy:**
    - Provider (required) → determines available models
    - Model (optional) → must be valid for the provider
    - Endpoint type (optional) → must be valid for provider+model, requires model
    - Context length (optional) → validated against provider+model+endpoint_type, requires model
    - Rate type (optional) → validated against provider+model+endpoint_type+context_length, requires model
    
    All validators query the database dynamically to ensure only valid combinations are accepted.
    
    **Pricing Display:**
    - For hourly rates (batch inference): shows dbu_per_hour
    - For token-based rates: shows dbu_per_1M_tokens
    
    **Example Requests:**
    - `/api/v1/fmapi/proprietary-models?provider=anthropic` - All Anthropic models
    - `/api/v1/fmapi/proprietary-models?provider=openai&model=gpt-4o` - Specific model
    - `/api/v1/fmapi/proprietary-models?provider=anthropic&model=claude-sonnet-4-5&endpoint_type=in_geo` - Filter by endpoint
    - `/api/v1/fmapi/proprietary-models?provider=anthropic&model=claude-sonnet-4-5&endpoint_type=in_geo&context_length=short` - Filter by context
    - `/api/v1/fmapi/proprietary-models?provider=openai&model=gpt-4o&rate_type=input_token` - Filter by rate type
    """
    # Validate provider (required)
    error = await validate_fmapi_proprietary_provider(provider, db)
    if error:
        return error
    
    # Validate cloud if provided
    if cloud:
        error = await validate_cloud(cloud)
        if error:
            return error
    
    # Validate model if provided (checks against provider's available models)
    if model:
        error = await validate_fmapi_proprietary_model(model, provider, db)
        if error:
            return error
    
    # Validate endpoint_type if provided (requires model)
    if endpoint_type:
        if not model:
            return {
                "success": False,
                "error": {
                    "code": "MISSING_PARAMETER",
                    "message": "endpoint_type filter requires model parameter to be specified",
                    "field": "endpoint_type"
                }
            }
        error = await validate_fmapi_proprietary_endpoint_type(provider, model, endpoint_type, db)
        if error:
            return error
    
    # Validate context_length if provided (requires model, can use endpoint_type if specified)
    if context_length:
        if not model:
            return {
                "success": False,
                "error": {
                    "code": "MISSING_PARAMETER",
                    "message": "context_length filter requires model parameter to be specified",
                    "field": "context_length"
                }
            }
        error = await validate_fmapi_proprietary_context_length(
            provider, model, context_length, endpoint_type, db
        )
        if error:
            return error
    
    # Validate rate_type if provided (requires model, can use endpoint_type and context_length if specified)
    if rate_type:
        if not model:
            return {
                "success": False,
                "error": {
                    "code": "MISSING_PARAMETER",
                    "message": "rate_type filter requires model parameter to be specified",
                    "field": "rate_type"
                }
            }
        error = await validate_fmapi_proprietary_rate_type(
            provider, model, rate_type, endpoint_type, context_length, db
        )
        if error:
            return error
    
    try:
        # Build WHERE clause
        where_conditions = []
        params = {}
        
        # Provider is required, always add it
        where_conditions.append("provider = :provider")
        params["provider"] = provider.lower()
        
        if cloud:
            where_conditions.append("cloud = :cloud")
            params["cloud"] = cloud.upper()
        
        if model:
            where_conditions.append("model = :model")
            params["model"] = model
        
        if endpoint_type:
            where_conditions.append("endpoint_type = :endpoint_type")
            params["endpoint_type"] = endpoint_type
        
        if context_length:
            where_conditions.append("context_length = :context_length")
            params["context_length"] = context_length
        
        if rate_type:
            where_conditions.append("rate_type = :rate_type")
            params["rate_type"] = rate_type
        
        where_clause = "WHERE " + " AND ".join(where_conditions)
        
        query = text(f"""
            SELECT 
                cloud,
                provider,
                model,
                endpoint_type,
                context_length,
                rate_type,
                dbu_rate,
                input_divisor,
                is_hourly
            FROM lakemeter.sync_product_fmapi_proprietary
            {where_clause}
            ORDER BY cloud, provider, model, endpoint_type, context_length, rate_type
        """)
        result = await db.execute(query, params)
        results = result.fetchall()
        
        # Group by cloud, provider, and model
        models = {}
        for r in results:
            key = f"{r.cloud}:{r.provider}:{r.model}"
            if key not in models:
                models[key] = {
                    "cloud": r.cloud,
                    "provider": r.provider,
                    "model": r.model,
                    "pricing": []
                }
            
            pricing_entry = {
                "endpoint_type": r.endpoint_type,
                "context_length": r.context_length,
                "rate_type": r.rate_type
            }
            
            # If hourly, show dbu_per_hour; if token-based, show dbu_per_1M_tokens
            if r.is_hourly:
                pricing_entry["dbu_per_hour"] = float(r.dbu_rate) if r.dbu_rate else None
            elif r.input_divisor == 1000000:
                pricing_entry["dbu_per_1M_tokens"] = float(r.dbu_rate) if r.dbu_rate else None
            else:
                # Fallback
                pricing_entry["dbu_rate"] = float(r.dbu_rate) if r.dbu_rate else None
                pricing_entry["input_divisor"] = float(r.input_divisor) if r.input_divisor else None
            
            models[key]["pricing"].append(pricing_entry)
        
        return {
            "success": True,
            "data": {
                "cloud_filter": cloud.upper() if cloud else None,
                "provider_filter": provider,
                "model_filter": model if model else None,
                "endpoint_type_filter": endpoint_type if endpoint_type else None,
                "context_length_filter": context_length if context_length else None,
                "rate_type_filter": rate_type if rate_type else None,
                "count": len(models),
                "models": list(models.values())
            }
        }
    except Exception as e:
        logger.error(f"Error fetching FMAPI proprietary models: {e}")
        return {
            "success": False,
            "error": {"message": str(e), "code": "DATABASE_ERROR"}
        }


# ============================================================================
# COST CALCULATION ENDPOINTS
# ============================================================================

# Request Models
class JobsClassicCalculationRequest(BaseModel):
    """Request model for JOBS Classic cost calculation"""
    # Core parameters
    cloud: str = Field(..., description="Cloud provider: AWS, AZURE, GCP")
    region: str = Field(..., description="Region code (e.g., us-east-1)")
    tier: str = Field(..., description="Pricing tier: STANDARD, PREMIUM, ENTERPRISE")
    
    # Compute configuration
    driver_node_type: str = Field(..., description="Driver instance type (e.g., m5.xlarge)")
    worker_node_type: str = Field(..., description="Worker instance type (e.g., m5.xlarge)")
    num_workers: int = Field(..., ge=0, description="Number of worker nodes")
    photon_enabled: bool = Field(default=False, description="Enable Photon acceleration")
    
    # Pricing tiers
    driver_pricing_tier: str = Field(default="on_demand", description="Driver VM pricing tier: on_demand, spot, reserved_1y, reserved_3y")
    worker_pricing_tier: str = Field(default="on_demand", description="Worker VM pricing tier: on_demand, spot, reserved_1y, reserved_3y")
    driver_payment_option: Optional[str] = Field(default="NA", description="Payment option for reserved instances: NA, no_upfront, partial_upfront, all_upfront")
    worker_payment_option: Optional[str] = Field(default="NA", description="Payment option for reserved instances: NA, no_upfront, partial_upfront, all_upfront")
    
    # Usage patterns (provide EITHER run-based OR direct hours)
    runs_per_day: Optional[int] = Field(None, ge=0, description="Number of job runs per day (optional if hours_per_month provided)")
    avg_runtime_minutes: Optional[int] = Field(None, ge=0, description="Average runtime per run in minutes (optional if hours_per_month provided)")
    days_per_month: Optional[int] = Field(None, ge=1, le=31, description="Number of days per month (optional if hours_per_month provided)")
    hours_per_month: Optional[float] = Field(None, ge=0, description="Direct hours per month (optional if run-based parameters provided)")


@app.post("/api/v1/calculate/jobs-classic", tags=["Cost Calculation"])
async def calculate_jobs_classic_cost(
    request: JobsClassicCalculationRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Calculate cost for JOBS Classic workload.
    
    **This endpoint:**
    - Calculates DBU and VM costs for JOBS Classic workloads
    - Supports all clouds (AWS, AZURE, GCP)
    - Supports all pricing tiers and payment options
    - Returns detailed cost breakdown
    
    **Formula:**
    ```
    Hours/Month = runs_per_day × (avg_runtime_minutes / 60) × days_per_month
    DBU/Hour = (driver_dbu_rate + worker_dbu_rate × num_workers) × photon_multiplier
    DBU/Month = DBU/Hour × Hours/Month
    VM Cost/Hour = driver_vm_cost + worker_vm_cost × num_workers
    VM Cost/Month = VM Cost/Hour × Hours/Month
    DBU Cost = DBU/Month × base_dbu_price ($/DBU)
    Total Cost = DBU Cost + VM Cost
    ```
    
    **Example Requests:**
    
    Option 1 - Run-based calculation:
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "driver_node_type": "m5.xlarge",
      "worker_node_type": "m5.xlarge",
      "num_workers": 10,
      "photon_enabled": true,
      "driver_pricing_tier": "on_demand",
      "worker_pricing_tier": "spot",
      "driver_payment_option": "NA",
      "worker_payment_option": "NA",
      "runs_per_day": 8,
      "avg_runtime_minutes": 60,
      "days_per_month": 30
    }
    ```
    
    Option 2 - Direct hours:
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "driver_node_type": "m5.xlarge",
      "worker_node_type": "m5.xlarge",
      "num_workers": 10,
      "photon_enabled": true,
      "driver_pricing_tier": "on_demand",
      "worker_pricing_tier": "spot",
      "driver_payment_option": "NA",
      "worker_payment_option": "NA",
      "hours_per_month": 160
    }
    ```
    """
    # Validate usage parameters - must provide EITHER run-based OR direct hours
    has_run_params = all([
        request.runs_per_day is not None,
        request.avg_runtime_minutes is not None
    ])
    has_hours = request.hours_per_month is not None
    
    if not has_run_params and not has_hours:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "MISSING_USAGE_PARAMETERS",
                "message": "Must provide either (runs_per_day + avg_runtime_minutes) OR hours_per_month",
                "required": "Either ['runs_per_day', 'avg_runtime_minutes'] or ['hours_per_month']"
            }
        )
    
    if has_run_params and has_hours:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "CONFLICTING_USAGE_PARAMETERS",
                "message": "Cannot provide both run-based parameters and hours_per_month. Choose one method.",
                "conflict": "Provided both run-based parameters AND hours_per_month"
            }
        )
    
    # Set defaults for days_per_month if using run-based calculation
    if has_run_params and request.days_per_month is None:
        request.days_per_month = 30
    
    # Validate cloud
    error = await validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate region
    error = await validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate tier
    error = await validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate instance types
    error = await validate_instance_type(request.cloud, request.driver_node_type, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_instance_type(request.cloud, request.worker_node_type, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate pricing tiers (driver cannot be spot)
    error = validate_pricing_tier(request.driver_pricing_tier, is_driver=True)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = validate_pricing_tier(request.worker_pricing_tier, is_driver=False)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate payment options
    if request.driver_payment_option:
        error = validate_payment_option(request.driver_payment_option)
        if error:
            raise HTTPException(status_code=400, detail=error["error"])
    
    if request.worker_payment_option:
        error = validate_payment_option(request.worker_payment_option)
        if error:
            raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate pricing_tier and payment_option combinations (cloud-specific)
    error = validate_pricing_payment_combination(request.cloud, request.driver_pricing_tier, request.driver_payment_option)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = validate_pricing_payment_combination(request.cloud, request.worker_pricing_tier, request.worker_payment_option)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    try:
        # Call the database function - use :param syntax which SQLAlchemy will convert
        query = text("""
            SELECT 
                dbu_per_hour,
                hours_per_month,
                dbu_per_month,
                dbu_price,
                dbu_cost_per_month,
                driver_vm_cost_per_hour,
                worker_vm_cost_per_hour,
                total_vm_cost_per_hour,
                driver_vm_cost_per_month,
                total_worker_vm_cost_per_month,
                vm_cost_per_month,
                cost_per_month
            FROM lakemeter.calculate_line_item_costs(
                :p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10,
                :p11, :p12, :p13, :p14, :p15, :p16, :p17, :p18, :p19, :p20,
                :p21, :p22, :p23, :p24, :p25, :p26, :p27, :p28, :p29, :p30,
                :p31, :p32, :p33, :p34, :p35
            )
        """)
        
        result = await db.execute(query, {
            "p1": "JOBS",
            "p2": request.cloud.upper(),
            "p3": request.region,
            "p4": request.tier.upper(),
            "p5": False,
            "p6": request.photon_enabled,
            "p7": None,
            "p8": request.driver_node_type,
            "p9": request.worker_node_type,
            "p10": request.num_workers,
            "p11": request.driver_pricing_tier,
            "p12": request.worker_pricing_tier,
            "p13": request.runs_per_day if has_run_params else 0,
            "p14": request.avg_runtime_minutes if has_run_params else 0,
            "p15": request.days_per_month if has_run_params else 30,
            "p16": request.hours_per_month if has_hours else None,
            "p17": "standard",
            "p18": None,
            "p19": None,
            "p20": 1,
            "p21": "on_demand",
            "p22": None,
            "p23": 0,
            "p24": None,
            "p25": None,
            "p26": None,
            "p27": "global",
            "p28": "all",
            "p29": "input_token",
            "p30": 0,
            "p31": 0,
            "p32": 1,
            "p33": request.driver_payment_option or "NA",
            "p34": request.worker_payment_option or "NA",
            "p35": "NA"
        })
        
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")
        
        # Determine SKU type
        sku_type = get_sku_type(
            workload_type="JOBS",
            serverless_enabled=False,
            photon_enabled=request.photon_enabled
        )
        
        return {
            "success": True,
            "data": {
                "workload_type": "JOBS_CLASSIC",
                "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "driver_node_type": request.driver_node_type,
                    "worker_node_type": request.worker_node_type,
                    "num_workers": request.num_workers,
                    "photon_enabled": request.photon_enabled,
                    "driver_pricing_tier": request.driver_pricing_tier,
                    "worker_pricing_tier": request.worker_pricing_tier,
                    "driver_payment_option": request.driver_payment_option,
                    "worker_payment_option": request.worker_payment_option
                },
                "usage": {
                    "runs_per_day": request.runs_per_day,
                    "avg_runtime_minutes": request.avg_runtime_minutes,
                    "days_per_month": request.days_per_month,
                    "hours_per_month": float(row.hours_per_month) if row.hours_per_month else 0
                },
                "dbu_calculation": {
                    "dbu_per_hour": float(row.dbu_per_hour) if row.dbu_per_hour else 0,
                    "dbu_per_month": float(row.dbu_per_month) if row.dbu_per_month else 0,
                    "dbu_price": float(row.dbu_price) if row.dbu_price else 0,
                    "dbu_cost_per_month": float(row.dbu_cost_per_month) if row.dbu_cost_per_month else 0
                },
                "vm_costs": {
                    "driver_vm_cost_per_hour": float(row.driver_vm_cost_per_hour) if row.driver_vm_cost_per_hour else 0,
                    "worker_vm_cost_per_hour": float(row.worker_vm_cost_per_hour) if row.worker_vm_cost_per_hour else 0,
                    "total_vm_cost_per_hour": float(row.total_vm_cost_per_hour) if row.total_vm_cost_per_hour else 0,
                    "driver_vm_cost_per_month": float(row.driver_vm_cost_per_month) if row.driver_vm_cost_per_month else 0,
                    "total_worker_vm_cost_per_month": float(row.total_worker_vm_cost_per_month) if row.total_worker_vm_cost_per_month else 0,
                    "vm_cost_per_month": float(row.vm_cost_per_month) if row.vm_cost_per_month else 0
                },
                "total_cost": {
                    "cost_per_month": float(row.cost_per_month) if row.cost_per_month else 0,
                    "breakdown": {
                        "dbu_cost": float(row.dbu_cost_per_month) if row.dbu_cost_per_month else 0,
                        "vm_cost": float(row.vm_cost_per_month) if row.vm_cost_per_month else 0
                    }
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        }
        logger.error(f"Error calculating JOBS Classic cost: {error_detail}")
        return error_detail


# Request Model for All-Purpose Compute
class AllPurposeClassicCalculationRequest(BaseModel):
    """Request model for All-Purpose Classic Compute cost calculation"""
    # Core parameters
    cloud: str = Field(..., description="Cloud provider: AWS, AZURE, GCP")
    region: str = Field(..., description="Region code (e.g., us-east-1)")
    tier: str = Field(..., description="Pricing tier: STANDARD, PREMIUM, ENTERPRISE")
    
    # Compute configuration
    driver_node_type: str = Field(..., description="Driver node instance type (e.g., m5.xlarge)")
    worker_node_type: str = Field(..., description="Worker node instance type (e.g., m5.xlarge)")
    num_workers: int = Field(..., description="Number of worker nodes", ge=0)
    photon_enabled: bool = Field(False, description="Enable Photon acceleration")
    
    # Pricing options
    driver_pricing_tier: str = Field("on_demand", description="Driver pricing: on_demand, spot, reserved_1y, reserved_3y")
    worker_pricing_tier: str = Field("on_demand", description="Worker pricing: on_demand, spot, reserved_1y, reserved_3y")
    driver_payment_option: str = Field("NA", description="Driver payment: NA, no_upfront, partial_upfront, all_upfront")
    worker_payment_option: str = Field("NA", description="Worker payment: NA, no_upfront, partial_upfront, all_upfront")
    
    # Usage parameters (provide EITHER run-based OR direct hours)
    runs_per_day: Optional[int] = Field(None, ge=0, description="Number of cluster starts per day (optional if hours_per_month provided)")
    avg_runtime_minutes: Optional[int] = Field(None, ge=0, description="Average runtime per session in minutes (optional if hours_per_month provided)")
    days_per_month: Optional[int] = Field(None, ge=1, le=31, description="Number of days per month (optional if hours_per_month provided)")
    hours_per_month: Optional[float] = Field(None, ge=0, description="Direct hours per month (optional if run-based parameters provided)")


@app.post("/api/v1/calculate/all-purpose-classic", tags=["Cost Calculation"])
async def calculate_all_purpose_classic_cost(
    request: AllPurposeClassicCalculationRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Calculate cost for All-Purpose Classic Compute workload.
    
    **All-Purpose Classic:**
    - Used for interactive notebooks, ad-hoc queries, and development
    - Supports scheduled starts or continuous running
    - Same pricing structure as JOBS Classic but for interactive use
    
    **Formula:**
    ```
    Hours/Month = runs_per_day × (avg_runtime_minutes / 60) × days_per_month
              OR = hours_per_month (if provided directly)
    DBU/Hour = (driver_dbu_rate + worker_dbu_rate × num_workers) × photon_multiplier
    DBU/Month = DBU/Hour × Hours/Month
    VM Cost/Hour = driver_vm_cost + worker_vm_cost × num_workers
    VM Cost/Month = VM Cost/Hour × Hours/Month
    DBU Cost = DBU/Month × base_dbu_price ($/DBU)
    Total Cost = DBU Cost + VM Cost
    ```
    
    **Example Requests:**
    
    Option 1 - Run-based calculation (scheduled clusters):
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "driver_node_type": "m5.xlarge",
      "worker_node_type": "m5.xlarge",
      "num_workers": 2,
      "photon_enabled": false,
      "driver_pricing_tier": "on_demand",
      "worker_pricing_tier": "spot",
      "driver_payment_option": "NA",
      "worker_payment_option": "NA",
      "runs_per_day": 3,
      "avg_runtime_minutes": 120,
      "days_per_month": 22
    }
    ```
    
    Option 2 - Direct hours (continuous/always-on clusters):
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "driver_node_type": "m5.xlarge",
      "worker_node_type": "m5.xlarge",
      "num_workers": 2,
      "photon_enabled": false,
      "driver_pricing_tier": "on_demand",
      "worker_pricing_tier": "reserved_1y",
      "driver_payment_option": "NA",
      "worker_payment_option": "no_upfront",
      "hours_per_month": 730
    }
    ```
    """
    # Validate usage parameters - must provide EITHER run-based OR direct hours
    has_run_params = all([
        request.runs_per_day is not None,
        request.avg_runtime_minutes is not None
    ])
    has_hours = request.hours_per_month is not None
    
    if not has_run_params and not has_hours:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "MISSING_USAGE_PARAMETERS",
                "message": "Must provide either (runs_per_day + avg_runtime_minutes) OR hours_per_month",
                "required": "Either ['runs_per_day', 'avg_runtime_minutes'] or ['hours_per_month']"
            }
        )
    
    if has_run_params and has_hours:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "CONFLICTING_USAGE_PARAMETERS",
                "message": "Cannot provide both run-based parameters and hours_per_month. Choose one method.",
                "conflict": "Provided both run-based parameters AND hours_per_month"
            }
        )
    
    # Set defaults for days_per_month if using run-based calculation
    if has_run_params and request.days_per_month is None:
        request.days_per_month = 30
    
    # Validate cloud
    error = await validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate region
    error = await validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate tier
    error = await validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate instance types
    error = await validate_instance_type(request.cloud, request.driver_node_type, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_instance_type(request.cloud, request.worker_node_type, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate pricing tiers and payment options (driver cannot be spot)
    error = validate_pricing_tier(request.driver_pricing_tier, is_driver=True)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = validate_pricing_tier(request.worker_pricing_tier, is_driver=False)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate payment options
    if request.driver_payment_option:
        error = validate_payment_option(request.driver_payment_option)
        if error:
            raise HTTPException(status_code=400, detail=error["error"])
    
    if request.worker_payment_option:
        error = validate_payment_option(request.worker_payment_option)
        if error:
            raise HTTPException(status_code=400, detail=error["error"])
    
    try:
        # Call the database function (ALL_PURPOSE uses same calculation as JOBS)
        query = text("""
            SELECT 
                dbu_per_hour,
                hours_per_month,
                dbu_per_month,
                dbu_price,
                dbu_cost_per_month,
                driver_vm_cost_per_hour,
                worker_vm_cost_per_hour,
                total_vm_cost_per_hour,
                driver_vm_cost_per_month,
                total_worker_vm_cost_per_month,
                vm_cost_per_month,
                cost_per_month
            FROM lakemeter.calculate_line_item_costs(
                :p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10,
                :p11, :p12, :p13, :p14, :p15, :p16, :p17, :p18, :p19, :p20,
                :p21, :p22, :p23, :p24, :p25, :p26, :p27, :p28, :p29, :p30,
                :p31, :p32, :p33, :p34, :p35
            )
        """)
        
        result = await db.execute(query, {
            "p1": "ALL_PURPOSE",                         # workload_type (different from JOBS)
            "p2": request.cloud.upper(),                 # cloud
            "p3": request.region,                        # region
            "p4": request.tier.upper(),                  # tier
            "p5": False,                                 # serverless_enabled
            "p6": request.photon_enabled,                # photon_enabled
            "p7": None,                                  # dlt_edition
            "p8": request.driver_node_type,              # driver_node_type
            "p9": request.worker_node_type,              # worker_node_type
            "p10": request.num_workers,                  # num_workers
            "p11": request.driver_pricing_tier,          # driver_pricing_tier
            "p12": request.worker_pricing_tier,          # worker_pricing_tier
            "p13": request.runs_per_day if has_run_params else 0,                # runs_per_day
            "p14": request.avg_runtime_minutes if has_run_params else 0,         # avg_runtime_minutes
            "p15": request.days_per_month if has_run_params else 30,             # days_per_month
            "p16": request.hours_per_month if has_hours else None,               # hours_per_month
            "p17": "standard",                           # serverless_mode
            "p18": None,                                 # dbsql_warehouse_type
            "p19": None,                                 # dbsql_warehouse_size
            "p20": 1,                                    # dbsql_num_clusters
            "p21": "on_demand",                          # dbsql_vm_pricing_tier
            "p22": None,                                 # vector_search_mode
            "p23": 0,                                    # vector_search_capacity_millions
            "p24": None,                                 # model_serving_gpu_type
            "p25": None,                                 # fmapi_model
            "p26": None,                                 # fmapi_provider
            "p27": "global",                             # fmapi_endpoint_type
            "p28": "all",                                # fmapi_context_length
            "p29": "input_token",                        # fmapi_rate_type
            "p30": 0,                                    # fmapi_quantity
            "p31": 0,                                    # lakebase_cu
            "p32": 1,                                    # lakebase_ha_nodes
            "p33": request.driver_payment_option or "NA", # driver_payment_option
            "p34": request.worker_payment_option or "NA", # worker_payment_option
            "p35": "NA"                                  # dbsql_vm_payment_option
        })
        
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")
        
        # Determine SKU type
        sku_type = get_sku_type(
            workload_type="ALL_PURPOSE",
            serverless_enabled=False,
            photon_enabled=request.photon_enabled
        )
        
        return {
            "success": True,
            "data": {
                "workload_type": "ALL_PURPOSE_COMPUTE",
                "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "driver_node_type": request.driver_node_type,
                    "worker_node_type": request.worker_node_type,
                    "num_workers": request.num_workers,
                    "photon_enabled": request.photon_enabled,
                    "driver_pricing_tier": request.driver_pricing_tier,
                    "worker_pricing_tier": request.worker_pricing_tier,
                    "driver_payment_option": request.driver_payment_option,
                    "worker_payment_option": request.worker_payment_option
                },
                "usage": {
                    "hours_per_month": float(row[1])
                },
                "dbu_calculation": {
                    "dbu_per_hour": float(row[0]),
                    "dbu_per_month": float(row[2]),
                    "dbu_price": float(row[3]),
                    "dbu_cost_per_month": float(row[4])
                },
                "vm_costs": {
                    "driver_vm_cost_per_hour": float(row[5]),
                    "worker_vm_cost_per_hour": float(row[6]),
                    "total_vm_cost_per_hour": float(row[7]),
                    "driver_vm_cost_per_month": float(row[8]),
                    "total_worker_vm_cost_per_month": float(row[9]),
                    "vm_cost_per_month": float(row[10])
                },
                "total_cost": {
                    "cost_per_month": float(row[11]),
                    "breakdown": {
                        "dbu_cost": float(row[4]),
                        "vm_cost": float(row[10])
                    }
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        }
        logger.error(f"Error calculating All-Purpose Compute cost: {error_detail}")
        return error_detail


# Request Model for JOBS Serverless
class JobsServerlessCalculationRequest(BaseModel):
    """Request model for JOBS Serverless cost calculation"""
    # Core parameters
    cloud: str = Field(..., description="Cloud provider: AWS, AZURE, GCP")
    region: str = Field(..., description="Region code (e.g., us-east-1)")
    tier: str = Field(..., description="Pricing tier: STANDARD, PREMIUM, ENTERPRISE")
    
    # Node types (needed for DBU rate calculation even though no VM costs)
    driver_node_type: str = Field(..., description="Driver node instance type (e.g., m5.xlarge)")
    worker_node_type: str = Field(..., description="Worker node instance type (e.g., m5.xlarge)")
    num_workers: int = Field(..., description="Number of worker nodes", ge=0)
    
    # Serverless configuration
    # Note: Photon is ALWAYS enabled for serverless workloads (no parameter needed)
    serverless_mode: str = Field("standard", description="Serverless mode: standard or performance")
    
    # Usage parameters (provide EITHER run-based OR direct hours)
    runs_per_day: Optional[int] = Field(None, ge=0, description="Number of job runs per day (optional if hours_per_month provided)")
    avg_runtime_minutes: Optional[int] = Field(None, ge=0, description="Average runtime per job in minutes (optional if hours_per_month provided)")
    days_per_month: Optional[int] = Field(None, ge=1, le=31, description="Number of days per month (optional if hours_per_month provided)")
    hours_per_month: Optional[float] = Field(None, ge=0, description="Direct hours per month (optional if run-based parameters provided)")


@app.post("/api/v1/calculate/jobs-serverless", tags=["Cost Calculation"])
async def calculate_jobs_serverless_cost(
    request: JobsServerlessCalculationRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Calculate cost for JOBS Serverless workload.
    
    **JOBS Serverless:**
    - No infrastructure management
    - Pay only for DBU usage (no VM costs)
    - Automatic scaling
    - Photon is ALWAYS enabled (included in serverless)
    - Two modes: standard (1x) and performance (2x multiplier)
    
    **Formula:**
    ```
    Hours/Month = runs_per_day × (avg_runtime_minutes / 60) × days_per_month
    DBU/Hour = base_dbu_rate × photon_multiplier (always on) × serverless_multiplier
    DBU/Month = DBU/Hour × Hours/Month
    Total Cost = DBU/Month × dbu_price (no VM costs for serverless)
    ```
    
    **Example Request:**
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "driver_node_type": "m5.xlarge",
      "worker_node_type": "m5.xlarge",
      "num_workers": 2,
      "serverless_mode": "performance",
      "runs_per_day": 10,
      "avg_runtime_minutes": 30,
      "days_per_month": 30
    }
    ```
    
    Or with direct hours:
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "driver_node_type": "m5.xlarge",
      "worker_node_type": "m5.xlarge",
      "num_workers": 2,
      "serverless_mode": "performance",
      "hours_per_month": 150
    }
    ```
    """
    # Validate usage parameters - must provide EITHER run-based OR direct hours
    has_run_params = all([
        request.runs_per_day is not None,
        request.avg_runtime_minutes is not None
    ])
    has_hours = request.hours_per_month is not None
    
    if not has_run_params and not has_hours:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "MISSING_USAGE_PARAMETERS",
                "message": "Must provide either (runs_per_day + avg_runtime_minutes) OR hours_per_month",
                "required": "Either ['runs_per_day', 'avg_runtime_minutes'] or ['hours_per_month']"
            }
        )
    
    if has_run_params and has_hours:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "CONFLICTING_USAGE_PARAMETERS",
                "message": "Cannot provide both run-based parameters and hours_per_month. Choose one method.",
                "conflict": "Provided both run-based parameters AND hours_per_month"
            }
        )
    
    # Set defaults for days_per_month if using run-based calculation
    if has_run_params and request.days_per_month is None:
        request.days_per_month = 30
    
    # Validate cloud
    error = await validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate region
    error = await validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate tier
    error = await validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate instance types (needed for DBU calculation even though no VM costs)
    error = await validate_instance_type(request.cloud, request.driver_node_type, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_instance_type(request.cloud, request.worker_node_type, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate serverless mode
    if request.serverless_mode.lower() not in ["standard", "performance"]:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_SERVERLESS_MODE",
                "message": f"Invalid serverless mode: {request.serverless_mode}",
                "field": "serverless_mode",
                "allowed_values": ["standard", "performance"]
            }
        )
    
    try:
        # Call the database function with serverless parameters
        query = text("""
            SELECT 
                dbu_per_hour,
                hours_per_month,
                dbu_per_month,
                dbu_price,
                dbu_cost_per_month,
                driver_vm_cost_per_hour,
                worker_vm_cost_per_hour,
                total_vm_cost_per_hour,
                driver_vm_cost_per_month,
                total_worker_vm_cost_per_month,
                vm_cost_per_month,
                cost_per_month
            FROM lakemeter.calculate_line_item_costs(
                :p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10,
                :p11, :p12, :p13, :p14, :p15, :p16, :p17, :p18, :p19, :p20,
                :p21, :p22, :p23, :p24, :p25, :p26, :p27, :p28, :p29, :p30,
                :p31, :p32, :p33, :p34, :p35
            )
        """)
        
        result = await db.execute(query, {
            "p1": "JOBS",                                # workload_type
            "p2": request.cloud.upper(),                 # cloud
            "p3": request.region,                        # region
            "p4": request.tier.upper(),                  # tier
            "p5": True,                                  # serverless_enabled = TRUE
            "p6": True,                                  # photon_enabled (ALWAYS TRUE for serverless)
            "p7": None,                                  # dlt_edition
            "p8": request.driver_node_type,              # driver_node_type (needed for DBU calculation)
            "p9": request.worker_node_type,              # worker_node_type (needed for DBU calculation)
            "p10": request.num_workers,                  # num_workers
            "p11": "on_demand",                          # driver_pricing_tier (not used)
            "p12": "on_demand",                          # worker_pricing_tier (not used)
            "p13": request.runs_per_day if has_run_params else 0,                 # runs_per_day
            "p14": request.avg_runtime_minutes if has_run_params else 0,          # avg_runtime_minutes
            "p15": request.days_per_month if has_run_params else 30,               # days_per_month
            "p16": request.hours_per_month if has_hours else None,                                 # hours_per_month
            "p17": request.serverless_mode.lower(),      # serverless_mode
            "p18": None,                                 # dbsql_warehouse_type
            "p19": None,                                 # dbsql_warehouse_size
            "p20": 1,                                    # dbsql_num_clusters
            "p21": "on_demand",                          # dbsql_vm_pricing_tier
            "p22": None,                                 # vector_search_mode
            "p23": 0,                                    # vector_search_capacity_millions
            "p24": None,                                 # model_serving_gpu_type
            "p25": None,                                 # fmapi_model
            "p26": None,                                 # fmapi_provider
            "p27": "global",                             # fmapi_endpoint_type
            "p28": "all",                                # fmapi_context_length
            "p29": "input_token",                        # fmapi_rate_type
            "p30": 0,                                    # fmapi_quantity
            "p31": 0,                                    # lakebase_cu
            "p32": 1,                                    # lakebase_ha_nodes
            "p33": "NA",                                 # driver_payment_option
            "p34": "NA",                                 # worker_payment_option
            "p35": "NA"                                  # dbsql_vm_payment_option
        })
        
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")
        
        # Determine SKU type
        sku_type = get_sku_type(
            workload_type="JOBS",
            serverless_enabled=True
        )
        
        return {
            "success": True,
            "data": {
                "workload_type": "JOBS_SERVERLESS",
                "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "driver_node_type": request.driver_node_type,
                    "worker_node_type": request.worker_node_type,
                    "num_workers": request.num_workers,
                    "photon_enabled": True,
                    "serverless_mode": request.serverless_mode.lower(),
                    "note": "Photon is always enabled for serverless workloads"
                },
                "usage": {
                    "runs_per_day": request.runs_per_day,
                    "avg_runtime_minutes": request.avg_runtime_minutes,
                    "days_per_month": request.days_per_month,
                    "hours_per_month": float(row[1])
                },
                "dbu_calculation": {
                    "dbu_per_hour": float(row[0]),
                    "dbu_per_month": float(row[2]),
                    "dbu_price": float(row[3]),
                    "dbu_cost_per_month": float(row[4])
                },
                "total_cost": {
                    "cost_per_month": float(row[11]),
                    "note": "Serverless has no VM costs - only DBU costs"
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        }
        logger.error(f"Error calculating JOBS Serverless cost: {error_detail}")
        return error_detail


# Request Model for All-Purpose Serverless
class AllPurposeServerlessCalculationRequest(BaseModel):
    """Request model for All-Purpose Serverless cost calculation"""
    # Core parameters
    cloud: str = Field(..., description="Cloud provider: AWS, AZURE, GCP")
    region: str = Field(..., description="Region code (e.g., us-east-1)")
    tier: str = Field(..., description="Pricing tier: STANDARD, PREMIUM, ENTERPRISE")
    
    # Node types (needed for DBU rate calculation even though no VM costs)
    driver_node_type: str = Field(..., description="Driver node instance type (e.g., m5.xlarge)")
    worker_node_type: str = Field(..., description="Worker node instance type (e.g., m5.xlarge)")
    num_workers: int = Field(..., description="Number of worker nodes", ge=0)
    
    # Serverless configuration
    # Note: Photon is ALWAYS enabled for serverless workloads (no parameter needed)
    serverless_mode: str = Field("standard", description="Serverless mode: standard or performance")
    
    # Usage parameters (provide EITHER run-based OR direct hours)
    runs_per_day: Optional[int] = Field(None, ge=0, description="Number of cluster starts per day (optional if hours_per_month provided)")
    avg_runtime_minutes: Optional[int] = Field(None, ge=0, description="Average runtime per session in minutes (optional if hours_per_month provided)")
    days_per_month: Optional[int] = Field(None, ge=1, le=31, description="Number of days per month (optional if hours_per_month provided)")
    hours_per_month: Optional[float] = Field(None, ge=0, description="Direct hours per month (optional if run-based parameters provided)")


@app.post("/api/v1/calculate/all-purpose-serverless", tags=["Cost Calculation"])
async def calculate_all_purpose_serverless_cost(
    request: AllPurposeServerlessCalculationRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Calculate cost for All-Purpose Serverless workload.
    
    **All-Purpose Serverless:**
    - No infrastructure management for interactive workloads
    - Pay only for DBU usage (no VM costs)
    - Automatic scaling
    - Photon is ALWAYS enabled (included in serverless)
    - Two modes: standard (1x) and performance (2x multiplier)
    
    **Formula:**
    ```
    Hours/Month = runs_per_day × (avg_runtime_minutes / 60) × days_per_month
              OR = hours_per_month (if provided directly)
    DBU/Hour = base_dbu_rate × photon_multiplier (always on) × serverless_multiplier
    DBU/Month = DBU/Hour × Hours/Month
    Total Cost = DBU/Month × dbu_price (no VM costs for serverless)
    ```
    
    **Example Requests:**
    
    Option 1 - Run-based calculation (scheduled clusters):
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "driver_node_type": "m5.xlarge",
      "worker_node_type": "m5.xlarge",
      "num_workers": 2,
      "serverless_mode": "performance",
      "runs_per_day": 5,
      "avg_runtime_minutes": 90,
      "days_per_month": 22
    }
    ```
    
    Option 2 - Direct hours (continuous/always-on):
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "driver_node_type": "m5.xlarge",
      "worker_node_type": "m5.xlarge",
      "num_workers": 2,
      "serverless_mode": "standard",
      "hours_per_month": 730
    }
    ```
    """
    # Validate usage parameters - must provide EITHER run-based OR direct hours
    has_run_params = all([
        request.runs_per_day is not None,
        request.avg_runtime_minutes is not None
    ])
    has_hours = request.hours_per_month is not None
    
    if not has_run_params and not has_hours:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "MISSING_USAGE_PARAMETERS",
                "message": "Must provide either (runs_per_day + avg_runtime_minutes) OR hours_per_month",
                "required": "Either ['runs_per_day', 'avg_runtime_minutes'] or ['hours_per_month']"
            }
        )
    
    if has_run_params and has_hours:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "CONFLICTING_USAGE_PARAMETERS",
                "message": "Cannot provide both run-based parameters and hours_per_month. Choose one method.",
                "conflict": "Provided both run-based parameters AND hours_per_month"
            }
        )
    
    # Set defaults for days_per_month if using run-based calculation
    if has_run_params and request.days_per_month is None:
        request.days_per_month = 30
    
    # Validate cloud
    error = await validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate region
    error = await validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate tier
    error = await validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate instance types (needed for DBU calculation even though no VM costs)
    error = await validate_instance_type(request.cloud, request.driver_node_type, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_instance_type(request.cloud, request.worker_node_type, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate serverless mode
    if request.serverless_mode.lower() not in ["standard", "performance"]:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_SERVERLESS_MODE",
                "message": f"Invalid serverless mode: {request.serverless_mode}",
                "field": "serverless_mode",
                "allowed_values": ["standard", "performance"]
            }
        )
    
    try:
        # Call the database function with serverless parameters
        query = text("""
            SELECT 
                dbu_per_hour,
                hours_per_month,
                dbu_per_month,
                dbu_price,
                dbu_cost_per_month,
                driver_vm_cost_per_hour,
                worker_vm_cost_per_hour,
                total_vm_cost_per_hour,
                driver_vm_cost_per_month,
                total_worker_vm_cost_per_month,
                vm_cost_per_month,
                cost_per_month
            FROM lakemeter.calculate_line_item_costs(
                :p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10,
                :p11, :p12, :p13, :p14, :p15, :p16, :p17, :p18, :p19, :p20,
                :p21, :p22, :p23, :p24, :p25, :p26, :p27, :p28, :p29, :p30,
                :p31, :p32, :p33, :p34, :p35
            )
        """)
        
        result = await db.execute(query, {
            "p1": "ALL_PURPOSE",                         # workload_type
            "p2": request.cloud.upper(),                 # cloud
            "p3": request.region,                        # region
            "p4": request.tier.upper(),                  # tier
            "p5": True,                                  # serverless_enabled = TRUE
            "p6": True,                                  # photon_enabled (ALWAYS TRUE for serverless)
            "p7": None,                                  # dlt_edition
            "p8": request.driver_node_type,              # driver_node_type (needed for DBU calculation)
            "p9": request.worker_node_type,              # worker_node_type (needed for DBU calculation)
            "p10": request.num_workers,                  # num_workers
            "p11": "on_demand",                          # driver_pricing_tier (not used)
            "p12": "on_demand",                          # worker_pricing_tier (not used)
            "p13": request.runs_per_day if has_run_params else 0,                 # runs_per_day
            "p14": request.avg_runtime_minutes if has_run_params else 0,          # avg_runtime_minutes
            "p15": request.days_per_month if has_run_params else 30,               # days_per_month
            "p16": request.hours_per_month if has_hours else None,                                 # hours_per_month
            "p17": request.serverless_mode.lower(),      # serverless_mode
            "p18": None,                                 # dbsql_warehouse_type
            "p19": None,                                 # dbsql_warehouse_size
            "p20": 1,                                    # dbsql_num_clusters
            "p21": "on_demand",                          # dbsql_vm_pricing_tier
            "p22": None,                                 # vector_search_mode
            "p23": 0,                                    # vector_search_capacity_millions
            "p24": None,                                 # model_serving_gpu_type
            "p25": None,                                 # fmapi_model
            "p26": None,                                 # fmapi_provider
            "p27": "global",                             # fmapi_endpoint_type
            "p28": "all",                                # fmapi_context_length
            "p29": "input_token",                        # fmapi_rate_type
            "p30": 0,                                    # fmapi_quantity
            "p31": 0,                                    # lakebase_cu
            "p32": 1,                                    # lakebase_ha_nodes
            "p33": "NA",                                 # driver_payment_option
            "p34": "NA",                                 # worker_payment_option
            "p35": "NA"                                  # dbsql_vm_payment_option
        })
        
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")
        
        # Determine SKU type
        sku_type = get_sku_type(
            workload_type="ALL_PURPOSE",
            serverless_enabled=True
        )
        
        return {
            "success": True,
            "data": {
                "workload_type": "ALL_PURPOSE_SERVERLESS",
                "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "driver_node_type": request.driver_node_type,
                    "worker_node_type": request.worker_node_type,
                    "num_workers": request.num_workers,
                    "photon_enabled": True,
                    "serverless_mode": request.serverless_mode.lower(),
                    "note": "Photon is always enabled for serverless workloads"
                },
                "usage": {
                    "runs_per_day": request.runs_per_day if has_run_params else None,
                    "avg_runtime_minutes": request.avg_runtime_minutes if has_run_params else None,
                    "days_per_month": request.days_per_month if has_run_params else None,
                    "hours_per_month": float(row[1])
                },
                "dbu_calculation": {
                    "dbu_per_hour": float(row[0]),
                    "dbu_per_month": float(row[2]),
                    "dbu_price": float(row[3]),
                    "dbu_cost_per_month": float(row[4])
                },
                "total_cost": {
                    "cost_per_month": float(row[11]),
                    "note": "Serverless has no VM costs - only DBU costs"
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        }
        logger.error(f"Error calculating All-Purpose Serverless cost: {error_detail}")
        return error_detail


# Request Model for DBSQL Classic/Pro
class DBSQLClassicProCalculationRequest(BaseModel):
    """Request model for DBSQL Classic/Pro warehouse cost calculation"""
    # Core parameters
    cloud: str = Field(..., description="Cloud provider: AWS, AZURE, GCP")
    region: str = Field(..., description="Region code (e.g., us-east-1)")
    tier: str = Field(..., description="Pricing tier: STANDARD, PREMIUM, ENTERPRISE")
    
    # DBSQL Warehouse configuration
    warehouse_type: str = Field(..., description="Warehouse type: CLASSIC or PRO")
    warehouse_size: str = Field(..., description="Warehouse size: X-Small, Small, Medium, Large, etc.")
    num_clusters: int = Field(1, description="Number of clusters (for auto-scaling)", ge=1, le=30)
    
    # VM Pricing options (required for CLASSIC/PRO)
    vm_pricing_tier: str = Field("on_demand", description="VM pricing tier: on_demand, spot, reserved_1y, reserved_3y")
    vm_payment_option: str = Field("NA", description="Payment option: NA, no_upfront, partial_upfront, all_upfront")
    
    # Usage parameters (provide EITHER run-based OR direct hours)
    runs_per_day: Optional[int] = Field(None, ge=0, description="Number of query runs per day (optional if hours_per_month provided)")
    avg_runtime_minutes: Optional[int] = Field(None, ge=0, description="Average runtime per run in minutes (optional if hours_per_month provided)")
    days_per_month: Optional[int] = Field(None, ge=1, le=31, description="Number of days per month (optional if hours_per_month provided)")
    hours_per_month: Optional[float] = Field(None, ge=0, description="Direct hours per month (optional if run-based parameters provided)")


@app.post("/api/v1/calculate/dbsql-classic-pro", tags=["Cost Calculation"])
async def calculate_dbsql_classic_pro_cost(
    request: DBSQLClassicProCalculationRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Calculate cost for DBSQL Classic/Pro warehouses (with VM costs).
    
    **Warehouse Types:**
    - **CLASSIC**: i3 instances, local SSD storage
    - **PRO**: Same as Classic but with enhanced reliability features
    
    **Formula:**
    ```
    Hours/Month = runs_per_day × (avg_runtime_minutes / 60) × days_per_month
              OR = hours_per_month (if provided directly)
    
    DBU/Hour = warehouse_dbu_rate × num_clusters
    VM Cost/Hour = (driver_vm_cost + worker_vm_cost × workers) × num_clusters
    Total Cost = (DBU Cost + VM Cost) × Hours/Month
    ```
    
    **Example Requests:**
    
    Option 1 - Run-based calculation:
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "warehouse_type": "PRO",
      "warehouse_size": "Medium",
      "num_clusters": 2,
      "vm_pricing_tier": "on_demand",
      "vm_payment_option": "NA",
      "runs_per_day": 5,
      "avg_runtime_minutes": 90,
      "days_per_month": 22
    }
    ```
    
    Option 2 - Direct hours:
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "warehouse_type": "CLASSIC",
      "warehouse_size": "Large",
      "num_clusters": 1,
      "vm_pricing_tier": "reserved_1y",
      "vm_payment_option": "no_upfront",
      "hours_per_month": 730
    }
    ```
    """
    # Validate warehouse type is CLASSIC or PRO
    if request.warehouse_type.upper() not in ["CLASSIC", "PRO"]:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_WAREHOUSE_TYPE",
                "message": f"Invalid warehouse type '{request.warehouse_type}' for this endpoint. Use 'CLASSIC' or 'PRO'. For SERVERLESS, use /api/v1/calculate/dbsql-serverless",
                "field": "warehouse_type",
                "allowed_values": ["CLASSIC", "PRO"]
            }
        )
    
    # Validate cloud
    error = await validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate region
    error = await validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate tier
    error = await validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate warehouse type and size
    error = await validate_warehouse_type(request.warehouse_type, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_warehouse_size(request.cloud, request.warehouse_type, request.warehouse_size, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate VM pricing
    error = validate_pricing_tier(request.vm_pricing_tier)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = validate_payment_option(request.vm_payment_option)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate pricing_tier and payment_option combination (cloud-specific)
    error = validate_pricing_payment_combination(request.cloud, request.vm_pricing_tier, request.vm_payment_option)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate usage parameters - must provide EITHER run-based OR direct hours
    has_run_params = all([
        request.runs_per_day is not None,
        request.avg_runtime_minutes is not None
    ])
    has_hours = request.hours_per_month is not None
    
    if not has_run_params and not has_hours:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "MISSING_USAGE_PARAMETERS",
                "message": "Must provide either (runs_per_day + avg_runtime_minutes) OR hours_per_month",
                "required": "Either ['runs_per_day', 'avg_runtime_minutes'] or ['hours_per_month']"
            }
        )
    
    if has_run_params and has_hours:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "CONFLICTING_USAGE_PARAMETERS",
                "message": "Cannot provide both run-based parameters and hours_per_month. Choose one method.",
                "conflict": "Provided both run-based parameters AND hours_per_month"
            }
        )
    
    # Set defaults for days_per_month if using run-based calculation
    if has_run_params and request.days_per_month is None:
        request.days_per_month = 30
    
    # Calculate hours_per_month from run-based parameters if provided
    if has_run_params:
        calculated_hours = request.runs_per_day * (request.avg_runtime_minutes / 60) * request.days_per_month
    else:
        calculated_hours = request.hours_per_month
    
    try:
        # Call the database function
        query = text("""
            SELECT 
                dbu_per_hour,
                hours_per_month,
                dbu_per_month,
                dbu_price,
                dbu_cost_per_month,
                driver_vm_cost_per_hour,
                worker_vm_cost_per_hour,
                total_vm_cost_per_hour,
                driver_vm_cost_per_month,
                total_worker_vm_cost_per_month,
                vm_cost_per_month,
                cost_per_month
            FROM lakemeter.calculate_line_item_costs(
                :p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10,
                :p11, :p12, :p13, :p14, :p15, :p16, :p17, :p18, :p19, :p20,
                :p21, :p22, :p23, :p24, :p25, :p26, :p27, :p28, :p29, :p30,
                :p31, :p32, :p33, :p34, :p35
            )
        """)
        
        result = await db.execute(query, {
            "p1": "DBSQL",                               # workload_type
            "p2": request.cloud.upper(),                 # cloud
            "p3": request.region,                        # region
            "p4": request.tier.upper(),                  # tier
            "p5": False,                                 # serverless_enabled
            "p6": False,                                 # photon_enabled
            "p7": None,                                  # dlt_edition
            "p8": None,                                  # driver_node_type (handled by warehouse config)
            "p9": None,                                  # worker_node_type (handled by warehouse config)
            "p10": 0,                                    # num_workers (handled by warehouse config)
            "p11": "on_demand",                          # driver_pricing_tier (not used for DBSQL)
            "p12": "on_demand",                          # worker_pricing_tier (not used for DBSQL)
            "p13": request.runs_per_day if has_run_params else 0,                 # runs_per_day
            "p14": request.avg_runtime_minutes if has_run_params else 0,          # avg_runtime_minutes
            "p15": request.days_per_month if has_run_params else 30,              # days_per_month
            "p16": request.hours_per_month if has_hours else None,                # hours_per_month
            "p17": "standard",                           # serverless_mode
            "p18": request.warehouse_type.upper(),       # dbsql_warehouse_type
            "p19": request.warehouse_size,               # dbsql_warehouse_size
            "p20": request.num_clusters,                 # dbsql_num_clusters
            "p21": request.vm_pricing_tier,              # dbsql_vm_pricing_tier
            "p22": None,                                 # vector_search_mode
            "p23": 0,                                    # vector_search_capacity_millions
            "p24": None,                                 # model_serving_gpu_type
            "p25": None,                                 # fmapi_model
            "p26": None,                                 # fmapi_provider
            "p27": "global",                             # fmapi_endpoint_type
            "p28": "all",                                # fmapi_context_length
            "p29": "input_token",                        # fmapi_rate_type
            "p30": 0,                                    # fmapi_quantity
            "p31": 0,                                    # lakebase_cu
            "p32": 1,                                    # lakebase_ha_nodes
            "p33": "NA",                                 # driver_payment_option
            "p34": "NA",                                 # worker_payment_option
            "p35": request.vm_payment_option or "NA"  # dbsql_vm_payment_option
        })
        
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")
        
        # Determine SKU type
        sku_type = get_sku_type(
            workload_type="DBSQL",
            dbsql_warehouse_type=request.warehouse_type
        )
        
        return {
            "success": True,
            "data": {
                "workload_type": "DBSQL_CLASSIC_PRO",
                "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "warehouse_type": request.warehouse_type.upper(),
                    "warehouse_size": request.warehouse_size,
                    "num_clusters": request.num_clusters,
                    "vm_pricing_tier": request.vm_pricing_tier,
                    "vm_payment_option": request.vm_payment_option
                },
                "usage": {
                    "hours_per_month": float(row[1])
                },
                "dbu_costs": {
                    "dbu_per_hour": float(row[0]),
                    "dbu_per_month": float(row[2]),
                    "dbu_price": float(row[3]),
                    "dbu_cost_per_month": float(row[4])
                },
                "vm_costs": {
                    "driver_vm_cost_per_hour": float(row[5]),
                    "worker_vm_cost_per_hour": float(row[6]),
                    "total_vm_cost_per_hour": float(row[7]),
                    "driver_vm_cost_per_month": float(row[8]),
                    "total_worker_vm_cost_per_month": float(row[9]),
                    "vm_cost_per_month": float(row[10])
                },
                "total_cost": {
                    "cost_per_month": float(row[11]),
                    "breakdown": {
                        "dbu_cost": float(row[4]),
                        "vm_cost": float(row[10])
                    }
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        }
        logger.error(f"Error calculating DBSQL Classic/Pro cost: {error_detail}")
        return error_detail


# Request Model for DBSQL Serverless
class DBSQLServerlessCalculationRequest(BaseModel):
    """Request model for DBSQL Serverless warehouse cost calculation"""
    # Core parameters
    cloud: str = Field(..., description="Cloud provider: AWS, AZURE, GCP")
    region: str = Field(..., description="Region code (e.g., us-east-1)")
    tier: str = Field(..., description="Pricing tier: STANDARD, PREMIUM, ENTERPRISE")
    
    # DBSQL Warehouse configuration
    warehouse_size: str = Field(..., description="Warehouse size: X-Small, Small, Medium, Large, etc.")
    num_clusters: int = Field(1, description="Number of clusters (for auto-scaling)", ge=1, le=30)
    
    # Usage parameters (provide EITHER run-based OR direct hours)
    runs_per_day: Optional[int] = Field(None, ge=0, description="Number of query runs per day (optional if hours_per_month provided)")
    avg_runtime_minutes: Optional[int] = Field(None, ge=0, description="Average runtime per run in minutes (optional if hours_per_month provided)")
    days_per_month: Optional[int] = Field(None, ge=1, le=31, description="Number of days per month (optional if hours_per_month provided)")
    hours_per_month: Optional[float] = Field(None, ge=0, description="Direct hours per month (optional if run-based parameters provided)")


@app.post("/api/v1/calculate/dbsql-serverless", tags=["Cost Calculation"])
async def calculate_dbsql_serverless_cost(
    request: DBSQLServerlessCalculationRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Calculate cost for DBSQL Serverless warehouses (DBU costs only, no VM costs).
    
    **Warehouse Type:** SERVERLESS
    - No infrastructure management
    - Instant startup, auto-scaling
    - No VM costs - only DBU consumption
    
    **Formula:**
    ```
    Hours/Month = runs_per_day × (avg_runtime_minutes / 60) × days_per_month
              OR = hours_per_month (if provided directly)
    
    DBU/Hour = warehouse_dbu_rate × num_clusters
    Total Cost = DBU Cost × Hours/Month (no VM costs)
    ```
    
    **Example Requests:**
    
    Option 1 - Run-based calculation:
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "warehouse_size": "Medium",
      "num_clusters": 1,
      "runs_per_day": 10,
      "avg_runtime_minutes": 30,
      "days_per_month": 22
    }
    ```
    
    Option 2 - Direct hours:
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "warehouse_size": "Large",
      "num_clusters": 2,
      "hours_per_month": 730
    }
    ```
    """
    # Validate cloud
    error = await validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate region
    error = await validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate tier
    error = await validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate warehouse type (always SERVERLESS)
    error = await validate_warehouse_type("SERVERLESS", db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate warehouse size for SERVERLESS
    error = await validate_warehouse_size(request.cloud, "SERVERLESS", request.warehouse_size, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate usage parameters - must provide EITHER run-based OR direct hours
    has_run_params = all([
        request.runs_per_day is not None,
        request.avg_runtime_minutes is not None
    ])
    has_hours = request.hours_per_month is not None
    
    if not has_run_params and not has_hours:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "MISSING_USAGE_PARAMETERS",
                "message": "Must provide either (runs_per_day + avg_runtime_minutes) OR hours_per_month",
                "required": "Either ['runs_per_day', 'avg_runtime_minutes'] or ['hours_per_month']"
            }
        )
    
    if has_run_params and has_hours:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "CONFLICTING_USAGE_PARAMETERS",
                "message": "Cannot provide both run-based parameters and hours_per_month. Choose one method.",
                "conflict": "Provided both run-based parameters AND hours_per_month"
            }
        )
    
    # Set defaults for days_per_month if using run-based calculation
    if has_run_params and request.days_per_month is None:
        request.days_per_month = 30
    
    try:
        # Call the database function
        query = text("""
            SELECT 
                dbu_per_hour,
                hours_per_month,
                dbu_per_month,
                dbu_price,
                dbu_cost_per_month,
                driver_vm_cost_per_hour,
                worker_vm_cost_per_hour,
                total_vm_cost_per_hour,
                driver_vm_cost_per_month,
                total_worker_vm_cost_per_month,
                vm_cost_per_month,
                cost_per_month
            FROM lakemeter.calculate_line_item_costs(
                :p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10,
                :p11, :p12, :p13, :p14, :p15, :p16, :p17, :p18, :p19, :p20,
                :p21, :p22, :p23, :p24, :p25, :p26, :p27, :p28, :p29, :p30,
                :p31, :p32, :p33, :p34, :p35
            )
        """)
        
        result = await db.execute(query, {
            "p1": "DBSQL",                               # workload_type
            "p2": request.cloud.upper(),                 # cloud
            "p3": request.region,                        # region
            "p4": request.tier.upper(),                  # tier
            "p5": False,                                 # serverless_enabled
            "p6": False,                                 # photon_enabled
            "p7": None,                                  # dlt_edition
            "p8": None,                                  # driver_node_type
            "p9": None,                                  # worker_node_type
            "p10": 0,                                    # num_workers
            "p11": "on_demand",                          # driver_pricing_tier
            "p12": "on_demand",                          # worker_pricing_tier
            "p13": request.runs_per_day if has_run_params else 0,                 # runs_per_day
            "p14": request.avg_runtime_minutes if has_run_params else 0,          # avg_runtime_minutes
            "p15": request.days_per_month if has_run_params else 30,              # days_per_month
            "p16": request.hours_per_month if has_hours else None,                # hours_per_month
            "p17": "standard",                           # serverless_mode
            "p18": "SERVERLESS",                         # dbsql_warehouse_type
            "p19": request.warehouse_size,               # dbsql_warehouse_size
            "p20": request.num_clusters,                 # dbsql_num_clusters
            "p21": "on_demand",                          # dbsql_vm_pricing_tier (not applicable for serverless)
            "p22": None,                                 # vector_search_mode
            "p23": 0,                                    # vector_search_capacity_millions
            "p24": None,                                 # model_serving_gpu_type
            "p25": None,                                 # fmapi_model
            "p26": None,                                 # fmapi_provider
            "p27": "global",                             # fmapi_endpoint_type
            "p28": "all",                                # fmapi_context_length
            "p29": "input_token",                        # fmapi_rate_type
            "p30": 0,                                    # fmapi_quantity
            "p31": 0,                                    # lakebase_cu
            "p32": 1,                                    # lakebase_ha_nodes
            "p33": "NA",                                 # driver_payment_option
            "p34": "NA",                                 # worker_payment_option
            "p35": "NA"                                  # dbsql_vm_payment_option (not applicable)
        })
        
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")
        
        # Determine SKU type
        sku_type = get_sku_type(
            workload_type="DBSQL",
            dbsql_warehouse_type="SERVERLESS"
        )
        
        return {
            "success": True,
            "data": {
                "workload_type": "DBSQL_SERVERLESS",
                "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "warehouse_type": "SERVERLESS",
                    "warehouse_size": request.warehouse_size,
                    "num_clusters": request.num_clusters
                },
                "usage": {
                    "hours_per_month": float(row[1])
                },
                "dbu_costs": {
                    "dbu_per_hour": float(row[0]),
                    "dbu_per_month": float(row[2]),
                    "dbu_price": float(row[3]),
                    "dbu_cost_per_month": float(row[4])
                },
                "total_cost": {
                    "cost_per_month": float(row[11]),
                    "note": "Serverless warehouses have no VM costs"
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        }
        logger.error(f"Error calculating DBSQL Serverless cost: {error_detail}")
        return error_detail


# Request Model for DLT Classic
class DLTClassicCalculationRequest(BaseModel):
    """Request model for DLT Classic (Delta Live Tables) cost calculation"""
    # Core parameters
    cloud: str = Field(..., description="Cloud provider: AWS, AZURE, GCP")
    region: str = Field(..., description="Region code (e.g., us-east-1)")
    tier: str = Field(..., description="Pricing tier: STANDARD, PREMIUM, ENTERPRISE")
    
    # DLT configuration
    dlt_edition: str = Field(..., description="DLT edition: CORE, PRO, or ADVANCED")
    photon_enabled: bool = Field(False, description="Enable Photon acceleration")
    
    # Compute configuration (similar to JOBS)
    driver_node_type: str = Field(..., description="Driver node instance type (e.g., m5.xlarge)")
    worker_node_type: str = Field(..., description="Worker node instance type (e.g., m5.xlarge)")
    num_workers: int = Field(..., description="Number of worker nodes", ge=0)
    
    # Pricing options
    driver_pricing_tier: str = Field("on_demand", description="Driver pricing: on_demand, spot, reserved_1y, reserved_3y")
    worker_pricing_tier: str = Field("on_demand", description="Worker pricing: on_demand, spot, reserved_1y, reserved_3y")
    driver_payment_option: str = Field("NA", description="Driver payment: NA, no_upfront, partial_upfront, all_upfront")
    worker_payment_option: str = Field("NA", description="Worker payment: NA, no_upfront, partial_upfront, all_upfront")
    
    # Usage parameters (provide EITHER run-based OR direct hours)
    runs_per_day: Optional[int] = Field(None, ge=0, description="Number of pipeline runs per day (optional if hours_per_month provided)")
    avg_runtime_minutes: Optional[int] = Field(None, ge=0, description="Average runtime per run in minutes (optional if hours_per_month provided)")
    days_per_month: Optional[int] = Field(None, ge=1, le=31, description="Number of days per month (optional if hours_per_month provided)")
    hours_per_month: Optional[float] = Field(None, ge=0, description="Direct hours per month (optional if run-based parameters provided)")


@app.post("/api/v1/calculate/dlt-classic", tags=["Cost Calculation"])
async def calculate_dlt_classic_cost(
    request: DLTClassicCalculationRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Calculate cost for DLT Classic (Delta Live Tables) workload.
    
    **DLT Editions:**
    - **CORE**: Basic data pipelines
    - **PRO**: Enhanced reliability and maintenance
    - **ADVANCED**: Full governance and advanced features
    
    **Formula:**
    ```
    Hours/Month = runs_per_day × (avg_runtime_minutes / 60) × days_per_month
              OR = hours_per_month (if provided directly)
    DBU/Hour = (driver_dbu + worker_dbu × workers) × photon_multiplier × dlt_multiplier
    VM Cost/Hour = driver_vm_cost + worker_vm_cost × workers
    Total Cost = (DBU Cost + VM Cost) × Hours/Month
    ```
    
    **Example Requests:**
    
    Option 1 - Run-based calculation:
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "dlt_edition": "ADVANCED",
      "photon_enabled": true,
      "driver_node_type": "m5.xlarge",
      "worker_node_type": "m5.xlarge",
      "num_workers": 5,
      "driver_pricing_tier": "on_demand",
      "worker_pricing_tier": "spot",
      "driver_payment_option": "NA",
      "worker_payment_option": "NA",
      "runs_per_day": 12,
      "avg_runtime_minutes": 90,
      "days_per_month": 30
    }
    ```
    
    Option 2 - Direct hours:
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "dlt_edition": "PRO",
      "photon_enabled": false,
      "driver_node_type": "m5.xlarge",
      "worker_node_type": "m5.xlarge",
      "num_workers": 3,
      "driver_pricing_tier": "on_demand",
      "worker_pricing_tier": "reserved_1y",
      "driver_payment_option": "NA",
      "worker_payment_option": "no_upfront",
      "hours_per_month": 730
    }
    ```
    """
    # Validate usage parameters - must provide EITHER run-based OR direct hours
    has_run_params = all([
        request.runs_per_day is not None,
        request.avg_runtime_minutes is not None
    ])
    has_hours = request.hours_per_month is not None
    
    if not has_run_params and not has_hours:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "MISSING_USAGE_PARAMETERS",
                "message": "Must provide either (runs_per_day + avg_runtime_minutes) OR hours_per_month",
                "required": "Either ['runs_per_day', 'avg_runtime_minutes'] or ['hours_per_month']"
            }
        )
    
    if has_run_params and has_hours:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "CONFLICTING_USAGE_PARAMETERS",
                "message": "Cannot provide both run-based parameters and hours_per_month. Choose one method.",
                "conflict": "Provided both run-based parameters AND hours_per_month"
            }
        )
    
    # Set defaults for days_per_month if using run-based calculation
    if has_run_params and request.days_per_month is None:
        request.days_per_month = 30
    
    # Validate cloud
    error = await validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate region
    error = await validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate tier
    error = await validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate DLT edition
    if request.dlt_edition.upper() not in ["CORE", "PRO", "ADVANCED"]:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_DLT_EDITION",
                "message": f"Invalid DLT edition: {request.dlt_edition}",
                "field": "dlt_edition",
                "allowed_values": ["CORE", "PRO", "ADVANCED"]
            }
        )
    
    # Validate instance types
    error = await validate_instance_type(request.cloud, request.driver_node_type, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_instance_type(request.cloud, request.worker_node_type, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate pricing tiers (driver cannot be spot)
    error = validate_pricing_tier(request.driver_pricing_tier, is_driver=True)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = validate_pricing_tier(request.worker_pricing_tier, is_driver=False)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate payment options
    if request.driver_payment_option:
        error = validate_payment_option(request.driver_payment_option)
        if error:
            raise HTTPException(status_code=400, detail=error["error"])
    
    if request.worker_payment_option:
        error = validate_payment_option(request.worker_payment_option)
        if error:
            raise HTTPException(status_code=400, detail=error["error"])
    
    try:
        # Call the database function
        query = text("""
            SELECT 
                dbu_per_hour,
                hours_per_month,
                dbu_per_month,
                dbu_price,
                dbu_cost_per_month,
                driver_vm_cost_per_hour,
                worker_vm_cost_per_hour,
                total_vm_cost_per_hour,
                driver_vm_cost_per_month,
                total_worker_vm_cost_per_month,
                vm_cost_per_month,
                cost_per_month
            FROM lakemeter.calculate_line_item_costs(
                :p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10,
                :p11, :p12, :p13, :p14, :p15, :p16, :p17, :p18, :p19, :p20,
                :p21, :p22, :p23, :p24, :p25, :p26, :p27, :p28, :p29, :p30,
                :p31, :p32, :p33, :p34, :p35
            )
        """)
        
        result = await db.execute(query, {
            "p1": "DLT",                                 # workload_type
            "p2": request.cloud.upper(),                 # cloud
            "p3": request.region,                        # region
            "p4": request.tier.upper(),                  # tier
            "p5": False,                                 # serverless_enabled
            "p6": request.photon_enabled,                # photon_enabled
            "p7": request.dlt_edition.upper(),           # dlt_edition
            "p8": request.driver_node_type,              # driver_node_type
            "p9": request.worker_node_type,              # worker_node_type
            "p10": request.num_workers,                  # num_workers
            "p11": request.driver_pricing_tier,          # driver_pricing_tier
            "p12": request.worker_pricing_tier,          # worker_pricing_tier
            "p13": request.runs_per_day if has_run_params else 0,                 # runs_per_day
            "p14": request.avg_runtime_minutes if has_run_params else 0,          # avg_runtime_minutes
            "p15": request.days_per_month if has_run_params else 30,              # days_per_month
            "p16": request.hours_per_month if has_hours else None,                # hours_per_month
            "p17": "standard",                           # serverless_mode
            "p18": None,                                 # dbsql_warehouse_type
            "p19": None,                                 # dbsql_warehouse_size
            "p20": 1,                                    # dbsql_num_clusters
            "p21": "on_demand",                          # dbsql_vm_pricing_tier
            "p22": None,                                 # vector_search_mode
            "p23": 0,                                    # vector_search_capacity_millions
            "p24": None,                                 # model_serving_gpu_type
            "p25": None,                                 # fmapi_model
            "p26": None,                                 # fmapi_provider
            "p27": "global",                             # fmapi_endpoint_type
            "p28": "all",                                # fmapi_context_length
            "p29": "input_token",                        # fmapi_rate_type
            "p30": 0,                                    # fmapi_quantity
            "p31": 0,                                    # lakebase_cu
            "p32": 1,                                    # lakebase_ha_nodes
            "p33": request.driver_payment_option or "NA", # driver_payment_option
            "p34": request.worker_payment_option or "NA", # worker_payment_option
            "p35": "NA"                                  # dbsql_vm_payment_option
        })
        
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")
        
        # Determine SKU type
        sku_type = get_sku_type(
            workload_type="DLT",
            serverless_enabled=False,
            photon_enabled=request.photon_enabled,
            dlt_edition=request.dlt_edition
        )
        
        return {
            "success": True,
            "data": {
                "workload_type": "DLT",
                "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "dlt_edition": request.dlt_edition.upper(),
                    "driver_node_type": request.driver_node_type,
                    "worker_node_type": request.worker_node_type,
                    "num_workers": request.num_workers,
                    "photon_enabled": request.photon_enabled,
                    "driver_pricing_tier": request.driver_pricing_tier,
                    "worker_pricing_tier": request.worker_pricing_tier,
                    "driver_payment_option": request.driver_payment_option,
                    "worker_payment_option": request.worker_payment_option
                },
                "usage": {
                    "hours_per_month": float(row[1])
                },
                "dbu_calculation": {
                    "dbu_per_hour": float(row[0]),
                    "dbu_per_month": float(row[2]),
                    "dbu_price": float(row[3]),
                    "dbu_cost_per_month": float(row[4])
                },
                "vm_costs": {
                    "driver_vm_cost_per_hour": float(row[5]),
                    "worker_vm_cost_per_hour": float(row[6]),
                    "total_vm_cost_per_hour": float(row[7]),
                    "driver_vm_cost_per_month": float(row[8]),
                    "total_worker_vm_cost_per_month": float(row[9]),
                    "vm_cost_per_month": float(row[10])
                },
                "total_cost": {
                    "cost_per_month": float(row[11]),
                    "breakdown": {
                        "dbu_cost": float(row[4]),
                        "vm_cost": float(row[10])
                    }
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        }
        logger.error(f"Error calculating DLT Classic cost: {error_detail}")
        return error_detail


# Request Model for DLT Serverless
class DLTServerlessCalculationRequest(BaseModel):
    """Request model for DLT Serverless (Delta Live Tables) cost calculation"""
    # Core parameters
    cloud: str = Field(..., description="Cloud provider: AWS, AZURE, GCP")
    region: str = Field(..., description="Region code (e.g., us-east-1)")
    tier: str = Field(..., description="Pricing tier: STANDARD, PREMIUM, ENTERPRISE")
    
    # Note: Photon is ALWAYS enabled for serverless workloads (no parameter needed)
    # Note: DLT Serverless does NOT have editions - editions are only for Classic
    
    # Node types (needed for DBU rate calculation even though no VM costs)
    driver_node_type: str = Field(..., description="Driver instance type (e.g., m5.xlarge)")
    worker_node_type: str = Field(..., description="Worker instance type (e.g., m5.xlarge)")
    num_workers: int = Field(..., ge=0, description="Number of worker nodes")
    
    # Serverless configuration
    serverless_mode: str = Field("standard", description="Serverless mode: standard or performance")
    
    # Usage parameters (provide EITHER run-based OR direct hours)
    runs_per_day: Optional[int] = Field(None, ge=0, description="Number of pipeline runs per day (optional if hours_per_month provided)")
    avg_runtime_minutes: Optional[int] = Field(None, ge=0, description="Average runtime per run in minutes (optional if hours_per_month provided)")
    days_per_month: Optional[int] = Field(None, ge=1, le=31, description="Number of days per month (optional if hours_per_month provided)")
    hours_per_month: Optional[float] = Field(None, ge=0, description="Direct hours per month (optional if run-based parameters provided)")


@app.post("/api/v1/calculate/dlt-serverless", tags=["Cost Calculation"])
async def calculate_dlt_serverless_cost(
    request: DLTServerlessCalculationRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Calculate cost for DLT Serverless (Delta Live Tables) workload.
    
    **DLT Serverless:**
    - No infrastructure management
    - Pay only for DBU usage (no VM costs)
    - Automatic scaling
    - Photon is ALWAYS enabled (included in serverless)
    - Two modes: standard (1x) and performance (2x multiplier)
    - No DLT editions for serverless (editions only apply to Classic DLT)
    
    **Formula:**
    ```
    Hours/Month = runs_per_day × (avg_runtime_minutes / 60) × days_per_month
              OR = hours_per_month (if provided directly)
    DBU/Hour = base_dbu_rate × photon_multiplier (always on) × dlt_multiplier × serverless_multiplier
    DBU/Month = DBU/Hour × Hours/Month
    Total Cost = DBU/Month × dbu_price (no VM costs for serverless)
    ```
    
    **Example Requests:**
    
    Option 1 - Run-based calculation:
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "driver_node_type": "m5.xlarge",
      "worker_node_type": "m5.xlarge",
      "num_workers": 5,
      "serverless_mode": "performance",
      "runs_per_day": 10,
      "avg_runtime_minutes": 45,
      "days_per_month": 30
    }
    ```
    
    Option 2 - Direct hours:
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "driver_node_type": "m5.xlarge",
      "worker_node_type": "m5.xlarge",
      "num_workers": 3,
      "serverless_mode": "standard",
      "hours_per_month": 730
    }
    ```
    """
    # Validate usage parameters - must provide EITHER run-based OR direct hours
    has_run_params = all([
        request.runs_per_day is not None,
        request.avg_runtime_minutes is not None
    ])
    has_hours = request.hours_per_month is not None
    
    if not has_run_params and not has_hours:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "MISSING_USAGE_PARAMETERS",
                "message": "Must provide either (runs_per_day + avg_runtime_minutes) OR hours_per_month",
                "required": "Either ['runs_per_day', 'avg_runtime_minutes'] or ['hours_per_month']"
            }
        )
    
    if has_run_params and has_hours:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "CONFLICTING_USAGE_PARAMETERS",
                "message": "Cannot provide both run-based parameters and hours_per_month. Choose one method.",
                "conflict": "Provided both run-based parameters AND hours_per_month"
            }
        )
    
    # Set defaults for days_per_month if using run-based calculation
    if has_run_params and request.days_per_month is None:
        request.days_per_month = 30
    
    # Validate cloud
    error = await validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate region
    error = await validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate tier
    error = await validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Note: DLT Serverless does NOT have editions - only Classic DLT has editions
    
    # Validate instance types (needed for DBU calculation)
    error = await validate_instance_type(request.cloud, request.driver_node_type, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_instance_type(request.cloud, request.worker_node_type, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate serverless mode
    if request.serverless_mode.lower() not in ["standard", "performance"]:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_SERVERLESS_MODE",
                "message": f"Invalid serverless mode: {request.serverless_mode}",
                "field": "serverless_mode",
                "allowed_values": ["standard", "performance"]
            }
        )
    
    try:
        # Call the database function
        query = text("""
            SELECT 
                dbu_per_hour,
                hours_per_month,
                dbu_per_month,
                dbu_price,
                dbu_cost_per_month,
                driver_vm_cost_per_hour,
                worker_vm_cost_per_hour,
                total_vm_cost_per_hour,
                driver_vm_cost_per_month,
                total_worker_vm_cost_per_month,
                vm_cost_per_month,
                cost_per_month
            FROM lakemeter.calculate_line_item_costs(
                :p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10,
                :p11, :p12, :p13, :p14, :p15, :p16, :p17, :p18, :p19, :p20,
                :p21, :p22, :p23, :p24, :p25, :p26, :p27, :p28, :p29, :p30,
                :p31, :p32, :p33, :p34, :p35
            )
        """)
        
        result = await db.execute(query, {
            "p1": "DLT",                                 # workload_type
            "p2": request.cloud.upper(),                 # cloud
            "p3": request.region,                        # region
            "p4": request.tier.upper(),                  # tier
            "p5": True,                                  # serverless_enabled = TRUE
            "p6": True,                                  # photon_enabled (ALWAYS TRUE for serverless)
            "p7": None,                                  # dlt_edition (not applicable for serverless)
            "p8": request.driver_node_type,              # driver_node_type (needed for DBU calculation)
            "p9": request.worker_node_type,              # worker_node_type (needed for DBU calculation)
            "p10": request.num_workers,                  # num_workers
            "p11": "on_demand",                          # driver_pricing_tier (not used)
            "p12": "on_demand",                          # worker_pricing_tier (not used)
            "p13": request.runs_per_day if has_run_params else 0,                 # runs_per_day
            "p14": request.avg_runtime_minutes if has_run_params else 0,          # avg_runtime_minutes
            "p15": request.days_per_month if has_run_params else 30,              # days_per_month
            "p16": request.hours_per_month if has_hours else None,                # hours_per_month
            "p17": request.serverless_mode.lower(),      # serverless_mode
            "p18": None,                                 # dbsql_warehouse_type
            "p19": None,                                 # dbsql_warehouse_size
            "p20": 1,                                    # dbsql_num_clusters
            "p21": "on_demand",                          # dbsql_vm_pricing_tier
            "p22": None,                                 # vector_search_mode
            "p23": 0,                                    # vector_search_capacity_millions
            "p24": None,                                 # model_serving_gpu_type
            "p25": None,                                 # fmapi_model
            "p26": None,                                 # fmapi_provider
            "p27": "global",                             # fmapi_endpoint_type
            "p28": "all",                                # fmapi_context_length
            "p29": "input_token",                        # fmapi_rate_type
            "p30": 0,                                    # fmapi_quantity
            "p31": 0,                                    # lakebase_cu
            "p32": 1,                                    # lakebase_ha_nodes
            "p33": "NA",                                 # driver_payment_option
            "p34": "NA",                                 # worker_payment_option
            "p35": "NA"                                  # dbsql_vm_payment_option
        })
        
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")
        
        # Determine SKU type
        sku_type = get_sku_type(
            workload_type="DLT",
            serverless_enabled=True
        )
        
        return {
            "success": True,
            "data": {
                "workload_type": "DLT_SERVERLESS",
                "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "driver_node_type": request.driver_node_type,
                    "worker_node_type": request.worker_node_type,
                    "num_workers": request.num_workers,
                    "photon_enabled": True,
                    "serverless_mode": request.serverless_mode.lower(),
                    "note": "Photon is always enabled for serverless workloads. DLT editions only apply to Classic DLT."
                },
                "usage": {
                    "runs_per_day": request.runs_per_day if has_run_params else None,
                    "avg_runtime_minutes": request.avg_runtime_minutes if has_run_params else None,
                    "days_per_month": request.days_per_month if has_run_params else None,
                    "hours_per_month": float(row[1])
                },
                "dbu_calculation": {
                    "dbu_per_hour": float(row[0]),
                    "dbu_per_month": float(row[2]),
                    "dbu_price": float(row[3]),
                    "dbu_cost_per_month": float(row[4])
                },
                "total_cost": {
                    "cost_per_month": float(row[11]),
                    "note": "Serverless has no VM costs - only DBU costs"
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        }
        logger.error(f"Error calculating DLT Serverless cost: {error_detail}")
        return error_detail


# Request Model for Vector Search
class VectorSearchCalculationRequest(BaseModel):
    """Request model for Vector Search cost calculation"""
    cloud: str = Field(..., description="Cloud provider: AWS, AZURE, GCP")
    region: str = Field(..., description="Region code (e.g., us-east-1)")
    tier: str = Field(..., description="Pricing tier: STANDARD, PREMIUM, ENTERPRISE")
    mode: str = Field(..., description="Vector Search mode: standard or storage_optimized")
    vector_capacity_millions: float = Field(..., description="Vector capacity in millions", ge=0)
    hours_per_month: float = Field(730, description="Hours per month (default: 730 = 24/7)", ge=0)
    storage_gb: float = Field(0, description="Total storage in GB (first 20 GB per unit is free)", ge=0)


@app.post("/api/v1/calculate/vector-search", tags=["Cost Calculation"])
async def calculate_vector_search_cost(
    request: VectorSearchCalculationRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Calculate cost for Vector Search workload.
    
    **Vector Search Modes:**
    - **standard**: Standard Vector Search mode (2M vectors per unit)
    - **storage_optimized**: Storage-optimized mode for cost efficiency (64M vectors per unit)
    
    **Formula:**
    ```
    Units Used = CEILING(vector_capacity_millions / divisor)
      where divisor = 2 for standard, 64 for storage_optimized
    
    DBU/Hour = units_used × mode_dbu_rate
    DBU Cost = DBU/Hour × hours_per_month × dbu_price
    
    Storage:
    Free Storage = units_used × 20 GB
    Billable Storage = MAX(0, storage_gb - free_storage_gb)
    Storage Cost = billable_storage_gb × price_per_gb_per_month
    
    Total Cost = DBU Cost + Storage Cost
    ```
    
    **Examples:**
    - 10M vectors in standard mode → CEILING(10/2) = 5 units → 100 GB free storage
    - 3M vectors in standard mode → CEILING(3/2) = 2 units → 40 GB free storage
    - 100M vectors in storage_optimized → CEILING(100/64) = 2 units → 40 GB free storage
    
    **Example Request:**
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "mode": "standard",
      "vector_capacity_millions": 10,
      "hours_per_month": 730,
      "storage_gb": 200
    }
    ```
    
    **Example Response:**
    ```json
    {
      "usage": {
        "hours_per_month": 730,
        "units_used": 5
      },
      "dbu_calculation": {
        "dbu_per_hour": ...,
        "dbu_per_month": ...,
        "dbu_price": ...,
        "dbu_cost_per_month": ...
      },
      "storage_calculation": {
        "total_storage_gb": 200,
        "free_storage_gb": 100,
        "billable_storage_gb": 100,
        "price_per_gb_per_month": 0.023,
        "storage_cost_per_month": 2.30
      },
      "total_cost": {
        "cost_per_month": ...,
        "breakdown": {
          "dbu_cost": ...,
          "storage_cost": 2.30
        }
      }
    }
    ```
    """
    error = await validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_vector_search_mode(request.mode, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Calculate units used based on mode
    if request.mode.lower() == 'standard':
        units_used = math.ceil(request.vector_capacity_millions / 2)
    elif request.mode.lower() == 'storage_optimized':
        units_used = math.ceil(request.vector_capacity_millions / 64)
    else:
        units_used = 0  # Fallback for unknown modes
    
    # Calculate storage costs
    # Free storage: 20 GB per unit
    FREE_STORAGE_PER_UNIT = 20
    free_storage_gb = units_used * FREE_STORAGE_PER_UNIT
    billable_storage_gb = max(0, request.storage_gb - free_storage_gb)
    
    # Get storage price from database (always query, even if no billable storage)
    storage_cost_per_month = 0.0
    price_per_gb_per_month = 0.0
    
    try:
        # Get storage price (region column uses region_code, not sku_region)
        storage_price_query = text("""
            SELECT price_per_dbu as price_per_gb_per_month 
            FROM lakemeter.sync_pricing_dbu_rates
            WHERE product_type = 'DATABRICKS_STORAGE' 
              AND usage_unit = 'DSU'
              AND cloud = :cloud 
              AND region = :region
              AND tier = :tier
            LIMIT 1
        """)
        storage_result = await db.execute(storage_price_query, {
            "cloud": request.cloud.upper(),
            "region": request.region,
            "tier": request.tier.upper()
        })
        storage_row = storage_result.fetchone()
        if storage_row:
            price_per_gb_per_month = float(storage_row[0])
            storage_cost_per_month = billable_storage_gb * price_per_gb_per_month
        else:
            logger.warning(f"No storage price found for {request.cloud.upper()}/{request.region}/{request.tier.upper()}")
    except Exception as e:
        logger.warning(f"Could not fetch storage price: {e}")
    
    try:
        query = text("""
            SELECT 
                dbu_per_hour, hours_per_month, dbu_per_month, dbu_price, dbu_cost_per_month,
                driver_vm_cost_per_hour, worker_vm_cost_per_hour, total_vm_cost_per_hour,
                driver_vm_cost_per_month, total_worker_vm_cost_per_month, vm_cost_per_month, cost_per_month
            FROM lakemeter.calculate_line_item_costs(
                :p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10,
                :p11, :p12, :p13, :p14, :p15, :p16, :p17, :p18, :p19, :p20,
                :p21, :p22, :p23, :p24, :p25, :p26, :p27, :p28, :p29, :p30,
                :p31, :p32, :p33, :p34, :p35
            )
        """)
        
        result = await db.execute(query, {
            "p1": "VECTOR_SEARCH", "p2": request.cloud.upper(), "p3": request.region, "p4": request.tier.upper(),
            "p5": False, "p6": False, "p7": None, "p8": None, "p9": None, "p10": 0,
            "p11": "on_demand", "p12": "on_demand", "p13": 0, "p14": 0, "p15": 30,
            "p16": request.hours_per_month, "p17": "standard", "p18": None, "p19": None, "p20": 1,
            "p21": "on_demand", "p22": request.mode, "p23": request.vector_capacity_millions,
            "p24": None, "p25": None, "p26": None, "p27": "global", "p28": "all",
            "p29": "input_token", "p30": 0, "p31": 0, "p32": 1, "p33": "NA", "p34": "NA", "p35": "NA"
        })
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")
        
        # Determine SKU type
        sku_type = get_sku_type(workload_type="VECTOR_SEARCH")
        
        # Calculate total cost including storage
        dbu_cost_per_month = float(row[4])
        total_cost_per_month = dbu_cost_per_month + storage_cost_per_month
        
        return {
            "success": True,
            "data": {
                "workload_type": "VECTOR_SEARCH",
                "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "mode": request.mode,
                    "vector_capacity_millions": request.vector_capacity_millions,
                    "storage_gb": request.storage_gb
                },
                "usage": {
                    "hours_per_month": float(row[1]),
                    "units_used": units_used
                },
                "dbu_calculation": {
                    "dbu_per_hour": float(row[0]),
                    "dbu_per_month": float(row[2]),
                    "dbu_price": float(row[3]),
                    "dbu_cost_per_month": dbu_cost_per_month
                },
                "storage_calculation": {
                    "total_storage_gb": request.storage_gb,
                    "free_storage_per_unit_gb": FREE_STORAGE_PER_UNIT,
                    "free_storage_gb": free_storage_gb,
                    "billable_storage_gb": billable_storage_gb,
                    "price_per_gb_per_month": price_per_gb_per_month,
                    "storage_cost_per_month": storage_cost_per_month
                },
                "total_cost": {
                    "cost_per_month": total_cost_per_month,
                    "breakdown": {
                        "dbu_cost": dbu_cost_per_month,
                        "storage_cost": storage_cost_per_month
                    },
                    "note": "Vector Search is serverless - no VM costs"
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        }


# Request Model for Model Serving
class ModelServingCalculationRequest(BaseModel):
    """Request model for Model Serving cost calculation"""
    cloud: str = Field(..., description="Cloud provider: AWS, AZURE, GCP")
    region: str = Field(..., description="Region code (e.g., us-east-1)")
    tier: str = Field(..., description="Pricing tier: STANDARD, PREMIUM, ENTERPRISE")
    gpu_type: str = Field(..., description="GPU type (e.g., gpu_small_t4, gpu_xlarge_a100_80gb_8x)")
    hours_per_month: float = Field(730, description="Hours per month (default: 730 = 24/7)", ge=0)


@app.post("/api/v1/calculate/model-serving", tags=["Cost Calculation"])
async def calculate_model_serving_cost(
    request: ModelServingCalculationRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Calculate cost for Model Serving workload.
    
    **GPU Types:** cpu, gpu_small_t4, gpu_medium_a10g_1x, gpu_xlarge_a100_80gb_8x, etc.
    
    **Formula:**
    ```
    DBU/Hour = gpu_type_dbu_rate
    Total Cost = DBU/Hour × hours_per_month × dbu_price
    ```
    
    **Example Request:**
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "gpu_type": "gpu_small_t4",
      "hours_per_month": 730
    }
    ```
    """
    error = await validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate GPU type exists for this cloud
    query_check = text("""
        SELECT COUNT(*) FROM lakemeter.sync_product_serverless_rates
        WHERE product = 'model_serving' AND cloud = :cloud AND size_or_model = :gpu_type
    """)
    result_check = await db.execute(query_check, {"cloud": request.cloud.upper(), "gpu_type": request.gpu_type})
    count = result_check.scalar()
    
    if count == 0:
        # Fetch available GPU types for this cloud
        query_available = text("""
            SELECT size_or_model as gpu_type, dbu_rate
            FROM lakemeter.sync_product_serverless_rates
            WHERE product = 'model_serving' AND cloud = :cloud
            ORDER BY size_or_model
        """)
        result_available = await db.execute(query_available, {"cloud": request.cloud.upper()})
        available_gpus = result_available.fetchall()
        
        gpu_list = [f"{row.gpu_type} ({row.dbu_rate} DBU/hour)" for row in available_gpus]
        
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_GPU_TYPE",
                "message": f"GPU type '{request.gpu_type}' not available for {request.cloud.upper()}. Available GPU types: {', '.join(gpu_list)}",
                "field": "gpu_type",
                "allowed_values": [row.gpu_type for row in available_gpus]
            }
        )
    
    try:
        query = text("""
            SELECT 
                dbu_per_hour, hours_per_month, dbu_per_month, dbu_price, dbu_cost_per_month,
                driver_vm_cost_per_hour, worker_vm_cost_per_hour, total_vm_cost_per_hour,
                driver_vm_cost_per_month, total_worker_vm_cost_per_month, vm_cost_per_month, cost_per_month
            FROM lakemeter.calculate_line_item_costs(
                :p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10,
                :p11, :p12, :p13, :p14, :p15, :p16, :p17, :p18, :p19, :p20,
                :p21, :p22, :p23, :p24, :p25, :p26, :p27, :p28, :p29, :p30,
                :p31, :p32, :p33, :p34, :p35
            )
        """)
        
        result = await db.execute(query, {
            "p1": "MODEL_SERVING", "p2": request.cloud.upper(), "p3": request.region, "p4": request.tier.upper(),
            "p5": False, "p6": False, "p7": None, "p8": None, "p9": None, "p10": 0,
            "p11": "on_demand", "p12": "on_demand", "p13": 0, "p14": 0, "p15": 30,
            "p16": request.hours_per_month, "p17": "standard", "p18": None, "p19": None, "p20": 1,
            "p21": "on_demand", "p22": None, "p23": 0, "p24": request.gpu_type,
            "p25": None, "p26": None, "p27": "global", "p28": "all",
            "p29": "input_token", "p30": 0, "p31": 0, "p32": 1, "p33": "NA", "p34": "NA", "p35": "NA"
        })
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")
        
        # Determine SKU type
        sku_type = get_sku_type(workload_type="MODEL_SERVING")
        
        return {
            "success": True,
            "data": {
                "workload_type": "MODEL_SERVING",
                "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "gpu_type": request.gpu_type
                },
                "usage": {"hours_per_month": float(row[1])},
                "dbu_calculation": {
                    "dbu_per_hour": float(row[0]),
                    "dbu_per_month": float(row[2]),
                    "dbu_price": float(row[3]),
                    "dbu_cost_per_month": float(row[4])
                },
                "total_cost": {
                    "cost_per_month": float(row[11]),
                    "note": "Model Serving is serverless - no VM costs"
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        }


# Request Model for FMAPI
class FMAPICalculationRequest(BaseModel):
    """Request model for FMAPI (Foundation Model API) cost calculation"""
    cloud: str = Field(..., description="Cloud provider: AWS, AZURE, GCP")
    region: str = Field(..., description="Region code (e.g., us-east-1)")
    tier: str = Field(..., description="Pricing tier: STANDARD, PREMIUM, ENTERPRISE")
    
    # FMAPI configuration
    provider: str = Field(..., description="Provider: databricks, openai, anthropic, google")
    model: str = Field(..., description="Model name (e.g., claude-sonnet-4-5, gpt-4o)")
    endpoint_type: str = Field("global", description="Endpoint type: global or regional")
    context_length: str = Field("all", description="Context length category")
    rate_type: str = Field(..., description="Rate type: input_token, output_token, provisioned_scaling, etc.")
    quantity: int = Field(..., description="Quantity (tokens or hours depending on rate_type)", ge=0)


@app.post("/api/v1/calculate/fmapi", tags=["Cost Calculation"])
async def calculate_fmapi_cost(
    request: FMAPICalculationRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Calculate cost for FMAPI (Foundation Model API) usage.
    
    **Providers:**
    - **databricks**: Databricks-hosted models (llama-3-3-70b, gpt-oss-120b, gemma-3-12b, etc.)
    - **openai**: OpenAI models (gpt-4o, gpt-4o-mini, gpt-4-turbo, etc.)
    - **anthropic**: Anthropic models (claude-sonnet-4-5, claude-opus-4, claude-haiku-4, etc.)
    - **google**: Google models (gemini-2-0-flash, gemini-1-5-pro, gemini-1-5-flash, etc.)
    
    **Rate Types:**
    - **Token-based**: input_token, output_token (quantity = number of tokens)
    - **Provisioned**: provisioned_scaling, provisioned_entry (quantity = hours)
    
    **Formula:**
    ```
    For token-based: Cost = (quantity / 1,000,000) × dbu_per_1M_tokens × dbu_price
    For provisioned: Cost = quantity × dbu_per_hour × dbu_price
    ```
    
    **Example Requests:**
    
    Option 1 - Token-based pricing (per million tokens):
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "provider": "anthropic",
      "model": "claude-sonnet-4-5",
      "endpoint_type": "global",
      "context_length": "all",
      "rate_type": "input_token",
      "quantity": 1000000
    }
    ```
    
    Option 2 - Provisioned pricing (per hour):
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "provider": "openai",
      "model": "gpt-4o",
      "endpoint_type": "global",
      "context_length": "all",
      "rate_type": "provisioned_scaling",
      "quantity": 730
    }
    ```
    """
    error = await validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate FMAPI model (will validate provider, model, rate_type)
    if request.provider.lower() == "databricks":
        error = await validate_fmapi_databricks_model(request.model, db)
        if error:
            raise HTTPException(status_code=400, detail=error["error"])
        error = await validate_fmapi_databricks_rate_type(request.model, request.rate_type, db)
        if error:
            raise HTTPException(status_code=400, detail=error["error"])
    else:
        error = await validate_fmapi_proprietary_provider(request.provider, db)
        if error:
            raise HTTPException(status_code=400, detail=error["error"])
        error = await validate_fmapi_proprietary_model(request.model, request.provider, db)
        if error:
            raise HTTPException(status_code=400, detail=error["error"])
    
    try:
        query = text("""
            SELECT 
                dbu_per_hour, hours_per_month, dbu_per_month, dbu_price, dbu_cost_per_month,
                driver_vm_cost_per_hour, worker_vm_cost_per_hour, total_vm_cost_per_hour,
                driver_vm_cost_per_month, total_worker_vm_cost_per_month, vm_cost_per_month, cost_per_month
            FROM lakemeter.calculate_line_item_costs(
                :p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10,
                :p11, :p12, :p13, :p14, :p15, :p16, :p17, :p18, :p19, :p20,
                :p21, :p22, :p23, :p24, :p25, :p26, :p27, :p28, :p29, :p30,
                :p31, :p32, :p33, :p34, :p35
            )
        """)
        
        result = await db.execute(query, {
            "p1": "FMAPI", "p2": request.cloud.upper(), "p3": request.region, "p4": request.tier.upper(),
            "p5": False, "p6": False, "p7": None, "p8": None, "p9": None, "p10": 0,
            "p11": "on_demand", "p12": "on_demand", "p13": 0, "p14": 0, "p15": 30,
            "p16": None, "p17": "standard", "p18": None, "p19": None, "p20": 1,
            "p21": "on_demand", "p22": None, "p23": 0, "p24": None,
            "p25": request.model, "p26": request.provider,
            "p27": request.endpoint_type, "p28": request.context_length,
            "p29": request.rate_type, "p30": request.quantity,
            "p31": 0, "p32": 1, "p33": "NA", "p34": "NA", "p35": "NA"
        })
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")
        
        return {
            "success": True,
            "data": {
                "workload_type": "FMAPI",
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "provider": request.provider,
                    "model": request.model,
                    "endpoint_type": request.endpoint_type,
                    "context_length": request.context_length,
                    "rate_type": request.rate_type,
                    "quantity": request.quantity
                },
                "cost": {
                    "total_cost": float(row[11]),
                    "note": "Cost based on token or provisioned usage"
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        }


# ==========================================================================================
# FMAPI - SPLIT ENDPOINTS (Databricks vs Proprietary)
# ==========================================================================================

# Request Model for FMAPI Databricks
class FMAPIDatabricksCalculationRequest(BaseModel):
    """Request model for FMAPI Databricks-hosted models cost calculation"""
    cloud: str = Field(..., description="Cloud provider: AWS, AZURE, GCP")
    region: str = Field(..., description="Region code (e.g., us-east-1)")
    tier: str = Field(..., description="Pricing tier: STANDARD, PREMIUM, ENTERPRISE")
    model: str = Field(..., description="Databricks model name (e.g., llama-3-3-70b, gpt-oss-120b, gemma-3-12b)")
    rate_type: str = Field(..., description="Rate type: input_token, output_token, provisioned_scaling, provisioned_entry")
    quantity: int = Field(..., description="Quantity (tokens or hours depending on rate_type)", ge=0)


@app.post("/api/v1/calculate/fmapi-databricks", tags=["Cost Calculation"])
async def calculate_fmapi_databricks_cost(
    request: FMAPIDatabricksCalculationRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Calculate cost for Databricks-hosted FMAPI models.
    
    **Available Models:**
    - llama-3-3-70b
    - llama-4-maverick
    - gpt-oss-120b, gpt-oss-20b
    - gemma-3-12b
    - bge-large, gte
    - And more...
    
    **Rate Types:**
    - **Token-based**: input_token, output_token (quantity = number of tokens)
    - **Provisioned**: provisioned_scaling, provisioned_entry (quantity = hours)
    
    **Formula:**
    ```
    For token-based: Cost = (quantity / 1,000,000) × dbu_per_1M_tokens × dbu_price
    For provisioned: Cost = quantity × dbu_per_hour × dbu_price
    ```
    
    **Example Requests:**
    
    Option 1 - Token-based:
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "model": "llama-3-3-70b",
      "rate_type": "input_token",
      "quantity": 1000000
    }
    ```
    
    Option 2 - Provisioned:
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "model": "gpt-oss-120b",
      "rate_type": "provisioned_scaling",
      "quantity": 730
    }
    ```
    """
    error = await validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate Databricks model
    error = await validate_fmapi_databricks_model(request.model, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate rate type for this model
    error = await validate_fmapi_databricks_rate_type(request.model, request.rate_type, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    try:
        query = text("""
            SELECT 
                dbu_per_hour, hours_per_month, dbu_per_month, dbu_price, dbu_cost_per_month,
                driver_vm_cost_per_hour, worker_vm_cost_per_hour, total_vm_cost_per_hour,
                driver_vm_cost_per_month, total_worker_vm_cost_per_month, vm_cost_per_month, cost_per_month
            FROM lakemeter.calculate_line_item_costs(
                :p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10,
                :p11, :p12, :p13, :p14, :p15, :p16, :p17, :p18, :p19, :p20,
                :p21, :p22, :p23, :p24, :p25, :p26, :p27, :p28, :p29, :p30,
                :p31, :p32, :p33, :p34, :p35
            )
        """)
        
        result = await db.execute(query, {
            "p1": "FMAPI_DATABRICKS", "p2": request.cloud.upper(), "p3": request.region, "p4": request.tier.upper(),
            "p5": False, "p6": False, "p7": None, "p8": None, "p9": None, "p10": 0,
            "p11": "on_demand", "p12": "on_demand", "p13": 1, "p14": 60, "p15": 30,
            "p16": None, "p17": "standard", "p18": None, "p19": None, "p20": 1,
            "p21": "on_demand", "p22": None, "p23": 0, "p24": None,
            "p25": request.model, "p26": None,
            "p27": "global", "p28": "all",
            "p29": request.rate_type, "p30": request.quantity,
            "p31": 0, "p32": 1, "p33": "NA", "p34": "NA", "p35": "NA"
        })
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")
        
        # Determine SKU type
        sku_type = get_sku_type(workload_type="FMAPI_DATABRICKS")
        
        return {
            "success": True,
            "data": {
                "workload_type": "FMAPI_DATABRICKS",
                "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "provider": "databricks",
                    "model": request.model,
                    "rate_type": request.rate_type,
                    "quantity": request.quantity
                },
                "cost": {
                    "total_cost": float(row[11]),
                    "note": "Cost based on token or provisioned usage"
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        }


# Request Model for FMAPI Proprietary
class FMAPIProprietaryCalculationRequest(BaseModel):
    """Request model for FMAPI proprietary models cost calculation"""
    cloud: str = Field(..., description="Cloud provider: AWS, AZURE, GCP")
    region: str = Field(..., description="Region code (e.g., us-east-1)")
    tier: str = Field(..., description="Pricing tier: STANDARD, PREMIUM, ENTERPRISE")
    provider: str = Field(..., description="Provider: openai, anthropic, google")
    model: str = Field(..., description="Model name (e.g., claude-sonnet-4-5, gpt-4o, gemini-2-0-flash)")
    endpoint_type: str = Field("global", description="Endpoint type: global or regional")
    context_length: str = Field("all", description="Context length category")
    rate_type: str = Field(..., description="Rate type: input_token, output_token, provisioned_scaling, etc.")
    quantity: int = Field(..., description="Quantity (tokens or hours depending on rate_type)", ge=0)


@app.post("/api/v1/calculate/fmapi-proprietary", tags=["Cost Calculation"])
async def calculate_fmapi_proprietary_cost(
    request: FMAPIProprietaryCalculationRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Calculate cost for proprietary FMAPI models (OpenAI, Anthropic, Google).
    
    **Providers:**
    - **openai**: gpt-4o, gpt-4o-mini, gpt-4-turbo, etc.
    - **anthropic**: claude-sonnet-4-5, claude-opus-4, claude-haiku-4, etc.
    - **google**: gemini-2-0-flash, gemini-1-5-pro, gemini-1-5-flash, etc.
    
    **Rate Types:**
    - **Token-based**: input_token, output_token (quantity = number of tokens)
    - **Provisioned**: provisioned_scaling (quantity = hours)
    
    **Formula:**
    ```
    For token-based: Cost = (quantity / 1,000,000) × dbu_per_1M_tokens × dbu_price
    For provisioned: Cost = quantity × dbu_per_hour × dbu_price
    ```
    
    **Example Requests:**
    
    Option 1 - Token-based (Anthropic):
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "provider": "anthropic",
      "model": "claude-sonnet-4-5",
      "endpoint_type": "global",
      "context_length": "all",
      "rate_type": "input_token",
      "quantity": 1000000
    }
    ```
    
    Option 2 - Provisioned (OpenAI):
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "provider": "openai",
      "model": "gpt-4o",
      "endpoint_type": "global",
      "context_length": "all",
      "rate_type": "provisioned_scaling",
      "quantity": 730
    }
    ```
    """
    error = await validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Validate proprietary provider and model
    error = await validate_fmapi_proprietary_provider(request.provider, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_fmapi_proprietary_model(request.model, request.provider, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    try:
        query = text("""
            SELECT 
                dbu_per_hour, hours_per_month, dbu_per_month, dbu_price, dbu_cost_per_month,
                driver_vm_cost_per_hour, worker_vm_cost_per_hour, total_vm_cost_per_hour,
                driver_vm_cost_per_month, total_worker_vm_cost_per_month, vm_cost_per_month, cost_per_month
            FROM lakemeter.calculate_line_item_costs(
                :p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10,
                :p11, :p12, :p13, :p14, :p15, :p16, :p17, :p18, :p19, :p20,
                :p21, :p22, :p23, :p24, :p25, :p26, :p27, :p28, :p29, :p30,
                :p31, :p32, :p33, :p34, :p35
            )
        """)
        
        result = await db.execute(query, {
            "p1": "FMAPI_PROPRIETARY", "p2": request.cloud.upper(), "p3": request.region, "p4": request.tier.upper(),
            "p5": False, "p6": False, "p7": None, "p8": None, "p9": None, "p10": 0,
            "p11": "on_demand", "p12": "on_demand", "p13": 1, "p14": 60, "p15": 30,
            "p16": None, "p17": "standard", "p18": None, "p19": None, "p20": 1,
            "p21": "on_demand", "p22": None, "p23": 0, "p24": None,
            "p25": request.model, "p26": request.provider,
            "p27": request.endpoint_type, "p28": request.context_length,
            "p29": request.rate_type, "p30": request.quantity,
            "p31": 0, "p32": 1, "p33": "NA", "p34": "NA", "p35": "NA"
        })
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")
        
        # Determine SKU type
        sku_type = get_sku_type(
            workload_type="FMAPI_PROPRIETARY",
            fmapi_provider=request.provider
        )
        
        return {
            "success": True,
            "data": {
                "workload_type": "FMAPI_PROPRIETARY",
                "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "provider": request.provider,
                    "model": request.model,
                    "endpoint_type": request.endpoint_type,
                    "context_length": request.context_length,
                    "rate_type": request.rate_type,
                    "quantity": request.quantity
                },
                "cost": {
                    "total_cost": float(row[11]),
                    "note": "Cost based on token or provisioned usage"
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        }


# Request Model for Lakebase
class LakebaseCalculationRequest(BaseModel):
    """Request model for Lakebase cost calculation"""
    cloud: str = Field(..., description="Cloud provider: AWS, AZURE, GCP")
    region: str = Field(..., description="Region code (e.g., us-east-1)")
    tier: str = Field(..., description="Pricing tier: STANDARD, PREMIUM, ENTERPRISE")
    cu_size: int = Field(..., description="Compute unit size: 1, 2, 4, or 8", ge=1, le=8)
    num_nodes: int = Field(..., description="Number of nodes: 1-3 for HA", ge=1, le=3)
    hours_per_month: float = Field(730, description="Hours per month (default: 730 = 24/7)", ge=0)
    storage_gb: float = Field(0, description="Storage in GB (max 8192 GB = 8 TB, no free tier)", ge=0, le=8192)


@app.post("/api/v1/calculate/lakebase", tags=["Cost Calculation"])
async def calculate_lakebase_cost(
    request: LakebaseCalculationRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Calculate cost for Lakebase (managed PostgreSQL) workload.
    
    **CU Sizes:** 1, 2, 4, 8  
    **Nodes:** 1-3 (for high availability)
    **Storage:** 0 - 8192 GB (8 TB max), no free tier
    
    **Formula:**
    ```
    DBU/Hour = cu_size × num_nodes
    DBU Cost = DBU/Hour × hours_per_month × dbu_price
    
    Storage:
    Total DSU = storage_gb × 15 (each GB consumes 15 DSU)
    Storage Cost = Total DSU × price_per_dsu
    
    Total Cost = DBU Cost + Storage Cost
    ```
    
    **Example Request:**
    ```json
    {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "cu_size": 4,
      "num_nodes": 2,
      "hours_per_month": 730,
      "storage_gb": 500
    }
    ```
    
    **Example Response:**
    ```json
    {
      "dbu_calculation": {
        "dbu_per_hour": 8,
        "dbu_cost_per_month": 408.80
      },
      "storage_calculation": {
        "storage_gb": 500,
        "max_storage_gb": 8192,
        "dsu_per_gb": 15,
        "total_dsu": 7500,
        "price_per_dsu": 0.023,
        "storage_cost_per_month": 172.50
      },
      "total_cost": {
        "cost_per_month": 581.30,
        "breakdown": {
          "dbu_cost": 408.80,
          "storage_cost": 172.50
        }
      }
    }
    ```
    """
    # Validate cloud, region, tier
    error = await validate_cloud(request.cloud)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_region(request.cloud, request.region, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_tier(request.cloud, request.tier, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_lakebase_cu_size(request.cu_size, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    error = await validate_lakebase_num_nodes(request.num_nodes, db)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    
    # Storage constants for Lakebase
    MAX_STORAGE_GB = 8192  # 8 TB
    DSU_PER_GB = 15  # Each GB consumes 15 DSU
    
    # Validate storage (also validated in Pydantic, but explicit check for clear error)
    if request.storage_gb > MAX_STORAGE_GB:
        raise HTTPException(status_code=400, detail={
            "code": "INVALID_STORAGE_SIZE",
            "message": f"Storage cannot exceed {MAX_STORAGE_GB} GB (8 TB)",
            "field": "storage_gb",
            "max_value": MAX_STORAGE_GB
        })
    
    # Calculate storage costs (no free tier for Lakebase)
    total_dsu = request.storage_gb * DSU_PER_GB
    storage_cost_per_month = 0.0
    price_per_dsu = 0.0
    
    if request.storage_gb > 0:
        try:
            # Get DSU price from database
            storage_price_query = text("""
                SELECT price_per_dbu as price_per_dsu 
                FROM lakemeter.sync_pricing_dbu_rates
                WHERE product_type = 'DATABRICKS_STORAGE' 
                  AND usage_unit = 'DSU'
                  AND cloud = :cloud 
                  AND region = :region
                  AND tier = :tier
                LIMIT 1
            """)
            storage_result = await db.execute(storage_price_query, {
                "cloud": request.cloud.upper(),
                "region": request.region,
                "tier": request.tier.upper()
            })
            storage_row = storage_result.fetchone()
            if storage_row:
                price_per_dsu = float(storage_row[0])
                storage_cost_per_month = total_dsu * price_per_dsu
            else:
                logger.warning(f"No storage price found for Lakebase: {request.cloud.upper()}/{request.region}/{request.tier.upper()}")
        except Exception as e:
            logger.warning(f"Could not fetch storage price for Lakebase: {e}")
    
    try:
        query = text("""
            SELECT 
                dbu_per_hour, hours_per_month, dbu_per_month, dbu_price, dbu_cost_per_month,
                driver_vm_cost_per_hour, worker_vm_cost_per_hour, total_vm_cost_per_hour,
                driver_vm_cost_per_month, total_worker_vm_cost_per_month, vm_cost_per_month, cost_per_month
            FROM lakemeter.calculate_line_item_costs(
                :p1, :p2, :p3, :p4, :p5, :p6, :p7, :p8, :p9, :p10,
                :p11, :p12, :p13, :p14, :p15, :p16, :p17, :p18, :p19, :p20,
                :p21, :p22, :p23, :p24, :p25, :p26, :p27, :p28, :p29, :p30,
                :p31, :p32, :p33, :p34, :p35
            )
        """)
        
        result = await db.execute(query, {
            "p1": "LAKEBASE", "p2": request.cloud.upper(), "p3": request.region, "p4": request.tier.upper(),
            "p5": False, "p6": False, "p7": None, "p8": None, "p9": None, "p10": 0,
            "p11": "on_demand", "p12": "on_demand", "p13": 0, "p14": 0, "p15": 30,
            "p16": request.hours_per_month, "p17": "standard", "p18": None, "p19": None, "p20": 1,
            "p21": "on_demand", "p22": None, "p23": 0, "p24": None,
            "p25": None, "p26": None, "p27": "global", "p28": "all",
            "p29": "input_token", "p30": 0,
            "p31": request.cu_size, "p32": request.num_nodes,
            "p33": "NA", "p34": "NA", "p35": "NA"
        })
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="No calculation result returned")
        
        # Determine SKU type
        sku_type = get_sku_type(workload_type="LAKEBASE")
        
        # Calculate total cost including storage
        dbu_cost_per_month = float(row[4])
        total_cost_per_month = dbu_cost_per_month + storage_cost_per_month
        
        return {
            "success": True,
            "data": {
                "workload_type": "LAKEBASE",
                "sku_type": sku_type,
                "configuration": {
                    "cloud": request.cloud.upper(),
                    "region": request.region,
                    "tier": request.tier.upper(),
                    "cu_size": request.cu_size,
                    "num_nodes": request.num_nodes,
                    "storage_gb": request.storage_gb
                },
                "usage": {"hours_per_month": float(row[1])},
                "dbu_calculation": {
                    "dbu_per_hour": float(row[0]),
                    "dbu_per_month": float(row[2]),
                    "dbu_price": float(row[3]),
                    "dbu_cost_per_month": dbu_cost_per_month
                },
                "storage_calculation": {
                    "storage_gb": request.storage_gb,
                    "max_storage_gb": MAX_STORAGE_GB,
                    "dsu_per_gb": DSU_PER_GB,
                    "total_dsu": total_dsu,
                    "price_per_dsu": price_per_dsu,
                    "storage_cost_per_month": storage_cost_per_month
                },
                "total_cost": {
                    "cost_per_month": total_cost_per_month,
                    "breakdown": {
                        "dbu_cost": dbu_cost_per_month,
                        "storage_cost": storage_cost_per_month
                    },
                    "note": "Lakebase is serverless - no VM costs"
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": {
                "code": "CALCULATION_ERROR",
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        }
