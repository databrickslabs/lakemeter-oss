# Databricks notebook source
# MAGIC %md
# MAGIC # Test Case: ALL_PURPOSE (Interactive) Classic Compute
# MAGIC 
# MAGIC **Objective:** Validate cost calculations for ALL_PURPOSE workload type with classic compute across:
# MAGIC - 3 clouds: AWS, Azure, GCP
# MAGIC - 2 regions per cloud (US + Europe)
# MAGIC - 3 tiers: STANDARD, PREMIUM, ENTERPRISE
# MAGIC - Multiple configurations:
# MAGIC   - Photon enabled/disabled
# MAGIC   - Different instance types
# MAGIC   - Different worker counts
# MAGIC   - Different VM pricing tiers (on_demand, spot, reserved)
# MAGIC   - Different usage patterns (continuous vs intermittent)
# MAGIC 
# MAGIC **Key Differences from JOBS:**
# MAGIC - Typically runs continuously or for long periods
# MAGIC - Used for interactive notebooks and ad-hoc analysis
# MAGIC - Same VM + DBU cost structure as JOBS
# MAGIC - Product types: ALL_PURPOSE_COMPUTE, ALL_PURPOSE_COMPUTE_(PHOTON)
# MAGIC 
# MAGIC **Test Matrix:**
# MAGIC - Cloud: AWS (us-east-1, eu-west-1), Azure (eastus, westeurope), GCP (us-central1, europe-west1)
# MAGIC - Instance types: Small, Medium, Large
# MAGIC - Photon: Enabled, Disabled
# MAGIC - VM Pricing: on_demand, spot (50%), reserved_1y
# MAGIC - Usage: Part-time (8h/day), Full-time (24h/day, continuous)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Setup - Install Dependencies & Connect to Lakebase

# COMMAND ----------

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
# MAGIC ## 2. Generate Test User

# COMMAND ----------

TEST_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
TEST_USER_ID = str(uuid.uuid4())

create_user_sql = """
INSERT INTO lakemeter.users (user_id, full_name, email, role, is_active, created_at)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (user_id) DO NOTHING;
"""

execute_query(
    create_user_sql,
    (TEST_USER_ID, f'test_all_purpose_{TEST_RUN_ID}', f'test_{TEST_RUN_ID}@databricks.com', 'admin', True, datetime.now()),
    fetch=False
)

