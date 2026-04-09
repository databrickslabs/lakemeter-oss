# Databricks notebook source
# MAGIC %md
# MAGIC # Test_Func_10: Vector Search Cost Calculation
# MAGIC
# MAGIC **Objective:** Validate `calculate_line_item_costs()` function for Vector Search workloads
# MAGIC
# MAGIC **Approach:** Call function directly (no database INSERTs)
# MAGIC
# MAGIC **Test Matrix:**
# MAGIC - **Clouds:** AWS, Azure, GCP (2 regions each)
# MAGIC - **Tiers:** PREMIUM, ENTERPRISE (Vector Search not available in STANDARD)
# MAGIC - **Vector Search Modes:** standard, storage_optimized
# MAGIC - **Capacity:** 3M, 10M, 50M, 100M vectors
# MAGIC - **Usage:** Monthly pricing
# MAGIC
# MAGIC **Expected Results:**
# MAGIC - PREMIUM/ENTERPRISE tiers: Positive costs
# MAGIC - standard mode: 2M vectors per unit (capacity / 2M, rounded up)
# MAGIC - storage_optimized mode: 64M vectors per unit (capacity / 64M, rounded up)
# MAGIC - Different costs for different modes and capacities

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd
from decimal import Decimal
import math

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

# Vector search modes and capacities
vector_search_modes = ['standard', 'storage_optimized']
capacities_millions = [3, 10, 50, 100]  # Million vectors

# COMMAND ----------

# Generate test scenarios
test_scenarios = []
scenario_id = 1

for cloud in clouds:
    for region_type in ['us', 'eu']:
        region = region_map[cloud][region_type]
        
        for tier in ['PREMIUM', 'ENTERPRISE']:
            if cloud == 'AZURE' and tier == 'ENTERPRISE':
                continue
            
            for mode in vector_search_modes:
                for capacity in capacities_millions:
                    # Calculate expected units
                    if mode == 'standard':
                        units = math.ceil(capacity / 2.0)  # 2M per unit
                    else:  # storage_optimized
                        units = math.ceil(capacity / 64.0)  # 64M per unit
                    
                    test_scenarios.append({
                        'scenario_id': scenario_id,
                        'cloud': cloud,
                        'region': region,
                        'tier': tier,
                        'mode': mode,
                        'capacity_millions': capacity,
                        'expected_units': units,
                        'label': f"{cloud} {tier} {mode} {capacity}M"
                    })
                    scenario_id += 1

