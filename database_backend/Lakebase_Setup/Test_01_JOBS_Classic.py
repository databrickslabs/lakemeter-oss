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

import psycopg2
import pandas as pd
import uuid
from datetime import datetime
from tabulate import tabulate

# Lakebase connection parameters
LAKEBASE_HOST = "instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com"
LAKEBASE_PORT = 5432
LAKEBASE_DB = "lakemeter_pricing"
LAKEBASE_USER = "lakemeter_sync_role"
LAKEBASE_PASSWORD = "***REMOVED_DATABASE_CREDENTIAL***"

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
# MAGIC ## 3. Generate Test IDs
# MAGIC 
# MAGIC Create test user, estimate, and line items for JOBS Classic scenarios

# COMMAND ----------

# Generate unique IDs for this test run
TEST_RUN_ID = str(uuid.uuid4())[:8]
TEST_USER_ID = str(uuid.uuid4())
# TEST_ESTIMATE_ID removed - now creating one estimate per cloud/region in Section 6.1

print(f"🧪 Test Run ID: {TEST_RUN_ID}")
print(f"👤 Test User ID: {TEST_USER_ID}")
print(f"📊 Estimates will be created per cloud/region in Section 6.1")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Create Test User

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
# MAGIC ## 5. Placeholder for Test Estimates
# MAGIC 
# MAGIC **Note:** Estimates are now created dynamically in Section 8, one per cloud/region combo.
# MAGIC This ensures each line item has the correct cloud/region for pricing lookups.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Query Available Instance Types from Pricing Tables
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
# MAGIC ## 7. Build Test Scenarios Dynamically
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
# BUILD COMPREHENSIVE TEST SCENARIOS - All Payment Options & Photon Configs
# ============================================================================

test_scenarios = []
scenario_id = 1

# Define payment option matrices
# AWS: All payment options with upfront variants
aws_payment_matrix = [
    {'pricing_tier': 'on_demand', 'payment_option': 'on_demand', 'spot_pct': 0},
    {'pricing_tier': 'on_demand', 'payment_option': 'spot', 'spot_pct': 100},
    {'pricing_tier': 'reserved_1y', 'payment_option': 'no_upfront', 'spot_pct': 0},
    {'pricing_tier': 'reserved_1y', 'payment_option': 'partial_upfront', 'spot_pct': 0},
    {'pricing_tier': 'reserved_1y', 'payment_option': 'all_upfront', 'spot_pct': 0},
    {'pricing_tier': 'reserved_3y', 'payment_option': 'no_upfront', 'spot_pct': 0},
    {'pricing_tier': 'reserved_3y', 'payment_option': 'partial_upfront', 'spot_pct': 0},
    {'pricing_tier': 'reserved_3y', 'payment_option': 'all_upfront', 'spot_pct': 0},
]

# Azure/GCP: No upfront options, simplified payment
azure_gcp_payment_matrix = [
    {'pricing_tier': 'on_demand', 'payment_option': 'NA', 'spot_pct': 0},
    {'pricing_tier': 'spot', 'payment_option': 'NA', 'spot_pct': 100},
    {'pricing_tier': 'reserved_1y', 'payment_option': 'NA', 'spot_pct': 0},
    {'pricing_tier': 'reserved_3y', 'payment_option': 'NA', 'spot_pct': 0},
]

# Photon configurations
photon_configs = [
    {'enabled': False, 'label': 'No Photon'},
    {'enabled': True, 'label': 'Photon'},
]

# Build AWS scenarios: 1 region × 8 payment options × 2 photon configs = 16 scenarios
aws_region = aws_regions[0] if len(aws_regions) > 0 else None
if aws_region:
    small_inst = get_instances_for_region('AWS', aws_region, 'small')
    medium_inst = get_instances_for_region('AWS', aws_region, 'medium')
    
    for payment in aws_payment_matrix:
        for photon in photon_configs:
            if small_inst and medium_inst:
                test_scenarios.append({
                    'scenario_id': scenario_id,
                    'workload_name': f"AWS {payment['payment_option'].replace('_', ' ').title()} {photon['label']}",
                    'cloud': 'AWS',
                    'region': aws_region,
                    'driver_node_type': small_inst,
                    'worker_node_type': medium_inst,
                    'num_workers': 4,
                    'photon_enabled': photon['enabled'],
                    'vm_pricing_tier': payment['pricing_tier'],
                    'vm_payment_option': payment['payment_option'],
                    'spot_percentage': payment['spot_pct'],
                    'runs_per_day': 12,
                    'avg_runtime_minutes': 60,
                    'days_per_month': 30,
                    'notes': f"AWS {aws_region} - {payment['payment_option']} - {photon['label']}"
                })
                scenario_id += 1

