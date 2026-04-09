#!/usr/bin/env python3
"""
Generate static pricing bundle JSON files from Lakebase reference tables.

This script queries Lakebase database and generates JSON files that the frontend
loads on app init for instant cost calculations (no runtime API calls).

Tables queried:
1. lakemeter.sync_ref_instance_dbu_rates - Instance DBU rates
2. lakemeter.sync_ref_photon_multipliers - Photon multipliers
3. lakemeter.sync_pricing_vm_costs - VM pricing
4. lakemeter.sync_product_dbu_rates - DBU pricing ($/DBU)
5. lakemeter.sync_product_dbsql_rates - DBSQL warehouse DBU rates
6. lakemeter.sync_ref_dbsql_warehouse_config - DBSQL warehouse VM config
7. lakemeter.sync_product_serverless_rates - Vector Search & Model Serving rates
8. lakemeter.sync_product_fmapi_databricks - FMAPI Databricks rates
9. lakemeter.sync_product_fmapi_proprietary - FMAPI Proprietary rates

Usage:
    python backend/scripts/generate_pricing_bundle.py
    
Output:
    backend/static/pricing/*.json
"""

import json
import os
import sys
from decimal import Decimal
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text


def decimal_default(obj):
    """JSON serializer for Decimal types."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def ensure_output_dir(output_dir: str):
    """Create output directory if it doesn't exist."""
    os.makedirs(output_dir, exist_ok=True)
    print(f"📁 Output directory: {output_dir}")


def generate_instance_dbu_rates(conn, output_dir: str):
    """
    Generate instance DBU rates from lakemeter.sync_ref_instance_dbu_rates.
    
    Output structure:
    {
        "aws": {
            "m5.xlarge": {"dbu_rate": 0.5, "vcpus": 4, "memory_gb": 16, "family": "General Purpose"},
            ...
        },
        "azure": {...},
        "gcp": {...}
    }
    """
    print("\n📊 Generating instance DBU rates...")
    
    result = conn.execute(text("""
        SELECT cloud, instance_type, dbu_rate, vcpus, memory_gb, instance_family
        FROM lakemeter.sync_ref_instance_dbu_rates
        ORDER BY cloud, instance_type
    """))
    
    data = {'aws': {}, 'azure': {}, 'gcp': {}}
    count = 0
    
    for row in result.mappings():
        cloud = row['cloud'].lower() if row['cloud'] else 'aws'
        if cloud not in data:
            data[cloud] = {}
        
        data[cloud][row['instance_type']] = {
            'dbu_rate': float(row['dbu_rate']) if row['dbu_rate'] else 0,
            'vcpus': row['vcpus'],
            'memory_gb': float(row['memory_gb']) if row['memory_gb'] else None,
            'family': row['instance_family']
        }
        count += 1
    
    output_file = os.path.join(output_dir, 'instance-dbu-rates.json')
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=decimal_default)
    
    print(f"   ✅ Generated {count} instance DBU rates")
    return count


def generate_dbu_multipliers(conn, output_dir: str):
    """
    Generate DBU multipliers from lakemeter.sync_ref_dbu_multipliers.
    
    This table contains ALL multipliers:
    - Photon multipliers (feature = 'photon')
    - Serverless multipliers (feature = 'serverless_dlt', 'serverless_jobs', 'serverless_notebook')
    - Lakebase multipliers (sku_type = 'DATABASE_SERVERLESS_COMPUTE')
    
    Output structure (photon-multipliers.json):
    {
        "aws:JOBS_COMPUTE": {"multiplier": 2.0, "category": "CLASSIC_COMPUTE", "feature": "photon"},
        "aws:ALL_PURPOSE_COMPUTE": {"multiplier": 2.0, "category": "CLASSIC_COMPUTE", "feature": "photon"},
        ...
    }
    """
    print("\n⚡ Generating DBU multipliers (photon, serverless, lakebase)...")
    
    result = conn.execute(text("""
        SELECT cloud, sku_type, feature, multiplier, category
        FROM lakemeter.sync_ref_dbu_multipliers
        ORDER BY cloud, sku_type, feature
    """))
    
    data = {}
    count = 0
    
    for row in result.mappings():
        cloud = row['cloud'].lower() if row['cloud'] else 'aws'
        feature = row['feature'] or 'unknown'
        # Create key with feature to distinguish photon vs serverless for same SKU
        key = f"{cloud}:{row['sku_type']}:{feature}"
        data[key] = {
            'multiplier': float(row['multiplier']) if row['multiplier'] else 1.0,
            'category': row['category'],
            'feature': feature
        }
        count += 1
    
    # Write to dbu-multipliers.json (renamed from photon-multipliers.json)
    output_file = os.path.join(output_dir, 'dbu-multipliers.json')
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=decimal_default)
    
    print(f"   ✅ Generated {count} DBU multipliers (photon, serverless, lakebase)")
    return count


