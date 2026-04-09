# Databricks notebook source
# MAGIC %md
# MAGIC # Test Case: DBSQL Serverless Warehouse
# MAGIC 
# MAGIC **Objective:** Validate DBSQL Serverless cost calculations across all supported configurations
# MAGIC 
# MAGIC **DBSQL Serverless Characteristics:**
# MAGIC - **Product type:** SERVERLESS_SQL_COMPUTE
# MAGIC - **Instant startup** with auto-scaling
# MAGIC - **No VM costs** (serverless compute)
# MAGIC - **Photon always enabled** (required for serverless)
# MAGIC - **Tier availability (cloud-specific):**
# MAGIC   - **AWS:** STANDARD, PREMIUM, ENTERPRISE ✅
# MAGIC   - **Azure:** STANDARD, PREMIUM ✅ (no ENTERPRISE)
# MAGIC   - **GCP:** PREMIUM, ENTERPRISE only (NOT in STANDARD) ❌
# MAGIC 
# MAGIC **Test Scenarios:**
# MAGIC - **Clouds:** AWS, Azure, GCP
# MAGIC - **Regions:** 2 per cloud (1 US + 1 Europe)
# MAGIC - **Tiers:** STANDARD, PREMIUM, ENTERPRISE (cloud-dependent)
# MAGIC - **Warehouse Sizes:** Small, Medium, Large, X-Large
# MAGIC - **Usage Pattern:** 12 runs/day, 60 min/run, 30 days/month
# MAGIC 
# MAGIC **Test Matrix:**
# MAGIC - **AWS:** 2 regions × 3 tiers × 4 sizes = **24 scenarios** (all tiers)
# MAGIC - **AZURE:** 2 regions × 2 tiers × 4 sizes = **16 scenarios** (STANDARD + PREMIUM, no ENTERPRISE)
# MAGIC - **GCP:** 2 regions × 3 tiers × 4 sizes = **24 scenarios** (includes STANDARD for validation)
# MAGIC - **TOTAL: ~64 scenarios**
# MAGIC 
# MAGIC **Validation:**
# MAGIC - ✅ AWS/Azure STANDARD + All PREMIUM/ENTERPRISE: Positive DBU costs
# MAGIC - ✅ GCP STANDARD: $0 costs (not available)
# MAGIC - ✅ VM costs: $0 for all scenarios (serverless has no VMs)
# MAGIC - ✅ Photon automatically enabled for all scenarios

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
              (TEST_USER_ID, f'test_dbsql_serverless_{TEST_RUN_ID}', f'test_{TEST_RUN_ID}@databricks.com', 'admin', True, datetime.now()), fetch=False)

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
warehouse_sizes = ['Small', 'Medium', 'Large', 'X-Large']

