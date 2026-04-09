"""
Validation functions for API endpoints.
Ported from database_backend/steven_api_backend/validators.py (async→sync).
All validators return None if valid, or an error dict if invalid.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Dict, Optional, Union


def validate_cloud(cloud: str) -> Optional[Dict]:
    VALID_CLOUDS = ["AWS", "AZURE", "GCP"]
    if cloud.upper() not in VALID_CLOUDS:
        return {
            "success": False,
            "error": {
                "code": "INVALID_CLOUD",
                "message": f"Invalid cloud provider '{cloud}'. Must be one of: {', '.join(VALID_CLOUDS)}",
                "field": "cloud",
                "allowed_values": VALID_CLOUDS,
            },
        }
    return None


def validate_region(cloud: str, region: str, db: Session) -> Optional[Dict]:
    query = text("""
        SELECT DISTINCT region_code, sku_region
        FROM lakemeter.sync_ref_sku_region_map
        WHERE cloud = :cloud
        ORDER BY sku_region
    """)
    result = db.execute(query, {"cloud": cloud.upper()})
    valid_regions = [{"region_code": r.region_code, "sku_region": r.sku_region} for r in result.fetchall()]
    valid_region_codes = [r["region_code"] for r in valid_regions]

    if region not in valid_region_codes:
        return {
            "success": False,
            "error": {
                "code": "INVALID_REGION",
                "message": f"Invalid region '{region}' for {cloud.upper()}.",
                "field": "region",
                "allowed_values": valid_regions,
            },
        }
    return None


def validate_tier(cloud: str, tier: str, db: Session) -> Optional[Dict]:
    query = text("""
        SELECT DISTINCT tier
        FROM lakemeter.sync_pricing_dbu_rates
        WHERE cloud = :cloud
        ORDER BY tier
    """)
    result = db.execute(query, {"cloud": cloud.upper()})
    valid_tiers = [r.tier for r in result.fetchall()]

    if not valid_tiers:
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
                "allowed_values": valid_tiers,
            },
        }
    return None


def validate_instance_family(instance_family: str, db: Session) -> Optional[Dict]:
    query = text("""
        SELECT DISTINCT instance_family
        FROM lakemeter.sync_ref_instance_dbu_rates
        ORDER BY instance_family
    """)
    result = db.execute(query)
    valid_families = [r.instance_family for r in result.fetchall()]

    if instance_family not in valid_families:
        return {
            "success": False,
            "error": {
                "code": "INVALID_INSTANCE_FAMILY",
                "message": f"Invalid instance family '{instance_family}'.",
                "field": "instance_family",
                "allowed_values": valid_families,
            },
        }
    return None


def validate_instance_type(cloud: str, instance_type: str, db: Session) -> Optional[Dict]:
    query = text("""
        SELECT instance_type, vcpus, memory_gb, instance_family, dbu_rate
        FROM lakemeter.sync_ref_instance_dbu_rates
        WHERE cloud = :cloud AND instance_type = :instance_type
    """)
    result = db.execute(query, {"cloud": cloud.upper(), "instance_type": instance_type})
    instance_info = result.fetchone()

    if not instance_info:
        available_query = text("""
            SELECT instance_type
            FROM lakemeter.sync_ref_instance_dbu_rates
            WHERE cloud = :cloud
            ORDER BY instance_type
            LIMIT 20
        """)
        available_result = db.execute(available_query, {"cloud": cloud.upper()})
        available_types = [r.instance_type for r in available_result.fetchall()]
        return {
            "success": False,
            "error": {
                "code": "INVALID_INSTANCE_TYPE",
                "message": f"Instance type '{instance_type}' not found for {cloud.upper()}.",
                "field": "instance_type",
                "allowed_values": available_types,
            },
        }
    return None


def get_instance_info(cloud: str, instance_type: str, db: Session) -> Optional[Dict]:
    query = text("""
        SELECT instance_type, vcpus, memory_gb, instance_family, dbu_rate
        FROM lakemeter.sync_ref_instance_dbu_rates
        WHERE cloud = :cloud AND instance_type = :instance_type
    """)
    result = db.execute(query, {"cloud": cloud.upper(), "instance_type": instance_type})
    row = result.fetchone()
    if not row:
        return None
    return {
        "vcpus": row.vcpus,
        "memory_gb": float(row.memory_gb),
        "instance_family": row.instance_family,
        "dbu_rate": float(row.dbu_rate),
    }


def validate_pricing_tier(pricing_tier: str, is_driver: bool = False) -> Optional[Dict]:
    VALID_PRICING_TIERS = ["on_demand", "spot", "reserved_1y", "reserved_3y"]
    VALID_DRIVER_PRICING_TIERS = ["on_demand", "reserved_1y", "reserved_3y"]

    if pricing_tier.lower() not in VALID_PRICING_TIERS:
        return {
            "success": False,
            "error": {
                "code": "INVALID_PRICING_TIER",
                "message": f"Invalid pricing tier '{pricing_tier}'. Must be one of: {', '.join(VALID_PRICING_TIERS)}",
                "field": "pricing_tier",
                "allowed_values": VALID_PRICING_TIERS,
            },
        }
    if is_driver and pricing_tier.lower() == "spot":
        return {
            "success": False,
            "error": {
                "code": "INVALID_DRIVER_PRICING_TIER",
                "message": f"Driver nodes cannot use spot pricing tier.",
                "field": "driver_pricing_tier",
                "allowed_values": VALID_DRIVER_PRICING_TIERS,
            },
        }
    return None


def validate_payment_option(payment_option: str) -> Optional[Dict]:
    VALID_PAYMENT_OPTIONS = ["NA", "no_upfront", "partial_upfront", "all_upfront"]
    if payment_option not in VALID_PAYMENT_OPTIONS:
        return {
            "success": False,
            "error": {
                "code": "INVALID_PAYMENT_OPTION",
                "message": f"Invalid payment option '{payment_option}'. Must be one of: {', '.join(VALID_PAYMENT_OPTIONS)}",
                "field": "payment_option",
                "allowed_values": VALID_PAYMENT_OPTIONS,
            },
        }
    return None


def validate_pricing_payment_combination(cloud: str, pricing_tier: str, payment_option: str) -> Optional[Dict]:
    pricing_lower = pricing_tier.lower()
    cloud_upper = cloud.upper()

    if cloud_upper in ["AZURE", "GCP"]:
        if payment_option != "NA":
            return {
                "success": False,
                "error": {
                    "code": "INVALID_PAYMENT_OPTION_FOR_CLOUD",
                    "message": f"Payment option must be 'NA' for {cloud_upper}.",
                    "field": "payment_option",
                    "allowed_values": ["NA"],
                },
            }
        return None

    if cloud_upper == "AWS":
        if pricing_lower in ["on_demand", "spot"]:
            if payment_option != "NA":
                return {
                    "success": False,
                    "error": {
                        "code": "INVALID_PAYMENT_OPTION_FOR_PRICING_TIER",
                        "message": f"Payment option must be 'NA' for '{pricing_tier}' on AWS.",
                        "field": "payment_option",
                        "allowed_values": ["NA"],
                    },
                }
        elif pricing_lower in ["reserved_1y", "reserved_3y"]:
            if payment_option == "NA":
                return {
                    "success": False,
                    "error": {
                        "code": "INVALID_PAYMENT_OPTION_FOR_PRICING_TIER",
                        "message": f"Payment option cannot be 'NA' for '{pricing_tier}' on AWS. Must specify: no_upfront, partial_upfront, or all_upfront.",
                        "field": "payment_option",
                        "allowed_values": ["no_upfront", "partial_upfront", "all_upfront"],
                    },
                }
            elif payment_option not in ["no_upfront", "partial_upfront", "all_upfront"]:
                return {
                    "success": False,
                    "error": {
                        "code": "INVALID_PAYMENT_OPTION_FOR_PRICING_TIER",
                        "message": f"Invalid payment option '{payment_option}' for '{pricing_tier}' on AWS.",
                        "field": "payment_option",
                        "allowed_values": ["no_upfront", "partial_upfront", "all_upfront"],
                    },
                }
    return None


def validate_warehouse_type(warehouse_type: str) -> Optional[Dict]:
    VALID_TYPES = ["CLASSIC", "PRO", "SERVERLESS"]
    if warehouse_type.upper() not in VALID_TYPES:
        return {
            "success": False,
            "error": {
                "code": "INVALID_WAREHOUSE_TYPE",
                "message": f"Invalid warehouse type '{warehouse_type}'. Must be one of: {', '.join(VALID_TYPES)}",
                "field": "warehouse_type",
                "allowed_values": VALID_TYPES,
            },
        }
    return None


def validate_warehouse_size(cloud: str, warehouse_type: str, warehouse_size: str, db: Session) -> Optional[Dict]:
    if warehouse_type.upper() == "SERVERLESS":
        query = text("""
            SELECT DISTINCT warehouse_size
            FROM lakemeter.sync_product_dbsql_rates
            WHERE UPPER(cloud) = :cloud AND UPPER(warehouse_type) = 'SERVERLESS'
        """)
    else:
        # Note: In the OSS DB, column names are swapped:
        # warehouse_size = type ("classic"/"pro"), warehouse_type = size ("2X-Small" etc)
        query = text("""
            SELECT DISTINCT warehouse_type AS warehouse_size
            FROM lakemeter.sync_ref_dbsql_warehouse_config
            WHERE cloud = :cloud AND UPPER(warehouse_size) = UPPER(:warehouse_type)
        """)

    result = db.execute(query, {"cloud": cloud.upper(), "warehouse_type": warehouse_type})
    valid_sizes = [r.warehouse_size for r in result.fetchall()]

    if not any(warehouse_size.upper() == s.upper() for s in valid_sizes):
        return {
            "success": False,
            "error": {
                "code": "INVALID_WAREHOUSE_SIZE",
                "message": f"Invalid warehouse size '{warehouse_size}' for {cloud.upper()} {warehouse_type.upper()}. Must be one of: {', '.join(valid_sizes)}",
                "field": "warehouse_size",
                "allowed_values": valid_sizes,
            },
        }
    return None


def validate_lakebase_cu_size(cu_size: float) -> Optional[Dict]:
    VALID_CU_SIZES = [
        0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
        17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32,
        36, 40, 44, 48, 52, 56, 60, 64, 72, 80, 88, 96, 104, 112,
    ]
    if float(cu_size) not in VALID_CU_SIZES:
        return {
            "success": False,
            "error": {
                "code": "INVALID_CU_SIZE",
                "message": f"Invalid CU size '{cu_size}'. Valid autoscaling sizes: 0.5, 1-32. Fixed sizes: 36, 40, 44, 48, 52, 56, 60, 64, 72, 80, 88, 96, 104, 112.",
                "field": "cu_size",
                "allowed_values": VALID_CU_SIZES,
            },
        }
    return None


def validate_lakebase_num_nodes(num_nodes: int) -> Optional[Dict]:
    if num_nodes < 1 or num_nodes > 3:
        return {
            "success": False,
            "error": {
                "code": "INVALID_NUM_NODES",
                "message": f"Invalid number of nodes '{num_nodes}'. Must be between 1 and 3.",
                "field": "num_nodes",
                "allowed_values": [1, 2, 3],
            },
        }
    return None


def validate_vector_search_mode(mode: str, cloud: str, db: Session) -> Optional[Dict]:
    query = text("""
        SELECT DISTINCT size_or_model as mode
        FROM lakemeter.sync_product_serverless_rates
        WHERE product = 'vector_search' AND cloud = :cloud
        ORDER BY mode
    """)
    result = db.execute(query, {"cloud": cloud.upper()})
    valid_modes = [r.mode for r in result.fetchall()]

    if not valid_modes:
        return {
            "success": False,
            "error": {"code": "NO_DATA", "message": f"No Vector Search modes found for cloud '{cloud}'", "field": "mode"},
        }
    if mode not in valid_modes:
        return {
            "success": False,
            "error": {
                "code": "INVALID_MODE",
                "message": f"Invalid Vector Search mode '{mode}' for {cloud}. Must be one of: {', '.join(valid_modes)}",
                "field": "mode",
                "allowed_values": valid_modes,
            },
        }
    return None


def validate_photon_sku_type(cloud: str, sku_type: str, db: Session) -> Optional[Dict]:
    query = text("""
        SELECT DISTINCT sku_type
        FROM lakemeter.sync_ref_dbu_multipliers
        WHERE feature = 'photon' AND cloud = :cloud
        ORDER BY sku_type
    """)
    result = db.execute(query, {"cloud": cloud.upper()})
    valid_types = [r.sku_type for r in result.fetchall()]

    if not valid_types:
        return {
            "success": False,
            "error": {"code": "NO_DATA", "message": f"No Photon multipliers found for cloud '{cloud}'", "field": "sku_type"},
        }
    if sku_type not in valid_types:
        return {
            "success": False,
            "error": {
                "code": "INVALID_SKU_TYPE",
                "message": f"Invalid SKU type '{sku_type}' for Photon in {cloud}. Must be one of: {', '.join(valid_types)}",
                "field": "sku_type",
                "allowed_values": valid_types,
            },
        }
    return None


def validate_product_type(cloud: str, region: str, product_type: str, db: Session) -> Optional[Dict]:
    query = text("""
        SELECT DISTINCT product_type
        FROM lakemeter.sync_pricing_dbu_rates
        WHERE cloud = :cloud AND region = :region
        ORDER BY product_type
    """)
    result = db.execute(query, {"cloud": cloud.upper(), "region": region})
    valid_types = [r.product_type for r in result.fetchall()]

    if product_type.upper() not in [pt.upper() for pt in valid_types]:
        return {
            "success": False,
            "error": {
                "code": "INVALID_PRODUCT_TYPE",
                "message": f"Invalid product type '{product_type}' for {cloud}/{region}.",
                "field": "product_type",
                "allowed_values": valid_types,
            },
        }
    return None


def validate_fmapi_databricks_model(model: str, db: Session) -> Optional[Dict]:
    query = text("SELECT DISTINCT model FROM lakemeter.sync_product_fmapi_databricks ORDER BY model")
    result = db.execute(query)
    valid_models = [r.model for r in result.fetchall()]
    if model not in valid_models:
        return {
            "success": False,
            "error": {
                "code": "INVALID_MODEL",
                "message": f"Invalid model '{model}'.",
                "field": "model",
                "allowed_values": valid_models,
            },
        }
    return None


def validate_fmapi_databricks_rate_type(model: str, rate_type: str, db: Session) -> Optional[Dict]:
    query = text("SELECT DISTINCT rate_type FROM lakemeter.sync_product_fmapi_databricks WHERE model = :model ORDER BY rate_type")
    result = db.execute(query, {"model": model})
    valid_types = [r.rate_type for r in result.fetchall()]
    if not valid_types:
        return {"success": False, "error": {"code": "NO_DATA", "message": f"No rate types found for model '{model}'", "field": "rate_type"}}
    if rate_type not in valid_types:
        return {
            "success": False,
            "error": {
                "code": "INVALID_RATE_TYPE",
                "message": f"Invalid rate type '{rate_type}' for model '{model}'. Must be one of: {', '.join(valid_types)}",
                "field": "rate_type",
                "allowed_values": valid_types,
            },
        }
    return None


def validate_fmapi_proprietary_provider(provider: str, db: Session) -> Optional[Dict]:
    query = text("SELECT DISTINCT provider FROM lakemeter.sync_product_fmapi_proprietary ORDER BY provider")
    result = db.execute(query)
    valid_providers = [r.provider for r in result.fetchall()]
    if provider not in valid_providers:
        return {
            "success": False,
            "error": {
                "code": "INVALID_PROVIDER",
                "message": f"Invalid provider '{provider}'. Must be one of: {', '.join(valid_providers)}",
                "field": "provider",
                "allowed_values": valid_providers,
            },
        }
    return None


def validate_fmapi_proprietary_model(model: str, provider: str, db: Session) -> Optional[Dict]:
    query = text("SELECT DISTINCT model FROM lakemeter.sync_product_fmapi_proprietary WHERE provider = :provider ORDER BY model")
    result = db.execute(query, {"provider": provider.lower()})
    valid_models = [r.model for r in result.fetchall()]
    if model not in valid_models:
        return {
            "success": False,
            "error": {
                "code": "INVALID_MODEL",
                "message": f"Invalid model '{model}' for provider '{provider}'.",
                "field": "model",
                "allowed_values": valid_models,
            },
        }
    return None


def validate_fmapi_proprietary_endpoint_type(provider: str, model: str, endpoint_type: str, db: Session) -> Optional[Dict]:
    query = text("""
        SELECT DISTINCT endpoint_type FROM lakemeter.sync_product_fmapi_proprietary
        WHERE provider = :provider AND model = :model ORDER BY endpoint_type
    """)
    result = db.execute(query, {"provider": provider.lower(), "model": model})
    valid_types = [r.endpoint_type for r in result.fetchall()]
    if endpoint_type not in valid_types:
        return {
            "success": False,
            "error": {
                "code": "INVALID_ENDPOINT_TYPE",
                "message": f"Invalid endpoint type '{endpoint_type}' for {provider}/{model}. Must be one of: {', '.join(valid_types)}",
                "field": "endpoint_type",
                "allowed_values": valid_types,
            },
        }
    return None


def validate_fmapi_proprietary_context_length(
    provider: str, model: str, context_length: str,
    endpoint_type: str = None, db: Session = None,
) -> Optional[Dict]:
    where = ["provider = :provider", "model = :model"]
    params = {"provider": provider.lower(), "model": model}
    if endpoint_type:
        where.append("endpoint_type = :endpoint_type")
        params["endpoint_type"] = endpoint_type

    query = text(f"SELECT DISTINCT context_length FROM lakemeter.sync_product_fmapi_proprietary WHERE {' AND '.join(where)} ORDER BY context_length")
    result = db.execute(query, params)
    valid_lengths = [r.context_length for r in result.fetchall()]

    if not valid_lengths:
        return {"success": False, "error": {"code": "NO_DATA", "message": f"No context lengths found for {provider}/{model}", "field": "context_length"}}
    if context_length not in valid_lengths:
        return {
            "success": False,
            "error": {
                "code": "INVALID_CONTEXT_LENGTH",
                "message": f"Invalid context length '{context_length}' for {provider}/{model}. Must be one of: {', '.join(valid_lengths)}",
                "field": "context_length",
                "allowed_values": valid_lengths,
            },
        }
    return None


def validate_fmapi_proprietary_rate_type(
    provider: str, model: str, rate_type: str,
    endpoint_type: str = None, context_length: str = None, db: Session = None,
) -> Optional[Dict]:
    where = ["provider = :provider", "model = :model"]
    params = {"provider": provider.lower(), "model": model}
    if endpoint_type:
        where.append("endpoint_type = :endpoint_type")
        params["endpoint_type"] = endpoint_type
    if context_length:
        where.append("context_length = :context_length")
        params["context_length"] = context_length

    query = text(f"SELECT DISTINCT rate_type FROM lakemeter.sync_product_fmapi_proprietary WHERE {' AND '.join(where)} ORDER BY rate_type")
    result = db.execute(query, params)
    valid_types = [r.rate_type for r in result.fetchall()]

    if not valid_types:
        return {"success": False, "error": {"code": "NO_DATA", "message": f"No rate types found for {provider}/{model}", "field": "rate_type"}}
    if rate_type not in valid_types:
        return {
            "success": False,
            "error": {
                "code": "INVALID_RATE_TYPE",
                "message": f"Invalid rate type '{rate_type}' for {provider}/{model}. Must be one of: {', '.join(valid_types)}",
                "field": "rate_type",
                "allowed_values": valid_types,
            },
        }
    return None


def validate_sku_specific_discounts(sku_specific: dict, db: Session) -> Optional[Dict]:
    if not sku_specific:
        return None
    query = text("SELECT sku, discount_category, workload_group, description FROM lakemeter.sku_discount_mapping ORDER BY workload_group, sku")
    result = db.execute(query)
    rows = result.fetchall()
    valid_skus = [row[0] for row in rows]
    invalid_skus = [sku for sku in sku_specific.keys() if sku not in valid_skus]
    if invalid_skus:
        return {
            "success": False,
            "error": {
                "code": "INVALID_SKU_IN_DISCOUNT_CONFIG",
                "message": f"Invalid SKU(s): {', '.join(invalid_skus)}",
                "field": "discount_config.sku_specific",
                "invalid_skus": invalid_skus,
                "valid_skus": valid_skus,
            },
        }
    return None


def validate_pagination(limit: int, offset: int) -> Optional[Dict]:
    if limit < 1 or limit > 1000:
        return {"success": False, "error": {"code": "INVALID_LIMIT", "message": f"Limit must be between 1 and 1000. Got: {limit}", "field": "limit"}}
    if offset < 0:
        return {"success": False, "error": {"code": "INVALID_OFFSET", "message": f"Offset must be >= 0. Got: {offset}", "field": "offset"}}
    return None
