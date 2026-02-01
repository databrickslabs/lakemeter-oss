# Databricks notebook source
# MAGIC %md
# MAGIC # Test Case: DLT (Delta Live Tables) Serverless Compute
# MAGIC 
# MAGIC **Objective:** Validate DLT serverless cost calculations
# MAGIC 
# MAGIC **DLT Serverless Features:**
# MAGIC - **Serverless modes:** standard (1x), performance (2x multiplier)
# MAGIC - **NO VM costs**
# MAGIC - **Photon always enabled**
# MAGIC - **Product type:** JOBS_SERVERLESS_COMPUTE
# MAGIC - **Pipeline modes:** CONTINUOUS, TRIGGERED
# MAGIC 
# MAGIC **Test Matrix:**
# MAGIC - 3 clouds × 2 regions × 3 tiers × 2 modes × 2 pipeline types = ~72 scenarios

# COMMAND ----------

%pip install psycopg2-binary pandas tabulate

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import psycopg2, pandas as pd, uuid
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

print("✅ Setup complete!")

# COMMAND ----------

# Create test user
TEST_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
TEST_USER_ID = str(uuid.uuid4())
execute_query("INSERT INTO lakemeter.users (user_id, full_name, email, role, is_active, created_at) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;",
              (TEST_USER_ID, f'test_dlt_serverless_{TEST_RUN_ID}', f'test_{TEST_RUN_ID}@databricks.com', 'admin', True, datetime.now()), fetch=False)

# Get instances (for sizing only)
available_instances_df = execute_query("SELECT cloud, instance_type, dbu_rate FROM lakemeter.sync_ref_instance_dbu_rates WHERE (cloud = 'AWS' AND instance_type LIKE 'i3.%') OR (cloud = 'AZURE' AND instance_type LIKE 'Standard_D%as%') OR (cloud = 'GCP' AND instance_type LIKE 'n2-standard-%') ORDER BY cloud, dbu_rate;")
instance_map = {}
for cloud in ['AWS', 'AZURE', 'GCP']:
    cloud_instances = available_instances_df[available_instances_df['cloud'] == cloud].sort_values('dbu_rate')
    if len(cloud_instances) >= 2:
        instance_map[cloud] = {'driver': cloud_instances.iloc[0]['instance_type'], 'worker': cloud_instances.iloc[1]['instance_type']}

# Get regions
available_regions_df = execute_query("SELECT DISTINCT cloud, region_code FROM lakemeter.sync_ref_sku_region_map WHERE (cloud = 'AWS' AND (region_code LIKE 'us-east-%' OR region_code LIKE 'eu-west-%')) OR (cloud = 'AZURE' AND region_code IN ('eastus', 'westeurope')) OR (cloud = 'GCP' AND (region_code LIKE 'us-central%' OR region_code LIKE 'europe-west%')) ORDER BY cloud, region_code;")
region_map = {}
for cloud in ['AWS', 'AZURE', 'GCP']:
    cloud_regions = available_regions_df[available_regions_df['cloud'] == cloud]
    if len(cloud_regions) >= 2:
        us_region = cloud_regions[cloud_regions['region_code'].str.contains('us')].iloc[0]['region_code']
        eu_region = cloud_regions[cloud_regions['region_code'].str.contains('eu')].iloc[0]['region_code']
        region_map[cloud] = {'us': us_region, 'eu': eu_region}

print("✅ Test data loaded")

# COMMAND ----------

# Define scenarios
test_scenarios = []
scenario_id = 1
serverless_modes = ['standard', 'performance']
pipeline_modes = ['CONTINUOUS', 'TRIGGERED']
usage_patterns = [{'runs': 4, 'mins': 60}, {'runs': 24, 'mins': 60}]

for cloud in ['AWS', 'AZURE', 'GCP']:
    for region_key in ['us', 'eu']:
        for tier in ['STANDARD', 'PREMIUM', 'ENTERPRISE']:
            if cloud == 'AZURE' and tier == 'ENTERPRISE':
                continue
            for mode in serverless_modes:
                for pipe_mode in pipeline_modes:
                    usage_idx = 1 if pipe_mode == 'CONTINUOUS' else 0
                    usage = usage_patterns[usage_idx]
                    region = region_map[cloud][region_key]
                    test_scenarios.append({
                        'scenario_id': scenario_id, 'cloud': cloud, 'region': region, 'tier': tier,
                        'workload_name': f"{cloud} {region} {tier} {mode.upper()} {pipe_mode}",
                        'serverless_mode': mode, 'dlt_pipeline_mode': pipe_mode,
                        'driver_node_type': instance_map[cloud]['driver'], 'worker_node_type': instance_map[cloud]['worker'],
                        'num_workers': 4, 'runs_per_day': usage['runs'], 'avg_runtime_minutes': usage['mins'], 'days_per_month': 30,
                        'notes': f"DLT Serverless {mode} {pipe_mode}"
                    })
                    scenario_id += 1

