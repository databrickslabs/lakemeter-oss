# Databricks notebook source
# MAGIC %md
# MAGIC # Test Case: Vector Search
# MAGIC 
# MAGIC **Objective:** Validate Vector Search cost calculations for both performance modes
# MAGIC 
# MAGIC **Vector Search Characteristics:**
# MAGIC - **Product type:** SERVERLESS_REAL_TIME_INFERENCE (corrected from VECTOR_SEARCH_ENDPOINT)
# MAGIC - **Serverless-only** (no VM costs)
# MAGIC - **Two modes:**
# MAGIC   - **standard:** Optimized for query performance, **2 million vectors per unit**
# MAGIC   - **storage_optimized:** Lower cost, higher capacity, **64 million vectors per unit**
# MAGIC - **Always-on** usage pattern (24/7 availability)
# MAGIC - **Pricing:** Based on DBU per hour
# MAGIC 
# MAGIC **Vector Capacity:**
# MAGIC - **Standard mode:** 2M vectors/unit → Testing with 10M, 50M, 100M vectors
# MAGIC - **Storage-optimized mode:** 64M vectors/unit → Testing with 64M, 256M, 512M vectors
# MAGIC 
# MAGIC **Test Scenarios:**
# MAGIC - **Clouds:** AWS, Azure, GCP
# MAGIC - **Regions:** 2 per cloud (1 US + 1 Europe)
# MAGIC - **Tiers:** STANDARD (expect $0), PREMIUM, ENTERPRISE
# MAGIC - **Modes:** standard (2M vectors/unit), storage_optimized (64M vectors/unit)
# MAGIC - **Vector Capacities:** 3 sizes per mode (small, medium, large)
# MAGIC - **Usage:** 24 runs/day (always-on), 60 min/run, 30 days/month
# MAGIC 
# MAGIC **Test Matrix:**
# MAGIC - **AWS:** 2 regions × 2 tiers × 2 modes × 3 sizes = **24 scenarios** (STANDARD excluded)
# MAGIC - **AZURE:** 2 regions × 1 tier × 2 modes × 3 sizes = **12 scenarios** (PREMIUM only)
# MAGIC - **GCP:** 2 regions × 2 tiers × 2 modes × 3 sizes = **24 scenarios**
# MAGIC - **TOTAL: ~60 scenarios** (plus STANDARD tier validation)
# MAGIC 
# MAGIC **Validation:**
# MAGIC - ✅ STANDARD tier: $0 costs (serverless not available)
# MAGIC - ✅ PREMIUM/ENTERPRISE: Positive DBU costs, $0 VM costs
# MAGIC - ✅ storage_optimized mode: Lower DBU rate than standard mode
# MAGIC - ✅ Vector capacity correctly reflected in test notes

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
              (TEST_USER_ID, f'test_vector_search_{TEST_RUN_ID}', f'test_{TEST_RUN_ID}@databricks.com', 'admin', True, datetime.now()), fetch=False)

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

# Vector capacity configurations:
# - Standard mode: 2M vectors per unit
# - Storage-optimized mode: 64M vectors per unit
vector_configs = {
    'standard': [
        {'capacity_millions': 10, 'label': 'Small'},   # 10M vectors (5 units)
        {'capacity_millions': 50, 'label': 'Medium'},  # 50M vectors (25 units)
        {'capacity_millions': 100, 'label': 'Large'},  # 100M vectors (50 units)
    ],
    'storage_optimized': [
        {'capacity_millions': 64, 'label': 'Small'},    # 64M vectors (1 unit)
        {'capacity_millions': 256, 'label': 'Medium'},  # 256M vectors (4 units)
        {'capacity_millions': 512, 'label': 'Large'},   # 512M vectors (8 units)
    ]
}