print(f"\n📋 Generated {len(test_scenarios)} test scenarios")
print(f"   AWS: {len([s for s in test_scenarios if s['cloud'] == 'AWS'])} scenarios")
print(f"   AZURE: {len([s for s in test_scenarios if s['cloud'] == 'AZURE'])} scenarios (no ENTERPRISE)")
print(f"   GCP: {len([s for s in test_scenarios if s['cloud'] == 'GCP'])} scenarios")

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
        '{scenario['mode']}'::VARCHAR as mode,
        {scenario['capacity_millions']}::DECIMAL as capacity_millions,
        {scenario['expected_units']}::INT as expected_units,
        *
    FROM lakemeter.calculate_line_item_costs(
        'VECTOR_SEARCH'::VARCHAR,                -- workload_type
        '{scenario['cloud']}'::VARCHAR,          -- cloud
        '{scenario['region']}'::VARCHAR,         -- region
        '{scenario['tier']}'::VARCHAR,           -- tier
        FALSE::BOOLEAN,                          -- serverless_enabled
        FALSE::BOOLEAN,                          -- photon_enabled
        NULL::VARCHAR,                           -- dlt_edition
        NULL::VARCHAR,                           -- driver_node_type
        NULL::VARCHAR,                           -- worker_node_type
        0::INT,                                  -- num_workers
        'NA'::VARCHAR,                           -- driver_pricing_tier
        'NA'::VARCHAR,                           -- worker_pricing_tier
        0::INT,                                  -- runs_per_day
        0::INT,                                  -- avg_runtime_minutes
        30::INT,                                 -- days_per_month
        720::INT,                                -- hours_per_month (24*30 for 24/7 availability)
        'standard'::VARCHAR,                     -- serverless_mode
        NULL::VARCHAR,                           -- dbsql_warehouse_type
        NULL::VARCHAR,                           -- dbsql_warehouse_size
        1::INT,                                  -- dbsql_num_clusters
        'NA'::VARCHAR,                           -- dbsql_vm_pricing_tier
        '{scenario['mode']}'::VARCHAR,           -- vector_search_mode
        {scenario['capacity_millions']}::DECIMAL,-- vector_search_capacity_millions (DECIMAL not BIGINT!)
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
numeric_cols = ['capacity_millions', 'expected_units', 'dbu_per_month', 'dbu_price', 'dbu_cost_per_month', 'cost_per_month']
for col in numeric_cols:
    if col in results_df.columns:
        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

print(f"✅ Retrieved {len(results_df)} results")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Display Results

# COMMAND ----------

display_cols = ['scenario_id', 'cloud', 'region', 'tier', 'mode', 'capacity_millions', 
                'expected_units', 'dbu_price', 'dbu_per_month', 'dbu_cost_per_month', 'cost_per_month']

available_cols = [col for col in display_cols if col in results_df.columns]

print("=" * 80)
print("VECTOR SEARCH TEST RESULTS")
print("=" * 80)
display(results_df[available_cols])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation

# COMMAND ----------

print("=" * 80)
print("VALIDATION CHECKS")
print("=" * 80)

# Check 1: All scenarios should have positive costs
zero_costs = results_df[results_df['cost_per_month'] == 0]
if len(zero_costs) == 0:
    print(f"✅ PASS: All {len(results_df)} scenarios have positive costs")
else:
    print(f"❌ FAIL: {len(zero_costs)} scenarios have $0 costs!")
    display(zero_costs[available_cols])

# Check 2: Verify unit calculation (for standard mode: capacity / 2M, for storage_optimized: capacity / 64M)
results_df['calculated_units_standard'] = results_df.apply(
    lambda row: math.ceil(row['capacity_millions'] / 2.0) if row['mode'] == 'standard' else None, axis=1
)
results_df['calculated_units_storage'] = results_df.apply(
    lambda row: math.ceil(row['capacity_millions'] / 64.0) if row['mode'] == 'storage_optimized' else None, axis=1
)

# Validate expected units match calculated units
unit_mismatches = results_df[
    ((results_df['mode'] == 'standard') & (results_df['expected_units'] != results_df['calculated_units_standard'])) |
    ((results_df['mode'] == 'storage_optimized') & (results_df['expected_units'] != results_df['calculated_units_storage']))
]

if len(unit_mismatches) == 0:
    print("✅ PASS: All expected units match calculated units (CEILING logic)")
else:
    print(f"❌ FAIL: {len(unit_mismatches)} scenarios have unit calculation mismatches!")
    display(unit_mismatches[available_cols + ['calculated_units_standard', 'calculated_units_storage']])

# Check 3: Different modes should have different costs for the same capacity
for cloud in clouds:
    for tier in ['PREMIUM', 'ENTERPRISE']:
        if cloud == 'AZURE' and tier == 'ENTERPRISE':
            continue
        for capacity in capacities_millions:
            subset = results_df[
                (results_df['cloud'] == cloud) & 
                (results_df['tier'] == tier) & 
                (results_df['capacity_millions'] == capacity)
            ]
            if len(subset) == 2:  # Should have both standard and storage_optimized
                costs = subset.groupby('mode')['cost_per_month'].first()
                if costs['standard'] != costs['storage_optimized']:
                    print(f"✅ PASS: {cloud} {tier} {capacity}M - Different costs for different modes")
                else:
                    print(f"⚠️  WARNING: {cloud} {tier} {capacity}M - Same costs for both modes")

print("=" * 80)
print("VECTOR SEARCH TEST COMPLETE")
print("=" * 80)