print(f"✅ Generated {len(test_scenarios)} scenarios")

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
    execute_query("INSERT INTO lakemeter.estimates (estimate_id, owner_user_id, estimate_name, cloud, region, tier, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);",
                  (estimate_id, TEST_USER_ID, f"Test: {combo['cloud']} {combo['region']} {combo['tier']}", combo['cloud'], combo['region'], combo['tier'], datetime.now(), datetime.now()), fetch=False)

print(f"✅ Created {len(estimate_map)} estimates")

# COMMAND ----------

# Insert line items
line_item_ids = []
for i, scenario in enumerate(test_scenarios, 1):
    line_item_id = str(uuid.uuid4())
    line_item_ids.append(line_item_id)
    estimate_key = f"{scenario['cloud']}_{scenario['region']}_{scenario['tier']}"
    execute_query("""INSERT INTO lakemeter.line_items (line_item_id, estimate_id, display_order, workload_name, workload_type, serverless_enabled, serverless_mode, photon_enabled, vector_search_mode, dlt_edition, dlt_pipeline_mode, driver_node_type, worker_node_type, num_workers, runs_per_day, avg_runtime_minutes, days_per_month, driver_pricing_tier, worker_pricing_tier, vm_payment_option, notes, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                  (line_item_id, estimate_map[estimate_key], scenario['scenario_id'], scenario['workload_name'], 'DLT', True, scenario['serverless_mode'], True, None, 'CORE', scenario['dlt_pipeline_mode'], scenario['driver_node_type'], scenario['worker_node_type'], scenario['num_workers'], scenario['runs_per_day'], scenario['avg_runtime_minutes'], scenario['days_per_month'], None, None, None, scenario['notes'], datetime.now(), datetime.now()), fetch=False)

print(f"✅ Inserted {len(line_item_ids)} line items")

# COMMAND ----------

# Query results
results_df = execute_query("SELECT c.display_order, c.workload_name, c.cloud, c.region, c.tier, c.serverless_mode, c.dlt_pipeline_mode, c.hours_per_month, c.dbu_per_hour, c.price_per_dbu, c.vm_cost_per_month, c.dbu_cost_per_month, c.cost_per_month FROM lakemeter.v_line_items_with_costs c WHERE c.line_item_id = ANY(%s::uuid[]) ORDER BY c.display_order;", (line_item_ids,))

for col in ['display_order', 'hours_per_month', 'dbu_per_hour', 'price_per_dbu', 'vm_cost_per_month', 'dbu_cost_per_month', 'cost_per_month']:
    if col in results_df.columns:
        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

print(f"✅ Retrieved {len(results_df)} results")
print(f"   Total VM cost (should be $0): ${results_df['vm_cost_per_month'].sum():,.2f}")
print(f"   Total DBU cost: ${results_df['dbu_cost_per_month'].sum():,.2f}")

# COMMAND ----------

# Display
results_df['dbu_per_hour'] = results_df['dbu_per_hour'].round(4)
results_df['price_per_dbu'] = results_df['price_per_dbu'].round(6)
results_df['vm_cost_per_month'] = results_df['vm_cost_per_month'].round(2)
results_df['dbu_cost_per_month'] = results_df['dbu_cost_per_month'].round(2)
results_df['cost_per_month'] = results_df['cost_per_month'].round(2)

print("=" * 180)
print("DLT SERVERLESS - COST CALCULATION SUMMARY")
print("=" * 180)
print(tabulate(results_df.head(20), headers='keys', tablefmt='grid', showindex=False, maxcolwidths=30))
display(results_df)

# COMMAND ----------

# Validation
print("\n" + "=" * 120)
print("📊 FINAL SUMMARY - DLT SERVERLESS TEST")
print("=" * 120)
print(f"\n✅ Total scenarios: {len(results_df)}")
assert results_df['vm_cost_per_month'].sum() == 0, "❌ FAIL: VM cost should be $0"
print("   ✅ VM costs are $0 (correct for serverless)")
assert len(results_df) == len(test_scenarios), "❌ FAIL: Missing scenarios"
print(f"   ✅ All {len(test_scenarios)} scenarios present")
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
print("\n🎉 ALL TESTS PASSED!")
print("=" * 120)

# COMMAND ----------
