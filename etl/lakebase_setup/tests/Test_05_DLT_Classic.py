# Databricks notebook source
# MAGIC %md
# MAGIC # Test Case: DLT (Delta Live Tables) Classic Compute
# MAGIC 
# MAGIC **Objective:** Validate DLT cost calculations with classic compute
# MAGIC 
# MAGIC **DLT-Specific Features:**
# MAGIC - **Editions:** CORE, PRO, ADVANCED (different DBU rates)
# MAGIC - **Pipeline Mode:** CONTINUOUS, TRIGGERED
# MAGIC - **Product Types:** DLT_CORE_COMPUTE, DLT_PRO_COMPUTE, DLT_ADVANCED_COMPUTE
# MAGIC - **Photon:** Optional (separate product type with (PHOTON) suffix)
# MAGIC 
# MAGIC **Test Matrix:**
# MAGIC - 3 clouds × 2 regions × 3 tiers × 3 editions × 2 photon × 2 modes = ~216 scenarios

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

LAKEBASE_HOST = "instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com"
LAKEBASE_PORT = 5432
LAKEBASE_DB = "lakemeter_pricing"
LAKEBASE_USER = "lakemeter_sync_role"
LAKEBASE_PASSWORD = dbutils.secrets.get(scope="lakemeter-credentials", key="lakebase-password")

def get_connection():
    return psycopg2.connect(host=LAKEBASE_HOST, port=LAKEBASE_PORT, database=LAKEBASE_DB, user=LAKEBASE_USER, password=LAKEBASE_PASSWORD)

def execute_query(query, params=None, fetch=True):
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
# MAGIC ## Setup Test Data

# COMMAND ----------

TEST_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
TEST_USER_ID = str(uuid.uuid4())

execute_query(
    "INSERT INTO lakemeter.users (user_id, full_name, email, role, is_active, created_at) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (user_id) DO NOTHING;",
    (TEST_USER_ID, f'test_dlt_classic_{TEST_RUN_ID}', f'test_{TEST_RUN_ID}@databricks.com', 'admin', True, datetime.now()),
    fetch=False
)

# Get instances
instance_query_sql = """
SELECT cloud, instance_type, dbu_rate
FROM lakemeter.sync_ref_instance_dbu_rates
WHERE (cloud = 'AWS' AND instance_type LIKE 'i3.%')
   OR (cloud = 'AZURE' AND instance_type LIKE 'Standard_D%as%')
   OR (cloud = 'GCP' AND instance_type LIKE 'n2-standard-%')
ORDER BY cloud, dbu_rate;
"""

available_instances_df = execute_query(instance_query_sql)

instance_map = {}
for cloud in ['AWS', 'AZURE', 'GCP']:
    cloud_instances = available_instances_df[available_instances_df['cloud'] == cloud].sort_values('dbu_rate')
    if len(cloud_instances) >= 2:
        instance_map[cloud] = {'driver': cloud_instances.iloc[0]['instance_type'], 'worker': cloud_instances.iloc[1]['instance_type']}