def generate_vm_pricing(conn, output_dir: str):
    """
    Generate VM pricing from lakemeter.sync_pricing_vm_costs.
    
    Output structure:
    {
        "aws:us-east-1:m5.xlarge:on_demand:NA": 0.192,
        "aws:us-east-1:m5.xlarge:spot:NA": 0.058,
        ...
    }
    """
    print("\n💰 Generating VM pricing...")
    
    result = conn.execute(text("""
        SELECT cloud, region, instance_type, pricing_tier, payment_option, cost_per_hour
        FROM lakemeter.sync_pricing_vm_costs
        ORDER BY cloud, region, instance_type, pricing_tier
    """))
    
    data = {}
    count = 0
    
    for row in result.mappings():
        cloud = row['cloud'].lower() if row['cloud'] else 'aws'
        key = f"{cloud}:{row['region']}:{row['instance_type']}:{row['pricing_tier']}:{row['payment_option'] or 'NA'}"
        data[key] = float(row['cost_per_hour']) if row['cost_per_hour'] else 0
        count += 1
    
    output_file = os.path.join(output_dir, 'vm-costs.json')
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=decimal_default)
    
    print(f"   ✅ Generated {count} VM pricing entries")
    return count


def generate_dbu_rates(conn, output_dir: str):
    """
    Generate DBU pricing ($/DBU) from lakemeter.sync_pricing_dbu_rates.
    
    This table has both GLOBAL and REGIONAL pricing:
    - GLOBAL: applies to all regions (sku_region is null)
    - REGIONAL: specific to a region (sku_region has a value)
    
    Strategy: For each cloud/region/tier/product_type, use REGIONAL price if available,
    otherwise fall back to GLOBAL price.
    
    Output structure:
    {
        "aws:us-east-1:PREMIUM": {
            "JOBS_COMPUTE": 0.15,
            "JOBS_COMPUTE_(PHOTON)": 0.15,
            "ALL_PURPOSE_COMPUTE": 0.40,
            ...
        },
        ...
    }
    """
    print("\n💵 Generating DBU rates ($/DBU)...")
    
    # Product types we're interested in for cost calculations
    # Include both base and _(PHOTON) variants, as well as provider-specific FMAPI rates
    RELEVANT_PRODUCT_TYPES = [
        # Classic compute
        'JOBS_COMPUTE', 'JOBS_COMPUTE_(PHOTON)', 'JOBS_LIGHT_COMPUTE',
        'ALL_PURPOSE_COMPUTE', 'ALL_PURPOSE_COMPUTE_(PHOTON)', 'ALL_PURPOSE_COMPUTE_(DLT)',
        # DLT
        'DLT_CORE_COMPUTE', 'DLT_CORE_COMPUTE_(PHOTON)',
        'DLT_PRO_COMPUTE', 'DLT_PRO_COMPUTE_(PHOTON)',
        'DLT_ADVANCED_COMPUTE', 'DLT_ADVANCED_COMPUTE_(PHOTON)',
        # Serverless compute
        'JOBS_SERVERLESS_COMPUTE', 'ALL_PURPOSE_SERVERLESS_COMPUTE',
        'INTERACTIVE_SERVERLESS_COMPUTE', 'DELTA_LIVE_TABLES_SERVERLESS',
        # SQL
        'SQL_COMPUTE', 'SQL_PRO_COMPUTE', 'SERVERLESS_SQL_COMPUTE',
        # Inference/AI
        'SERVERLESS_REAL_TIME_INFERENCE', 'SERVERLESS_REAL_TIME_INFERENCE_LAUNCH',
        'MODEL_TRAINING',
        # Provider-specific FMAPI (for $/DBU lookup)
        'OPENAI_MODEL_SERVING', 'ANTHROPIC_MODEL_SERVING', 'GEMINI_MODEL_SERVING',
        # Lakebase
        'DATABASE_SERVERLESS_COMPUTE',
        # Storage
        'DATABRICKS_STORAGE'
    ]
    
    # Tiers to exclude from the bundle (deprecated tiers)
    EXCLUDED_TIERS = ['STANDARD']
    
    # Query all DBU rates (excluding deprecated tiers)
    result = conn.execute(text("""
        SELECT cloud, tier, product_type, region, pricing_type, price_per_dbu
        FROM lakemeter.sync_pricing_dbu_rates
        WHERE product_type IN :product_types
          AND tier NOT IN :excluded_tiers
        ORDER BY cloud, region, tier, product_type, pricing_type
    """), {"product_types": tuple(RELEVANT_PRODUCT_TYPES), "excluded_tiers": tuple(EXCLUDED_TIERS)})
    
    # Build a lookup: cloud -> region -> tier -> product_type -> price
    # For each combination, prefer REGIONAL over GLOBAL
    global_rates = {}  # cloud:tier:product_type -> price (global fallback)
    regional_rates = {}  # cloud:region:tier:product_type -> price (region-specific)
    
    # Also track all unique regions per cloud and all tiers per cloud
    regions_per_cloud = {}  # cloud -> set of regions
    tiers_per_cloud = {}    # cloud -> set of tiers
    
    for row in result.mappings():
        cloud = row['cloud'].lower() if row['cloud'] else 'aws'
        tier = row['tier']
        product_type = row['product_type']
        region = row['region']
        pricing_type = row['pricing_type']
        price = float(row['price_per_dbu']) if row['price_per_dbu'] else 0
        
        # Track tiers
        if cloud not in tiers_per_cloud:
            tiers_per_cloud[cloud] = set()
        tiers_per_cloud[cloud].add(tier)
        
        if pricing_type == 'GLOBAL':
            global_key = f"{cloud}:{tier}:{product_type}"
            global_rates[global_key] = price
        else:  # REGIONAL
            regional_key = f"{cloud}:{region}:{tier}:{product_type}"
            regional_rates[regional_key] = price
            # Track regions - only REGIONAL pricing_type indicates an actual Databricks control plane
            if cloud not in regions_per_cloud:
                regions_per_cloud[cloud] = set()
            regions_per_cloud[cloud].add(region)
    
    # Build output: for each cloud/region/tier, collect all product_type prices
    data = {}
    count = 0
    
    # Get all unique cloud:region:tier combinations
    # Key insight: We need to create entries for ALL tiers (including ENTERPRISE) 
    # for ALL regions, even if that tier only has GLOBAL rates
    all_keys = set()
    
    # First, add all regional combinations found directly
    for key in regional_rates.keys():
        parts = key.split(':')
        all_keys.add(f"{parts[0]}:{parts[1]}:{parts[2]}")  # cloud:region:tier
    
    # Then, for each cloud's regions, add entries for ALL tiers that cloud supports
    # This ensures ENTERPRISE tier (which may only have GLOBAL rates) gets entries for all regions
    for cloud, regions in regions_per_cloud.items():
        cloud_tiers = tiers_per_cloud.get(cloud, set())
        for region in regions:
            for tier in cloud_tiers:
                all_keys.add(f"{cloud}:{region}:{tier}")
    
    print(f"   Found {len(regions_per_cloud)} clouds with regions, {len(all_keys)} total combinations")
    
    # Build the output data
    for combo_key in sorted(all_keys):
        parts = combo_key.split(':')
        cloud, region, tier = parts[0], parts[1], parts[2]
        
        if combo_key not in data:
            data[combo_key] = {}
        
        # For each product type, get regional price or fall back to global
        for product_type in RELEVANT_PRODUCT_TYPES:
            regional_key = f"{cloud}:{region}:{tier}:{product_type}"
            global_key = f"{cloud}:{tier}:{product_type}"
            
            if regional_key in regional_rates:
                data[combo_key][product_type] = regional_rates[regional_key]
                count += 1
            elif global_key in global_rates:
                data[combo_key][product_type] = global_rates[global_key]
                count += 1
    
    output_file = os.path.join(output_dir, 'dbu-rates.json')
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=decimal_default)
    
    print(f"   ✅ Generated {count} DBU rate entries across {len(data)} cloud/region/tier combinations")
    return count