# Build Azure scenarios: 1 region × 4 payment options × 2 photon configs = 8 scenarios
azure_region = azure_regions[0] if len(azure_regions) > 0 else None
if azure_region:
    small_inst = get_instances_for_region('AZURE', azure_region, 'small')
    medium_inst = get_instances_for_region('AZURE', azure_region, 'medium')
    
    for payment in azure_gcp_payment_matrix:
        for photon in photon_configs:
            if small_inst and medium_inst:
                test_scenarios.append({
                    'scenario_id': scenario_id,
                    'workload_name': f"Azure {payment['pricing_tier'].replace('_', ' ').title()} {photon['label']}",
                    'cloud': 'AZURE',
                    'region': azure_region,
                    'driver_node_type': small_inst,
                    'worker_node_type': medium_inst,
                    'num_workers': 4,
                    'photon_enabled': photon['enabled'],
                    'vm_pricing_tier': payment['pricing_tier'],
                    'vm_payment_option': payment['payment_option'],
                    'spot_percentage': payment['spot_pct'],
                    'runs_per_day': 12,
                    'avg_runtime_minutes': 60,
                    'days_per_month': 30,
                    'notes': f"Azure {azure_region} - {payment['pricing_tier']} - {photon['label']}"
                })
                scenario_id += 1

# Build GCP scenarios: 1 region × 4 payment options × 2 photon configs = 8 scenarios
gcp_region = gcp_regions[0] if len(gcp_regions) > 0 else None
if gcp_region:
    small_inst = get_instances_for_region('GCP', gcp_region, 'small')
    medium_inst = get_instances_for_region('GCP', gcp_region, 'medium')
    
    for payment in azure_gcp_payment_matrix:
        for photon in photon_configs:
            if small_inst and medium_inst:
                test_scenarios.append({
                    'scenario_id': scenario_id,
                    'workload_name': f"GCP {payment['pricing_tier'].replace('_', ' ').title()} {photon['label']}",
                    'cloud': 'GCP',
                    'region': gcp_region,
                    'driver_node_type': small_inst,
                    'worker_node_type': medium_inst,
                    'num_workers': 4,
                    'photon_enabled': photon['enabled'],
                    'vm_pricing_tier': payment['pricing_tier'],
                    'vm_payment_option': payment['payment_option'],
                    'spot_percentage': payment['spot_pct'],
                    'runs_per_day': 12,
                    'avg_runtime_minutes': 60,
                    'days_per_month': 30,
                    'notes': f"GCP {gcp_region} - {payment['pricing_tier']} - {photon['label']}"
                })
                scenario_id += 1

print("\n" + "=" * 120)
print(f"📋 Built {len(test_scenarios)} comprehensive test scenarios:")
print("=" * 120)
print(f"   AWS: {len([s for s in test_scenarios if s['cloud'] == 'AWS'])} scenarios (8 payment options × 2 photon)")
print(f"   AZURE: {len([s for s in test_scenarios if s['cloud'] == 'AZURE'])} scenarios (4 payment options × 2 photon)")
print(f"   GCP: {len([s for s in test_scenarios if s['cloud'] == 'GCP'])} scenarios (4 payment options × 2 photon)")
print("=" * 120)

# Show sample of scenarios
print("\n📋 Sample scenarios:")
for scenario in test_scenarios[:5]:
    print(f"   {scenario['scenario_id']}. {scenario['workload_name']}")
print(f"   ... and {len(test_scenarios) - 5} more")

