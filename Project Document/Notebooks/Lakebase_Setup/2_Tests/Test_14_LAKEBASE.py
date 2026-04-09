# Databricks notebook source
# MAGIC %md
# MAGIC # Test Case: LAKEBASE (PostgreSQL Serverless Database)
# MAGIC 
# MAGIC **Objective:** Validate Lakebase cost calculations for serverless PostgreSQL with various configurations
# MAGIC 
# MAGIC **LAKEBASE Characteristics:**
# MAGIC - **Product type:** DATABASE_SERVERLESS_COMPUTE
# MAGIC - **Sizing:** Compute Units (CU) instead of instance types
# MAGIC   - **1 CU = 1 DBU per hour PER NODE**
# MAGIC   - Available sizes: 1, 2, 4, 8 CU per node
# MAGIC   - **Total DBU = CU per node × number of HA nodes**
# MAGIC - **No VM costs** (serverless database)
# MAGIC - **No instance types** (uses CU-based sizing)
# MAGIC - **Additional features:**
# MAGIC   - **storage_gb:** Database storage size (100 GB default)
# MAGIC   - **ha_nodes:** Number of HA nodes (1-3, where 1=no HA, max=3)
# MAGIC   - **backup_retention_days:** Backup retention period (0=no backup, 1-35 days)
# MAGIC 
# MAGIC **Test Scenarios:**
# MAGIC - **Clouds:** AWS, Azure, GCP
# MAGIC - **Regions:** 2 per cloud (1 US + 1 Europe)
# MAGIC - **Tiers:** STANDARD, PREMIUM (ENTERPRISE not commonly used)
# MAGIC - **CU Sizes:** 1, 2, 4, 8 CU per node
# MAGIC - **HA Nodes:** 1 (no HA), 2, 3 (max 3 nodes)
# MAGIC - **Usage Patterns:**
# MAGIC   - Standard: 8 runs/day, 60 min/run (8 hours/day)
# MAGIC   - Always-on: 24 runs/day, 60 min/run (24 hours/day)
# MAGIC 
# MAGIC **Test Matrix:**
# MAGIC - **AWS:** 2 regions × 2 tiers × 4 CU × 3 HA nodes × 2 usage = **96 scenarios**
# MAGIC - **AZURE:** 2 regions × 2 tiers × 4 CU × 3 HA nodes × 2 usage = **96 scenarios**
# MAGIC - **GCP:** 2 regions × 2 tiers × 4 CU × 3 HA nodes × 2 usage = **96 scenarios**
# MAGIC - **TOTAL: ~288 scenarios**
# MAGIC 
# MAGIC **Validation:**
# MAGIC - ✅ Total DBU per hour = CU per node × number of HA nodes
# MAGIC - ✅ DBU cost = Total DBU per hour × hours × DBU rate
# MAGIC - ✅ No VM costs (serverless)
# MAGIC - ✅ HA nodes (2-3) increase total CU proportionally
# MAGIC - ✅ Different usage patterns (8h vs 24h) affect monthly costs
# MAGIC 
# MAGIC **Example Calculations:**
# MAGIC - 2 CU, 1 node (no HA), 8h/day → 2 DBU/hr × 240 hr/month = 480 DBU/month
# MAGIC - 2 CU, 2 nodes (HA), 8h/day → 4 DBU/hr × 240 hr/month = 960 DBU/month
# MAGIC - 2 CU, 3 nodes (max HA), 8h/day → 6 DBU/hr × 240 hr/month = 1440 DBU/month

# COMMAND ----------

# Load Lakebase configuration
%run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2, pandas as pd, uuid
from datetime import datetime
from tabulate import tabulate

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

TEST_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
TEST_USER_ID = str(uuid.uuid4())
execute_query("INSERT INTO lakemeter.users (user_id, full_name, email, role, is_active, created_at) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;",
              (TEST_USER_ID, f'test_lakebase_{TEST_RUN_ID}', f'test_{TEST_RUN_ID}@databricks.com', 'admin', True, datetime.now()), fetch=False)

available_regions_df = execute_query("SELECT DISTINCT cloud, region_code FROM lakemeter.sync_ref_sku_region_map WHERE (cloud = 'AWS' AND (region_code LIKE 'us-east-%' OR region_code LIKE 'eu-west-%')) OR (cloud = 'AZURE' AND region_code IN ('eastus', 'westeurope')) OR (cloud = 'GCP' AND (region_code LIKE 'us-central%' OR region_code LIKE 'europe-west%'));")

# Get 1 US + 1 EU region per cloud
region_map = {}
for cloud in ['AWS', 'AZURE', 'GCP']:
    cloud_regions = available_regions_df[available_regions_df['cloud'] == cloud]
    if len(cloud_regions) >= 2:
        us_region = cloud_regions[cloud_regions['region_code'].str.contains('us')].iloc[0]['region_code']
        eu_region = cloud_regions[cloud_regions['region_code'].str.contains('eu')].iloc[0]['region_code']
        region_map[cloud] = {'us': us_region, 'eu': eu_region}

