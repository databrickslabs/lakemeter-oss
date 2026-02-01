# Databricks notebook source
# MAGIC %md
# MAGIC # Test Case: JOBS Serverless Compute
# MAGIC 
# MAGIC **Objective:** Validate cost calculations for JOBS workload type with serverless compute across:
# MAGIC - 3 clouds: AWS, Azure, GCP
# MAGIC - 2 regions per cloud (US + Europe)
# MAGIC - 3 tiers: STANDARD, PREMIUM, ENTERPRISE
# MAGIC - 2 serverless modes: **standard** and **performance** (2x cost multiplier)
# MAGIC - Multiple configurations:
# MAGIC   - Photon always enabled (serverless requirement)
# MAGIC   - Different instance types (for sizing estimation only)
# MAGIC   - Different worker counts (for sizing estimation only)
# MAGIC   - Different usage patterns
# MAGIC 
# MAGIC **Key Differences from Classic:**
# MAGIC - ✅ NO VM costs (serverless doesn't charge for VMs)
# MAGIC - ✅ DBU costs only
# MAGIC - ✅ Performance mode = 2x DBU cost multiplier
# MAGIC - ✅ Photon always enabled
# MAGIC - ✅ No driver/worker pricing tiers
# MAGIC - ✅ Uses JOBS_SERVERLESS_COMPUTE product type
# MAGIC 
# MAGIC **Test Matrix:**
# MAGIC - Cloud: AWS (us-east-1, eu-west-1), Azure (eastus, westeurope), GCP (us-central1, europe-west1)
# MAGIC - Serverless Mode: standard (1x), performance (2x)
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
LAKEBASE_PASSWORD = dbutils.secrets.get(scope="lakemeter-credentials", key="lakebase-password")

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
# MAGIC Check if we have DBU pricing data for JOBS_SERVERLESS_COMPUTE

# COMMAND ----------

# Check DBU pricing data for serverless
dbu_pricing_check_sql = """
SELECT 
    cloud,
    region,
    tier,
    product_type,
    price_per_dbu
FROM lakemeter.sync_pricing_dbu_rates
WHERE product_type = 'JOBS_SERVERLESS_COMPUTE'
ORDER BY cloud, region, tier
LIMIT 20;
"""

dbu_pricing_df = execute_query(dbu_pricing_check_sql)

print("=" * 100)
print("📊 DBU PRICING DATA FOR JOBS_SERVERLESS_COMPUTE")
print("=" * 100)
print(f"Total rows: {len(dbu_pricing_df)}")
print("\nSample data:")
print(dbu_pricing_df.to_string(index=False))
print("=" * 100)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Generate Test User

# COMMAND ----------

# Generate unique test run ID
TEST_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
TEST_USER_ID = str(uuid.uuid4())

# Create test user
create_user_sql = """
INSERT INTO lakemeter.users (user_id, full_name, email, role, is_active, created_at)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (user_id) DO NOTHING;
"""

execute_query(
    create_user_sql,
    (TEST_USER_ID, f'test_jobs_serverless_{TEST_RUN_ID}', f'test_{TEST_RUN_ID}@databricks.com', 'admin', True, datetime.now()),
    fetch=False
)

