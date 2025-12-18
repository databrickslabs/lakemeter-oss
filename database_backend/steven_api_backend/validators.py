"""
Common validation functions for API endpoints.
Provides reusable validation logic for cloud, region, instance types, etc.
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Optional


async def validate_cloud(cloud: str) -> Optional[Dict]:
    """
    Validate cloud provider.
    Returns error dict if invalid, None if valid.
    """
    VALID_CLOUDS = ["AWS", "AZURE", "GCP"]
    if cloud.upper() not in VALID_CLOUDS:
        return {
            "success": False,
            "error": {
                "code": "INVALID_CLOUD",
                "message": f"Invalid cloud provider '{cloud}'. Must be one of: {', '.join(VALID_CLOUDS)}",
                "field": "cloud",
                "allowed_values": VALID_CLOUDS
            }
        }
    return None


async def validate_region(cloud: str, region: str, db: AsyncSession) -> Optional[Dict]:
    """
    Validate region for a specific cloud.
    Returns error dict if invalid, None if valid.
    """
    query = text("""
        SELECT DISTINCT region_code, sku_region
        FROM lakemeter.sync_ref_sku_region_map
        WHERE cloud = :cloud
        ORDER BY sku_region
    """)
    result = await db.execute(query, {"cloud": cloud.upper()})
    valid_regions = [{"region_code": r.region_code, "sku_region": r.sku_region} for r in result.fetchall()]
    valid_region_codes = [r["region_code"] for r in valid_regions]
    
    if region not in valid_region_codes:
        return {
            "success": False,
            "error": {
                "code": "INVALID_REGION",
                "message": f"Invalid region '{region}' for {cloud.upper()}. Must be one of the valid regions.",
                "field": "region",
                "allowed_values": valid_regions
            }
        }
    return None


async def validate_instance_family(instance_family: str, db: AsyncSession) -> Optional[Dict]:
    """
    Validate instance family (global, not cloud-specific).
    Returns error dict if invalid, None if valid.
    """
    query = text("""
        SELECT DISTINCT instance_family
        FROM lakemeter.sync_ref_instance_dbu_rates
        ORDER BY instance_family
    """)
    result = await db.execute(query)
    valid_families = [r.instance_family for r in result.fetchall()]
    
    if instance_family not in valid_families:
        return {
            "success": False,
            "error": {
                "code": "INVALID_INSTANCE_FAMILY",
                "message": f"Invalid instance family '{instance_family}'. Must be one of the valid families.",
                "field": "instance_family",
                "allowed_values": valid_families
            }
        }
    return None


async def validate_instance_type(cloud: str, instance_type: str, db: AsyncSession) -> Optional[Dict]:
    """
    Validate instance type for a specific cloud.
    Returns error dict if invalid, None if valid.
    Also returns instance info if valid (vcpus, memory, etc).
    """
    query = text("""
        SELECT instance_type, vcpus, memory_gb, instance_family, dbu_rate
        FROM lakemeter.sync_ref_instance_dbu_rates
        WHERE cloud = :cloud AND instance_type = :instance_type
    """)
    result = await db.execute(query, {"cloud": cloud.upper(), "instance_type": instance_type})
    instance_info = result.fetchone()
    
    if not instance_info:
        # Fetch available instance types for this cloud (limited to 20 for readability)
        available_query = text("""
            SELECT instance_type
            FROM lakemeter.sync_ref_instance_dbu_rates
            WHERE cloud = :cloud
            ORDER BY instance_type
            LIMIT 20
        """)
        available_result = await db.execute(available_query, {"cloud": cloud.upper()})
        available_types = [r.instance_type for r in available_result.fetchall()]
        
        return {
            "success": False,
            "error": {
                "code": "INVALID_INSTANCE_TYPE",
                "message": f"Instance type '{instance_type}' not found for {cloud.upper()}. Available types (showing first 20): {', '.join(available_types[:10])}... Use /api/v1/instances/types endpoint to see all available types.",
                "field": "instance_type",
                "allowed_values": available_types,
                "note": f"Total available instance types: Use GET /api/v1/instances/types?cloud={cloud.upper()} to see complete list"
            }
        }
    return None


async def get_instance_info(cloud: str, instance_type: str, db: AsyncSession) -> Optional[Dict]:
    """
    Get instance information (vcpus, memory, family, dbu_rate).
    Returns None if instance not found.
    """
    query = text("""
        SELECT instance_type, vcpus, memory_gb, instance_family, dbu_rate
        FROM lakemeter.sync_ref_instance_dbu_rates
        WHERE cloud = :cloud AND instance_type = :instance_type
    """)
    result = await db.execute(query, {"cloud": cloud.upper(), "instance_type": instance_type})
    instance_info = result.fetchone()
    
    if not instance_info:
        return None
    
    return {
        "vcpus": instance_info.vcpus,
        "memory_gb": float(instance_info.memory_gb),
        "instance_family": instance_info.instance_family,
        "dbu_rate": float(instance_info.dbu_rate)
    }


async def validate_warehouse_size(cloud: str, warehouse_type: str, warehouse_size: str, db: AsyncSession) -> Optional[Dict]:
    """
    Validate warehouse size for a specific cloud and warehouse type.
    Returns error dict with valid sizes if invalid, None if valid.
    
    For SERVERLESS: Validates against sync_product_dbsql_rates (DBU pricing)
    For CLASSIC/PRO: Validates against sync_ref_dbsql_warehouse_config (hardware specs)
    """
    # For SERVERLESS, validate against sync_product_dbsql_rates
    if warehouse_type.upper() == "SERVERLESS":
        query = text("""
            SELECT DISTINCT warehouse_size,
                CASE UPPER(warehouse_size)
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
            FROM lakemeter.sync_product_dbsql_rates
            WHERE UPPER(cloud) = :cloud
                AND UPPER(warehouse_type) = 'SERVERLESS'
            ORDER BY size_order
        """)
    else:
        # For CLASSIC/PRO, validate against sync_ref_dbsql_warehouse_config
        query = text("""
            SELECT DISTINCT warehouse_size,
                CASE UPPER(warehouse_size)
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
            FROM lakemeter.sync_ref_dbsql_warehouse_config
            WHERE cloud = :cloud
                AND UPPER(warehouse_type) = UPPER(:warehouse_type)
            ORDER BY size_order
        """)
    
    result = await db.execute(query, {
        "cloud": cloud.upper(),
        "warehouse_type": warehouse_type
    })
    valid_sizes = [r.warehouse_size for r in result.fetchall()]
    
    # Check if the provided size is valid (case-insensitive)
    if not any(warehouse_size.upper() == s.upper() for s in valid_sizes):
        return {
            "success": False,
            "error": {
                "code": "INVALID_WAREHOUSE_SIZE",
                "message": f"Invalid warehouse size '{warehouse_size}' for {cloud.upper()} {warehouse_type.upper()}. Must be one of: {', '.join(valid_sizes)}",
                "field": "warehouse_size",
                "allowed_values": valid_sizes
            }
        }
    return None


def validate_pricing_tier(pricing_tier: str, is_driver: bool = False) -> Optional[Dict]:
    """
    Validate pricing tier.
    Returns error dict if invalid, None if valid.
    
    Args:
        pricing_tier: The pricing tier to validate
        is_driver: If True, validates driver pricing tier (spot not allowed)
    """
    VALID_PRICING_TIERS = ["on_demand", "spot", "reserved_1y", "reserved_3y"]
    VALID_DRIVER_PRICING_TIERS = ["on_demand", "reserved_1y", "reserved_3y"]

    if pricing_tier.lower() not in VALID_PRICING_TIERS:
        return {
            "success": False,
            "error": {
                "code": "INVALID_PRICING_TIER",
                "message": f"Invalid pricing tier '{pricing_tier}'. Must be one of: {', '.join(VALID_PRICING_TIERS)}",
                "field": "pricing_tier",
                "allowed_values": VALID_PRICING_TIERS
            }
        }
    
    # Driver nodes cannot be spot instances
    if is_driver and pricing_tier.lower() == "spot":
        return {
            "success": False,
            "error": {
                "code": "INVALID_DRIVER_PRICING_TIER",
                "message": f"Driver nodes cannot use spot pricing tier. Driver must use: {', '.join(VALID_DRIVER_PRICING_TIERS)}",
                "field": "driver_pricing_tier",
                "allowed_values": VALID_DRIVER_PRICING_TIERS
            }
        }
    
    return None


def validate_payment_option(payment_option: str) -> Optional[Dict]:
    """
    Validate payment option.
    Returns error dict if invalid, None if valid.
    """
    VALID_PAYMENT_OPTIONS = ["NA", "no_upfront", "partial_upfront", "all_upfront"]
    
    if payment_option not in VALID_PAYMENT_OPTIONS:
        return {
            "success": False,
            "error": {
                "code": "INVALID_PAYMENT_OPTION",
                "message": f"Invalid payment option '{payment_option}'. Must be one of: {', '.join(VALID_PAYMENT_OPTIONS)}",
                "field": "payment_option",
                "allowed_values": VALID_PAYMENT_OPTIONS
            }
        }
    return None


def validate_pricing_payment_combination(cloud: str, pricing_tier: str, payment_option: str) -> Optional[Dict]:
    """
    Validate that pricing_tier and payment_option combination is valid for the given cloud.
    
    Rules:
    - AWS:
      - on_demand and spot: must use 'NA'
      - reserved_1y and reserved_3y: must use 'no_upfront', 'partial_upfront', or 'all_upfront'
    - Azure and GCP:
      - All pricing tiers: must use 'NA' (simpler reserved pricing model)
    
    Returns error dict if invalid, None if valid.
    """
    pricing_lower = pricing_tier.lower()
    cloud_upper = cloud.upper()
    
    # Azure and GCP always use NA for all pricing tiers
    if cloud_upper in ["AZURE", "GCP"]:
        if payment_option != "NA":
            return {
                "success": False,
                "error": {
                    "code": "INVALID_PAYMENT_OPTION_FOR_CLOUD",
                    "message": f"Payment option must be 'NA' for {cloud_upper}. Granular payment options (no_upfront, partial_upfront, all_upfront) are only available on AWS.",
                    "field": "payment_option",
                    "allowed_values": ["NA"],
                    "provided": {
                        "cloud": cloud,
                        "pricing_tier": pricing_tier,
                        "payment_option": payment_option
                    }
                }
            }
        return None
    
    # AWS-specific validation
    if cloud_upper == "AWS":
        # For on_demand and spot, payment option must be NA
        if pricing_lower in ["on_demand", "spot"]:
            if payment_option != "NA":
                return {
                    "success": False,
                    "error": {
                        "code": "INVALID_PAYMENT_OPTION_FOR_PRICING_TIER",
                        "message": f"Payment option must be 'NA' for '{pricing_tier}' pricing tier on AWS. Reserved payment options (no_upfront, partial_upfront, all_upfront) are only valid for reserved_1y and reserved_3y.",
                        "field": "payment_option",
                        "allowed_values": ["NA"],
                        "provided": {
                            "cloud": cloud,
                            "pricing_tier": pricing_tier,
                            "payment_option": payment_option
                        }
                    }
                }
        
        # For reserved pricing on AWS, payment option must NOT be NA
        elif pricing_lower in ["reserved_1y", "reserved_3y"]:
            if payment_option == "NA":
                return {
                    "success": False,
                    "error": {
                        "code": "INVALID_PAYMENT_OPTION_FOR_PRICING_TIER",
                        "message": f"Payment option cannot be 'NA' for '{pricing_tier}' pricing tier on AWS. Must specify: no_upfront, partial_upfront, or all_upfront.",
                        "field": "payment_option",
                        "allowed_values": ["no_upfront", "partial_upfront", "all_upfront"],
                        "provided": {
                            "cloud": cloud,
                            "pricing_tier": pricing_tier,
                            "payment_option": payment_option
                        }
                    }
                }
            elif payment_option not in ["no_upfront", "partial_upfront", "all_upfront"]:
                return {
                    "success": False,
                    "error": {
                        "code": "INVALID_PAYMENT_OPTION_FOR_PRICING_TIER",
                        "message": f"Invalid payment option '{payment_option}' for '{pricing_tier}' on AWS. Must be: no_upfront, partial_upfront, or all_upfront.",
                        "field": "payment_option",
                        "allowed_values": ["no_upfront", "partial_upfront", "all_upfront"],
                        "provided": {
                            "cloud": cloud,
                            "pricing_tier": pricing_tier,
                            "payment_option": payment_option
                        }
                    }
                }
    
    return None


async def validate_vector_search_mode(
    mode: str,
    cloud: str,
    db: AsyncSession
) -> Optional[Dict]:
    """
    Validate Vector Search mode for a specific cloud.
    Returns error dict if invalid, None if valid.
    """
    query = text("""
        SELECT DISTINCT size_or_model as mode
        FROM lakemeter.sync_product_serverless_rates
        WHERE product = 'vector_search' AND cloud = :cloud
        ORDER BY mode
    """)
    result = await db.execute(query, {"cloud": cloud.upper()})
    valid_modes = [r.mode for r in result.fetchall()]
    
    if not valid_modes:
        return {
            "success": False,
            "error": {
                "code": "NO_DATA",
                "message": f"No Vector Search modes found for cloud '{cloud}'",
                "field": "mode"
            }
        }
    
    if mode not in valid_modes:
        return {
            "success": False,
            "error": {
                "code": "INVALID_MODE",
                "message": f"Invalid Vector Search mode '{mode}' for {cloud}. Must be one of: {', '.join(valid_modes)}",
                "field": "mode",
                "allowed_values": valid_modes
            }
        }
    return None


async def validate_photon_sku_type(
    cloud: str,
    sku_type: str,
    db: AsyncSession
) -> Optional[Dict]:
    """
    Validate SKU type for Photon multipliers for a specific cloud.
    Returns error dict if invalid, None if valid.
    """
    query = text("""
        SELECT DISTINCT sku_type
        FROM lakemeter.sync_ref_dbu_multipliers
        WHERE feature = 'photon' AND cloud = :cloud
        ORDER BY sku_type
    """)
    result = await db.execute(query, {"cloud": cloud.upper()})
    valid_types = [r.sku_type for r in result.fetchall()]
    
    if not valid_types:
        return {
            "success": False,
            "error": {
                "code": "NO_DATA",
                "message": f"No Photon multipliers found for cloud '{cloud}'",
                "field": "sku_type"
            }
        }
    
    if sku_type not in valid_types:
        return {
            "success": False,
            "error": {
                "code": "INVALID_SKU_TYPE",
                "message": f"Invalid SKU type '{sku_type}' for Photon multipliers in {cloud}. Must be one of: {', '.join(valid_types)}",
                "field": "sku_type",
                "allowed_values": valid_types
            }
        }
    return None


async def validate_product_type(
    cloud: str,
    region: str,
    product_type: str,
    db: AsyncSession
) -> Optional[Dict]:
    """
    Validate product_type for DBU pricing for a specific cloud and region.
    Returns error dict if invalid, None if valid.
    """
    query = text("""
        SELECT DISTINCT product_type
        FROM lakemeter.sync_pricing_dbu_rates
        WHERE cloud = :cloud AND region = :region
        ORDER BY product_type
    """)
    result = await db.execute(query, {"cloud": cloud.upper(), "region": region})
    valid_types = [r.product_type for r in result.fetchall()]
    
    if not valid_types:
        return {
            "success": False,
            "error": {
                "code": "NO_DATA",
                "message": f"No DBU pricing data found for {cloud}/{region}",
                "field": "product_type"
            }
        }
    
    if product_type.upper() not in valid_types:
        return {
            "success": False,
            "error": {
                "code": "INVALID_PRODUCT_TYPE",
                "message": f"Invalid product type '{product_type}' for {cloud}/{region}. Must be one of: {', '.join(valid_types)}",
                "field": "product_type",
                "allowed_values": valid_types
            }
        }
    return None


async def validate_fmapi_databricks_rate_type(
    model: str,
    rate_type: str,
    db: AsyncSession
) -> Optional[Dict]:
    """
    Validate rate_type for a specific Databricks FMAPI model.
    Returns error dict if invalid, None if valid.
    """
    query = text("""
        SELECT DISTINCT rate_type
        FROM lakemeter.sync_product_fmapi_databricks
        WHERE model = :model
        ORDER BY rate_type
    """)
    result = await db.execute(query, {"model": model})
    valid_types = [r.rate_type for r in result.fetchall()]
    
    if not valid_types:
        return {
            "success": False,
            "error": {
                "code": "NO_DATA",
                "message": f"No rate types found for model '{model}'",
                "field": "rate_type"
            }
        }
    
    if rate_type not in valid_types:
        return {
            "success": False,
            "error": {
                "code": "INVALID_RATE_TYPE",
                "message": f"Invalid rate type '{rate_type}' for model '{model}'. Must be one of: {', '.join(valid_types)}",
                "field": "rate_type",
                "allowed_values": valid_types
            }
        }
    return None


async def validate_fmapi_databricks_model(model: str, db: AsyncSession) -> Optional[Dict]:
    """
    Validate model name for FMAPI Databricks models.
    Returns error dict if invalid, None if valid.
    """
    query = text("""
        SELECT DISTINCT model
        FROM lakemeter.sync_product_fmapi_databricks
        ORDER BY model
    """)
    result = await db.execute(query)
    valid_models = [r.model for r in result.fetchall()]
    
    if model not in valid_models:
        return {
            "success": False,
            "error": {
                "code": "INVALID_MODEL",
                "message": f"Invalid model '{model}'. Must be one of the available Databricks models.",
                "field": "model",
                "allowed_values": valid_models
            }
        }
    return None


async def validate_fmapi_proprietary_provider(provider: str, db: AsyncSession) -> Optional[Dict]:
    """
    Validate provider for FMAPI proprietary models.
    Returns error dict if invalid, None if valid.
    """
    query = text("""
        SELECT DISTINCT provider
        FROM lakemeter.sync_product_fmapi_proprietary
        ORDER BY provider
    """)
    result = await db.execute(query)
    valid_providers = [r.provider for r in result.fetchall()]
    
    if provider not in valid_providers:
        return {
            "success": False,
            "error": {
                "code": "INVALID_PROVIDER",
                "message": f"Invalid provider '{provider}'. Must be one of: {', '.join(valid_providers)}",
                "field": "provider",
                "allowed_values": valid_providers
            }
        }
    return None


async def validate_fmapi_proprietary_model(model: str, provider: str, db: AsyncSession) -> Optional[Dict]:
    """
    Validate model name for FMAPI proprietary models given a provider.
    Returns error dict if invalid, None if valid.
    """
    query = text("""
        SELECT DISTINCT model
        FROM lakemeter.sync_product_fmapi_proprietary
        WHERE provider = :provider
        ORDER BY model
    """)
    result = await db.execute(query, {"provider": provider.lower()})
    valid_models = [r.model for r in result.fetchall()]
    
    if model not in valid_models:
        return {
            "success": False,
            "error": {
                "code": "INVALID_MODEL",
                "message": f"Invalid model '{model}' for provider '{provider}'. Must be one of the available models for this provider.",
                "field": "model",
                "allowed_values": valid_models
            }
        }
    return None


async def validate_fmapi_proprietary_endpoint_type(
    provider: str, 
    model: str, 
    endpoint_type: str, 
    db: AsyncSession
) -> Optional[Dict]:
    """
    Validate endpoint_type for a specific provider and model.
    Returns error dict if invalid, None if valid.
    """
    query = text("""
        SELECT DISTINCT endpoint_type
        FROM lakemeter.sync_product_fmapi_proprietary
        WHERE provider = :provider AND model = :model
        ORDER BY endpoint_type
    """)
    result = await db.execute(query, {
        "provider": provider.lower(),
        "model": model
    })
    valid_types = [r.endpoint_type for r in result.fetchall()]
    
    if endpoint_type not in valid_types:
        return {
            "success": False,
            "error": {
                "code": "INVALID_ENDPOINT_TYPE",
                "message": f"Invalid endpoint type '{endpoint_type}' for {provider}/{model}. Must be one of: {', '.join(valid_types)}",
                "field": "endpoint_type",
                "allowed_values": valid_types
            }
        }
    return None


async def validate_fmapi_proprietary_context_length(
    provider: str, 
    model: str, 
    context_length: str,
    endpoint_type: str = None,
    db: AsyncSession = None
) -> Optional[Dict]:
    """
    Validate context_length for a specific provider, model, and optionally endpoint_type.
    Returns error dict if invalid, None if valid.
    """
    where_conditions = ["provider = :provider", "model = :model"]
    params = {"provider": provider.lower(), "model": model}
    
    if endpoint_type:
        where_conditions.append("endpoint_type = :endpoint_type")
        params["endpoint_type"] = endpoint_type
    
    where_clause = " AND ".join(where_conditions)
    
    query = text(f"""
        SELECT DISTINCT context_length
        FROM lakemeter.sync_product_fmapi_proprietary
        WHERE {where_clause}
        ORDER BY context_length
    """)
    result = await db.execute(query, params)
    valid_lengths = [r.context_length for r in result.fetchall()]
    
    if not valid_lengths:
        return {
            "success": False,
            "error": {
                "code": "NO_DATA",
                "message": f"No context lengths found for {provider}/{model}" + (f"/{endpoint_type}" if endpoint_type else ""),
                "field": "context_length"
            }
        }
    
    if context_length not in valid_lengths:
        return {
            "success": False,
            "error": {
                "code": "INVALID_CONTEXT_LENGTH",
                "message": f"Invalid context length '{context_length}' for {provider}/{model}" + (f"/{endpoint_type}" if endpoint_type else "") + f". Must be one of: {', '.join(valid_lengths)}",
                "field": "context_length",
                "allowed_values": valid_lengths
            }
        }
    return None


async def validate_fmapi_proprietary_rate_type(
    provider: str, 
    model: str, 
    rate_type: str,
    endpoint_type: str = None,
    context_length: str = None,
    db: AsyncSession = None
) -> Optional[Dict]:
    """
    Validate rate_type for a specific provider, model, and optionally endpoint_type and context_length.
    Returns error dict if invalid, None if valid.
    """
    where_conditions = ["provider = :provider", "model = :model"]
    params = {"provider": provider.lower(), "model": model}
    
    if endpoint_type:
        where_conditions.append("endpoint_type = :endpoint_type")
        params["endpoint_type"] = endpoint_type
    
    if context_length:
        where_conditions.append("context_length = :context_length")
        params["context_length"] = context_length
    
    where_clause = " AND ".join(where_conditions)
    
    query = text(f"""
        SELECT DISTINCT rate_type
        FROM lakemeter.sync_product_fmapi_proprietary
        WHERE {where_clause}
        ORDER BY rate_type
    """)
    result = await db.execute(query, params)
    valid_types = [r.rate_type for r in result.fetchall()]
    
    if not valid_types:
        context_str = f"/{endpoint_type}" if endpoint_type else ""
        context_str += f"/{context_length}" if context_length else ""
        return {
            "success": False,
            "error": {
                "code": "NO_DATA",
                "message": f"No rate types found for {provider}/{model}{context_str}",
                "field": "rate_type"
            }
        }
    
    if rate_type not in valid_types:
        context_str = f"/{endpoint_type}" if endpoint_type else ""
        context_str += f"/{context_length}" if context_length else ""
        return {
            "success": False,
            "error": {
                "code": "INVALID_RATE_TYPE",
                "message": f"Invalid rate type '{rate_type}' for {provider}/{model}{context_str}. Must be one of: {', '.join(valid_types)}",
                "field": "rate_type",
                "allowed_values": valid_types
            }
        }
    return None


async def validate_tier(cloud: str, tier: str, db: AsyncSession):
    """
    Validate that the tier is valid for the given cloud provider.
    Azure does not support ENTERPRISE tier.
    Returns None if valid, error dict if invalid.
    """
    # Query database to get valid tiers for this cloud
    query = text("""
        SELECT DISTINCT tier
        FROM lakemeter.sync_pricing_dbu_rates
        WHERE cloud = :cloud
        ORDER BY tier
    """)
    result = await db.execute(query, {"cloud": cloud.upper()})
    valid_tiers = [r.tier for r in result.fetchall()]
    
    if not valid_tiers:
        # Fallback to default tiers if no data in DB
        valid_tiers = ["STANDARD", "PREMIUM"]
        if cloud.upper() != "AZURE":
            valid_tiers.append("ENTERPRISE")
    
    if tier.upper() not in [t.upper() for t in valid_tiers]:
        cloud_note = ""
        if cloud.upper() == "AZURE" and tier.upper() == "ENTERPRISE":
            cloud_note = " (Note: Azure does not support ENTERPRISE tier)"
        
        return {
            "success": False,
            "error": {
                "code": "INVALID_TIER",
                "message": f"Invalid tier '{tier}' for cloud '{cloud}'. Must be one of: {', '.join(valid_tiers)}{cloud_note}",
                "field": "tier",
                "allowed_values": valid_tiers
            }
        }
    return None


async def validate_product_type(cloud: str, region: str, product_type: str, db: AsyncSession):
    """
    Validate that the product type exists for the given cloud and region.
    Returns None if valid, error dict if invalid.
    """
    query = text("""
        SELECT DISTINCT product_type
        FROM lakemeter.sync_pricing_dbu_rates
        WHERE cloud = :cloud AND region = :region
        ORDER BY product_type
    """)
    result = await db.execute(query, {"cloud": cloud.upper(), "region": region})
    valid_product_types = [r.product_type for r in result.fetchall()]
    
    if product_type.upper() not in [pt.upper() for pt in valid_product_types]:
        return {
            "success": False,
            "error": {
                "code": "INVALID_PRODUCT_TYPE",
                "message": f"Invalid product type '{product_type}' for cloud '{cloud}' and region '{region}'. Must be one of: {', '.join(valid_product_types)}",
                "field": "product_type",
                "allowed_values": valid_product_types
            }
        }
    return None


async def validate_vector_search_mode(mode: str, db: AsyncSession) -> Optional[Dict]:
    """
    Validate Vector Search mode.
    Returns error dict if invalid, None if valid.
    """
    query = text("""
        SELECT DISTINCT size_or_model 
        FROM lakemeter.sync_product_serverless_rates
        WHERE product = 'vector_search'
    """)
    result = await db.execute(query)
    valid_modes = [row[0] for row in result.fetchall()]
    
    if mode.lower() not in [m.lower() for m in valid_modes]:
        return {
            "success": False,
            "error": {
                "code": "INVALID_VECTOR_SEARCH_MODE",
                "message": f"Invalid Vector Search mode '{mode}'. Must be one of: {', '.join(valid_modes)}",
                "field": "mode",
                "allowed_values": valid_modes
            }
        }
    return None


async def validate_lakebase_cu_size(cu_size: int, db: AsyncSession) -> Optional[Dict]:
    """
    Validate Lakebase CU size.
    Returns error dict if invalid, None if valid.
    """
    VALID_CU_SIZES = [1, 2, 4, 8]
    
    if cu_size not in VALID_CU_SIZES:
        return {
            "success": False,
            "error": {
                "code": "INVALID_CU_SIZE",
                "message": f"Invalid CU size '{cu_size}'. Must be one of: {', '.join(map(str, VALID_CU_SIZES))}",
                "field": "cu_size",
                "allowed_values": VALID_CU_SIZES
            }
        }
    return None


async def validate_lakebase_num_nodes(num_nodes: int, db: AsyncSession) -> Optional[Dict]:
    """
    Validate Lakebase number of nodes.
    Returns error dict if invalid, None if valid.
    """
    if num_nodes < 1 or num_nodes > 3:
        return {
            "success": False,
            "error": {
                "code": "INVALID_NUM_NODES",
                "message": f"Invalid number of nodes '{num_nodes}'. Must be between 1 and 3 for HA.",
                "field": "num_nodes",
                "allowed_values": [1, 2, 3]
            }
        }
    return None


async def validate_warehouse_type(warehouse_type: str, db: AsyncSession) -> Optional[Dict]:
    """
    Validate DBSQL warehouse type.
    Returns error dict if invalid, None if valid.
    """
    VALID_TYPES = ["CLASSIC", "PRO", "SERVERLESS"]
    
    if warehouse_type.upper() not in VALID_TYPES:
        return {
            "success": False,
            "error": {
                "code": "INVALID_WAREHOUSE_TYPE",
                "message": f"Invalid warehouse type '{warehouse_type}'. Must be one of: {', '.join(VALID_TYPES)}",
                "field": "warehouse_type",
                "allowed_values": VALID_TYPES
            }
        }
    return None

