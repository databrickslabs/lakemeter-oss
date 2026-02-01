# Databricks notebook source
# MAGIC %md
# MAGIC # Test Case: ALL_PURPOSE (Interactive) Serverless Compute
# MAGIC 
# MAGIC **Objective:** Validate cost calculations for ALL_PURPOSE workload type with serverless compute
# MAGIC 
# MAGIC **Key Characteristics:**
# MAGIC - ✅ NO VM costs (serverless)
# MAGIC - ✅ DBU costs only
# MAGIC - ✅ Photon always enabled
# MAGIC - ✅ NO performance mode (unlike JOBS/DLT serverless)
# MAGIC - ✅ Uses ALL_PURPOSE_SERVERLESS_COMPUTE product type
# MAGIC 
# MAGIC **Test Matrix:**
# MAGIC - 3 clouds × 2 regions × 3 tiers × 2 usage patterns = ~36 scenarios

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
# MAGIC ## Generate Test Data

# COMMAND ----------

TEST_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
TEST_USER_ID = str(uuid.uuid4())

execute_query(
    "INSERT INTO lakemeter.users (user_id, full_name, email, role, is_active, created_at) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (user_id) DO NOTHING;",
    (TEST_USER_ID, f'test_all_purpose_serverless_{TEST_RUN_ID}', f'test_{TEST_RUN_ID}@databricks.com', 'admin', True, datetime.now()),
    fetch=False
)

print(f"✅ Test user created: test_all_purpose_serverless_{TEST_RUN_ID}")

# COMMAND ----------

# Get instance types (for sizing estimation only)
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

print("✅ Instance types and regions loaded")

# COMMAND ----------

# Define test scenarios
test_scenarios = []
scenario_id = 1

usage_patterns = [
    {'name': 'Part-Time', 'runs_per_day': 8, 'avg_runtime_minutes': 60},   # 8 hours/day
    {'name': 'Full-Time', 'runs_per_day': 24, 'avg_runtime_minutes': 60},  # 24/7
]

for cloud in ['AWS', 'AZURE', 'GCP']:
    for region_key in ['us', 'eu']:
        for tier in ['STANDARD', 'PREMIUM', 'ENTERPRISE']:
            if cloud == 'AZURE' and tier == 'ENTERPRISE':
                continue
            
            for usage in usage_patterns:
                region = region_map[cloud][region_key]
                driver_instance = instance_map[cloud]['driver']
                worker_instance = instance_map[cloud]['worker']
                
                scenario = {
                    'scenario_id': scenario_id,
                    'cloud': cloud,
                    'region': region,
                    'tier': tier,
                    'workload_name': f"{cloud} {region} {tier} {usage['name']} Interactive",
                    'driver_node_type': driver_instance,
                    'worker_node_type': worker_instance,
                    'num_workers': 4,
                    'runs_per_day': usage['runs_per_day'],
                    'avg_runtime_minutes': usage['avg_runtime_minutes'],
                    'days_per_month': 30,
                    'notes': f"ALL_PURPOSE Serverless {usage['name']} (VMs for sizing only)"
                }
                
                test_scenarios.append(scenario)
                scenario_id += 1

print(f"✅ Generated {len(test_scenarios)} test scenarios")

# COMMAND ----------

# Create estimates
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
    driver_node_type, worker_node_type, num_workers,
    runs_per_day, avg_runtime_minutes, days_per_month,
    driver_pricing_tier, worker_pricing_tier, vm_payment_option,
    notes, created_at, updated_at
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
"""

line_item_ids = []

for i, scenario in enumerate(test_scenarios, 1):
    line_item_id = str(uuid.uuid4())
    line_item_ids.append(line_item_id)
    
    estimate_key = f"{scenario['cloud']}_{scenario['region']}_{scenario['tier']}"
    estimate_id = estimate_map[estimate_key]
    
    execute_query(
        insert_line_item_sql,
        (line_item_id, estimate_id, scenario['scenario_id'], scenario['workload_name'], 'ALL_PURPOSE',
         True, None, True, None,  # serverless_enabled=TRUE, serverless_mode=NULL, photon=TRUE
         scenario['driver_node_type'], scenario['worker_node_type'], scenario['num_workers'],
         scenario['runs_per_day'], scenario['avg_runtime_minutes'], scenario['days_per_month'],
         None, None, None,  # No pricing tiers for serverless
         scenario['notes'], datetime.now(), datetime.now()),
        fetch=False
    )

print(f"✅ Inserted {len(line_item_ids)} line items")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Query Results

# COMMAND ----------

query_results_sql = """
SELECT c.display_order, c.workload_name, c.workload_type, c.cloud, c.region, c.tier,
       c.driver_node_type, c.worker_node_type, c.num_workers, c.photon_enabled, c.serverless_enabled,
       c.runs_per_day, c.avg_runtime_minutes, c.days_per_month, c.hours_per_month,
       c.driver_dbu_rate, c.worker_dbu_rate, c.photon_multiplier, c.dbu_per_hour, c.dbu_per_month,
       c.driver_vm_cost_per_hour, c.worker_vm_cost_per_hour, c.vm_cost_per_month,
       c.price_per_dbu as dbu_price, c.product_type_for_pricing, c.dbu_cost_per_month, c.cost_per_month