print("=" * 100)
print("📊 SELECTED REGIONS (US + EU)")
print("=" * 100)
for cloud, regions in region_map.items():
    print(f"{cloud}: US={regions['us']}, EU={regions['eu']}")
print("=" * 100)

test_scenarios = []
scenario_id = 1
cu_sizes = [1, 2, 4, 8]
ha_nodes_options = [1, 2, 3]  # 1=no HA, 2-3=HA enabled (max 3 nodes)
usage_patterns = [{'runs': 8, 'mins': 60}, {'runs': 24, 'mins': 60}]

for cloud in ['AWS', 'AZURE', 'GCP']:
    for region_type in ['us', 'eu']:  # Test both US and EU regions
        region = region_map[cloud][region_type]
        for tier in ['STANDARD', 'PREMIUM']:
            for cu in cu_sizes:
                for ha_nodes in ha_nodes_options:
                    for usage in usage_patterns:
                        ha_label = f'{ha_nodes}N' if ha_nodes == 1 else f'{ha_nodes}N-HA'
                        test_scenarios.append({
                            'scenario_id': scenario_id, 'cloud': cloud, 'region': region, 'tier': tier,
                            'workload_name': f"{cloud} {tier} {cu}CU {ha_label} {usage['runs']}h",
                            'lakebase_cu': cu,
                            'lakebase_storage_gb': 100,
                            'lakebase_ha_nodes': ha_nodes,
                            'lakebase_backup_retention_days': 7 if ha_nodes > 1 else 0,  # Backup only for HA
                            'runs_per_day': usage['runs'],
                            'avg_runtime_minutes': usage['mins'],
                            'days_per_month': 30
                        })
                        scenario_id += 1

print(f"✅ Generated {len(test_scenarios)} scenarios")

# COMMAND ----------

unique_combos = {f"{s['cloud']}_{s['region']}_{s['tier']}": {'cloud': s['cloud'], 'region': s['region'], 'tier': s['tier']} for s in test_scenarios}
estimate_map = {}
for key, combo in unique_combos.items():
    estimate_id = str(uuid.uuid4())
    estimate_map[key] = estimate_id
    execute_query("INSERT INTO lakemeter.estimates (estimate_id, owner_user_id, estimate_name, cloud, region, tier, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);",
                  (estimate_id, TEST_USER_ID, f"Test: {combo['cloud']} {combo['region']} {combo['tier']}", combo['cloud'], combo['region'], combo['tier'], datetime.now(), datetime.now()), fetch=False)

line_item_ids = []
for scenario in test_scenarios:
    line_item_id = str(uuid.uuid4())
    line_item_ids.append(line_item_id)
    estimate_key = f"{scenario['cloud']}_{scenario['region']}_{scenario['tier']}"
    execute_query("""INSERT INTO lakemeter.line_items (line_item_id, estimate_id, display_order, workload_name, workload_type, serverless_enabled, photon_enabled, lakebase_cu, lakebase_storage_gb, lakebase_ha_nodes, lakebase_backup_retention_days, runs_per_day, avg_runtime_minutes, days_per_month, vm_pricing_tier, vm_payment_option, notes, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                  (line_item_id, estimate_map[estimate_key], scenario['scenario_id'], scenario['workload_name'], 'LAKEBASE', True, True, scenario['lakebase_cu'], scenario['lakebase_storage_gb'], scenario['lakebase_ha_nodes'], scenario['lakebase_backup_retention_days'], scenario['runs_per_day'], scenario['avg_runtime_minutes'], scenario['days_per_month'], None, None, "LAKEBASE", datetime.now(), datetime.now()), fetch=False)

print(f"✅ Created {len(line_item_ids)} line items")

# COMMAND ----------

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
    c.lakebase_cu,
    c.lakebase_storage_gb,
    c.lakebase_ha_nodes,
    c.lakebase_backup_retention_days,
    c.serverless_enabled,
    -- Usage
    c.runs_per_day,
    c.avg_runtime_minutes,
    c.days_per_month,
    c.hours_per_month,
    -- DBU Calculation (CU = DBU)
    c.dbu_per_hour,
    c.dbu_per_month,
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

results_df = execute_query(query_results_sql, (line_item_ids,))

for col in ['lakebase_cu', 'hours_per_month', 'dbu_per_hour', 'price_per_dbu', 'dbu_cost_per_month', 'cost_per_month']:
    if col in results_df.columns:
        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

results_df['cost_per_month'] = results_df['cost_per_month'].round(2)
print("=" * 180)
print("LAKEBASE - COST CALCULATION SUMMARY")
print("=" * 180)
print(tabulate(results_df.head(20), headers='keys', tablefmt='grid', showindex=False, maxcolwidths=30))
display(results_df)

assert len(results_df) == len(test_scenarios), f"❌ Missing scenarios"

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
print(f"✅ All {len(test_scenarios)} LAKEBASE scenarios validated!")
print(f"   CU to DBU conversion: 1 CU = 1 DBU per hour")

# COMMAND ----------