def generate_dbsql_rates(conn, output_dir: str):
    """
    Generate DBSQL warehouse DBU rates from lakemeter.sync_product_dbsql_rates.
    
    Output structure:
    {
        "aws:classic:Medium": {"dbu_per_hour": 24, "sku_product_type": "SQL_COMPUTE"},
        "aws:pro:Medium": {"dbu_per_hour": 24, "sku_product_type": "SQL_PRO_COMPUTE"},
        "aws:serverless:Medium": {"dbu_per_hour": 24, "sku_product_type": "SERVERLESS_SQL_COMPUTE"},
        ...
    }
    """
    print("\n🗄️ Generating DBSQL warehouse rates...")
    
    result = conn.execute(text("""
        SELECT cloud, warehouse_type, warehouse_size, sku_product_type, dbu_per_hour, includes_compute
        FROM lakemeter.sync_product_dbsql_rates
        ORDER BY cloud, warehouse_type, warehouse_size
    """))
    
    data = {}
    count = 0
    
    for row in result.mappings():
        cloud = row['cloud'].lower() if row['cloud'] else 'aws'
        key = f"{cloud}:{row['warehouse_type']}:{row['warehouse_size']}"
        data[key] = {
            'dbu_per_hour': float(row['dbu_per_hour']) if row['dbu_per_hour'] else 0,
            'sku_product_type': row['sku_product_type'],
            'includes_compute': row['includes_compute']
        }
        count += 1
    
    output_file = os.path.join(output_dir, 'dbsql-rates.json')
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=decimal_default)
    
    print(f"   ✅ Generated {count} DBSQL rate entries")
    return count