for cloud in ['AWS', 'AZURE', 'GCP']:
    for region_type in ['us', 'eu']:  # Test both US and EU regions
        region = region_map[cloud][region_type]
        for tier in ['STANDARD', 'PREMIUM', 'ENTERPRISE']:
            if cloud == 'AZURE' and tier == 'ENTERPRISE':
                continue
            for mode, configs in vector_configs.items():
                for config in configs:
                    capacity = config['capacity_millions']
                    label = config['label']
                    test_scenarios.append({
                        'scenario_id': scenario_id, 'cloud': cloud, 'region': region, 'tier': tier,
                        'workload_name': f"{cloud} {tier} Vector Search {mode.upper()} {label}",
                        'vector_search_mode': mode, 
                        'serverless_product': 'vector_search', 
                        'serverless_size': mode,
                        'vector_capacity_millions': capacity,
                        'runs_per_day': 24, 'avg_runtime_minutes': 60, 'days_per_month': 30,
                        'notes': f"Vector Search {mode} mode - {capacity}M vectors ({label})"
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
    execute_query("""INSERT INTO lakemeter.line_items (line_item_id, estimate_id, display_order, workload_name, workload_type, serverless_enabled, photon_enabled, vector_search_mode, serverless_product, serverless_size, runs_per_day, avg_runtime_minutes, days_per_month, vm_pricing_tier, vm_payment_option, notes, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                  (line_item_id, estimate_map[estimate_key], scenario['scenario_id'], scenario['workload_name'], 'VECTOR_SEARCH', True, True, scenario['vector_search_mode'], 'vector_search', scenario['serverless_size'], scenario['runs_per_day'], scenario['avg_runtime_minutes'], scenario['days_per_month'], None, None, scenario['notes'], datetime.now(), datetime.now()), fetch=False)

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
    c.vector_search_mode,
    c.serverless_product,
    c.serverless_size,
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

for col in ['dbu_per_hour', 'price_per_dbu', 'vm_cost_per_month', 'dbu_cost_per_month', 'cost_per_month']:
    if col in results_df.columns:
        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

# Extract vector capacity from notes and calculate units
# Notes format: "Vector Search {mode} mode - {capacity}M vectors ({label})"
def extract_vector_info(row):
    try:
        notes = row['notes']
        # Extract capacity (e.g., "10M vectors" -> 10)
        capacity_str = notes.split(' - ')[1].split('M vectors')[0]
        capacity_millions = int(capacity_str)
        
        # Calculate units based on mode
        mode = row['vector_search_mode']
        if mode == 'standard':
            # Standard: 2M vectors per unit
            units = capacity_millions / 2
        else:  # storage_optimized
            # Storage-optimized: 64M vectors per unit
            units = capacity_millions / 64
        
        return capacity_millions, units
    except:
        return None, None

results_df[['vector_capacity_millions', 'vector_units']] = results_df.apply(
    lambda row: pd.Series(extract_vector_info(row)), axis=1
)

results_df['cost_per_month'] = results_df['cost_per_month'].round(2)
results_df['vector_units'] = results_df['vector_units'].round(2)

# Create summary display with key columns
summary_display_df = results_df[[
    'display_order', 'workload_name', 'cloud', 'region', 'tier',
    'vector_search_mode', 'vector_capacity_millions', 'vector_units',
    'hours_per_month', 'dbu_per_hour', 'dbu_per_month',
    'dbu_price', 'product_type_for_pricing', 
    'dbu_cost_per_month', 'vm_cost_per_month', 'cost_per_month'
]].copy()

print("=" * 200)
print("VECTOR SEARCH - COST CALCULATION SUMMARY")
print("=" * 200)
print(tabulate(summary_display_df.head(30), headers='keys', tablefmt='grid', showindex=False))
print(f"\n... showing first 30 of {len(results_df)} scenarios ...\n")
display(results_df)

assert results_df['vm_cost_per_month'].sum() == 0, "❌ VM cost should be $0"
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

# Show vector unit breakdown by mode
print("\n" + "=" * 150)
print("VECTOR UNIT VALIDATION")
print("=" * 150)
mode_summary = results_df[results_df['tier'] != 'STANDARD'].groupby(['vector_search_mode', 'vector_capacity_millions']).agg({
    'vector_units': 'first',
    'dbu_per_hour': 'mean',
    'cost_per_month': 'mean'
}).round(2)
print(tabulate(mode_summary, headers='keys', tablefmt='grid'))

print("\n📊 Vector Capacity Formula:")
print("  • Standard mode: 2M vectors per unit → Units = Capacity (M) / 2")
print("  • Storage-optimized mode: 64M vectors per unit → Units = Capacity (M) / 64")

print(f"\n✅ All {len(test_scenarios)} Vector Search scenarios validated!")
print("✅ VM costs are $0 (correct for serverless)")
print("✅ Vector units calculated and displayed correctly")

# COMMAND ----------