FROM lakemeter.v_line_items_with_costs c
WHERE c.line_item_id = ANY(%s::uuid[])
ORDER BY c.display_order;
"""

results_df = execute_query(query_results_sql, (line_item_ids,))

numeric_columns = ['display_order', 'num_workers', 'runs_per_day', 'avg_runtime_minutes', 'days_per_month', 'hours_per_month',
                   'driver_dbu_rate', 'worker_dbu_rate', 'photon_multiplier', 'dbu_per_hour', 'dbu_per_month',
                   'driver_vm_cost_per_hour', 'worker_vm_cost_per_hour', 'vm_cost_per_month',
                   'dbu_price', 'dbu_cost_per_month', 'cost_per_month']
for col in numeric_columns:
    if col in results_df.columns:
        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

print(f"✅ Retrieved {len(results_df)} results")

# COMMAND ----------

# Display summary
summary_df = results_df.groupby(['cloud', 'tier']).agg({
    'workload_name': 'count',
    'vm_cost_per_month': 'sum',
    'dbu_cost_per_month': 'sum',
    'cost_per_month': 'sum'
}).rename(columns={'workload_name': 'count'})

print("\n" + "=" * 100)
print("📊 RESULTS SUMMARY BY CLOUD")
print("=" * 100)
print(summary_df.to_string())
print(f"\n⚠️  Total VM cost should be $0: ${results_df['vm_cost_per_month'].sum():,.2f}")

# COMMAND ----------

# Display results
summary_display_df = results_df[[
    'workload_name', 'cloud', 'region', 'tier',
    'driver_node_type', 'worker_node_type', 'num_workers',
    'hours_per_month', 'dbu_per_hour', 'dbu_price',
    'vm_cost_per_month', 'dbu_cost_per_month', 'cost_per_month'
]].copy()

summary_display_df['dbu_per_hour'] = summary_display_df['dbu_per_hour'].round(4)
summary_display_df['dbu_price'] = summary_display_df['dbu_price'].round(6)
summary_display_df['vm_cost_per_month'] = summary_display_df['vm_cost_per_month'].round(2)
summary_display_df['dbu_cost_per_month'] = summary_display_df['dbu_cost_per_month'].round(2)
summary_display_df['cost_per_month'] = summary_display_df['cost_per_month'].round(2)

print("=" * 180)
print("ALL_PURPOSE SERVERLESS - COST CALCULATION SUMMARY")
print("=" * 180)
print(tabulate(summary_display_df, headers='keys', tablefmt='grid', showindex=False, maxcolwidths=30))

display(summary_display_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation

# COMMAND ----------

print("\n" + "=" * 120)
print("📊 FINAL SUMMARY - ALL_PURPOSE SERVERLESS TEST")
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

# VM costs should be $0
assert total_vm_cost == 0, f"❌ FAIL: VM cost should be $0, got ${total_vm_cost:,.2f}"
print("   ✅ VM costs are $0 (correct for serverless)")

# All scenarios present
assert total_scenarios == len(test_scenarios), f"❌ FAIL: Expected {len(test_scenarios)}, got {total_scenarios}"
print(f"   ✅ All {total_scenarios} scenarios present")

# STANDARD tier should have $0 costs (serverless not available)
standard_tier_results = results_df[results_df['tier'] == 'STANDARD']
if len(standard_tier_results) > 0:
    assert (standard_tier_results['cost_per_month'] == 0).all(), "❌ FAIL: STANDARD tier should have $0 costs (serverless not available)"
    print(f"   ✅ All {len(standard_tier_results)} STANDARD tier scenarios have $0 costs (expected - serverless N/A)")

# PREMIUM/ENTERPRISE tiers should have positive costs
premium_enterprise_results = results_df[results_df['tier'].isin(['PREMIUM', 'ENTERPRISE'])]
if len(premium_enterprise_results) > 0:
    assert (premium_enterprise_results['cost_per_month'] > 0).all(), "❌ FAIL: PREMIUM/ENTERPRISE should have positive costs"
    print(f"   ✅ All {len(premium_enterprise_results)} PREMIUM/ENTERPRISE scenarios have positive costs")

# DBU cost = Total cost
assert (results_df['dbu_cost_per_month'] == results_df['cost_per_month']).all(), "❌ FAIL: DBU cost should equal total"
print("   ✅ DBU cost = Total cost")

print("\n" + "=" * 120)
print("🎉 ALL TESTS PASSED!")
print("=" * 120)
print(f"\n✅ ALL_PURPOSE Serverless cost calculation working correctly!")
print(f"   Total: {total_scenarios} scenarios across 3 clouds, 6 regions, 3 tiers, 2 usage patterns")
print("=" * 120)

# COMMAND ----------