def generate_dbsql_warehouse_config(conn, output_dir: str):
    """
    Generate DBSQL warehouse VM config from lakemeter.sync_ref_dbsql_warehouse_config.
    
    Output structure:
    {
        "aws:classic:2X-Large": {
            "driver_count": 1,
            "driver_instance_type": "i3.16xlarge",
            "worker_count": 64,
            "worker_instance_type": "i3.2xlarge"
        },
        ...
    }
    """
    print("\n🖥️ Generating DBSQL warehouse config...")
    
    result = conn.execute(text("""
        SELECT cloud, warehouse_type, warehouse_size, 
               driver_count, driver_instance_type,
               worker_count, worker_instance_type
        FROM lakemeter.sync_ref_dbsql_warehouse_config
        ORDER BY cloud, warehouse_type, warehouse_size
    """))
    
    data = {}
    count = 0
    
    for row in result.mappings():
        cloud = row['cloud'].lower() if row['cloud'] else 'aws'
        key = f"{cloud}:{row['warehouse_type']}:{row['warehouse_size']}"
        data[key] = {
            'driver_count': row['driver_count'] or 1,
            'driver_instance_type': row['driver_instance_type'],
            'worker_count': row['worker_count'] or 0,
            'worker_instance_type': row['worker_instance_type']
        }
        count += 1
    
    output_file = os.path.join(output_dir, 'dbsql-warehouse-config.json')
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=decimal_default)
    
    print(f"   ✅ Generated {count} DBSQL warehouse configs")
    return count