print(f"✅ Test user created: test_jobs_serverless_{TEST_RUN_ID}")
print(f"   User ID: {TEST_USER_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Query Available Instance Types Dynamically
# MAGIC 
# MAGIC Get actual instance types from the pricing table to avoid mismatches

# COMMAND ----------

# Get available instance types per cloud
instance_query_sql = """
SELECT 
    cloud,
    instance_type,
    dbu_rate
FROM lakemeter.sync_ref_instance_dbu_rates
WHERE 
    (cloud = 'AWS' AND instance_type LIKE 'i3.%')
    OR (cloud = 'AZURE' AND instance_type LIKE 'Standard_D%as%')
    OR (cloud = 'GCP' AND instance_type LIKE 'n2-standard-%')
ORDER BY cloud, dbu_rate
LIMIT 100;
"""

available_instances_df = execute_query(instance_query_sql)

# Group by cloud and get small/medium instances for each
instance_map = {}
for cloud in ['AWS', 'AZURE', 'GCP']:
    cloud_instances = available_instances_df[available_instances_df['cloud'] == cloud].sort_values('dbu_rate')
    if len(cloud_instances) >= 2:
        instance_map[cloud] = {
            'driver': cloud_instances.iloc[0]['instance_type'],  # Smallest
            'worker': cloud_instances.iloc[1]['instance_type']   # Second smallest
        }

print("=" * 100)
print("📊 SELECTED INSTANCE TYPES FOR SERVERLESS (Sizing Estimation Only)")
print("=" * 100)
for cloud, instances in instance_map.items():
    print(f"{cloud}:")
    print(f"   Driver: {instances['driver']}")
    print(f"   Worker: {instances['worker']}")
print("=" * 100)
print("ℹ️  Note: Serverless doesn't charge for VMs - instances are for sizing estimation only!")
print("=" * 100)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Query Available Regions Dynamically

# COMMAND ----------

# Get available regions per cloud
region_query_sql = """
SELECT DISTINCT 
    cloud,
    region_code
FROM lakemeter.sync_ref_sku_region_map
WHERE 
    (cloud = 'AWS' AND (region_code LIKE 'us-east-%' OR region_code LIKE 'eu-west-%'))
    OR (cloud = 'AZURE' AND region_code IN ('eastus', 'westeurope'))
    OR (cloud = 'GCP' AND (region_code LIKE 'us-central%' OR region_code LIKE 'europe-west%'))
ORDER BY cloud, region_code;
"""

available_regions_df = execute_query(region_query_sql)

# Get 1 US + 1 Europe region per cloud
region_map = {}
for cloud in ['AWS', 'AZURE', 'GCP']:
    cloud_regions = available_regions_df[available_regions_df['cloud'] == cloud]
    if len(cloud_regions) >= 2:
        us_region = cloud_regions[cloud_regions['region_code'].str.contains('us')].iloc[0]['region_code']
        eu_region = cloud_regions[cloud_regions['region_code'].str.contains('eu')].iloc[0]['region_code']
        region_map[cloud] = {'us': us_region, 'eu': eu_region}

print("=" * 100)
print("📊 SELECTED REGIONS")
print("=" * 100)
for cloud, regions in region_map.items():
    print(f"{cloud}: US={regions['us']}, EU={regions['eu']}")
print("=" * 100)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Define Test Scenarios
# MAGIC 
# MAGIC Create comprehensive test matrix for JOBS Serverless:
# MAGIC - 3 clouds × 2 regions × 3 tiers × 2 modes × 3 usage patterns = 108 scenarios

# COMMAND ----------

test_scenarios = []
scenario_id = 1

# Usage patterns
usage_patterns = [
    {'name': 'Light', 'runs_per_day': 4, 'avg_runtime_minutes': 30},
    {'name': 'Medium', 'runs_per_day': 12, 'avg_runtime_minutes': 60},
    {'name': 'Heavy', 'runs_per_day': 24, 'avg_runtime_minutes': 120}
]

# Serverless modes
serverless_modes = ['standard', 'performance']

# Generate scenarios
for cloud in ['AWS', 'AZURE', 'GCP']:
    for region_key in ['us', 'eu']:
        for tier in ['STANDARD', 'PREMIUM', 'ENTERPRISE']:
            # Skip Azure ENTERPRISE (doesn't exist)
            if cloud == 'AZURE' and tier == 'ENTERPRISE':
                continue
            
            for mode in serverless_modes:
                for usage in usage_patterns:
                    region = region_map[cloud][region_key]
                    driver_instance = instance_map[cloud]['driver']
                    worker_instance = instance_map[cloud]['worker']
                    
                    scenario = {
                        'scenario_id': scenario_id,
                        'cloud': cloud,
                        'region': region,
                        'tier': tier,
                        'workload_name': f"{cloud} {region} {tier} {mode.upper()} {usage['name']} ETL",
                        'serverless_mode': mode,
                        'driver_node_type': driver_instance,
                        'worker_node_type': worker_instance,
                        'num_workers': 4,  # For sizing estimation
                        'photon_enabled': True,  # Always true for serverless
                        'runs_per_day': usage['runs_per_day'],
                        'avg_runtime_minutes': usage['avg_runtime_minutes'],
                        'days_per_month': 30,
                        'notes': f"Serverless {mode} mode, {usage['name']} usage (VMs for sizing only)"
                    }
                    
                    test_scenarios.append(scenario)
                    scenario_id += 1

print(f"✅ Generated {len(test_scenarios)} test scenarios")
print(f"   Clouds: 3 (AWS, Azure, GCP)")
print(f"   Regions per cloud: 2 (US + Europe)")
print(f"   Tiers: 3 (STANDARD, PREMIUM, ENTERPRISE)")
print(f"   Serverless modes: 2 (standard, performance)")
print(f"   Usage patterns: 3 (Light, Medium, Heavy)")
print(f"   Azure ENTERPRISE excluded (doesn't exist)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Create Estimates (One per Cloud/Region/Tier Combination)

# COMMAND ----------

# Get unique cloud/region/tier combinations
unique_combos = {}
for scenario in test_scenarios:
    key = f"{scenario['cloud']}_{scenario['region']}_{scenario['tier']}"
    if key not in unique_combos:
        unique_combos[key] = {
            'cloud': scenario['cloud'],
            'region': scenario['region'],
            'tier': scenario['tier']
        }

print(f"📝 Creating {len(unique_combos)} estimates...")

# Create estimates
estimate_map = {}  # Maps "CLOUD_REGION_TIER" to estimate_id

for key, combo in unique_combos.items():
    estimate_id = str(uuid.uuid4())
    estimate_map[key] = estimate_id
    
    create_estimate_sql = """
    INSERT INTO lakemeter.estimates (
        estimate_id, owner_user_id, estimate_name,
        cloud, region, tier,
        created_at, updated_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """
    
    execute_query(
        create_estimate_sql,
        (
            estimate_id,
            TEST_USER_ID,
            f"Test: {combo['cloud']} {combo['region']} {combo['tier']}",
            combo['cloud'],
            combo['region'],
            combo['tier'],
            datetime.now(),
            datetime.now()
        ),
        fetch=False
    )

print(f"✅ Created {len(estimate_map)} estimates")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Insert Line Items

# COMMAND ----------

# SQL for inserting line items
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
            True,  # serverless_enabled (KEY!)
            scenario['serverless_mode'],  # standard or performance
            True,  # photon_enabled (always true for serverless)
            None,   # vector_search_mode
            scenario['driver_node_type'],
            scenario['worker_node_type'],
            scenario['num_workers'],
            scenario['runs_per_day'],
            scenario['avg_runtime_minutes'],
            scenario['days_per_month'],
            None,  # driver_pricing_tier (N/A for serverless)
            None,  # worker_pricing_tier (N/A for serverless)
            None,  # vm_payment_option (N/A for serverless)
            scenario['notes'],
            datetime.now(),
            datetime.now()
        ),
        fetch=False
    )
    
    if i % 20 == 0:
        print(f"   ✅ Inserted {i}/{len(test_scenarios)} line items...")

