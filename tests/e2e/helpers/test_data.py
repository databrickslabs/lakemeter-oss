"""Test data: cloud/region configs, instance types, workload params.

All data here is used by parametrized tests across all workload types.
"""

# 6 estimate configurations: 3 clouds × 2 regions
ESTIMATE_CONFIGS = [
    {"name": "AWS US East PREMIUM", "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM"},
    {"name": "AWS EU West ENTERPRISE", "cloud": "AWS", "region": "eu-west-1", "tier": "ENTERPRISE"},
    {"name": "Azure East US PREMIUM", "cloud": "AZURE", "region": "eastus", "tier": "PREMIUM"},
    {"name": "Azure West Europe PREMIUM", "cloud": "AZURE", "region": "westeurope", "tier": "PREMIUM"},
    {"name": "GCP US Central PREMIUM", "cloud": "GCP", "region": "us-central1", "tier": "PREMIUM"},
    {"name": "GCP Europe West ENTERPRISE", "cloud": "GCP", "region": "europe-west1", "tier": "ENTERPRISE"},
]

# Instance types per cloud (driver + worker)
INSTANCE_TYPES = {
    "AWS": {
        "driver": ["i3.xlarge", "m5d.xlarge", "r5.xlarge"],
        "worker": ["i3.2xlarge", "m5d.2xlarge", "r5.2xlarge"],
    },
    "AZURE": {
        "driver": ["Standard_DS3_v2", "Standard_D4s_v3", "Standard_D16s_v3"],
        "worker": ["Standard_DS4_v2", "Standard_D8s_v3", "Standard_E8s_v3"],
    },
    "GCP": {
        "driver": ["n1-standard-4", "n2-standard-4", "n1-highmem-4"],
        "worker": ["n1-standard-8", "n2-standard-8", "n1-highmem-8"],
    },
}

# DBSQL warehouse sizes
DBSQL_WAREHOUSE_SIZES = ["2X-Small", "X-Small", "Small", "Medium", "Large", "X-Large"]

# DLT editions
DLT_EDITIONS = ["CORE", "PRO", "ADVANCED"]

# Vector search modes
VECTOR_SEARCH_MODES = ["standard", "storage_optimized"]

# Lakebase CU sizes
LAKEBASE_CU_SIZES = [0.5, 1, 2, 4, 8, 16, 32]

# GPU types for model serving
GPU_TYPES = {
    "AWS": ["gpu_small_t4", "gpu_medium_a10g_1x", "gpu_xlarge_a100_40gb_8x"],
    "AZURE": ["gpu_small_t4", "gpu_xlarge_a100_80gb_1x"],
    "GCP": ["gpu_medium_g2_standard_8"],
}

# Model Serving scale-outs
MODEL_SERVING_SCALE_OUTS = ["small", "medium", "large"]

# Usage parameter templates for run-based vs hourly
USAGE_RUN_BASED = {"runs_per_day": 5, "avg_runtime_minutes": 30, "days_per_month": 22}
USAGE_HOURLY = {"hours_per_month": 100}

# Usage parameter templates for hourly-based workloads (All-Purpose, DBSQL, etc.)
USAGE_HOURS_PER_DAY = {"hours_per_day": 8, "days_per_month": 22}
USAGE_HOURS_DIRECT = {"hours_per_month": 176}

# Serverless modes
SERVERLESS_MODES = ["standard", "performance"]

# Pricing tiers
PRICING_TIERS = ["on_demand", "1yr_reserved", "3yr_reserved"]


# Databricks Apps sizes
DATABRICKS_APPS_SIZES = ["medium", "large"]

# Clean Room collaborator counts
CLEAN_ROOM_COLLABORATORS = [1, 3, 5, 10]

# AI Parse configurations
AI_PARSE_COMPLEXITIES = ["low_text", "low_images", "medium", "high"]
AI_PARSE_PAGES = [1.0, 10.0, 50.0]  # thousands of pages

# Shutterstock image counts
SHUTTERSTOCK_IMAGE_COUNTS = [100, 500, 1000, 5000]

# Lakeflow Connect configurations
LAKEFLOW_CONNECT_EDITIONS = ["CORE", "PRO", "ADVANCED"]
LAKEFLOW_GATEWAY_INSTANCES = {
    "AWS": "i3.xlarge",
    "AZURE": "Standard_DS3_v2",
    "GCP": "n1-standard-4",
}


def config_id(config: dict) -> str:
    """Generate a short ID for a cloud/region config for test parametrization."""
    return f"{config['cloud']}-{config['region']}-{config['tier']}"
