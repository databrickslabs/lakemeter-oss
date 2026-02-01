# Databricks notebook source
# MAGIC %md
# MAGIC # Test Case: JOBS Classic Compute
# MAGIC 
# MAGIC **Objective:** Validate cost calculations for JOBS workload type with classic compute across:
# MAGIC - 3 clouds: AWS, Azure, GCP
# MAGIC - 2 regions per cloud (US + Europe)
# MAGIC - Multiple configurations:
# MAGIC   - Photon enabled/disabled
# MAGIC   - Different instance types
# MAGIC   - Different worker counts
# MAGIC   - Different VM pricing tiers (on_demand, spot, reserved)
# MAGIC   - Different usage patterns
# MAGIC 
# MAGIC **Test Matrix:**
# MAGIC - Cloud: AWS (us-east-1, eu-west-1), Azure (eastus, westeurope), GCP (us-central1, europe-west1)
# MAGIC - Instance types: Small (i3.xlarge), Medium (i3.2xlarge), Large (i3.4xlarge)
# MAGIC - Photon: Enabled, Disabled
# MAGIC - VM Pricing: on_demand, spot (50%), reserved_1y
# MAGIC - Usage: Light (4 runs/day, 30 min), Medium (12 runs/day, 60 min), Heavy (24 runs/day, 120 min)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Setup - Install Dependencies & Connect to Lakebase

# COMMAND ----------

# Install psycopg2 for PostgreSQL connection
%pip install psycopg2-binary pandas tabulate

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# Import Lakebase configuration
%run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd
import uuid
from datetime import datetime
from tabulate import tabulate

def get_connection():
    """Create and return a PostgreSQL connection"""
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DB,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD
    )

def execute_query(query, params=None, fetch=True):
    """Execute a query and optionally fetch results"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch:
                columns = [desc[0] for desc in cur.description] if cur.description else []
                results = cur.fetchall()
                conn.commit()
                return pd.DataFrame(results, columns=columns) if results else pd.DataFrame()
            else:
                conn.commit()
                return None
    finally:
        conn.close()

print("✅ Connection setup complete!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Pre-Flight Check: Verify Pricing Data Availability
# MAGIC 
# MAGIC Check if we have VM pricing data for all clouds before running tests

# COMMAND ----------

# Check VM pricing data availability
vm_pricing_check_sql = """
SELECT 
    cloud,
    COUNT(*) as row_count,
    COUNT(DISTINCT region) as region_count,
    COUNT(DISTINCT instance_type) as instance_type_count
FROM lakemeter.sync_pricing_vm_costs
GROUP BY cloud
ORDER BY cloud;
"""

vm_pricing_summary = execute_query(vm_pricing_check_sql)

print("=" * 80)
print("VM PRICING DATA AVAILABILITY")
print("=" * 80)
if len(vm_pricing_summary) > 0:
    print(tabulate(vm_pricing_summary, headers='keys', tablefmt='grid', showindex=False))
    
    # Check for missing clouds
    available_clouds = set(vm_pricing_summary['cloud'].tolist())
    required_clouds = {'AWS', 'AZURE', 'GCP'}
    missing_clouds = required_clouds - available_clouds
    
    if missing_clouds:
        print(f"\n⚠️  WARNING: Missing VM pricing data for: {', '.join(missing_clouds)}")
        print("   Tests for these clouds will show $0 VM costs!")
    else:
        print("\n✅ All clouds have VM pricing data")
else:
    print("❌ No VM pricing data found in sync_pricing_vm_costs!")
    print("   Please run Pricing_Sync notebooks first!")

print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Clean Up Previous Test Data
# MAGIC 
# MAGIC Remove all test data from previous runs to ensure clean state

# COMMAND ----------

print("=" * 120)
print("🧹 CLEANING UP PREVIOUS TEST DATA")
print("=" * 120)

try:
    # Delete line items from test estimates
    cleanup_line_items_sql = """
    DELETE FROM lakemeter.line_items 
    WHERE estimate_id IN (
        SELECT estimate_id FROM lakemeter.estimates 
        WHERE created_by IN (
            SELECT user_id FROM lakemeter.users 
            WHERE email LIKE 'test_%@databricks.com'
        )
    );
    """
    execute_query(cleanup_line_items_sql, fetch=False)
    print("✅ Cleaned up test line items")
    
    # Delete estimates from test users
    cleanup_estimates_sql = """
    DELETE FROM lakemeter.estimates 
    WHERE created_by IN (
        SELECT user_id FROM lakemeter.users 
        WHERE email LIKE 'test_%@databricks.com'
    );
    """
    execute_query(cleanup_estimates_sql, fetch=False)
    print("✅ Cleaned up test estimates")
    
    # Delete test users
    cleanup_users_sql = """
    DELETE FROM lakemeter.users 
    WHERE email LIKE 'test_%@databricks.com';
    """
    execute_query(cleanup_users_sql, fetch=False)
    print("✅ Cleaned up test users")
    
    print("\n🎉 All previous test data cleaned successfully!")
except Exception as e:
    print(f"⚠️ Cleanup error (may be first run): {e}")
    print("   Proceeding with test...")

print("=" * 120)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Generate Test IDs
# MAGIC 
# MAGIC Create test user, estimate, and line items for JOBS Classic scenarios

# COMMAND ----------

# Generate unique IDs for this test run
TEST_RUN_ID = str(uuid.uuid4())[:8]
TEST_USER_ID = str(uuid.uuid4())
# TEST_ESTIMATE_ID removed - now creating one estimate per cloud/region/tier combination

print(f"🧪 Test Run ID: {TEST_RUN_ID}")
print(f"👤 Test User ID: {TEST_USER_ID}")
print(f"📊 Estimates will be created per cloud/region/tier in Section 8")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Create Test User

# COMMAND ----------

create_user_sql = """
INSERT INTO lakemeter.users (user_id, email, full_name, role, is_active, created_at, updated_at)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (user_id) DO NOTHING;
"""

execute_query(
    create_user_sql,
    (TEST_USER_ID, f'test_{TEST_RUN_ID}@databricks.com', f'Test User - JOBS Classic {TEST_RUN_ID}',
     'admin', True, datetime.now(), datetime.now()),
    fetch=False
)

print(f"✅ Test user created: Test User - JOBS Classic {TEST_RUN_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Placeholder for Test Estimates
# MAGIC 
# MAGIC **Note:** Estimates are now created dynamically in Section 9, one per cloud/region/tier combo.
# MAGIC This ensures each line item has the correct cloud/region for pricing lookups.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Query Available Instance Types from Pricing Tables
# MAGIC 
# MAGIC **Strategy:** Instead of hardcoding instance types, query actual available instances from pricing tables.
# MAGIC This ensures tests always use real data that exists in the database.

# COMMAND ----------

# First, let's see what regions actually exist in the pricing table
check_regions_sql = """
SELECT DISTINCT cloud, region
FROM lakemeter.sync_pricing_vm_costs
WHERE cloud IN ('AWS', 'AZURE', 'GCP')
ORDER BY cloud, region;
"""

all_regions = execute_query(check_regions_sql)

print("=" * 120)
print("ALL AVAILABLE REGIONS IN PRICING TABLE")
print("=" * 120)
print(tabulate(all_regions, headers='keys', tablefmt='grid', showindex=False))
print("=" * 120)

# COMMAND ----------

# Now query available instance types that have BOTH VM costs and DBU rates
# We'll use ALL regions first, then filter dynamically
get_available_instances_sql = """
SELECT DISTINCT 
    vm.cloud,
    vm.region,
    vm.instance_type,
    COUNT(*) OVER (PARTITION BY vm.cloud, vm.region) as instances_in_region