print(f"\n🎉 Successfully inserted {len(line_item_ids)} test line items!")
print(f"   Cloud/Region/Tier combinations: {len(estimate_map)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Execute Cost Calculation View & Display Results

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
    c.serverless_mode,
    -- Usage
    c.runs_per_day,
    c.avg_runtime_minutes,
    c.days_per_month,
    c.hours_per_month,
    -- DBU Rates (for audit)
    c.driver_dbu_rate,
    c.worker_dbu_rate,
    c.photon_multiplier,
    -- DBU Calculation
    c.dbu_per_hour,
    c.dbu_per_month,
    -- VM Costs (should be $0 for serverless!)
    c.driver_vm_cost_per_hour,
    c.worker_vm_cost_per_hour,
    c.total_vm_cost_per_hour,
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
    'hours_per_month', 'driver_dbu_rate', 'worker_dbu_rate', 
    'photon_multiplier', 'dbu_per_hour', 'dbu_per_month', 
    'driver_vm_cost_per_hour', 'worker_vm_cost_per_hour', 
    'total_vm_cost_per_hour', 'vm_cost_per_month',
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

summary_df = results_df.groupby(['cloud', 'tier', 'serverless_mode']).agg({
    'workload_name': 'count',
    'vm_cost_per_month': 'sum',
    'dbu_cost_per_month': 'sum',
    'cost_per_month': 'sum'
}).rename(columns={'workload_name': 'count'})

print(summary_df.to_string())
print("\n⚠️  VM costs should be $0 for all serverless scenarios!")

# COMMAND ----------

# Show key columns for all results
print("\n" + "=" * 100)
print("📋 DETAILED RESULTS (Key Columns)")
print("=" * 100)

display_columns = [
    'workload_name', 'cloud', 'region', 'tier',
    'serverless_mode', 'photon_enabled',
    'driver_node_type', 'worker_node_type', 'num_workers',
    'runs_per_day', 'avg_runtime_minutes', 'hours_per_month',
    'dbu_per_hour', 'dbu_price', 
    'vm_cost_per_month', 'dbu_cost_per_month', 'cost_per_month'
]

# Filter to only columns that exist
display_columns = [col for col in display_columns if col in results_df.columns]

print(f"Showing {len(display_columns)} columns for {len(results_df)} scenarios:")
print(results_df[display_columns].to_string(index=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Display Results - Summary View

# COMMAND ----------

# Create summary view with key metrics (human-readable)
summary_display_df = results_df[[
    'workload_name',
    'cloud',
    'region',
    'tier',
    'serverless_mode',
    'driver_node_type',
    'worker_node_type',
    'num_workers',
    'runs_per_day',
    'avg_runtime_minutes',
    'hours_per_month',
    'dbu_per_hour',
    'dbu_price',
    'vm_cost_per_month',
    'dbu_cost_per_month',
    'cost_per_month'
]].copy()

# Format for display
summary_display_df['dbu_per_hour'] = summary_display_df['dbu_per_hour'].round(4)
summary_display_df['dbu_price'] = summary_display_df['dbu_price'].round(6)
summary_display_df['vm_cost_per_month'] = summary_display_df['vm_cost_per_month'].round(2)
summary_display_df['dbu_cost_per_month'] = summary_display_df['dbu_cost_per_month'].round(2)
summary_display_df['cost_per_month'] = summary_display_df['cost_per_month'].round(2)

print("=" * 200)
print("JOBS SERVERLESS - COST CALCULATION SUMMARY (ALL SCENARIOS)")
print("=" * 200)
print(tabulate(summary_display_df, headers='keys', tablefmt='grid', showindex=False, maxcolwidths=30))
print("=" * 200)

# Display Spark DataFrame for better Databricks visualization
display(summary_display_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11. Detailed Breakdown by Cloud & Mode

# COMMAND ----------

# AWS breakdown
aws_scenarios = [s for s in test_scenarios if s['cloud'] == 'AWS']
aws_results = results_df[results_df['display_order'].isin([s['scenario_id'] for s in aws_scenarios])]

print("\n" + "=" * 120)
print("AWS SERVERLESS RESULTS")
print("=" * 120)
print(f"Total Scenarios: {len(aws_scenarios)}")
print(f"Standard Mode: {len([s for s in aws_scenarios if s['serverless_mode'] == 'standard'])}")
print(f"Performance Mode: {len([s for s in aws_scenarios if s['serverless_mode'] == 'performance'])}")
print(f"Total Monthly Cost: ${aws_results['cost_per_month'].sum():,.2f}")
print(f"Total DBUs: {aws_results['dbu_per_month'].sum():,.2f}")
print(f"Total VM Cost: ${aws_results['vm_cost_per_month'].sum():,.2f} (should be $0!)")
print("=" * 120)

display(aws_results[['workload_name', 'region', 'tier', 'serverless_mode',
                      'runs_per_day', 'avg_runtime_minutes', 'hours_per_month',
                      'dbu_per_hour', 'dbu_price', 'dbu_cost_per_month', 'cost_per_month']])

# COMMAND ----------

# Azure breakdown
azure_scenarios = [s for s in test_scenarios if s['cloud'] == 'AZURE']
azure_results = results_df[results_df['display_order'].isin([s['scenario_id'] for s in azure_scenarios])]

print("\n" + "=" * 120)
print("AZURE SERVERLESS RESULTS")
print("=" * 120)
print(f"Total Scenarios: {len(azure_scenarios)}")
print(f"Standard Mode: {len([s for s in azure_scenarios if s['serverless_mode'] == 'standard'])}")
print(f"Performance Mode: {len([s for s in azure_scenarios if s['serverless_mode'] == 'performance'])}")
print(f"Total Monthly Cost: ${azure_results['cost_per_month'].sum():,.2f}")
print(f"Total DBUs: {azure_results['dbu_per_month'].sum():,.2f}")
print(f"Total VM Cost: ${azure_results['vm_cost_per_month'].sum():,.2f} (should be $0!)")
print("=" * 120)

display(azure_results[['workload_name', 'region', 'tier', 'serverless_mode',
                        'runs_per_day', 'avg_runtime_minutes', 'hours_per_month',
                        'dbu_per_hour', 'dbu_price', 'dbu_cost_per_month', 'cost_per_month']])

# COMMAND ----------

# GCP breakdown
gcp_scenarios = [s for s in test_scenarios if s['cloud'] == 'GCP']
gcp_results = results_df[results_df['display_order'].isin([s['scenario_id'] for s in gcp_scenarios])]

print("\n" + "=" * 120)
print("GCP SERVERLESS RESULTS")
print("=" * 120)
print(f"Total Scenarios: {len(gcp_scenarios)}")
print(f"Standard Mode: {len([s for s in gcp_scenarios if s['serverless_mode'] == 'standard'])}")
print(f"Performance Mode: {len([s for s in gcp_scenarios if s['serverless_mode'] == 'performance'])}")
print(f"Total Monthly Cost: ${gcp_results['cost_per_month'].sum():,.2f}")
print(f"Total DBUs: {gcp_results['dbu_per_month'].sum():,.2f}")
print(f"Total VM Cost: ${gcp_results['vm_cost_per_month'].sum():,.2f} (should be $0!)")
print("=" * 120)

display(gcp_results[['workload_name', 'region', 'tier', 'serverless_mode',
                      'runs_per_day', 'avg_runtime_minutes', 'hours_per_month',
                      'dbu_per_hour', 'dbu_price', 'dbu_cost_per_month', 'cost_per_month']])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 12. Validation: Standard vs Performance Mode
# MAGIC 
# MAGIC Verify that Performance mode costs exactly 2x Standard mode

# COMMAND ----------

print("\n" + "=" * 120)
print("🧪 VALIDATION: Performance Mode = 2× Standard Mode")
print("=" * 120)

# Group by cloud/region/tier/usage, compare standard vs performance
validation_results = []

for cloud in ['AWS', 'AZURE', 'GCP']:
    for region_key in ['us', 'eu']:
        for tier in ['STANDARD', 'PREMIUM', 'ENTERPRISE']:
            if cloud == 'AZURE' and tier == 'ENTERPRISE':
                continue
            
            for usage in usage_patterns:
                region = region_map[cloud][region_key]
                
                # Get standard mode scenario
                standard_scenario = [s for s in test_scenarios 
                                   if s['cloud'] == cloud 
                                   and s['region'] == region 
                                   and s['tier'] == tier
                                   and s['serverless_mode'] == 'standard'
                                   and s['runs_per_day'] == usage['runs_per_day']]
                
                # Get performance mode scenario
                performance_scenario = [s for s in test_scenarios 
                                      if s['cloud'] == cloud 
                                      and s['region'] == region 
                                      and s['tier'] == tier
                                      and s['serverless_mode'] == 'performance'
                                      and s['runs_per_day'] == usage['runs_per_day']]
                
                if standard_scenario and performance_scenario:
                    std_id = standard_scenario[0]['scenario_id']
                    perf_id = performance_scenario[0]['scenario_id']
                    
                    std_cost = results_df[results_df['display_order'] == std_id]['cost_per_month'].iloc[0]
                    perf_cost = results_df[results_df['display_order'] == perf_id]['cost_per_month'].iloc[0]
                    
                    # SPECIAL CASE: Serverless not available in STANDARD tier
                    if tier == 'STANDARD':
                        # Expect $0 costs for STANDARD tier (serverless not available)
                        is_valid = (std_cost == 0 and perf_cost == 0)
                        ratio = 0
                        status = '✅ (N/A)' if is_valid else '❌'
                    else:
                        # PREMIUM/ENTERPRISE: Validate 2x ratio
                        ratio = perf_cost / std_cost if std_cost > 0 else 0
                        is_valid = abs(ratio - 2.0) < 0.01  # Allow 1% tolerance
                        status = '✅' if is_valid else '❌'
                    
                    validation_results.append({
                        'cloud': cloud,
                        'region': region,
                        'tier': tier,
                        'usage': usage['name'],
                        'standard_cost': std_cost,
                        'performance_cost': perf_cost,
                        'ratio': ratio,
                        'valid': status,
                        'is_valid_bool': is_valid
                    })

validation_df = pd.DataFrame(validation_results)

# Separate STANDARD tier (N/A) from PREMIUM/ENTERPRISE
standard_tier_df = validation_df[validation_df['tier'] == 'STANDARD']
premium_enterprise_df = validation_df[validation_df['tier'].isin(['PREMIUM', 'ENTERPRISE'])]

print(f"\nTotal validations: {len(validation_df)}")
print(f"  STANDARD tier (serverless N/A): {len(standard_tier_df)}")
print(f"  PREMIUM/ENTERPRISE tier: {len(premium_enterprise_df)}")
print(f"\nValid: {len(validation_df[validation_df['is_valid_bool'] == True])}")
print(f"Invalid: {len(validation_df[validation_df['is_valid_bool'] == False])}")

print("\n📋 STANDARD Tier Validation (Serverless Not Available):")
if len(standard_tier_df) > 0:
    print(standard_tier_df[['cloud', 'region', 'tier', 'usage', 'standard_cost', 'performance_cost', 'valid']].head(6).to_string(index=False))
    if (standard_tier_df['is_valid_bool'] == True).all():
        print("✅ All STANDARD tier scenarios correctly return $0 (serverless not available)")
    else:
        print("❌ Some STANDARD tier scenarios have unexpected non-zero costs!")

print("\n📋 PREMIUM/ENTERPRISE Tier Validation (2× Multiplier):")
if len(premium_enterprise_df) > 0:
    print(premium_enterprise_df[['cloud', 'region', 'tier', 'usage', 'standard_cost', 'performance_cost', 'ratio', 'valid']].head(10).to_string(index=False))

if len(validation_df[validation_df['is_valid_bool'] == False]) > 0:
    print("\n⚠️  FAILED VALIDATIONS:")
    failed_df = validation_df[validation_df['is_valid_bool'] == False]
    print(failed_df[['cloud', 'region', 'tier', 'usage', 'standard_cost', 'performance_cost', 'ratio', 'valid']].to_string(index=False))
else:
    print("\n✅ ALL VALIDATIONS PASSED!")
    print("   • STANDARD tier: $0 costs (expected - serverless not available)")
    print("   • PREMIUM/ENTERPRISE: Performance mode = 2× Standard mode")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 13. Summary & Assertions

# COMMAND ----------

print("\n" + "=" * 120)
print("📊 FINAL SUMMARY - JOBS SERVERLESS TEST")
print("=" * 120)

# Assertions
total_scenarios = len(results_df)
total_vm_cost = results_df['vm_cost_per_month'].sum()
total_dbu_cost = results_df['dbu_cost_per_month'].sum()
total_cost = results_df['cost_per_month'].sum()

print(f"\n✅ Total test scenarios: {total_scenarios}")
print(f"✅ Total VM cost: ${total_vm_cost:,.2f}")
print(f"✅ Total DBU cost: ${total_dbu_cost:,.2f}")
print(f"✅ Total cost: ${total_cost:,.2f}")

# Key assertions
print("\n🔍 Key Validations:")

# 1. VM costs should be $0
assert total_vm_cost == 0, f"❌ FAIL: VM cost should be $0 for serverless, got ${total_vm_cost:,.2f}"
print("   ✅ VM costs are $0 (correct for serverless)")

# 2. All scenarios have results
assert total_scenarios == len(test_scenarios), f"❌ FAIL: Expected {len(test_scenarios)} results, got {total_scenarios}"
print(f"   ✅ All {total_scenarios} scenarios have results")

# 3. STANDARD tier should have $0 costs (serverless not available)
standard_tier_results = results_df[results_df['tier'] == 'STANDARD']
if len(standard_tier_results) > 0:
    assert (standard_tier_results['cost_per_month'] == 0).all(), "❌ FAIL: STANDARD tier should have $0 costs"
    print(f"   ✅ All {len(standard_tier_results)} STANDARD tier scenarios have $0 costs (expected)")

# 4. PREMIUM/ENTERPRISE tiers should have positive costs
premium_enterprise_results = results_df[results_df['tier'].isin(['PREMIUM', 'ENTERPRISE'])]
if len(premium_enterprise_results) > 0:
    assert (premium_enterprise_results['cost_per_month'] > 0).all(), "❌ FAIL: PREMIUM/ENTERPRISE should have positive costs"
    print(f"   ✅ All {len(premium_enterprise_results)} PREMIUM/ENTERPRISE scenarios have positive costs")

# 5. Performance mode validation (excludes STANDARD tier N/A scenarios)
valid_performance_ratios = len(validation_df[validation_df['is_valid_bool'] == True])
total_validations = len(validation_df)
assert valid_performance_ratios == total_validations, f"❌ FAIL: {total_validations - valid_performance_ratios} validations failed"
print(f"   ✅ All {total_validations} validations passed:")
print(f"      • STANDARD tier: $0 (serverless not available)")
print(f"      • PREMIUM/ENTERPRISE: Performance = 2× Standard")

# 6. DBU cost = Total cost (since VM cost is $0)
assert (results_df['dbu_cost_per_month'] == results_df['cost_per_month']).all(), "❌ FAIL: DBU cost should equal total cost for serverless"
print("   ✅ DBU cost = Total cost (as expected for serverless)")

print("\n" + "=" * 120)
print("🎉 ALL TESTS PASSED!")
print("=" * 120)
print("\n📋 Test Coverage:")
print(f"   ✓ 3 clouds (AWS, Azure, GCP)")
print(f"   ✓ 6 regions (2 per cloud: US + Europe)")
print(f"   ✓ 3 tiers (STANDARD, PREMIUM, ENTERPRISE)")
print(f"   ✓ 2 serverless modes (standard, performance)")
print(f"   ✓ 3 usage patterns (Light, Medium, Heavy)")
print(f"   ✓ Total: {total_scenarios} comprehensive scenarios")
print("\n✅ JOBS Serverless cost calculation is working correctly!")
print("=" * 120)

# COMMAND ----------