# Get regions
region_query_sql = """
SELECT DISTINCT cloud, region_code
FROM lakemeter.sync_ref_sku_region_map
WHERE (cloud = 'AWS' AND (region_code LIKE 'us-east-%' OR region_code LIKE 'eu-west-%'))
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

print("✅ Test user and reference data loaded")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Define Test Scenarios

# COMMAND ----------

test_scenarios = []
scenario_id = 1

# DLT editions
editions = ['CORE', 'PRO', 'ADVANCED']

# Pipeline modes
pipeline_modes = ['CONTINUOUS', 'TRIGGERED']

# Photon options
photon_options = [True, False]

# Usage (for TRIGGERED mode)
usage_patterns = [
    {'runs_per_day': 4, 'avg_runtime_minutes': 60},   # Light
    {'runs_per_day': 24, 'avg_runtime_minutes': 60},  # CONTINUOUS equivalent
]

for cloud in ['AWS', 'AZURE', 'GCP']:
    for region_key in ['us', 'eu']:
        for tier in ['STANDARD', 'PREMIUM', 'ENTERPRISE']:
            if cloud == 'AZURE' and tier == 'ENTERPRISE':
                continue
            
            for edition in editions:
                for photon in photon_options:
                    for mode in pipeline_modes:
                        # Select usage pattern (use continuous for CONTINUOUS mode)
                        usage_idx = 1 if mode == 'CONTINUOUS' else 0
                        usage = usage_patterns[usage_idx]
                        
                        region = region_map[cloud][region_key]
                        driver_instance = instance_map[cloud]['driver']
                        worker_instance = instance_map[cloud]['worker']
                        
                        scenario = {
                            'scenario_id': scenario_id,
                            'cloud': cloud,
                            'region': region,
                            'tier': tier,
                            'workload_name': f"{cloud} {region} {tier} {edition} {'Photon' if photon else 'NoPhoton'} {mode}",
                            'dlt_edition': edition,
                            'dlt_pipeline_mode': mode,
                            'driver_node_type': driver_instance,
                            'worker_node_type': worker_instance,
                            'num_workers': 4,
                            'photon_enabled': photon,
                            'driver_pricing_tier': 'on_demand',
                            'worker_pricing_tier': 'on_demand',
                            'vm_payment_option': 'on_demand',
                            'runs_per_day': usage['runs_per_day'],
                            'avg_runtime_minutes': usage['avg_runtime_minutes'],
                            'days_per_month': 30,
                            'notes': f"DLT {edition} {mode} {'Photon' if photon else 'No Photon'}"
                        }
                        
                        test_scenarios.append(scenario)
                        scenario_id += 1

print(f"✅ Generated {len(test_scenarios)} test scenarios")
print(f"   3 clouds × 2 regions × 3 tiers × 3 editions × 2 photon × 2 modes")
print(f"   Azure ENTERPRISE excluded")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Estimates & Line Items

# COMMAND ----------

# Create estimates (one per cloud/region/tier)
unique_combos = {}
for scenario in test_scenarios:
    key = f"{scenario['cloud']}_{scenario['region']}_{scenario['tier']}"
    if key not in unique_combos:
        unique_combos[key] = {'cloud': scenario['cloud'], 'region': scenario['region'], 'tier': scenario['tier']}

estimate_map = {}

for key, combo in unique_combos.items():
    estimate_id = str(uuid.uuid4())
    estimate_map[key] = estimate_id
    
    execute_query(
        "INSERT INTO lakemeter.estimates (estimate_id, owner_user_id, estimate_name, cloud, region, tier, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);",
        (estimate_id, TEST_USER_ID, f"Test: {combo['cloud']} {combo['region']} {combo['tier']}", 
         combo['cloud'], combo['region'], combo['tier'], datetime.now(), datetime.now()),
        fetch=False
    )

print(f"✅ Created {len(estimate_map)} estimates")

# COMMAND ----------

# Insert line items
insert_line_item_sql = """
INSERT INTO lakemeter.line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, serverless_mode, photon_enabled, vector_search_mode,
    dlt_edition, dlt_pipeline_mode,
    driver_node_type, worker_node_type, num_workers,
    runs_per_day, avg_runtime_minutes, days_per_month,
    driver_pricing_tier, worker_pricing_tier, vm_payment_option,
    notes, created_at, updated_at
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
"""

line_item_ids = []

for i, scenario in enumerate(test_scenarios, 1):
    line_item_id = str(uuid.uuid4())
    line_item_ids.append(line_item_id)
    
    estimate_key = f"{scenario['cloud']}_{scenario['region']}_{scenario['tier']}"
    estimate_id = estimate_map[estimate_key]
    
    execute_query(
        insert_line_item_sql,
        (line_item_id, estimate_id, scenario['scenario_id'], scenario['workload_name'], 'DLT',
         False, None, scenario['photon_enabled'], None,  # serverless=FALSE (Classic)
         scenario['dlt_edition'], scenario['dlt_pipeline_mode'],
         scenario['driver_node_type'], scenario['worker_node_type'], scenario['num_workers'],
         scenario['runs_per_day'], scenario['avg_runtime_minutes'], scenario['days_per_month'],
         scenario['driver_pricing_tier'], scenario['worker_pricing_tier'], scenario['vm_payment_option'],
         scenario['notes'], datetime.now(), datetime.now()),
        fetch=False
    )
    
    if i % 50 == 0:
        print(f"   ✅ Inserted {i}/{len(test_scenarios)} line items...")

print(f"✅ Inserted {len(line_item_ids)} line items")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Query Results

# COMMAND ----------

query_results_sql = """
SELECT c.display_order, c.workload_name, c.workload_type, c.cloud, c.region, c.tier,
       c.dlt_edition, c.dlt_pipeline_mode,
       c.driver_node_type, c.worker_node_type, c.num_workers, c.photon_enabled, c.serverless_enabled,
       c.runs_per_day, c.avg_runtime_minutes, c.hours_per_month,
       c.driver_dbu_rate, c.worker_dbu_rate, c.photon_multiplier, c.dbu_per_hour, c.dbu_per_month,
       c.driver_vm_cost_per_hour, c.worker_vm_cost_per_hour, c.vm_cost_per_month,
       c.price_per_dbu as dbu_price, c.product_type_for_pricing, c.dbu_cost_per_month, c.cost_per_month