print(f"✅ Test user created: test_all_purpose_{TEST_RUN_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Query Available Instance Types & Regions Dynamically

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
ORDER BY cloud, dbu_rate;
"""

available_instances_df = execute_query(instance_query_sql)

instance_map = {}
for cloud in ['AWS', 'AZURE', 'GCP']:
    cloud_instances = available_instances_df[available_instances_df['cloud'] == cloud].sort_values('dbu_rate')
    if len(cloud_instances) >= 2:
        instance_map[cloud] = {
            'driver': cloud_instances.iloc[0]['instance_type'],
            'worker': cloud_instances.iloc[1]['instance_type']
        }

print("=" * 100)
print("📊 SELECTED INSTANCE TYPES")
print("=" * 100)
for cloud, instances in instance_map.items():
    print(f"{cloud}: Driver={instances['driver']}, Worker={instances['worker']}")
print("=" * 100)

# COMMAND ----------

# Get available regions
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

region_map = {}
for cloud in ['AWS', 'AZURE', 'GCP']:
    cloud_regions = available_regions_df[available_regions_df['cloud'] == cloud]
    if len(cloud_regions) >= 2:
        us_region = cloud_regions[cloud_regions['region_code'].str.contains('us')].iloc[0]['region_code']
        eu_region = cloud_regions[cloud_regions['region_code'].str.contains('eu')].iloc[0]['region_code']
        region_map[cloud] = {'us': us_region, 'eu': eu_region}

print("📊 SELECTED REGIONS")
for cloud, regions in region_map.items():
    print(f"{cloud}: US={regions['us']}, EU={regions['eu']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Define Test Scenarios
# MAGIC 
# MAGIC ALL_PURPOSE clusters typically run continuously or for long periods

# COMMAND ----------

test_scenarios = []
scenario_id = 1

# Usage patterns for ALL_PURPOSE (interactive use)
usage_patterns = [
    {'name': 'Part-Time', 'runs_per_day': 8, 'avg_runtime_minutes': 60},   # 8 hours/day
    {'name': 'Full-Time', 'runs_per_day': 24, 'avg_runtime_minutes': 60},  # 24/7 continuous
]

# VM pricing tiers (payment_option matches Test_01 pattern)
pricing_tiers = [
    {'name': 'OnDemand', 'driver_tier': 'on_demand', 'worker_tier': 'on_demand', 'payment': 'on_demand'},
    {'name': 'Spot', 'driver_tier': 'on_demand', 'worker_tier': 'spot', 'payment': 'spot'},  # Driver can't be spot
    {'name': 'Reserved1Y', 'driver_tier': 'reserved_1y', 'worker_tier': 'reserved_1y', 'payment': 'partial_upfront'},
]

# Photon options
photon_options = [True, False]

# Generate scenarios
for cloud in ['AWS', 'AZURE', 'GCP']:
    for region_key in ['us', 'eu']:
        for tier in ['STANDARD', 'PREMIUM', 'ENTERPRISE']:
            if cloud == 'AZURE' and tier == 'ENTERPRISE':
                continue
            
            for photon in photon_options:
                for pricing in pricing_tiers:
                    for usage in usage_patterns:
                        region = region_map[cloud][region_key]
                        driver_instance = instance_map[cloud]['driver']
                        worker_instance = instance_map[cloud]['worker']
                        
                        scenario = {
                            'scenario_id': scenario_id,
                            'cloud': cloud,
                            'region': region,
                            'tier': tier,
                            'workload_name': f"{cloud} {region} {tier} {'Photon' if photon else 'NoPhoton'} {pricing['name']} {usage['name']}",
                            'driver_node_type': driver_instance,
                            'worker_node_type': worker_instance,
                            'num_workers': 4,
                            'photon_enabled': photon,
                            'driver_pricing_tier': pricing['driver_tier'],
                            'worker_pricing_tier': pricing['worker_tier'],
                            'vm_payment_option': pricing['payment'],
                            'runs_per_day': usage['runs_per_day'],
                            'avg_runtime_minutes': usage['avg_runtime_minutes'],
                            'days_per_month': 30,
                            'notes': f"ALL_PURPOSE {usage['name']}, {pricing['name']}, {'Photon' if photon else 'No Photon'}"
                        }
                        
                        test_scenarios.append(scenario)
                        scenario_id += 1

print(f"✅ Generated {len(test_scenarios)} test scenarios")
print(f"   Clouds: 3, Regions: 2/cloud, Tiers: 3")
print(f"   Photon: 2, Pricing: 3, Usage: 2")
print(f"   Azure ENTERPRISE excluded")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Create Estimates

# COMMAND ----------

unique_combos = {}
for scenario in test_scenarios:
    key = f"{scenario['cloud']}_{scenario['region']}_{scenario['tier']}"
    if key not in unique_combos:
        unique_combos[key] = {
            'cloud': scenario['cloud'],
            'region': scenario['region'],
            'tier': scenario['tier']
        }

estimate_map = {}

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
# MAGIC ## 6. Insert Line Items

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

line_item_ids = []

print(f"📝 Inserting {len(test_scenarios)} line items...")
for i, scenario in enumerate(test_scenarios, 1):
    line_item_id = str(uuid.uuid4())
    line_item_ids.append(line_item_id)
    
    estimate_key = f"{scenario['cloud']}_{scenario['region']}_{scenario['tier']}"
    estimate_id = estimate_map[estimate_key]
    
    execute_query(
        insert_line_item_sql,
        (
            line_item_id,
            estimate_id,
            scenario['scenario_id'],
            scenario['workload_name'],
            'ALL_PURPOSE',  # workload_type (KEY!)
            False,  # serverless_enabled
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
    
    if i % 20 == 0:
        print(f"   ✅ Inserted {i}/{len(test_scenarios)} line items...")

print(f"\n🎉 Successfully inserted {len(line_item_ids)} test line items!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Execute Cost Calculation View & Display Results

# COMMAND ----------

query_results_sql = """
SELECT 
    c.display_order,
    c.workload_name,
    c.workload_type,
    c.cloud,
    c.region,
    c.tier,
    c.driver_node_type,
    c.worker_node_type,
    c.num_workers,
    c.photon_enabled,
    c.serverless_enabled,
    c.runs_per_day,
    c.avg_runtime_minutes,
    c.days_per_month,
    c.hours_per_month,
    c.driver_pricing_tier,
    c.worker_pricing_tier,
    c.vm_payment_option,
    c.driver_dbu_rate,
    c.worker_dbu_rate,
    c.photon_multiplier,
    c.dbu_per_hour,
    c.dbu_per_month,
    c.driver_vm_cost_per_hour,
    c.worker_vm_cost_per_hour,
    c.total_vm_cost_per_hour,
    c.vm_cost_per_month,
    c.price_per_dbu as dbu_price,
    c.product_type_for_pricing,
    c.dbu_cost_per_month,
    c.cost_per_month,
    c.notes
FROM lakemeter.v_line_items_with_costs c
WHERE c.line_item_id = ANY(%s::uuid[])
ORDER BY c.display_order;
"""

results_df = execute_query(query_results_sql, (line_item_ids,))

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

# COMMAND ----------

# Summary by cloud
print("\n" + "=" * 100)
print("📊 RESULTS SUMMARY BY CLOUD")
print("=" * 100)

summary_df = results_df.groupby(['cloud', 'tier', 'photon_enabled']).agg({
    'workload_name': 'count',
    'vm_cost_per_month': 'sum',
    'dbu_cost_per_month': 'sum',
    'cost_per_month': 'sum'
}).rename(columns={'workload_name': 'count'})

print(summary_df.to_string())

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Display Results - Summary View

# COMMAND ----------

summary_display_df = results_df[[
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
    'hours_per_month',
    'driver_vm_cost_per_hour',
    'worker_vm_cost_per_hour',
    'total_vm_cost_per_hour',
    'dbu_per_hour',
    'dbu_price',
    'vm_cost_per_month',
    'dbu_cost_per_month',
    'cost_per_month'
]].copy()

# Format
summary_display_df['driver_vm_cost_per_hour'] = summary_display_df['driver_vm_cost_per_hour'].round(6)
summary_display_df['worker_vm_cost_per_hour'] = summary_display_df['worker_vm_cost_per_hour'].round(6)
summary_display_df['total_vm_cost_per_hour'] = summary_display_df['total_vm_cost_per_hour'].round(6)
summary_display_df['dbu_per_hour'] = summary_display_df['dbu_per_hour'].round(4)
summary_display_df['dbu_price'] = summary_display_df['dbu_price'].round(6)
summary_display_df['vm_cost_per_month'] = summary_display_df['vm_cost_per_month'].round(2)
summary_display_df['dbu_cost_per_month'] = summary_display_df['dbu_cost_per_month'].round(2)
summary_display_df['cost_per_month'] = summary_display_df['cost_per_month'].round(2)

print("=" * 200)
print("ALL_PURPOSE CLASSIC - COST CALCULATION SUMMARY")
print("=" * 200)
print(tabulate(summary_display_df, headers='keys', tablefmt='grid', showindex=False, maxcolwidths=30))
print("=" * 200)

display(summary_display_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Detailed Breakdown by Cloud

# COMMAND ----------

# AWS
aws_scenarios = [s for s in test_scenarios if s['cloud'] == 'AWS']
aws_results = results_df[results_df['display_order'].isin([s['scenario_id'] for s in aws_scenarios])]

print("\n" + "=" * 120)
print("AWS ALL_PURPOSE RESULTS")
print("=" * 120)
print(f"Total Scenarios: {len(aws_scenarios)}")
print(f"Total Monthly Cost: ${aws_results['cost_per_month'].sum():,.2f}")
print(f"Total DBUs: {aws_results['dbu_per_month'].sum():,.2f}")
print("=" * 120)

display(aws_results[['workload_name', 'region', 'tier', 'photon_enabled',
                      'driver_pricing_tier', 'worker_pricing_tier',
                      'hours_per_month', 'vm_cost_per_month', 'dbu_cost_per_month', 'cost_per_month']])

# COMMAND ----------

# Azure
azure_scenarios = [s for s in test_scenarios if s['cloud'] == 'AZURE']
azure_results = results_df[results_df['display_order'].isin([s['scenario_id'] for s in azure_scenarios])]

print("\n" + "=" * 120)
print("AZURE ALL_PURPOSE RESULTS")
print("=" * 120)
print(f"Total Scenarios: {len(azure_scenarios)}")
print(f"Total Monthly Cost: ${azure_results['cost_per_month'].sum():,.2f}")
print(f"Total DBUs: {azure_results['dbu_per_month'].sum():,.2f}")
print("=" * 120)

display(azure_results[['workload_name', 'region', 'tier', 'photon_enabled',
                        'driver_pricing_tier', 'worker_pricing_tier',
                        'hours_per_month', 'vm_cost_per_month', 'dbu_cost_per_month', 'cost_per_month']])

# COMMAND ----------

# GCP
gcp_scenarios = [s for s in test_scenarios if s['cloud'] == 'GCP']
gcp_results = results_df[results_df['display_order'].isin([s['scenario_id'] for s in gcp_scenarios])]

print("\n" + "=" * 120)
print("GCP ALL_PURPOSE RESULTS")
print("=" * 120)
print(f"Total Scenarios: {len(gcp_scenarios)}")
print(f"Total Monthly Cost: ${gcp_results['cost_per_month'].sum():,.2f}")
print(f"Total DBUs: {gcp_results['dbu_per_month'].sum():,.2f}")
print("=" * 120)

display(gcp_results[['workload_name', 'region', 'tier', 'photon_enabled',
                      'driver_pricing_tier', 'worker_pricing_tier',
                      'hours_per_month', 'vm_cost_per_month', 'dbu_cost_per_month', 'cost_per_month']])

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Summary & Assertions

# COMMAND ----------

print("\n" + "=" * 120)
print("📊 FINAL SUMMARY - ALL_PURPOSE CLASSIC TEST")
print("=" * 120)

total_scenarios = len(results_df)
total_vm_cost = results_df['vm_cost_per_month'].sum()
total_dbu_cost = results_df['dbu_cost_per_month'].sum()
total_cost = results_df['cost_per_month'].sum()

print(f"\n✅ Total test scenarios: {total_scenarios}")
print(f"✅ Total VM cost: ${total_vm_cost:,.2f}")
print(f"✅ Total DBU cost: ${total_dbu_cost:,.2f}")
print(f"✅ Total cost: ${total_cost:,.2f}")

print("\n🔍 Key Validations:")

# 1. All scenarios have results
assert total_scenarios == len(test_scenarios), f"❌ FAIL: Expected {len(test_scenarios)} results, got {total_scenarios}"
print(f"   ✅ All {total_scenarios} scenarios have results")

# 2. All costs should be positive
assert (results_df['cost_per_month'] > 0).all(), "❌ FAIL: Some costs are $0 or negative"
print("   ✅ All costs are positive")

# 3. VM costs should be positive (classic compute)
assert (results_df['vm_cost_per_month'] > 0).all(), "❌ FAIL: Some VM costs are $0 for classic compute"
print("   ✅ All VM costs are positive (correct for classic)")

# 4. DBU costs should be positive
assert (results_df['dbu_cost_per_month'] > 0).all(), "❌ FAIL: Some DBU costs are $0"
print("   ✅ All DBU costs are positive")

# 5. Total cost = VM cost + DBU cost
cost_sum_check = (results_df['vm_cost_per_month'] + results_df['dbu_cost_per_month'] - results_df['cost_per_month']).abs() < 0.01
assert cost_sum_check.all(), "❌ FAIL: Total cost ≠ VM cost + DBU cost"
print("   ✅ Total cost = VM cost + DBU cost")

print("\n" + "=" * 120)
print("🎉 ALL TESTS PASSED!")
print("=" * 120)
print("\n📋 Test Coverage:")
print(f"   ✓ 3 clouds (AWS, Azure, GCP)")
print(f"   ✓ 6 regions (2 per cloud)")
print(f"   ✓ 3 tiers (STANDARD, PREMIUM, ENTERPRISE)")
print(f"   ✓ 2 Photon options (enabled/disabled)")
print(f"   ✓ 3 pricing tiers (on-demand, spot, reserved)")
print(f"   ✓ 2 usage patterns (part-time, full-time)")
print(f"   ✓ Total: {total_scenarios} comprehensive scenarios")
print("\n✅ ALL_PURPOSE Classic cost calculation is working correctly!")
print("=" * 120)

# COMMAND ----------

