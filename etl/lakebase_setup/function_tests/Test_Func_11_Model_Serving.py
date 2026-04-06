# Databricks notebook source
# MAGIC %md
# MAGIC # Test_Func_11: Model Serving Cost Calculation
# MAGIC
# MAGIC **Objective:** Validate `calculate_line_item_costs()` function for Model Serving workloads
# MAGIC
# MAGIC **Test Matrix:**
# MAGIC - **Clouds:** AWS, Azure, GCP (2 regions each)
# MAGIC - **Tiers:** PREMIUM, ENTERPRISE
# MAGIC - **GPU Types:** Cloud-specific (cpu, gpu_small_t4, gpu_medium/large, etc.)
# MAGIC - **Usage:** 8 hours/day, 30 days/month

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd

def get_connection():
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DATABASE,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD,
        sslmode='require'
    )

def execute_query(query):
    conn = get_connection()
    try:
        df = pd.read_sql(query, conn)
        return df
    finally:
        conn.close()

print("✅ Connection setup complete!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Test Scenarios

# COMMAND ----------

clouds = ['AWS', 'AZURE', 'GCP']
region_map = {
    'AWS': {'us': 'us-east-1', 'eu': 'eu-west-1'},
    'AZURE': {'us': 'eastus', 'eu': 'westeurope'},
    'GCP': {'us': 'us-central1', 'eu': 'europe-west1'}
}

# Cloud-specific GPU types
gpu_types_by_cloud = {
    'AWS': ['cpu', 'gpu_small_t4'],
    'AZURE': ['cpu', 'gpu_small_t4'],
    'GCP': ['cpu', 'gpu_medium_g2_standard_8']
}

# Generate scenarios
test_scenarios = []
scenario_id = 1

for cloud in clouds:
    for region_type in ['us', 'eu']:
        region = region_map[cloud][region_type]
        for tier in ['PREMIUM', 'ENTERPRISE']:
            if cloud == 'AZURE' and tier == 'ENTERPRISE':
                continue
            for gpu_type in gpu_types_by_cloud[cloud]:
                test_scenarios.append({
                    'scenario_id': scenario_id,
                    'cloud': cloud,
                    'region': region,
                    'tier': tier,
                    'gpu_type': gpu_type,
                    'label': f"{cloud} {tier} {gpu_type}"
                })
                scenario_id += 1

print(f"📋 Generated {len(test_scenarios)} scenarios")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Execute Function Calls

# COMMAND ----------

sql_parts = []
for scenario in test_scenarios:
    sql_parts.append(f"""
    SELECT 
        {scenario['scenario_id']} as scenario_id,
        '{scenario['label']}'::VARCHAR as label,
        '{scenario['cloud']}'::VARCHAR as cloud,
        '{scenario['tier']}'::VARCHAR as tier,
        '{scenario['gpu_type']}'::VARCHAR as gpu_type,
        *
    FROM lakemeter.calculate_line_item_costs(
        'MODEL_SERVING'::VARCHAR,
        '{scenario['cloud']}'::VARCHAR,
        '{scenario['region']}'::VARCHAR,
        '{scenario['tier']}'::VARCHAR,
        FALSE::BOOLEAN, FALSE::BOOLEAN, NULL::VARCHAR,
        NULL::VARCHAR, NULL::VARCHAR, 0::INT,
        'NA'::VARCHAR, 'NA'::VARCHAR,
        8::INT, 60::INT, 30::INT,
        720::INT,                                -- p_hours_per_month (24/7 for Model Serving)
        'standard'::VARCHAR, NULL::VARCHAR, NULL::VARCHAR,
        1::INT, 'NA'::VARCHAR, NULL::VARCHAR, 0::DECIMAL,
        '{scenario['gpu_type']}'::VARCHAR,
        NULL::VARCHAR, NULL::VARCHAR,
        'global'::VARCHAR, 'standard'::VARCHAR, 'pay_per_token'::VARCHAR,
        0::BIGINT, 0::BIGINT, 0::INT, 1::INT,
        'NA'::VARCHAR, 'NA'::VARCHAR, 'NA'::VARCHAR
    )
    """)

full_query = " UNION ALL ".join(sql_parts) + ";"

print(f"🔧 Executing {len(test_scenarios)} function calls...")
results_df = execute_query(full_query)

numeric_cols = ['dbu_per_month', 'dbu_price', 'dbu_cost_per_month', 'cost_per_month']
for col in numeric_cols:
    if col in results_df.columns:
        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

print(f"✅ Retrieved {len(results_df)} results")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Display & Validate

# COMMAND ----------

display_cols = ['scenario_id', 'cloud', 'tier', 'gpu_type', 'dbu_price', 'dbu_per_month', 'dbu_cost_per_month', 'cost_per_month']
available_cols = [col for col in display_cols if col in results_df.columns]

print("=" * 80)
print("MODEL SERVING TEST RESULTS")
print("=" * 80)
display(results_df[available_cols])

print("\n" + "=" * 80)
print("VALIDATION")
print("=" * 80)

zero_costs = results_df[results_df['cost_per_month'] == 0]
if len(zero_costs) == 0:
    print(f"✅ PASS: All {len(results_df)} scenarios have positive costs")
else:
    print(f"❌ FAIL: {len(zero_costs)} scenarios have $0 costs")
    display(zero_costs[available_cols])

print("=" * 80)
print("MODEL SERVING TEST COMPLETE")
print("=" * 80)