FROM lakemeter.v_line_items_with_costs c
WHERE c.line_item_id = ANY(%s::uuid[])
ORDER BY c.display_order;
"""

results_df = execute_query(query_results_sql, (line_item_ids,))

numeric_columns = ['display_order', 'num_workers', 'runs_per_day', 'avg_runtime_minutes', 'hours_per_month',
                   'driver_dbu_rate', 'worker_dbu_rate', 'photon_multiplier', 'dbu_per_hour', 'dbu_per_month',
                   'driver_vm_cost_per_hour', 'worker_vm_cost_per_hour', 'vm_cost_per_month',
                   'dbu_price', 'dbu_cost_per_month', 'cost_per_month']
for col in numeric_columns:
    if col in results_df.columns:
        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

print(f"✅ Retrieved {len(results_df)} results")

# COMMAND ----------

# Summary
summary_df = results_df.groupby(['cloud', 'tier', 'dlt_edition', 'photon_enabled']).agg({
    'workload_name': 'count',
    'vm_cost_per_month': 'sum',
    'dbu_cost_per_month': 'sum',
    'cost_per_month': 'sum'
}).rename(columns={'workload_name': 'count'})

print("\n" + "=" * 100)
print("📊 RESULTS SUMMARY")
print("=" * 100)
print(summary_df.head(20).to_string())

# COMMAND ----------

# Display results
summary_display_df = results_df[[
    'workload_name', 'cloud', 'region', 'tier',
    'dlt_edition', 'dlt_pipeline_mode', 'photon_enabled',
    'hours_per_month', 'dbu_per_hour', 'dbu_price',
    'vm_cost_per_month', 'dbu_cost_per_month', 'cost_per_month'
]].copy()

summary_display_df['dbu_per_hour'] = summary_display_df['dbu_per_hour'].round(4)
summary_display_df['dbu_price'] = summary_display_df['dbu_price'].round(6)
summary_display_df['vm_cost_per_month'] = summary_display_df['vm_cost_per_month'].round(2)
summary_display_df['dbu_cost_per_month'] = summary_display_df['dbu_cost_per_month'].round(2)
summary_display_df['cost_per_month'] = summary_display_df['cost_per_month'].round(2)

print("=" * 200)
print("DLT CLASSIC - COST CALCULATION SUMMARY")
print("=" * 200)
print(tabulate(summary_display_df.head(20), headers='keys', tablefmt='grid', showindex=False, maxcolwidths=25))

display(summary_display_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation

# COMMAND ----------

print("\n" + "=" * 120)
print("📊 FINAL SUMMARY - DLT CLASSIC TEST")
print("=" * 120)

total_scenarios = len(results_df)
total_vm_cost = results_df['vm_cost_per_month'].sum()
total_dbu_cost = results_df['dbu_cost_per_month'].sum()
total_cost = results_df['cost_per_month'].sum()

print(f"\n✅ Total scenarios: {total_scenarios}")
print(f"✅ Total VM cost: ${total_vm_cost:,.2f}")
print(f"✅ Total DBU cost: ${total_dbu_cost:,.2f}")
print(f"✅ Total cost: ${total_cost:,.2f}")

print("\n🔍 Validations:")

# All scenarios present
assert total_scenarios == len(test_scenarios), f"❌ FAIL: Expected {len(test_scenarios)}, got {total_scenarios}"
print(f"   ✅ All {total_scenarios} scenarios present")

# All costs positive
assert (results_df['cost_per_month'] > 0).all(), "❌ FAIL: Some costs are $0 or negative"
print("   ✅ All costs are positive")

# VM costs positive (classic compute)
assert (results_df['vm_cost_per_month'] > 0).all(), "❌ FAIL: Some VM costs are $0"
print("   ✅ All VM costs positive (correct for classic)")

# Total cost = VM + DBU
cost_sum_check = (results_df['vm_cost_per_month'] + results_df['dbu_cost_per_month'] - results_df['cost_per_month']).abs() < 0.01
assert cost_sum_check.all(), "❌ FAIL: Total ≠ VM + DBU"
print("   ✅ Total cost = VM cost + DBU cost")

print("\n" + "=" * 120)
print("🎉 ALL TESTS PASSED!")
print("=" * 120)
print(f"\n✅ DLT Classic cost calculation working correctly!")
print(f"   Covers: 3 editions (CORE/PRO/ADVANCED), 2 modes (CONTINUOUS/TRIGGERED), Photon on/off")
print("=" * 120)

# COMMAND ----------