def generate_vector_search_rates(conn, output_dir: str):
    """
    Generate Vector Search rates from lakemeter.sync_product_serverless_rates.
    
    Output structure:
    {
        "aws:standard": {"dbu_rate": 4, "input_divisor": 2000000, "sku_product_type": "..."},
        "aws:storage_optimized": {"dbu_rate": 18.29, "input_divisor": 64000000, "sku_product_type": "..."},
        ...
    }
    """
    print("\n🔍 Generating Vector Search rates...")
    
    result = conn.execute(text("""
        SELECT cloud, size_or_model as mode, dbu_rate, input_divisor, sku_product_type, description
        FROM lakemeter.sync_product_serverless_rates
        WHERE product = 'vector_search'
        ORDER BY cloud, size_or_model
    """))
    
    data = {}
    count = 0
    
    for row in result.mappings():
        cloud = row['cloud'].lower() if row['cloud'] else 'aws'
        key = f"{cloud}:{row['mode']}"
        data[key] = {
            'dbu_rate': float(row['dbu_rate']) if row['dbu_rate'] else 0,
            'input_divisor': int(row['input_divisor']) if row['input_divisor'] else 1,
            'sku_product_type': row['sku_product_type'],
            'description': row['description']
        }
        count += 1
    
    output_file = os.path.join(output_dir, 'vector-search-rates.json')
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=decimal_default)
    
    print(f"   ✅ Generated {count} Vector Search rate entries")
    return count


def generate_model_serving_rates(conn, output_dir: str):
    """
    Generate Model Serving GPU rates from lakemeter.sync_product_serverless_rates.
    
    Output structure:
    {
        "aws:cpu": {"dbu_rate": 1, "sku_product_type": "...", "description": "..."},
        "aws:gpu_small_t4": {"dbu_rate": 10.48, "sku_product_type": "...", "description": "..."},
        ...
    }
    """
    print("\n🤖 Generating Model Serving GPU rates...")
    
    result = conn.execute(text("""
        SELECT cloud, size_or_model as gpu_type, dbu_rate, sku_product_type, description
        FROM lakemeter.sync_product_serverless_rates
        WHERE product = 'model_serving'
        ORDER BY cloud, size_or_model
    """))
    
    data = {}
    count = 0
    
    for row in result.mappings():
        cloud = row['cloud'].lower() if row['cloud'] else 'aws'
        key = f"{cloud}:{row['gpu_type']}"
        data[key] = {
            'dbu_rate': float(row['dbu_rate']) if row['dbu_rate'] else 0,
            'sku_product_type': row['sku_product_type'],
            'description': row['description']
        }
        count += 1
    
    output_file = os.path.join(output_dir, 'model-serving-rates.json')
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=decimal_default)
    
    print(f"   ✅ Generated {count} Model Serving rate entries")
    return count


def generate_fmapi_databricks_rates(conn, output_dir: str):
    """
    Generate FMAPI Databricks rates from lakemeter.sync_product_fmapi_databricks.
    
    Output structure:
    {
        "aws:llama-3-3-70b:input_token": {"dbu_rate": 1.0, "input_divisor": 1000000, "is_hourly": false},
        "aws:llama-3-3-70b:output_token": {"dbu_rate": 3.0, "input_divisor": 1000000, "is_hourly": false},
        "aws:llama-3-3-70b:provisioned_scaling": {"dbu_rate": 200, "is_hourly": true},
        ...
    }
    """
    print("\n🧠 Generating FMAPI Databricks rates...")
    
    result = conn.execute(text("""
        SELECT cloud, model, rate_type, dbu_rate, input_divisor, is_hourly, sku_product_type
        FROM lakemeter.sync_product_fmapi_databricks
        ORDER BY cloud, model, rate_type
    """))
    
    data = {}
    count = 0
    
    for row in result.mappings():
        cloud = row['cloud'].lower() if row['cloud'] else 'aws'
        key = f"{cloud}:{row['model']}:{row['rate_type']}"
        data[key] = {
            'dbu_rate': float(row['dbu_rate']) if row['dbu_rate'] else 0,
            'input_divisor': int(row['input_divisor']) if row['input_divisor'] else 1000000,
            'is_hourly': row['is_hourly'] or False,
            'sku_product_type': row['sku_product_type']
        }
        count += 1
    
    output_file = os.path.join(output_dir, 'fmapi-databricks-rates.json')
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=decimal_default)
    
    print(f"   ✅ Generated {count} FMAPI Databricks rate entries")
    return count


