# Databricks notebook source
# MAGIC %md
# MAGIC # Test_Func_09: DBSQL Serverless Cost Calculation
# MAGIC
# MAGIC **Objective:** Validate `calculate_line_item_costs()` function for DBSQL Serverless workloads
# MAGIC
# MAGIC **Approach:** Call function directly (no database INSERTs) - faster and cleaner than view-based tests
# MAGIC
# MAGIC **Test Matrix:**
# MAGIC - **Clouds:** AWS, Azure, GCP (2 regions each: US + Europe)
# MAGIC - **Tiers:** PREMIUM, ENTERPRISE (STANDARD tier does NOT support DBSQL Serverless)
# MAGIC - **Warehouse Sizes:** X-SMALL, SMALL, MEDIUM (serverless warehouse sizes)
# MAGIC - **Usage:** 8 hours/day, 30 days/month
# MAGIC - **Photon:** Always enabled for serverless
# MAGIC
# MAGIC **Expected Results:**
# MAGIC - STANDARD tier: $0 costs (serverless not available)
# MAGIC - PREMIUM/ENTERPRISE tiers: Positive DBU costs
# MAGIC - NO VM costs (serverless compute)
# MAGIC - Total cost = DBU cost only

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd
from decimal import Decimal

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
    """Execute a SQL query and return results as DataFrame"""
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

# Test configuration
clouds = ['AWS', 'AZURE', 'GCP']
region_map = {
    'AWS': {'us': 'us-east-1', 'eu': 'eu-west-1'},
    'AZURE': {'us': 'eastus', 'eu': 'westeurope'},
    'GCP': {'us': 'us-central1', 'eu': 'europe-west1'}
}

# Serverless warehouse sizes
warehouse_sizes = ['X-SMALL', 'SMALL', 'MEDIUM']

# Usage
hours_per_day = 8
days_per_month = 30

# COMMAND ----------

# Generate test scenarios
test_scenarios = []
scenario_id = 1

for cloud in clouds:
    for region_type in ['us', 'eu']:
        region = region_map[cloud][region_type]
        
        for tier in ['STANDARD', 'PREMIUM', 'ENTERPRISE']:
            if cloud == 'AZURE' and tier == 'ENTERPRISE':
                continue
            if cloud == 'GCP' and tier == 'STANDARD':
                continue  # GCP STANDARD does not support DBSQL Serverless
            
            for warehouse_size in warehouse_sizes:
                test_scenarios.append({
                    'scenario_id': scenario_id,
                    'cloud': cloud,
                    'region': region,
                    'tier': tier,
                    'warehouse_size': warehouse_size,
                    'hours_per_day': hours_per_day,
                    'days_per_month': days_per_month,
                    'label': f"{cloud} {region} {tier} {warehouse_size}"
                })
                scenario_id += 1

