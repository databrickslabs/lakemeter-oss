# Databricks notebook source
# MAGIC %md
# MAGIC # Test Case: FMAPI Proprietary Models (OpenAI, Anthropic, Google)
# MAGIC 
# MAGIC **Proprietary Models served by Databricks:**
# MAGIC - **OpenAI:** gpt-4o, gpt-4o-mini
# MAGIC - **Anthropic:** claude-sonnet-4-20250514, claude-haiku-4
# MAGIC - **Google:** gemini-2.5-pro-preview-05-06
# MAGIC 
# MAGIC **Pricing factors:**
# MAGIC - endpoint_type: global, in_geo
# MAGIC - context_length: standard, long
# MAGIC - rate_type: input_token, output_token, cache_read, cache_write

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

TEST_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
TEST_USER_ID = str(uuid.uuid4())
execute_query("INSERT INTO lakemeter.users (user_id, full_name, email, role, is_active, created_at) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;",
              (TEST_USER_ID, f'test_fmapi_proprietary_{TEST_RUN_ID}', f'test_{TEST_RUN_ID}@databricks.com', 'admin', True, datetime.now()), fetch=False)

available_regions_df = execute_query("SELECT DISTINCT cloud, region_code FROM lakemeter.sync_ref_sku_region_map WHERE (cloud = 'AWS' AND region_code LIKE 'us-east-%') OR (cloud = 'AZURE' AND region_code = 'eastus') OR (cloud = 'GCP' AND region_code LIKE 'us-central%');")
region_map = {cloud: available_regions_df[available_regions_df['cloud'] == cloud].iloc[0]['region_code'] for cloud in ['AWS', 'AZURE', 'GCP'] if len(available_regions_df[available_regions_df['cloud'] == cloud]) >= 1}

test_scenarios = []
scenario_id = 1
providers_models = [
    {'provider': 'openai', 'model': 'gpt-4o'},
    {'provider': 'openai', 'model': 'gpt-4o-mini'},
    {'provider': 'anthropic', 'model': 'claude-sonnet-4-20250514'},
    {'provider': 'google', 'model': 'gemini-2.5-pro-preview-05-06'}
]
endpoint_types = ['global', 'in_geo']
token_volumes = [{'input': 1_000_000, 'output': 500_000}, {'input': 10_000_000, 'output': 5_000_000}]

for cloud in ['AWS', 'AZURE', 'GCP']:
    for tier in ['STANDARD', 'PREMIUM']:
        for pm in providers_models[:2]:  # Limit scenarios
            for endpoint_type in endpoint_types:
                for volume in token_volumes:
                    region = region_map[cloud]
                    test_scenarios.append({
                        'scenario_id': scenario_id, 'cloud': cloud, 'region': region, 'tier': tier,
                        'workload_name': f"{cloud} {tier} {pm['provider']} {pm['model'][:20]} {endpoint_type}",
                        'fmapi_provider': pm['provider'],
                        'fmapi_model': pm['model'],
                        'fmapi_endpoint_type': endpoint_type,
                        'fmapi_context_length': 'standard',
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
                  (estimate_id, TEST_USER_ID, f"Test: {combo[\'cloud\']} {combo[\'region\']} {combo[\'tier\']}", combo[\'cloud\'], combo['region'], combo['tier'], datetime.now(), datetime.now()), fetch=False)

line_item_ids = []
for scenario in test_scenarios:
    line_item_id = str(uuid.uuid4())
    line_item_ids.append(line_item_id)
    estimate_key = f"{scenario['cloud']}_{scenario['region']}_{scenario['tier']}"
    execute_query("""INSERT INTO lakemeter.line_items (line_item_id, estimate_id, display_order, workload_name, workload_type, serverless_enabled, fmapi_provider, fmapi_model, fmapi_endpoint_type, fmapi_context_length, fmapi_input_tokens_per_month, fmapi_output_tokens_per_month, notes, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                  (line_item_id, estimate_map[estimate_key], scenario['scenario_id'], scenario['workload_name'], 'FMAPI_PROPRIETARY', True, scenario['fmapi_provider'], scenario['fmapi_model'], scenario['fmapi_endpoint_type'], scenario['fmapi_context_length'], scenario['fmapi_input_tokens_per_month'], scenario['fmapi_output_tokens_per_month'], "FMAPI Proprietary", datetime.now(), datetime.now()), fetch=False)

print(f"✅ Created {len(line_item_ids)} line items")

# COMMAND ----------

results_df = execute_query("SELECT c.workload_name, c.cloud, c.tier, c.fmapi_provider, c.fmapi_model, c.fmapi_endpoint_type, c.cost_per_month FROM lakemeter.v_line_items_with_costs c WHERE c.line_item_id = ANY(%s::uuid[]) ORDER BY c.display_order;", (line_item_ids,))

for col in ['cost_per_month']:
    if col in results_df.columns:
        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

results_df['cost_per_month'] = results_df['cost_per_month'].round(2)
print("=" * 180)
print("FMAPI PROPRIETARY - COST CALCULATION SUMMARY")
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
print(f"✅ All {len(test_scenarios)} FMAPI Proprietary scenarios validated!")

# COMMAND ----------