for cloud in ['AWS', 'AZURE', 'GCP']:
    for region_type in ['us', 'eu']:  # Test both US and EU regions
        region = region_map[cloud][region_type]
        for tier in ['STANDARD', 'PREMIUM', 'ENTERPRISE']:
            if cloud == 'AZURE' and tier == 'ENTERPRISE':
                continue
            for size in warehouse_sizes:
                test_scenarios.append({
                    'scenario_id': scenario_id, 'cloud': cloud, 'region': region, 'tier': tier,
                    'workload_name': f"{cloud} {tier} {size} SERVERLESS",
                    'dbsql_warehouse_size': size, 'dbsql_num_clusters': 1,
                    'runs_per_day': 12, 'avg_runtime_minutes': 60, 'days_per_month': 30
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
    execute_query("""INSERT INTO lakemeter.line_items (line_item_id, estimate_id, display_order, workload_name, workload_type, serverless_enabled, photon_enabled, dbsql_warehouse_type, dbsql_warehouse_size, dbsql_num_clusters, runs_per_day, avg_runtime_minutes, days_per_month, vm_pricing_tier, vm_payment_option, notes, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                  (line_item_id, estimate_map[estimate_key], scenario['scenario_id'], scenario['workload_name'], 'DBSQL', True, True, 'SERVERLESS', scenario['dbsql_warehouse_size'], scenario['dbsql_num_clusters'], scenario['runs_per_day'], scenario['avg_runtime_minutes'], scenario['days_per_month'], None, None, "DBSQL Serverless", datetime.now(), datetime.now()), fetch=False)

print(f"✅ Created {len(estimate_map)} estimates, {len(line_item_ids)} line items")

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
    c.dbsql_warehouse_type,
    c.dbsql_warehouse_size,
    c.dbsql_num_clusters,
    c.serverless_enabled,
    -- Usage
    c.runs_per_day,
    c.avg_runtime_minutes,
    c.days_per_month,
    c.hours_per_month,
    -- DBU Calculation
    c.dbu_per_hour,
    c.dbu_per_month,
    -- DBU Pricing
    c.price_per_dbu as dbu_price,
    c.product_type_for_pricing,
    c.dbu_cost_per_month,
    -- VM Costs (should be $0 for serverless)
    c.vm_cost_per_month,
    -- Total (DBU only for serverless)
    c.cost_per_month,
    c.notes
FROM lakemeter.v_line_items_with_costs c
WHERE c.line_item_id = ANY(%s::uuid[])
ORDER BY c.display_order;
"""

results_df = execute_query(query_results_sql, (line_item_ids,))

for col in ['vm_cost_per_month', 'dbu_cost_per_month', 'cost_per_month']:
    if col in results_df.columns:
        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

results_df['cost_per_month'] = results_df['cost_per_month'].round(2)
print("=" * 150)
print("DBSQL SERVERLESS - COST CALCULATION SUMMARY")
print("=" * 150)
print(tabulate(results_df.head(20), headers='keys', tablefmt='grid', showindex=False))
display(results_df)

assert results_df['vm_cost_per_month'].sum() == 0, "❌ VM cost should be $0"
assert len(results_df) == len(test_scenarios), f"❌ Missing scenarios"

# DBSQL Serverless tier availability is cloud-specific:
# - AWS STANDARD: ✅ Available
# - AZURE STANDARD: ✅ Available
# - GCP STANDARD: ❌ NOT Available (expect $0)
# - All clouds PREMIUM/ENTERPRISE: ✅ Available

# GCP STANDARD should have $0 costs (not available)
gcp_standard_results = results_df[(results_df['cloud'] == 'GCP') & (results_df['tier'] == 'STANDARD')]
if len(gcp_standard_results) > 0:
    assert (gcp_standard_results['cost_per_month'] == 0).all(), "❌ FAIL: GCP STANDARD should have $0 costs (serverless not available)"
    print(f"✅ GCP STANDARD tier: {len(gcp_standard_results)} scenarios with $0 costs (expected - not available)")

# All other scenarios should have positive costs
other_scenarios = results_df[~((results_df['cloud'] == 'GCP') & (results_df['tier'] == 'STANDARD'))]
if len(other_scenarios) > 0:
    assert (other_scenarios['cost_per_month'] > 0).all(), "❌ FAIL: Non-GCP-STANDARD scenarios should have positive costs"
    print(f"✅ All other scenarios: {len(other_scenarios)} scenarios with positive costs")

# Validate by cloud and tier
cloud_tier_summary = results_df.groupby(['cloud', 'tier']).agg({
    'cost_per_month': ['count', 'mean', 'min', 'max'],
    'dbu_cost_per_month': 'mean'
}).round(2)
print("\n📊 Cost Summary by Cloud & Tier:")
print(tabulate(cloud_tier_summary, headers='keys', tablefmt='grid'))

print(f"\n✅ All {len(test_scenarios)} DBSQL Serverless scenarios validated!")
print(f"   • AWS STANDARD: {len(results_df[(results_df['cloud'] == 'AWS') & (results_df['tier'] == 'STANDARD')])} scenarios (AVAILABLE)")
print(f"   • AZURE STANDARD: {len(results_df[(results_df['cloud'] == 'AZURE') & (results_df['tier'] == 'STANDARD')])} scenarios (AVAILABLE)")
print(f"   • GCP STANDARD: {len(gcp_standard_results)} scenarios (NOT AVAILABLE - $0 costs expected)")
print(f"   • PREMIUM/ENTERPRISE: {len(other_scenarios) - len(results_df[(results_df['tier'] == 'STANDARD') & (results_df['cloud'] != 'GCP')])} scenarios (ALL AVAILABLE)")
print("✅ VM costs are $0 (correct for serverless)")
print("✅ DBU costs validated by cloud-tier availability")

# COMMAND ----------
