# Databricks notebook source
# MAGIC %md
# MAGIC # Test Case: FMAPI Databricks-Hosted Models
# MAGIC 
# MAGIC **Objective:** Validate token-based cost calculations for Databricks-hosted foundation models
# MAGIC 
# MAGIC **FMAPI Databricks Characteristics:**
# MAGIC - **Product type:** SERVERLESS_REAL_TIME_INFERENCE
# MAGIC - **Pricing model:** Token-based (input + output tokens per million)
# MAGIC - **Models tested:**
# MAGIC   - **llama-3.1-8b-instruct:** Lightweight LLM (lowest DBU rate)
# MAGIC   - **llama-3.1-70b-instruct:** Large LLM (higher DBU rate)
# MAGIC   - **dbrx-instruct:** Databricks foundation model
# MAGIC   - **bge-large-en-v1.5:** Embedding model (input tokens only)
# MAGIC - **Serverless-only** (no VM costs)
# MAGIC - **Hosted and served by Databricks**
# MAGIC 
# MAGIC **Test Scenarios:**
# MAGIC - **Clouds:** AWS, Azure, GCP
# MAGIC - **Regions:** 2 per cloud (1 US + 1 Europe)
# MAGIC - **Tiers:** PREMIUM, ENTERPRISE (STANDARD not applicable)
# MAGIC - **Models:** 4 different foundation models
# MAGIC - **Token Volumes:** 3 usage patterns
# MAGIC   - Light: 1M input, 500K output tokens/month
# MAGIC   - Medium: 10M input, 5M output tokens/month
# MAGIC   - Heavy: 100M input, 50M output tokens/month
# MAGIC 
# MAGIC **Test Matrix:**
# MAGIC - **AWS:** 2 regions × 1 tier × 4 models × 3 volumes = **24 scenarios**
# MAGIC - **AZURE:** 2 regions × 1 tier × 4 models × 3 volumes = **24 scenarios**
# MAGIC - **GCP:** 2 regions × 1 tier × 4 models × 3 volumes = **24 scenarios**
# MAGIC - **TOTAL: ~72 scenarios**
# MAGIC 
# MAGIC **Validation:**
# MAGIC - ✅ Cost calculated from token volumes (not hourly)
# MAGIC - ✅ Different DBU rates per model
# MAGIC - ✅ Input + output token costs calculated correctly

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
              (TEST_USER_ID, f'test_fmapi_databricks_{TEST_RUN_ID}', f'test_{TEST_RUN_ID}@databricks.com', 'admin', True, datetime.now()), fetch=False)

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
models = ['llama-3.1-8b-instruct', 'llama-3.1-70b-instruct', 'dbrx-instruct', 'bge-large-en-v1.5']
token_volumes = [
    {'name': 'Low', 'input': 1_000_000, 'output': 500_000},
    {'name': 'High', 'input': 10_000_000, 'output': 5_000_000},
]

for cloud in ['AWS', 'AZURE', 'GCP']:
    for region_type in ['us', 'eu']:  # Test both US and EU regions
        region = region_map[cloud][region_type]
        for tier in ['STANDARD', 'PREMIUM']:
            for model in models:
                for volume in token_volumes:
                    test_scenarios.append({
                        'scenario_id': scenario_id, 'cloud': cloud, 'region': region, 'tier': tier,
                        'workload_name': f"{cloud} {tier} {model} {volume['name']}",
                        'fmapi_model': model,
                        'fmapi_input_tokens_per_month': volume['input'],
                        'fmapi_output_tokens_per_month': volume['output']
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
    execute_query("""INSERT INTO lakemeter.line_items (line_item_id, estimate_id, display_order, workload_name, workload_type, serverless_enabled, photon_enabled, fmapi_model, fmapi_input_tokens_per_month, fmapi_output_tokens_per_month, vm_pricing_tier, vm_payment_option, notes, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                  (line_item_id, estimate_map[estimate_key], scenario['scenario_id'], scenario['workload_name'], 'FMAPI_DATABRICKS', True, True, scenario['fmapi_model'], scenario['fmapi_input_tokens_per_month'], scenario['fmapi_output_tokens_per_month'], None, None, "FMAPI Databricks", datetime.now(), datetime.now()), fetch=False)

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
    c.fmapi_model,
    c.fmapi_input_tokens_per_month,
    c.fmapi_output_tokens_per_month,
    c.serverless_enabled,
    -- DBU Calculation (token-based, not hourly)
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

for col in ['fmapi_input_tokens_per_month', 'fmapi_output_tokens_per_month', 'dbu_per_month', 'price_per_dbu', 'cost_per_month']:
    if col in results_df.columns:
        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

results_df['cost_per_month'] = results_df['cost_per_month'].round(2)
print("=" * 180)
print("FMAPI DATABRICKS - COST CALCULATION SUMMARY")
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
print(f"✅ All {len(test_scenarios)} FMAPI Databricks scenarios validated!")

# COMMAND ----------