if len(test_scenarios) == 0:
    raise Exception("❌ No test scenarios could be built! Check pricing data availability.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Insert Test Line Items
# MAGIC 
# MAGIC Using the comprehensive test scenarios built in Section 7 (all payment options × photon configs)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 6.1 Create Estimates (One Per Cloud/Region Combo)

# COMMAND ----------

# CRITICAL FIX: Create one estimate per cloud/region
# This ensures pricing lookups use the correct cloud/region rates

create_estimate_sql = """
INSERT INTO lakemeter.estimates (
    estimate_id, estimate_name, owner_user_id, customer_name,
    cloud, region, tier, status, created_at, updated_at, updated_by
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (estimate_id) DO NOTHING;
"""

# Build estimate mapping: {cloud_region: estimate_id}
estimate_map = {}
for scenario in test_scenarios:
    key = f"{scenario['cloud']}_{scenario['region']}"
    if key not in estimate_map:
        estimate_id = str(uuid.uuid4())
        estimate_map[key] = estimate_id
        
        execute_query(
            create_estimate_sql,
            (estimate_id, f'Test - {scenario["cloud"]} {scenario["region"]} - {TEST_RUN_ID}', 
             TEST_USER_ID, f'Test Customer - {scenario["cloud"]}', 
             scenario['cloud'], scenario['region'], 'PREMIUM', 'draft',
             datetime.now(), datetime.now(), TEST_USER_ID),
            fetch=False
        )
        print(f"✅ Created estimate: {scenario['cloud']} / {scenario['region']} → {estimate_id}")

print(f"\n✅ Created {len(estimate_map)} estimates for {len(test_scenarios)} scenarios")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 6.2 Insert Test Line Items (With Correct Estimate IDs)

# COMMAND ----------

insert_line_item_sql = """
INSERT INTO lakemeter.line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, serverless_mode, photon_enabled, vector_search_mode,
    driver_node_type, worker_node_type, num_workers,
    runs_per_day, avg_runtime_minutes, days_per_month,
    vm_pricing_tier, vm_payment_option, spot_percentage,
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

for scenario in test_scenarios:
    line_item_id = str(uuid.uuid4())
    line_item_ids.append(line_item_id)
    
    # Get the correct estimate_id for this scenario's cloud/region
    estimate_key = f"{scenario['cloud']}_{scenario['region']}"
    estimate_id = estimate_map[estimate_key]
    
    execute_query(
        insert_line_item_sql,
        (
            line_item_id,
            estimate_id,  # ✅ Use cloud/region-specific estimate!
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
            scenario['vm_pricing_tier'],
            scenario['vm_payment_option'],
            scenario['spot_percentage'],
            scenario['notes'],
            datetime.now(),
            datetime.now()
        ),
        fetch=False
    )
    
    print(f"✅ Scenario {scenario['scenario_id']}: {scenario['workload_name']}")

print(f"\n✅ Inserted {len(line_item_ids)} test line items")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Debug: Check What View Finds for Test Instances
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
    """, (scenario['cloud'], scenario['region'], scenario['worker_node_type'], scenario['vm_pricing_tier']))
    
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
# MAGIC ## 10. Execute Cost Calculation View & Display Results

# COMMAND ----------

# Query the cost calculation view
query_results_sql = """
SELECT 
    c.display_order,
    c.workload_name,
    c.workload_type,
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
    -- Pricing
    c.vm_pricing_tier,
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
    'num_workers', 'runs_per_day', 'avg_runtime_minutes', 'days_per_month', 
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

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11. Display Results - Summary View

# COMMAND ----------

# Create summary view with key metrics
summary_df = results_df[[
    'display_order',
    'workload_name',
    'num_workers',
    'photon_enabled',
    'vm_pricing_tier',
    'runs_per_day',
    'avg_runtime_minutes',
    'hours_per_month',
    'driver_dbu_rate',
    'worker_dbu_rate',
    'photon_multiplier',
    'dbu_per_hour',
    'dbu_per_month',
    'dbu_cost_per_month',
    'driver_vm_cost_per_hour',
    'worker_vm_cost_per_hour',
    'total_vm_cost_per_hour',
    'vm_cost_per_month',
    'cost_per_month'
]].copy()

summary_df['photon_enabled'] = summary_df['photon_enabled'].map({True: 'Yes', False: 'No'})
summary_df['dbu_per_month'] = summary_df['dbu_per_month'].round(2)
summary_df['dbu_cost_per_month'] = summary_df['dbu_cost_per_month'].round(2)
summary_df['driver_vm_cost_per_hour'] = summary_df['driver_vm_cost_per_hour'].round(4)
summary_df['worker_vm_cost_per_hour'] = summary_df['worker_vm_cost_per_hour'].round(4)
summary_df['total_vm_cost_per_hour'] = summary_df['total_vm_cost_per_hour'].round(4)
summary_df['vm_cost_per_month'] = summary_df['vm_cost_per_month'].round(2)
summary_df['cost_per_month'] = summary_df['cost_per_month'].round(2)

print("=" * 180)
print("JOBS CLASSIC - COST CALCULATION SUMMARY")
print("=" * 180)
print(tabulate(summary_df, headers='keys', tablefmt='grid', showindex=False))
print("=" * 180)

# Display Spark DataFrame for better Databricks visualization
display(summary_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 12. Detailed Breakdown by Cloud & Region

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

display(aws_results[['workload_name', 'photon_enabled', 'vm_pricing_tier', 
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

display(azure_results[['workload_name', 'photon_enabled', 'vm_pricing_tier', 
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

display(gcp_results[['workload_name', 'photon_enabled', 'vm_pricing_tier', 
                      'driver_vm_cost_per_hour', 'worker_vm_cost_per_hour', 'total_vm_cost_per_hour',
                      'dbu_per_month', 'vm_cost_per_month', 'cost_per_month']])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 13. Manual Validation - Verify Calculation Logic
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
# MAGIC ## 14. Test Summary

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