print(f"\n📋 Generated {len(test_scenarios)} test scenarios")
print(f"   AWS: {len([s for s in test_scenarios if s['cloud'] == 'AWS'])} scenarios")
print(f"   AZURE: {len([s for s in test_scenarios if s['cloud'] == 'AZURE'])} scenarios (no ENTERPRISE)")
print(f"   GCP: {len([s for s in test_scenarios if s['cloud'] == 'GCP'])} scenarios (no STANDARD)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Execute Function Calls

# COMMAND ----------

# Build SQL query
sql_parts = []
for scenario in test_scenarios:
    sql_parts.append(f"""
    SELECT 
        {scenario['scenario_id']} as scenario_id,
        '{scenario['label']}'::VARCHAR as label,
        '{scenario['cloud']}'::VARCHAR as cloud,
        '{scenario['region']}'::VARCHAR as region,
        '{scenario['tier']}'::VARCHAR as tier,
        '{scenario['warehouse_size']}'::VARCHAR as warehouse_size,
        *
    FROM lakemeter.calculate_line_item_costs(
        'DBSQL'::VARCHAR,                        -- workload_type
        '{scenario['cloud']}'::VARCHAR,          -- cloud
        '{scenario['region']}'::VARCHAR,         -- region
        '{scenario['tier']}'::VARCHAR,           -- tier
        TRUE::BOOLEAN,                           -- serverless_enabled
        TRUE::BOOLEAN,                           -- photon_enabled (always for serverless)
        NULL::VARCHAR,                           -- dlt_edition
        NULL::VARCHAR,                           -- driver_node_type
        NULL::VARCHAR,                           -- worker_node_type
        0::INT,                                  -- num_workers
        'NA'::VARCHAR,                           -- driver_pricing_tier
        'NA'::VARCHAR,                           -- worker_pricing_tier
        {scenario['hours_per_day']}::INT,        -- runs_per_day
        60::INT,                                 -- avg_runtime_minutes
        {scenario['days_per_month']}::INT,       -- days_per_month
        NULL::INT,                               -- p_hours_per_month
        'standard'::VARCHAR,                     -- serverless_mode
        'SERVERLESS'::VARCHAR,                   -- dbsql_warehouse_type
        '{scenario['warehouse_size']}'::VARCHAR, -- dbsql_warehouse_size
        1::INT,                                  -- dbsql_num_clusters
        'NA'::VARCHAR,                           -- dbsql_vm_pricing_tier
        NULL::VARCHAR,                           -- vector_search_mode
        0::DECIMAL,                              -- vector_search_capacity_millions
        NULL::VARCHAR,                           -- serverless_size
        NULL::VARCHAR,                           -- fmapi_model
        NULL::VARCHAR,                           -- fmapi_provider
        'global'::VARCHAR,                       -- fmapi_endpoint_type
        'standard'::VARCHAR,                     -- fmapi_context_length
        'pay_per_token'::VARCHAR,                -- fmapi_provisioned_type
        0::BIGINT,                               -- fmapi_input_tokens_per_month
        0::BIGINT,                               -- fmapi_output_tokens_per_month
        0::INT,                                  -- lakebase_cu
        1::INT,                                  -- lakebase_ha_nodes
        'NA'::VARCHAR,                           -- driver_payment_option
        'NA'::VARCHAR,                           -- worker_payment_option
        'NA'::VARCHAR                            -- dbsql_vm_payment_option
    )
    """)

full_query = " UNION ALL ".join(sql_parts) + ";"

print(f"🔧 Executing {len(test_scenarios)} function calls...")
results_df = execute_query(full_query)

# Convert Decimal columns to float
numeric_cols = ['hours_per_month', 'dbu_per_month', 'dbu_price', 'dbu_cost_per_month', 'cost_per_month']
for col in numeric_cols:
    if col in results_df.columns:
        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

print(f"✅ Retrieved {len(results_df)} results")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Display Results

# COMMAND ----------

display_cols = ['scenario_id', 'cloud', 'region', 'tier', 'warehouse_size', 
                'hours_per_month', 'dbu_price', 'dbu_per_month', 'dbu_cost_per_month', 'cost_per_month']

available_cols = [col for col in display_cols if col in results_df.columns]

print("=" * 80)
print("DBSQL SERVERLESS TEST RESULTS")
print("=" * 80)
display(results_df[available_cols])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation

# COMMAND ----------

print("=" * 80)
print("VALIDATION CHECKS")
print("=" * 80)

# Check 1: STANDARD tier should have $0 costs (serverless not available)
standard_results = results_df[results_df['tier'] == 'STANDARD']
if len(standard_results) > 0:
    zero_standard = standard_results[standard_results['cost_per_month'] == 0]
    if len(zero_standard) == len(standard_results):
        print(f"✅ PASS: All {len(standard_results)} STANDARD tier scenarios have $0 costs (expected)")
    else:
        print(f"❌ FAIL: Some STANDARD tier scenarios have non-zero costs!")
        display(standard_results[available_cols])

# Check 2: PREMIUM/ENTERPRISE tiers should have positive costs
premium_enterprise = results_df[results_df['tier'].isin(['PREMIUM', 'ENTERPRISE'])]
if len(premium_enterprise) > 0:
    zero_costs = premium_enterprise[premium_enterprise['cost_per_month'] == 0]
    if len(zero_costs) == 0:
        print(f"✅ PASS: All {len(premium_enterprise)} PREMIUM/ENTERPRISE scenarios have positive costs")
    else:
        print(f"❌ FAIL: {len(zero_costs)} PREMIUM/ENTERPRISE scenarios have $0 costs!")
        display(zero_costs[available_cols])

# Check 3: Total cost = DBU cost (no VM costs for serverless)
if 'vm_cost_per_month' in results_df.columns:
    non_zero_vm = results_df[results_df['vm_cost_per_month'] != 0]
    if len(non_zero_vm) == 0:
        print("✅ PASS: No VM costs for serverless (as expected)")
    else:
        print(f"❌ FAIL: {len(non_zero_vm)} scenarios have non-zero VM costs!")

# Check 4: Different warehouse sizes should have different costs
for cloud in clouds:
    for tier in ['PREMIUM', 'ENTERPRISE']:
        if cloud == 'AZURE' and tier == 'ENTERPRISE':
            continue
        if cloud == 'GCP' and tier == 'STANDARD':
            continue
        subset = results_df[(results_df['cloud'] == cloud) & (results_df['tier'] == tier)]
        if len(subset) > 0 and subset['cost_per_month'].sum() > 0:
            unique_costs = subset.groupby('warehouse_size')['cost_per_month'].mean()
            if len(unique_costs.unique()) == len(warehouse_sizes):
                print(f"✅ PASS: {cloud} {tier} - Different costs for different warehouse sizes")
            else:
                print(f"⚠️  WARNING: {cloud} {tier} - Same costs for different warehouse sizes")

print("=" * 80)
print("DBSQL SERVERLESS TEST COMPLETE")
print("=" * 80)