def generate_fmapi_proprietary_rates(conn, output_dir: str):
    """
    Generate FMAPI Proprietary rates from lakemeter.sync_product_fmapi_proprietary.
    
    Output structure:
    {
        "aws:anthropic:claude-sonnet-4-5:global:all:input_token": {"dbu_rate": 14.29, "input_divisor": 1000000},
        "aws:openai:gpt-4o:in_geo:all:output_token": {"dbu_rate": 21.43, "input_divisor": 1000000},
        ...
    }
    """
    print("\n🏢 Generating FMAPI Proprietary rates...")
    
    result = conn.execute(text("""
        SELECT cloud, provider, model, endpoint_type, context_length, 
               rate_type, dbu_rate, input_divisor, is_hourly, sku_product_type
        FROM lakemeter.sync_product_fmapi_proprietary
        ORDER BY cloud, provider, model, endpoint_type, context_length, rate_type
    """))
    
    data = {}
    count = 0
    
    for row in result.mappings():
        cloud = row['cloud'].lower() if row['cloud'] else 'aws'
        key = f"{cloud}:{row['provider']}:{row['model']}:{row['endpoint_type']}:{row['context_length']}:{row['rate_type']}"
        data[key] = {
            'dbu_rate': float(row['dbu_rate']) if row['dbu_rate'] else 0,
            'input_divisor': int(row['input_divisor']) if row['input_divisor'] else 1000000,
            'is_hourly': row['is_hourly'] or False,
            'sku_product_type': row['sku_product_type']
        }
        count += 1
    
    output_file = os.path.join(output_dir, 'fmapi-proprietary-rates.json')
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=decimal_default)
    
    print(f"   ✅ Generated {count} FMAPI Proprietary rate entries")
    return count


def generate_all_pricing_bundles():
    """Main function to generate all pricing bundle files."""
    print("=" * 60)
    print("🚀 Lakemeter Pricing Bundle Generator")
    print("=" * 60)
    
    # Import here to avoid circular imports
    from app.database import engine
    
    if engine is None:
        print("❌ Database engine not available. Please check database connection.")
        sys.exit(1)
    
    # Output directory
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'static', 'pricing'
    )
    ensure_output_dir(output_dir)
    
    total_count = 0
    
    with engine.connect() as conn:
        # Generate all pricing files
        total_count += generate_instance_dbu_rates(conn, output_dir)
        total_count += generate_dbu_multipliers(conn, output_dir)
        # NOTE: Skipping vm-costs.json - too large (50+ MB). VM costs are fetched on-demand per instance.
        # total_count += generate_vm_pricing(conn, output_dir)
        total_count += generate_dbu_rates(conn, output_dir)
        total_count += generate_dbsql_rates(conn, output_dir)
        total_count += generate_dbsql_warehouse_config(conn, output_dir)
        total_count += generate_vector_search_rates(conn, output_dir)
        total_count += generate_model_serving_rates(conn, output_dir)
        total_count += generate_fmapi_databricks_rates(conn, output_dir)
        total_count += generate_fmapi_proprietary_rates(conn, output_dir)
    
    print("\n" + "=" * 60)
    print(f"✅ Generated {total_count} total pricing entries")
    print(f"📁 Output: {output_dir}")
    print("=" * 60)
    
    # Generate a manifest file with metadata
    # NOTE: vm-costs.json excluded - too large, fetched on-demand per instance instead
    manifest = {
        'generated_at': datetime.now().isoformat(),
        'total_entries': total_count,
        'files': [
            'instance-dbu-rates.json',
            'dbu-multipliers.json',
            'dbu-rates.json',
            'dbsql-rates.json',
            'dbsql-warehouse-config.json',
            'vector-search-rates.json',
            'model-serving-rates.json',
            'fmapi-databricks-rates.json',
            'fmapi-proprietary-rates.json'
        ]
    }
    
    manifest_file = os.path.join(output_dir, 'manifest.json')
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n📋 Manifest written to: {manifest_file}")


if __name__ == '__main__':
    generate_all_pricing_bundles()

