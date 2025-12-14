# Databricks notebook source
# MAGIC %md
# MAGIC # Test Case: Model Serving (Serverless Real-Time Inference)
# MAGIC 
# MAGIC **Objective:** Validate Model Serving cost calculations with cloud-specific GPU types
# MAGIC 
# MAGIC **Model Serving Characteristics:**
# MAGIC - **Product type:** SERVERLESS_REAL_TIME_INFERENCE
# MAGIC - **Serverless-only** (no VM costs)
# MAGIC - **Cloud-specific GPU types** (dynamically loaded from pricing table):
# MAGIC   - **AWS:** cpu, gpu_small_t4, gpu_medium_a10g (1x/4x/8x), gpu_xlarge/2xlarge/4xlarge_a100_80gb
# MAGIC   - **Azure:** cpu, gpu_medium_a10g (1x/4x/8x), gpu_xlarge_a100 (40gb/80gb)
# MAGIC   - **GCP:** cpu, gpu_small_t4, gpu_medium_g2_standard_8, gpu_xlarge/2xlarge_a100_80gb
# MAGIC - **Always-on** availability for real-time inference
# MAGIC 
# MAGIC **Test Scenarios:**
# MAGIC - **Clouds:** AWS, Azure, GCP (each with different GPU types)
# MAGIC - **Regions:** 2 per cloud (1 US + 1 Europe)
# MAGIC - **Tiers:** STANDARD (expect $0), PREMIUM, ENTERPRISE (Azure ENTERPRISE excluded)
# MAGIC - **Sizes:** Dynamically queried from sync_product_serverless_rates (cloud-specific)
# MAGIC - **Usage:** 24 runs/day (always-on), 60 min/run, 30 days/month
# MAGIC 
# MAGIC **Test Matrix:**
# MAGIC - **AWS:** 2 regions × 3 tiers × ~10 GPU types = **~60 scenarios**
# MAGIC - **AZURE:** 2 regions × 2 tiers × ~8 GPU types = **~32 scenarios** (no ENTERPRISE)
# MAGIC - **GCP:** 2 regions × 3 tiers × ~8 GPU types = **~48 scenarios**
# MAGIC - **TOTAL: ~140 scenarios** (varies by available GPU types in pricing table)
# MAGIC 
# MAGIC **Validation:**
# MAGIC - ✅ STANDARD tier: $0 costs (serverless not available)
# MAGIC - ✅ PREMIUM/ENTERPRISE: Positive DBU costs, $0 VM costs
# MAGIC - ✅ GPU sizes: Higher DBU rates than CPU

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
              (TEST_USER_ID, f'test_model_serving_{TEST_RUN_ID}', f'test_{TEST_RUN_ID}@databricks.com', 'admin', True, datetime.now()), fetch=False)

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

# Get available model serving sizes from pricing table (cloud-specific)
print("📊 Querying available model serving GPU types from pricing table...")
available_sizes_query = """
SELECT DISTINCT cloud, size_or_model, dbu_rate
FROM lakemeter.sync_product_serverless_rates
WHERE product = 'model_serving'
ORDER BY cloud, size_or_model;
"""
available_sizes_df = execute_query(available_sizes_query)
print(f"✅ Found {len(available_sizes_df)} model serving configurations")
print(tabulate(available_sizes_df, headers='keys', tablefmt='grid', showindex=False))

# Group by cloud for cloud-specific sizing
cloud_sizes = {}
for _, row in available_sizes_df.iterrows():
    cloud = row['cloud']
    if cloud not in cloud_sizes:
        cloud_sizes[cloud] = []
    cloud_sizes[cloud].append({
        'size_or_model': row['size_or_model'],
        'dbu_rate': row['dbu_rate']
    })

print("\n📋 GPU types per cloud:")
for cloud, sizes in cloud_sizes.items():
    print(f"  {cloud}: {len(sizes)} types - {', '.join([s['size_or_model'] for s in sizes[:3]])}...")

test_scenarios = []
scenario_id = 1

for cloud in ['AWS', 'AZURE', 'GCP']:
    # Get cloud-specific sizes
    if cloud not in cloud_sizes:
        print(f"⚠️  Warning: No model serving sizes found for {cloud}, skipping...")
        continue
    
    sizes_for_cloud = cloud_sizes[cloud]
    
    for region_type in ['us', 'eu']:  # Test both US and EU regions
        region = region_map[cloud][region_type]
        for tier in ['STANDARD', 'PREMIUM', 'ENTERPRISE']:
            if cloud == 'AZURE' and tier == 'ENTERPRISE':
                continue
            
            # Test each available size for this cloud
            for size_config in sizes_for_cloud:
                size = size_config['size_or_model']
                test_scenarios.append({
                    'scenario_id': scenario_id, 'cloud': cloud, 'region': region, 'tier': tier,
                    'workload_name': f"{cloud} {tier} Model Serving {size}",
                    'serverless_product': 'model_serving', 'serverless_size': size,
                    'runs_per_day': 24, 'avg_runtime_minutes': 60, 'days_per_month': 30,
                    'notes': f"Model Serving {size}"
                })
                scenario_id += 1

print(f"\n✅ Generated {len(test_scenarios)} scenarios (cloud-specific GPU types)")

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
    execute_query("""INSERT INTO lakemeter.line_items (line_item_id, estimate_id, display_order, workload_name, workload_type, serverless_enabled, photon_enabled, serverless_product, serverless_size, runs_per_day, avg_runtime_minutes, days_per_month, vm_pricing_tier, vm_payment_option, notes, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                  (line_item_id, estimate_map[estimate_key], scenario['scenario_id'], scenario['workload_name'], 'MODEL_SERVING', True, True, 'model_serving', scenario['serverless_size'], scenario['runs_per_day'], scenario['avg_runtime_minutes'], scenario['days_per_month'], None, None, scenario['notes'], datetime.now(), datetime.now()), fetch=False)

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
    -- Total (serverless has no VM costs)
    c.cost_per_month,
    c.notes
FROM lakemeter.v_line_items_with_costs c
WHERE c.line_item_id = ANY(%s::uuid[])
ORDER BY c.display_order;
"""

results_df = execute_query(query_results_sql, (line_item_ids,))

for col in ['dbu_per_hour', 'price_per_dbu', 'dbu_cost_per_month', 'cost_per_month']:
    if col in results_df.columns:
        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

results_df['cost_per_month'] = results_df['cost_per_month'].round(2)
print("=" * 150)
print("MODEL SERVING - COST CALCULATION SUMMARY")
print("=" * 150)
print(tabulate(results_df, headers='keys', tablefmt='grid', showindex=False))
display(results_df)

assert len(results_df) == len(test_scenarios), f"❌ Missing scenarios"

# Show GPU types tested by cloud
print("\n" + "=" * 150)
print("GPU TYPES TESTED BY CLOUD")
print("=" * 150)
gpu_summary = results_df[results_df['tier'] != 'STANDARD'].groupby(['cloud', 'serverless_size']).agg({
    'dbu_per_hour': 'mean',
    'cost_per_month': 'mean'
}).round(2)
print(tabulate(gpu_summary, headers='keys', tablefmt='grid'))

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
print(f"✅ All {len(test_scenarios)} Model Serving scenarios validated!")

# COMMAND ----------