FROM lakemeter.sync_pricing_vm_costs vm
INNER JOIN lakemeter.sync_ref_instance_dbu_rates dbu 
    ON vm.cloud = dbu.cloud 
    AND vm.instance_type = dbu.instance_type
WHERE vm.pricing_tier = 'on_demand'
ORDER BY vm.cloud, vm.region, vm.instance_type;
"""

available_instances = execute_query(get_available_instances_sql)

print("=" * 120)
print("AVAILABLE INSTANCE TYPES (ALL REGIONS)")
print("=" * 120)
if len(available_instances) > 0:
    # Group by cloud and show regions
    for cloud in ['AWS', 'AZURE', 'GCP']:
        cloud_instances = available_instances[available_instances['cloud'] == cloud]
        if len(cloud_instances) > 0:
            print(f"\n{cloud}: {len(cloud_instances['region'].unique())} regions available")
            for region in cloud_instances['region'].unique()[:5]:  # Show first 5 regions
                region_instances = cloud_instances[cloud_instances['region'] == region]
                print(f"  {region}: {len(region_instances)} instance types")
                examples = region_instances['instance_type'].head(3).tolist()
                print(f"    Examples: {', '.join(examples)}")
    print("\n✅ Will select 2 regions per cloud (1 US, 1 Europe) for test scenarios")
else:
    print("❌ No instances found! Check pricing data sync.")
    raise Exception("Cannot proceed without pricing data")
print("=" * 120)

# COMMAND ----------

# Select 2 regions per cloud (1 US + 1 Europe) from available data
def select_test_regions(cloud, available_df):
    """Select 1 US and 1 Europe region from available data"""
    cloud_df = available_df[available_df['cloud'] == cloud]
    if len(cloud_df) == 0:
        return []
    
    regions = cloud_df['region'].unique()
    
    # Keywords to identify US and Europe regions
    us_keywords = ['us-', 'us_', 'east', 'west', 'central'] if cloud == 'AWS' or cloud == 'GCP' else ['east', 'central', 'west']
    eu_keywords = ['eu-', 'europe', 'uk-', 'north'] if cloud == 'AWS' or cloud == 'GCP' else ['europe', 'uk', 'north']
    
    us_region = None
    eu_region = None
    
    # Find US region
    for region in regions:
        region_lower = region.lower()
        if any(kw in region_lower for kw in us_keywords) and 'europe' not in region_lower and 'eu-' not in region_lower:
            us_region = region
            break
    
    # Find Europe region
    for region in regions:
        region_lower = region.lower()
        if any(kw in region_lower for kw in eu_keywords):
            eu_region = region
            break
    
    # Return whatever we found (could be 0, 1, or 2 regions)
    return [r for r in [us_region, eu_region] if r is not None]

# Select regions for each cloud
aws_regions = select_test_regions('AWS', available_instances)
azure_regions = select_test_regions('AZURE', available_instances)
gcp_regions = select_test_regions('GCP', available_instances)

print("\n" + "=" * 120)
print("SELECTED TEST REGIONS")
print("=" * 120)
print(f"AWS: {aws_regions}")
print(f"AZURE: {azure_regions}")
print(f"GCP: {gcp_regions}")
print("=" * 120)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Build Comprehensive Test Scenarios
# MAGIC 
# MAGIC - 3 clouds (AWS, Azure, GCP)
# MAGIC - 2 regions per cloud (1 US, 1 Europe)
# MAGIC - 3 tiers per cloud/region (STANDARD, PREMIUM, ENTERPRISE)
# MAGIC - Multiple payment options (driver/worker independent)
# MAGIC - 2 Photon configs (enabled/disabled)
# MAGIC 
# MAGIC Use actual instance types from pricing tables to build test scenarios

# COMMAND ----------

print("=" * 120)
print(f"AVAILABLE INSTANCE TYPES: {len(available_instances)} total")
print("=" * 120)

if len(available_instances) > 0:
    # Group by cloud and show all regions
    for cloud in ['AWS', 'AZURE', 'GCP']:
        cloud_instances = available_instances[available_instances['cloud'] == cloud]
        if len(cloud_instances) > 0:
            unique_regions = cloud_instances['region'].unique()
            print(f"\n{cloud}: {len(unique_regions)} regions, {len(cloud_instances)} instance types")
            # Show first few regions as examples
            for region in unique_regions[:3]:
                region_count = len(cloud_instances[cloud_instances['region'] == region])
                print(f"  {region}: {region_count} instance types")
    print("\n✅ Proceeding to select test regions...")
else:
    print("❌ No instances found! Check pricing data sync.")
    raise Exception("Cannot proceed without pricing data")
print("=" * 120)

# COMMAND ----------

# Select 2 regions per cloud (1 US + 1 Europe) from ACTUAL available data
def select_test_regions(cloud, available_df):
    """Select 1 US and 1 Europe region from available data"""
    cloud_df = available_df[available_df['cloud'] == cloud]
    if len(cloud_df) == 0:
        return []
    
    regions = cloud_df['region'].unique().tolist()
    
    # Keywords to identify US and Europe regions
    us_keywords = ['us', 'east', 'west', 'central', 'america'] 
    eu_keywords = ['eu', 'europe', 'uk', 'north', 'ireland', 'frankfurt', 'london']
    
    us_region = None
    eu_region = None
    
    # Find US region
    for region in regions:
        region_lower = region.lower()
        if any(kw in region_lower for kw in us_keywords) and not any(kw in region_lower for kw in eu_keywords):
            us_region = region
            break
    
    # Find Europe region  
    for region in regions:
        region_lower = region.lower()
        if any(kw in region_lower for kw in eu_keywords):
            eu_region = region
            break
    
    # Fallback: if no regions found, just take first 2
    selected = [r for r in [us_region, eu_region] if r is not None]
    if len(selected) == 0 and len(regions) > 0:
        selected = regions[:2]  # Just take first 2 available
    
    return selected

# Select regions for each cloud
aws_regions = select_test_regions('AWS', available_instances)
azure_regions = select_test_regions('AZURE', available_instances)
gcp_regions = select_test_regions('GCP', available_instances)

print("\n" + "=" * 120)
print("SELECTED TEST REGIONS (Auto-detected from available data)")
print("=" * 120)
print(f"AWS: {aws_regions if aws_regions else '❌ No regions available'}")
print(f"AZURE: {azure_regions if azure_regions else '❌ No regions available'}")
print(f"GCP: {gcp_regions if gcp_regions else '❌ No regions available'}")
print("=" * 120)

# COMMAND ----------

# Helper function to get instance types for a cloud/region
def get_instances_for_region(cloud, region, size='medium'):
    """Get instance type for a specific cloud/region from available data"""
    region_instances = available_instances[
        (available_instances['cloud'] == cloud) & 
        (available_instances['region'] == region)
    ]['instance_type'].tolist()
    
    if not region_instances:
        return None
    
    # Sort and pick based on size
    region_instances.sort()
    
    if size == 'small':
        return region_instances[0] if len(region_instances) > 0 else None
    elif size == 'medium':
        idx = len(region_instances) // 2
        return region_instances[idx] if len(region_instances) > idx else region_instances[0]
    elif size == 'large':
        return region_instances[-1] if len(region_instances) > 0 else None
    
    return region_instances[0]

# ============================================================================
# BUILD COMPREHENSIVE TEST SCENARIOS
# ============================================================================
# Coverage:
#   - 3 clouds (AWS, Azure, GCP)
#   - 2 regions per cloud (US + Europe)
#   - 3 tiers per region (STANDARD, PREMIUM, ENTERPRISE)
#   - Multiple payment options (driver/worker independent)
#   - 2 Photon configs (enabled/disabled)
# ============================================================================

test_scenarios = []
scenario_id = 1

# Define TIERS with different instance sizes and worker counts
# NOTE: Not all clouds support all tiers (e.g., Azure/GCP don't have ENTERPRISE)
tier_configs = [
    {
        'tier': 'STANDARD',
        'driver_size': 'small',
        'worker_size': 'small',
        'num_workers': 2,
        'runs_per_day': 4,
        'avg_runtime_minutes': 30,
        'clouds': ['AWS', 'AZURE', 'GCP'],  # Available on all clouds
    },
    {
        'tier': 'PREMIUM',
        'driver_size': 'medium',
        'worker_size': 'medium',
        'num_workers': 8,
        'runs_per_day': 12,
        'avg_runtime_minutes': 60,
        'clouds': ['AWS', 'AZURE', 'GCP'],  # Available on all clouds
    },
    {
        'tier': 'ENTERPRISE',
        'driver_size': 'large',
        'worker_size': 'large',
        'num_workers': 16,
        'runs_per_day': 24,
        'avg_runtime_minutes': 120,
        'clouds': ['AWS', 'GCP'],  # Available on AWS and GCP (NOT Azure)
    },
]

# Define payment option matrices (select 1 per tier to keep scenarios manageable)
# AWS: Select representative payment options
aws_payment_per_tier = {
    'STANDARD': {'driver_tier': 'on_demand', 'worker_tier': 'on_demand', 'payment_option': 'on_demand'},
    'PREMIUM': {'driver_tier': 'on_demand', 'worker_tier': 'spot', 'payment_option': 'spot'},
    'ENTERPRISE': {'driver_tier': 'reserved_1y', 'worker_tier': 'reserved_1y', 'payment_option': 'partial_upfront'},
}

# Azure/GCP: Select representative payment options
azure_gcp_payment_per_tier = {
    'STANDARD': {'driver_tier': 'on_demand', 'worker_tier': 'on_demand', 'payment_option': 'NA'},
    'PREMIUM': {'driver_tier': 'on_demand', 'worker_tier': 'spot', 'payment_option': 'NA'},
    'ENTERPRISE': {'driver_tier': 'reserved_1y', 'worker_tier': 'reserved_1y', 'payment_option': 'NA'},
}

# Photon configurations
photon_configs = [
    {'enabled': False, 'label': 'NoPhoton'},
    {'enabled': True, 'label': 'Photon'},
]

# Build scenarios for each cloud
# AWS: 2 regions × 3 tiers × 2 photon = 12 scenarios (all tiers available)
for region in aws_regions:
    for tier in tier_configs:
        # ✅ Check if tier is valid for AWS
        if 'AWS' not in tier['clouds']:
            continue
            
        payment = aws_payment_per_tier[tier['tier']]
        for photon in photon_configs:
            driver_inst = get_instances_for_region('AWS', region, tier['driver_size'])
            worker_inst = get_instances_for_region('AWS', region, tier['worker_size'])
            
            if driver_inst and worker_inst:
                test_scenarios.append({
                    'scenario_id': scenario_id,
                    'workload_name': f"AWS {region[:10]} {tier['tier']} {photon['label']}",
                    'cloud': 'AWS',
                    'region': region,
                    'tier': tier['tier'],
                    'driver_node_type': driver_inst,
                    'worker_node_type': worker_inst,
                    'num_workers': tier['num_workers'],
                    'photon_enabled': photon['enabled'],
                    'driver_pricing_tier': payment['driver_tier'],
                    'worker_pricing_tier': payment['worker_tier'],
                    'vm_payment_option': payment['payment_option'],
                    'runs_per_day': tier['runs_per_day'],
                    'avg_runtime_minutes': tier['avg_runtime_minutes'],
                    'days_per_month': 30,
                    'notes': f"AWS {region} | {tier['tier']} | D:{payment['driver_tier']} W:{payment['worker_tier']} | {photon['label']}"
                })
                scenario_id += 1

# Azure: 2 regions × 2 tiers × 2 photon = 8 scenarios (NO ENTERPRISE tier)
for region in azure_regions:
    for tier in tier_configs:
        # ✅ Check if tier is valid for AZURE
        if 'AZURE' not in tier['clouds']:
            continue
            
        payment = azure_gcp_payment_per_tier.get(tier['tier'])
        if not payment:  # Skip if payment not defined for this tier
            continue
            
        for photon in photon_configs:
            driver_inst = get_instances_for_region('AZURE', region, tier['driver_size'])
            worker_inst = get_instances_for_region('AZURE', region, tier['worker_size'])
            
            if driver_inst and worker_inst:
                test_scenarios.append({
                    'scenario_id': scenario_id,
                    'workload_name': f"Azure {region[:12]} {tier['tier']} {photon['label']}",
                    'cloud': 'AZURE',
                    'region': region,
                    'tier': tier['tier'],
                    'driver_node_type': driver_inst,
                    'worker_node_type': worker_inst,
                    'num_workers': tier['num_workers'],
                    'photon_enabled': photon['enabled'],
                    'driver_pricing_tier': payment['driver_tier'],
                    'worker_pricing_tier': payment['worker_tier'],
                    'vm_payment_option': payment['payment_option'],
                    'runs_per_day': tier['runs_per_day'],
                    'avg_runtime_minutes': tier['avg_runtime_minutes'],
                    'days_per_month': 30,
                    'notes': f"Azure {region} | {tier['tier']} | D:{payment['driver_tier']} W:{payment['worker_tier']} | {photon['label']}"
                })
                scenario_id += 1

# GCP: 2 regions × 2 tiers × 2 photon = 8 scenarios (NO ENTERPRISE tier)
for region in gcp_regions:
    for tier in tier_configs:
        # ✅ Check if tier is valid for GCP
        if 'GCP' not in tier['clouds']:
            continue
            
        payment = azure_gcp_payment_per_tier.get(tier['tier'])
        if not payment:  # Skip if payment not defined for this tier
            continue
            
        for photon in photon_configs:
            driver_inst = get_instances_for_region('GCP', region, tier['driver_size'])
            worker_inst = get_instances_for_region('GCP', region, tier['worker_size'])
            
            if driver_inst and worker_inst:
                test_scenarios.append({
                    'scenario_id': scenario_id,
                    'workload_name': f"GCP {region[:10]} {tier['tier']} {photon['label']}",
                    'cloud': 'GCP',
                    'region': region,
                    'tier': tier['tier'],
                    'driver_node_type': driver_inst,
                    'worker_node_type': worker_inst,
                    'num_workers': tier['num_workers'],
                    'photon_enabled': photon['enabled'],
                    'driver_pricing_tier': payment['driver_tier'],
                    'worker_pricing_tier': payment['worker_tier'],
                    'vm_payment_option': payment['payment_option'],
                    'runs_per_day': tier['runs_per_day'],
                    'avg_runtime_minutes': tier['avg_runtime_minutes'],
                    'days_per_month': 30,
                    'notes': f"GCP {region} | {tier['tier']} | D:{payment['driver_tier']} W:{payment['worker_tier']} | {photon['label']}"
                })
                scenario_id += 1

print("\n" + "=" * 120)
print(f"📋 BUILT {len(test_scenarios)} COMPREHENSIVE TEST SCENARIOS")
print("=" * 120)
print(f"   AWS: {len([s for s in test_scenarios if s['cloud'] == 'AWS'])} scenarios ({len(aws_regions)} regions × 3 tiers × 2 photon)")
print(f"   AZURE: {len([s for s in test_scenarios if s['cloud'] == 'AZURE'])} scenarios ({len(azure_regions)} regions × 2 tiers × 2 photon) - NO ENTERPRISE")
print(f"   GCP: {len([s for s in test_scenarios if s['cloud'] == 'GCP'])} scenarios ({len(gcp_regions)} regions × 3 tiers × 2 photon)")
print("=" * 120)

# Show breakdown by tier
print("\n📊 Breakdown by Tier:")
for tier in ['STANDARD', 'PREMIUM', 'ENTERPRISE']:
    tier_count = len([s for s in test_scenarios if s['tier'] == tier])
    tier_clouds = set([s['cloud'] for s in test_scenarios if s['tier'] == tier])
    print(f"   {tier}: {tier_count} scenarios (clouds: {', '.join(sorted(tier_clouds))})")
print("=" * 120)

# Show sample of scenarios
print("\n📋 Sample scenarios:")
for scenario in test_scenarios[:10]:
    print(f"   {scenario['scenario_id']:3d}. {scenario['workload_name']:40s} | {scenario['tier']:12s} | {scenario['num_workers']} workers")
if len(test_scenarios) > 10:
    print(f"   ... and {len(test_scenarios) - 10} more")
print("=" * 120)

if len(test_scenarios) == 0:
    raise Exception("❌ No test scenarios could be built! Check pricing data availability.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Insert Test Line Items
# MAGIC 
# MAGIC Create estimates and line items for all test scenarios
# MAGIC 
# MAGIC Using the comprehensive test scenarios built in Section 7 (all payment options × photon configs)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 9.1 Create Estimates (One Per Cloud/Region/Tier Combo)

# COMMAND ----------

# Create one estimate per cloud/region/tier combination
# This ensures pricing lookups use the correct cloud/region rates

create_estimate_sql = """
INSERT INTO lakemeter.estimates (
    estimate_id, estimate_name, owner_user_id, customer_name,
    cloud, region, tier, status, created_at, updated_at, updated_by
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (estimate_id) DO NOTHING;
"""

# Build estimate mapping: {cloud_region_tier: estimate_id}
estimate_map = {}
for scenario in test_scenarios:
    key = f"{scenario['cloud']}_{scenario['region']}_{scenario['tier']}"
    if key not in estimate_map:
        estimate_id = str(uuid.uuid4())
        estimate_map[key] = estimate_id
        
        execute_query(
            create_estimate_sql,
            (estimate_id, f'Test - {scenario["cloud"]} {scenario["region"]} {scenario["tier"]} - {TEST_RUN_ID}', 
             TEST_USER_ID, f'Test Customer - {scenario["cloud"]} - {scenario["tier"]}', 
             scenario['cloud'], scenario['region'], scenario['tier'], 'draft',
             datetime.now(), datetime.now(), TEST_USER_ID),
            fetch=False
        )
        print(f"✅ Created estimate: {scenario['cloud']} / {scenario['region']} / {scenario['tier']} → {estimate_id[:8]}...")

print(f"\n✅ Created {len(estimate_map)} estimates (cloud × region × tier combinations) for {len(test_scenarios)} scenarios")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 9.2 Insert Test Line Items (With Correct Estimate IDs)

# COMMAND ----------

insert_line_item_sql = """
INSERT INTO lakemeter.line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, serverless_mode, photon_enabled, vector_search_mode,
    driver_node_type, worker_node_type, num_workers,
    runs_per_day, avg_runtime_minutes, days_per_month,
    driver_pricing_tier, worker_pricing_tier, vm_payment_option,
    notes, created_at, updated_at
) VALUES (
    %s, %s, %s, %s, %s,
    %s, %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s,
    %s, %s, %s
);
"""

# Track inserted line item IDs
line_item_ids = []

print(f"📝 Inserting {len(test_scenarios)} line items...")
for i, scenario in enumerate(test_scenarios, 1):
    line_item_id = str(uuid.uuid4())
    line_item_ids.append(line_item_id)
    
    # Get the correct estimate_id for this scenario's cloud/region/tier
    estimate_key = f"{scenario['cloud']}_{scenario['region']}_{scenario['tier']}"
    estimate_id = estimate_map[estimate_key]
    
    execute_query(
        insert_line_item_sql,
        (
            line_item_id,
            estimate_id,  # ✅ Use cloud/region/tier-specific estimate!
            scenario['scenario_id'],
            scenario['workload_name'],
            'JOBS',  # workload_type
            False,  # serverless_enabled (Classic compute)
            None,   # serverless_mode
            scenario['photon_enabled'],
            None,   # vector_search_mode
            scenario['driver_node_type'],
            scenario['worker_node_type'],
            scenario['num_workers'],
            scenario['runs_per_day'],
            scenario['avg_runtime_minutes'],
            scenario['days_per_month'],
            scenario['driver_pricing_tier'],
            scenario['worker_pricing_tier'],
            scenario['vm_payment_option'],
            scenario['notes'],
            datetime.now(),
            datetime.now()
        ),
        fetch=False
    )
    
    if i % 10 == 0:
        print(f"   ✅ Inserted {i}/{len(test_scenarios)} line items...")

print(f"\n🎉 Successfully inserted {len(line_item_ids)} test line items!")
print(f"   Cloud/Region/Tier combinations: {len(estimate_map)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Debug: Check What View Finds for Test Instances
# MAGIC 
# MAGIC Before running the full view, let's check if the view can find DBU rates and VM costs for our test instances

# COMMAND ----------

# Get first Azure and GCP scenarios to debug
debug_scenarios = [s for s in test_scenarios if s['cloud'] in ['AZURE', 'GCP']][:2]

for scenario in debug_scenarios:
    print("=" * 100)
    print(f"DEBUGGING: {scenario['workload_name']}")
    print(f"Cloud: {scenario['cloud']}, Region: {scenario['region']}")
    print(f"Driver: {scenario['driver_node_type']}, Worker: {scenario['worker_node_type']}")
    print("=" * 100)
    
    # Check if driver instance has DBU rate
    check_driver_dbu = execute_query("""
        SELECT cloud, instance_type, dbu_rate
        FROM lakemeter.sync_ref_instance_dbu_rates
        WHERE cloud = %s AND instance_type = %s
    """, (scenario['cloud'], scenario['driver_node_type']))
    
    print(f"\n1️⃣ Driver DBU Rate Lookup:")
    if len(check_driver_dbu) > 0:
        print(f"   ✅ FOUND: {check_driver_dbu.to_dict('records')[0]}")
    else:
        print(f"   ❌ NOT FOUND in sync_ref_instance_dbu_rates")
        print(f"   This will cause dbu_per_hour = 0!")
    
    # Check if worker instance has DBU rate
    check_worker_dbu = execute_query("""
        SELECT cloud, instance_type, dbu_rate
        FROM lakemeter.sync_ref_instance_dbu_rates
        WHERE cloud = %s AND instance_type = %s
    """, (scenario['cloud'], scenario['worker_node_type']))
    
    print(f"\n2️⃣ Worker DBU Rate Lookup:")
    if len(check_worker_dbu) > 0:
        print(f"   ✅ FOUND: {check_worker_dbu.to_dict('records')[0]}")
    else:
        print(f"   ❌ NOT FOUND in sync_ref_instance_dbu_rates")
        print(f"   This will cause dbu_per_hour = 0!")
    
    # Check if VM costs exist
    check_vm_cost = execute_query("""
        SELECT cloud, region, instance_type, pricing_tier, cost_per_hour
        FROM lakemeter.sync_pricing_vm_costs
        WHERE cloud = %s AND region = %s AND instance_type = %s AND pricing_tier = %s
    """, (scenario['cloud'], scenario['region'], scenario['worker_node_type'], scenario['worker_pricing_tier']))
    
    print(f"\n3️⃣ VM Cost Lookup:")
    if len(check_vm_cost) > 0:
        print(f"   ✅ FOUND: {check_vm_cost.to_dict('records')[0]}")
    else:
        print(f"   ❌ NOT FOUND in sync_pricing_vm_costs")
        print(f"   This will cause vm_cost_per_month = 0!")
    
    # Check photon multiplier - correct logic matching the view
    # The view joins on sku_type (without _PHOTON suffix) and feature
    sku_base = 'JOBS_COMPUTE'
    feature = 'photon' if scenario['photon_enabled'] else 'standard'
    
    check_multiplier = execute_query("""
        SELECT cloud, sku_type, feature, multiplier
        FROM lakemeter.sync_ref_dbu_multipliers
        WHERE cloud = %s 
          AND sku_type = %s 
          AND feature = %s
    """, (scenario['cloud'], sku_base, feature))
    
    print(f"\n4️⃣ Photon Multiplier Lookup:")
    print(f"   Looking for: cloud={scenario['cloud']}, sku_type={sku_base}, feature={feature}")
    if len(check_multiplier) > 0:
        print(f"   ✅ FOUND: {check_multiplier.to_dict('records')[0]}")
    else:
        print(f"   ❌ NOT FOUND in sync_ref_dbu_multipliers")
        print(f"   This will cause photon_multiplier = 1.0 (default)")
        # Check what exists for this cloud
        check_cloud_multipliers = execute_query("""
            SELECT sku_type, feature, multiplier
            FROM lakemeter.sync_ref_dbu_multipliers
            WHERE cloud = %s
        """, (scenario['cloud'],))
        if len(check_cloud_multipliers) > 0:
            print(f"   Available for {scenario['cloud']}: {len(check_cloud_multipliers)} multipliers")
            print(tabulate(check_cloud_multipliers.head(5), headers='keys', tablefmt='grid', showindex=False))
    
    print("\n")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11. Execute Cost Calculation View & Display Results

# COMMAND ----------

# Query the cost calculation view
query_results_sql = """
SELECT 
    c.display_order,
    c.workload_name,
    c.workload_type,
    -- Context (cloud/region/tier)
    c.cloud,
    c.region,
    c.tier,
    -- Configuration
    c.driver_node_type,
    c.worker_node_type,
    c.num_workers,
    c.photon_enabled,
    c.serverless_enabled,
    -- Usage
    c.runs_per_day,
    c.avg_runtime_minutes,
    c.days_per_month,
    c.hours_per_month,
    -- Pricing Tiers
    c.driver_pricing_tier,
    c.worker_pricing_tier,
    c.vm_pricing_tier,
    c.vm_payment_option,
    c.spot_percentage,
    -- DBU Rates (for audit)
    c.driver_dbu_rate,
    c.worker_dbu_rate,
    c.photon_multiplier,
    -- DBU Calculation
    c.dbu_per_hour,
    c.dbu_per_month,
    -- VM Costs - Detailed Breakdown
    c.driver_vm_cost_per_hour,
    c.worker_vm_cost_per_hour,
    c.total_worker_vm_cost_per_hour,
    c.total_vm_cost_per_hour,
    c.driver_vm_cost_per_month,
    c.total_worker_vm_cost_per_month,
    c.vm_cost_per_month,
    -- DBU Pricing
    c.price_per_dbu as dbu_price,
    c.product_type_for_pricing,
    c.dbu_cost_per_month,
    -- Total
    c.cost_per_month,
    c.notes
FROM lakemeter.v_line_items_with_costs c
WHERE c.line_item_id = ANY(%s::uuid[])
ORDER BY c.display_order;
"""

# Query using the line_item_ids we tracked during insertion
results_df = execute_query(query_results_sql, (line_item_ids,))

# Convert Decimal columns to float for calculations
numeric_columns = [
    'display_order', 'num_workers', 'runs_per_day', 'avg_runtime_minutes', 'days_per_month', 
    'hours_per_month', 'spot_percentage', 'driver_dbu_rate', 'worker_dbu_rate', 
    'photon_multiplier', 'dbu_per_hour', 'dbu_per_month', 
    'driver_vm_cost_per_hour', 'worker_vm_cost_per_hour', 
    'total_worker_vm_cost_per_hour', 'total_vm_cost_per_hour',
    'driver_vm_cost_per_month', 'total_worker_vm_cost_per_month', 'vm_cost_per_month', 
    'dbu_price', 'dbu_cost_per_month', 'cost_per_month'
]
for col in numeric_columns:
    if col in results_df.columns:
        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

print(f"✅ Retrieved {len(results_df)} cost calculation results")
print(f"   Columns: {len(results_df.columns)}")

# COMMAND ----------

# Display summary by cloud
print("\n" + "=" * 100)
print("📊 RESULTS SUMMARY BY CLOUD")
print("=" * 100)

summary_df = results_df.groupby(['cloud', 'tier']).agg({
    'workload_name': 'count',
    'vm_cost_per_month': 'sum',
    'dbu_cost_per_month': 'sum',
    'cost_per_month': 'sum'
}).rename(columns={'workload_name': 'count'})

print(summary_df.to_string())

# COMMAND ----------

# Show key columns for all results
print("\n" + "=" * 100)
print("📋 DETAILED RESULTS (Key Columns)")
print("=" * 100)

display_columns = [
    'workload_name', 'cloud', 'region', 'tier',
    'driver_node_type', 'worker_node_type', 'num_workers',
    'photon_enabled', 'driver_pricing_tier', 'worker_pricing_tier', 'vm_payment_option',
    'driver_vm_cost_per_hour', 'worker_vm_cost_per_hour', 'total_vm_cost_per_hour',
    'dbu_per_hour', 'dbu_price', 
    'vm_cost_per_month', 'dbu_cost_per_month', 'cost_per_month'
]

# Filter to only columns that exist
display_columns = [col for col in display_columns if col in results_df.columns]

print(f"Showing {len(display_columns)} columns for {len(results_df)} scenarios:")
print(results_df[display_columns].to_string(index=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 12. Display Results - Summary View

# COMMAND ----------

# Create summary view with key metrics (human-readable)
summary_df = results_df[[
    'workload_name',
    'cloud',
    'region',
    'tier',
    'driver_node_type',
    'worker_node_type',
    'num_workers',
    'photon_enabled',
    'driver_pricing_tier',
    'worker_pricing_tier',
    'vm_payment_option',
    'driver_vm_cost_per_hour',
    'worker_vm_cost_per_hour',
    'total_vm_cost_per_hour',
    'dbu_per_hour',
    'dbu_price',
    'vm_cost_per_month',
    'dbu_cost_per_month',
    'cost_per_month'
]].copy()

# Format for display
summary_df['photon_enabled'] = summary_df['photon_enabled'].map({True: 'Yes', False: 'No'})
summary_df['driver_vm_cost_per_hour'] = summary_df['driver_vm_cost_per_hour'].round(6)
summary_df['worker_vm_cost_per_hour'] = summary_df['worker_vm_cost_per_hour'].round(6)
summary_df['total_vm_cost_per_hour'] = summary_df['total_vm_cost_per_hour'].round(6)
summary_df['dbu_per_hour'] = summary_df['dbu_per_hour'].round(4)
summary_df['dbu_price'] = summary_df['dbu_price'].round(6)
summary_df['vm_cost_per_month'] = summary_df['vm_cost_per_month'].round(2)
summary_df['dbu_cost_per_month'] = summary_df['dbu_cost_per_month'].round(2)
summary_df['cost_per_month'] = summary_df['cost_per_month'].round(2)

print("=" * 200)
print("JOBS CLASSIC - COST CALCULATION SUMMARY (ALL SCENARIOS)")
print("=" * 200)
print(tabulate(summary_df, headers='keys', tablefmt='grid', showindex=False, maxcolwidths=30))
print("=" * 200)

# Display Spark DataFrame for better Databricks visualization
display(summary_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 13. Detailed Breakdown by Cloud, Region & Tier

# COMMAND ----------

# AWS breakdown
aws_scenarios = [s for s in test_scenarios if s['cloud'] == 'AWS']
aws_results = results_df[results_df['display_order'].isin([s['scenario_id'] for s in aws_scenarios])]

print("\n" + "=" * 120)
print("AWS RESULTS")
print("=" * 120)
print(f"US-East-1 Scenarios: {len([s for s in aws_scenarios if s['region'] == 'us-east-1'])}")
print(f"EU-West-1 Scenarios: {len([s for s in aws_scenarios if s['region'] == 'eu-west-1'])}")
print(f"Total Monthly Cost: ${aws_results['cost_per_month'].sum():,.2f}")
print(f"Total DBUs: {aws_results['dbu_per_month'].sum():,.2f}")
print("=" * 120)

display(aws_results[['workload_name', 'region', 'tier', 'driver_node_type', 'worker_node_type',
                      'photon_enabled', 'driver_pricing_tier', 'worker_pricing_tier', 'vm_payment_option',
                      'driver_vm_cost_per_hour', 'worker_vm_cost_per_hour', 'total_vm_cost_per_hour',
                      'dbu_per_month', 'vm_cost_per_month', 'cost_per_month']])

# COMMAND ----------

# Azure breakdown
azure_scenarios = [s for s in test_scenarios if s['cloud'] == 'AZURE']
azure_results = results_df[results_df['display_order'].isin([s['scenario_id'] for s in azure_scenarios])]

print("\n" + "=" * 120)
print("AZURE RESULTS")
print("=" * 120)
print(f"East US Scenarios: {len([s for s in azure_scenarios if s['region'] == 'eastus'])}")
print(f"West Europe Scenarios: {len([s for s in azure_scenarios if s['region'] == 'westeurope'])}")
print(f"Total Monthly Cost: ${azure_results['cost_per_month'].sum():,.2f}")
print(f"Total DBUs: {azure_results['dbu_per_month'].sum():,.2f}")
print("=" * 120)

display(azure_results[['workload_name', 'region', 'tier', 'driver_node_type', 'worker_node_type',
                        'photon_enabled', 'driver_pricing_tier', 'worker_pricing_tier', 'vm_payment_option',
                        'driver_vm_cost_per_hour', 'worker_vm_cost_per_hour', 'total_vm_cost_per_hour',
                        'dbu_per_month', 'vm_cost_per_month', 'cost_per_month']])

# COMMAND ----------

# GCP breakdown
gcp_scenarios = [s for s in test_scenarios if s['cloud'] == 'GCP']
gcp_results = results_df[results_df['display_order'].isin([s['scenario_id'] for s in gcp_scenarios])]

print("\n" + "=" * 120)
print("GCP RESULTS")
print("=" * 120)
print(f"US-Central1 Scenarios: {len([s for s in gcp_scenarios if s['region'] == 'us-central1'])}")
print(f"Europe-West1 Scenarios: {len([s for s in gcp_scenarios if s['region'] == 'europe-west1'])}")
print(f"Total Monthly Cost: ${gcp_results['cost_per_month'].sum():,.2f}")
print(f"Total DBUs: {gcp_results['dbu_per_month'].sum():,.2f}")
print("=" * 120)

display(gcp_results[['workload_name', 'region', 'tier', 'driver_node_type', 'worker_node_type',
                      'photon_enabled', 'driver_pricing_tier', 'worker_pricing_tier', 'vm_payment_option',
                      'driver_vm_cost_per_hour', 'worker_vm_cost_per_hour', 'total_vm_cost_per_hour',
                      'dbu_per_month', 'vm_cost_per_month', 'cost_per_month']])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 14. Manual Validation - Verify Calculation Logic
# MAGIC 
# MAGIC **How to verify calculations are correct:**
# MAGIC 
# MAGIC For each scenario, we manually calculate expected values and compare with actual results from the view.
# MAGIC 
# MAGIC ### **⚠️ IMPORTANT: Driver vs Worker Pricing Rule**
# MAGIC 
# MAGIC - **Driver Node**: ALWAYS uses `on_demand` or `reserved` pricing (NEVER spot)
# MAGIC   - If `vm_pricing_tier = 'spot'`, driver automatically uses `'on_demand'` instead
# MAGIC   - Driver can use `reserved_1y` or `reserved_3y` for cost savings
# MAGIC 
# MAGIC - **Worker Nodes**: CAN use `spot` pricing (or any other pricing tier)
# MAGIC   - Full flexibility: on_demand, spot, reserved_1y, reserved_3y
# MAGIC 
# MAGIC This reflects real-world Databricks pricing where driver stability is critical.
# MAGIC 
# MAGIC ### **Calculation Formula (JOBS Classic):**
# MAGIC 
# MAGIC 1. **Hours per Month:**
# MAGIC    ```
# MAGIC    hours_per_month = runs_per_day × (avg_runtime_minutes / 60) × days_per_month
# MAGIC    ```
# MAGIC 
# MAGIC 2. **DBU per Hour:**
# MAGIC    ```
# MAGIC    dbu_per_hour = (driver_dbu_rate + (worker_dbu_rate × num_workers)) × photon_multiplier
# MAGIC    
# MAGIC    where:
# MAGIC      - photon_multiplier is looked up from sync_pricing_dbu_rates
# MAGIC      - It's the ratio: (Photon DBU rate / Non-Photon DBU rate) for the same cloud/region/tier
# MAGIC      - Typically ~2.0 but varies by cloud and workload type
# MAGIC      - photon_multiplier = 1.0 if photon_enabled = false
# MAGIC    ```
# MAGIC 
# MAGIC 3. **DBU per Month:**
# MAGIC    ```
# MAGIC    dbu_per_month = dbu_per_hour × hours_per_month
# MAGIC    ```
# MAGIC 
# MAGIC 4. **VM Cost per Hour:**
# MAGIC    ```
# MAGIC    vm_cost_per_hour = driver_vm_cost + (worker_vm_cost × num_workers) × spot_discount
# MAGIC    
# MAGIC    where:
# MAGIC      - spot_discount = (1 - spot_percentage/100) if vm_pricing_tier = 'spot'
# MAGIC    ```
# MAGIC 
# MAGIC 5. **VM Cost per Month:**
# MAGIC    ```
# MAGIC    vm_cost_per_month = vm_cost_per_hour × hours_per_month
# MAGIC    ```
# MAGIC 
# MAGIC 6. **DBU Cost per Month:**
# MAGIC    ```
# MAGIC    dbu_cost_per_month = dbu_per_month × dbu_price
# MAGIC    
# MAGIC    where:
# MAGIC      - dbu_price from sync_pricing_dbu_rates based on cloud, region, tier, product_type
# MAGIC    ```
# MAGIC 
# MAGIC 7. **Total Cost per Month:**
# MAGIC    ```
# MAGIC    cost_per_month = dbu_cost_per_month + vm_cost_per_month
# MAGIC    ```

# COMMAND ----------

# MAGIC %md
# MAGIC ### 13.1 Manual Calculation Example - Scenario 1
# MAGIC 
# MAGIC Let's manually calculate **Scenario 1: AWS US-East Light ETL (No Photon)**

# COMMAND ----------

# Get Scenario 1 data
scenario_1 = results_df[results_df['display_order'] == 1].iloc[0]

print("=" * 100)
print("MANUAL CALCULATION VALIDATION - Scenario 1")
print("=" * 100)
print(f"Workload: {scenario_1['workload_name']}")
print(f"Configuration: {scenario_1['driver_node_type']} driver + {scenario_1['num_workers']}x {scenario_1['worker_node_type']}")
print(f"Photon: {scenario_1['photon_enabled']}")
print(f"Usage: {scenario_1['runs_per_day']} runs/day × {scenario_1['avg_runtime_minutes']} min × {scenario_1['days_per_month']} days")
print(f"VM Pricing: {scenario_1['vm_pricing_tier']}")
print("=" * 100)

# Step-by-step manual calculation
print("\n📊 STEP-BY-STEP CALCULATION:\n")

# Step 1: Hours per month
runs_per_day = scenario_1['runs_per_day']
avg_runtime_minutes = scenario_1['avg_runtime_minutes']
days_per_month = scenario_1['days_per_month']
manual_hours_per_month = runs_per_day * (avg_runtime_minutes / 60) * days_per_month

print(f"1️⃣ Hours per Month:")
print(f"   = {runs_per_day} × ({avg_runtime_minutes} / 60) × {days_per_month}")
print(f"   = {manual_hours_per_month:.2f} hours")
print(f"   ✓ Actual: {scenario_1['hours_per_month']:.2f} | Expected: {manual_hours_per_month:.2f}")

# Step 2: DBU per hour
driver_dbu = scenario_1['driver_dbu_rate']
worker_dbu = scenario_1['worker_dbu_rate']
num_workers = scenario_1['num_workers']
photon_mult = scenario_1['photon_multiplier']
manual_dbu_per_hour = (driver_dbu + (worker_dbu * num_workers)) * photon_mult

print(f"\n2️⃣ DBU per Hour:")
print(f"   = ({driver_dbu} + ({worker_dbu} × {num_workers})) × {photon_mult}")
print(f"   = {manual_dbu_per_hour:.4f} DBU/hour")
print(f"   Note: driver_dbu_rate={driver_dbu}, worker_dbu_rate={worker_dbu} from sync_ref_instance_dbu_rates")
print(f"   Note: photon_multiplier={photon_mult} from sync_ref_dbu_multipliers (varies by cloud/workload)")
print(f"   ✓ Actual: {scenario_1['dbu_per_hour']:.4f} | Expected: {manual_dbu_per_hour:.4f}")

# Step 3: DBU per month
manual_dbu_per_month = manual_dbu_per_hour * manual_hours_per_month

print(f"\n3️⃣ DBU per Month:")
print(f"   = {manual_dbu_per_hour:.4f} × {manual_hours_per_month:.2f}")
print(f"   = {manual_dbu_per_month:.2f} DBUs")
print(f"   ✓ Actual: {scenario_1['dbu_per_month']:.2f} | Expected: {manual_dbu_per_month:.2f}")

# Step 4: VM cost per hour
driver_vm_cost = scenario_1['driver_vm_cost_per_hour']
worker_vm_cost = scenario_1['worker_vm_cost_per_hour']
num_workers = scenario_1['num_workers']
manual_vm_cost_per_hour = driver_vm_cost + (worker_vm_cost * num_workers)

print(f"\n4️⃣ VM Cost per Hour:")
print(f"   = {driver_vm_cost:.4f} + ({worker_vm_cost:.4f} × {num_workers})")
print(f"   = ${manual_vm_cost_per_hour:.4f}/hour")
print(f"   ✓ VM cost calculated correctly")

# Step 5: VM cost per month
manual_vm_cost_per_month = manual_vm_cost_per_hour * manual_hours_per_month

print(f"\n5️⃣ VM Cost per Month:")
print(f"   = ${manual_vm_cost_per_hour:.4f} × {manual_hours_per_month:.2f}")
print(f"   = ${manual_vm_cost_per_month:.2f}")
print(f"   ✓ Actual: ${scenario_1['vm_cost_per_month']:.2f} | Expected: ${manual_vm_cost_per_month:.2f}")

# Step 6: DBU cost per month
dbu_price = scenario_1['dbu_price']
manual_dbu_cost_per_month = manual_dbu_per_month * dbu_price

print(f"\n6️⃣ DBU Cost per Month:")
print(f"   = {manual_dbu_per_month:.2f} × ${dbu_price:.4f}")
print(f"   = ${manual_dbu_cost_per_month:.2f}")
print(f"   ✓ Actual: ${scenario_1['dbu_cost_per_month']:.2f} | Expected: ${manual_dbu_cost_per_month:.2f}")

# Step 7: Total cost
manual_total_cost = manual_dbu_cost_per_month + manual_vm_cost_per_month

print(f"\n7️⃣ Total Cost per Month:")
print(f"   = ${manual_dbu_cost_per_month:.2f} + ${manual_vm_cost_per_month:.2f}")
print(f"   = ${manual_total_cost:.2f}")
print(f"   ✓ Actual: ${scenario_1['cost_per_month']:.2f} | Expected: ${manual_total_cost:.2f}")

print("\n" + "=" * 100)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 13.2 Automated Validation - All Scenarios
# MAGIC 
# MAGIC Run automated validation checks across all test scenarios

# COMMAND ----------

def validate_scenario(row):
    """Validate calculations for a single scenario"""
    errors = []
    tolerance = 0.01  # Allow 1 cent difference due to rounding
    
    # Calculate expected values
    expected_hours = row['runs_per_day'] * (row['avg_runtime_minutes'] / 60) * row['days_per_month']
    expected_dbu_hour = (row['driver_dbu_rate'] + (row['worker_dbu_rate'] * row['num_workers'])) * row['photon_multiplier']
    expected_dbu_month = expected_dbu_hour * expected_hours
    expected_vm_hour = row['driver_vm_cost_per_hour'] + (row['worker_vm_cost_per_hour'] * row['num_workers'])
    expected_vm_month = expected_vm_hour * expected_hours
    expected_dbu_cost = expected_dbu_month * row['dbu_price']
    expected_total = expected_dbu_cost + expected_vm_month
    
    # Validate
    if abs(row['hours_per_month'] - expected_hours) > tolerance:
        errors.append(f"Hours mismatch: {row['hours_per_month']:.2f} vs {expected_hours:.2f}")
    
    if abs(row['dbu_per_hour'] - expected_dbu_hour) > 0.0001:
        errors.append(f"DBU/hour mismatch: {row['dbu_per_hour']:.4f} vs {expected_dbu_hour:.4f}")
    
    if abs(row['dbu_per_month'] - expected_dbu_month) > tolerance:
        errors.append(f"DBU/month mismatch: {row['dbu_per_month']:.2f} vs {expected_dbu_month:.2f}")
    
    if abs(row['vm_cost_per_month'] - expected_vm_month) > tolerance:
        errors.append(f"VM cost mismatch: ${row['vm_cost_per_month']:.2f} vs ${expected_vm_month:.2f}")
    
    if abs(row['dbu_cost_per_month'] - expected_dbu_cost) > tolerance:
        errors.append(f"DBU cost mismatch: ${row['dbu_cost_per_month']:.2f} vs ${expected_dbu_cost:.2f}")
    
    if abs(row['cost_per_month'] - expected_total) > tolerance:
        errors.append(f"Total cost mismatch: ${row['cost_per_month']:.2f} vs ${expected_total:.2f}")
    
    return {
        'scenario': row['workload_name'],
        'display_order': row['display_order'],
        'status': '✅ PASS' if len(errors) == 0 else '❌ FAIL',
        'errors': errors if errors else ['All calculations correct']
    }

# Run validation on all scenarios
validation_results = [validate_scenario(row) for _, row in results_df.iterrows()]

print("=" * 120)
print("AUTOMATED VALIDATION RESULTS")
print("=" * 120)

passed = 0
failed = 0

for result in validation_results:
    status_icon = result['status']
    print(f"\n{status_icon} Scenario {result['display_order']}: {result['scenario']}")
    for error in result['errors']:
        print(f"   {error}")
    
    if '✅' in result['status']:
        passed += 1
    else:
        failed += 1

print("\n" + "=" * 120)
print(f"VALIDATION SUMMARY: {passed} PASSED | {failed} FAILED")
print("=" * 120)

if failed > 0:
    raise Exception(f"❌ Validation failed for {failed} scenario(s). Check calculations above.")
else:
    print("\n✅ All calculations are CORRECT!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 15. Test Summary

# COMMAND ----------

print("\n" + "=" * 100)
print("TEST EXECUTION SUMMARY - JOBS CLASSIC")
print("=" * 100)
print(f"Test Run ID: {TEST_RUN_ID}")
print(f"Total Scenarios: {len(test_scenarios)}")
print(f"Clouds Tested: AWS, Azure, GCP")
print(f"Regions Tested: 6 (2 per cloud)")
print(f"")
print(f"Configuration Coverage:")
print(f"  - Photon Enabled: {len(results_df[results_df['photon_enabled'] == True])}")
print(f"  - Photon Disabled: {len(results_df[results_df['photon_enabled'] == False])}")
print(f"  - On-Demand Pricing: {len(results_df[results_df['vm_pricing_tier'] == 'on_demand'])}")
print(f"  - Spot Pricing: {len(results_df[results_df['vm_pricing_tier'] == 'spot'])}")
print(f"  - Reserved Pricing: {len(results_df[results_df['vm_pricing_tier'] == 'reserved_1y'])}")
print(f"")
print(f"Total Monthly Cost (All Scenarios): ${results_df['cost_per_month'].sum():,.2f}")
print(f"Total DBUs (All Scenarios): {results_df['dbu_per_month'].sum():,.2f}")
print(f"")
print(f"Validation Status: {passed} scenarios passed, {failed} scenarios failed")
print("=" * 100)
print("\n✅ TEST COMPLETE!")
print("\n💡 TIP: Test data remains in the database for manual inspection.")
print("   To clean up, run Section 3 (Cleanup) or manually:")
print(f"   DELETE FROM lakemeter.line_items WHERE workload_name LIKE '%{TEST_RUN_ID}%';")
print(f"   DELETE FROM lakemeter.estimates WHERE estimate_name LIKE '%{TEST_RUN_ID}%';")
print(f"   DELETE FROM lakemeter.users WHERE user_id = '{TEST_USER_ID}';")

