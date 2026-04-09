# Databricks notebook source
# MAGIC %md
# MAGIC # Test_Func_07: DBSQL Classic Cost Calculation
# MAGIC
# MAGIC **Objective:** Validate `calculate_line_item_costs()` function for DBSQL Classic workloads
# MAGIC
# MAGIC **Approach:** Call function directly (no database INSERTs) - faster and cleaner than view-based tests
# MAGIC
# MAGIC **Test Matrix:**
# MAGIC - **Clouds:** AWS, Azure, GCP (2 regions each: US + Europe)
# MAGIC - **Tiers:** STANDARD, PREMIUM, ENTERPRISE (skip Azure ENTERPRISE)
# MAGIC - **Warehouse Sizes:** SMALL, MEDIUM (dynamically fetched from sync_ref_dbsql_warehouse_config)
# MAGIC - **Num Clusters:** 1, 2
# MAGIC - **VM Pricing Tiers:** on_demand, reserved_1y, reserved_3y
# MAGIC - **VM Payment Options:** 
# MAGIC   - AWS: all_upfront, no_upfront, partial_upfront
# MAGIC   - Azure/GCP: NA (not applicable)
# MAGIC - **Usage:** 8 hours/day, 30 days/month
# MAGIC
# MAGIC **Expected Results:**
# MAGIC - Positive DBU costs for all scenarios
# MAGIC - Positive VM costs for all scenarios
# MAGIC - Total cost = DBU cost + VM cost
# MAGIC - Different pricing for different warehouse sizes
# MAGIC - Different pricing for different VM payment options (AWS only)

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
# MAGIC ## Check Function Exists

# COMMAND ----------

check_function_sql = """
SELECT 
    p.proname as function_name,
    pg_catalog.pg_get_function_arguments(p.oid) as arguments
FROM pg_catalog.pg_proc p
JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'lakemeter'
  AND p.proname = 'calculate_line_item_costs';
"""

func_check = execute_query(check_function_sql)

print("=" * 80)
if not func_check.empty:
    print("✅ calculate_line_item_costs() function EXISTS")
else:
    print("❌ calculate_line_item_costs() function DOES NOT EXIST!")
    print("   Please run: 4_Functions/09_Main_Orchestrator.py")
    dbutils.notebook.exit("Function not found - aborting test")

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

# Warehouse sizes (fetch from reference table)
warehouse_sizes = []
try:
    size_query = """
    SELECT DISTINCT warehouse_size 
    FROM lakemeter.sync_ref_dbsql_warehouse_config 
    WHERE cloud = 'AWS'
    ORDER BY warehouse_size
    LIMIT 2;
    """
    size_result = execute_query(size_query)
    if not size_result.empty:
        warehouse_sizes = size_result['warehouse_size'].tolist()
        print(f"📊 Warehouse sizes: {warehouse_sizes}")
except Exception as e:
    print(f"⚠️  Using default warehouse sizes: {e}")
    warehouse_sizes = ['SMALL', 'MEDIUM']

# Number of clusters
num_clusters_options = [1, 2]

# VM pricing tiers
vm_pricing_tiers = ['on_demand', 'reserved_1y', 'reserved_3y']

# VM payment options (AWS-specific)
aws_payment_options = ['all_upfront', 'no_upfront', 'partial_upfront']

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
            
            for warehouse_size in warehouse_sizes:
                for num_clusters in num_clusters_options:
                    for vm_pricing_tier in vm_pricing_tiers:
                        if cloud == 'AWS':
                            # AWS has specific payment options
                            if vm_pricing_tier == 'on_demand':
                                payment_options = ['NA']
                            else:
                                payment_options = aws_payment_options
                        else:
                            # Azure and GCP always use NA
                            payment_options = ['NA']
                        
                        for payment_option in payment_options:
                            test_scenarios.append({
                                'scenario_id': scenario_id,
                                'cloud': cloud,
                                'region': region,
                                'tier': tier,
                                'warehouse_size': warehouse_size,
                                'num_clusters': num_clusters,
                                'vm_pricing_tier': vm_pricing_tier,
                                'vm_payment_option': payment_option,
                                'hours_per_day': hours_per_day,
                                'days_per_month': days_per_month,
                                'label': f"{cloud} {region} {tier} {warehouse_size} {num_clusters}cl {vm_pricing_tier} {payment_option}"
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
        '{scenario['warehouse_size']}'::VARCHAR as warehouse_size,
        {scenario['num_clusters']}::INT as num_clusters,
        '{scenario['vm_pricing_tier']}'::VARCHAR as vm_pricing_tier,
        '{scenario['vm_payment_option']}'::VARCHAR as vm_payment_option,
        *
    FROM lakemeter.calculate_line_item_costs(
        'DBSQL'::VARCHAR,                        -- workload_type
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
        {scenario['hours_per_day']}::INT,        -- runs_per_day
        60::INT,                                 -- avg_runtime_minutes
        {scenario['days_per_month']}::INT,       -- days_per_month
        NULL::INT,                               -- p_hours_per_month
        'standard'::VARCHAR,                     -- serverless_mode
        'classic'::VARCHAR,                      -- dbsql_warehouse_type
        '{scenario['warehouse_size']}'::VARCHAR, -- dbsql_warehouse_size
        {scenario['num_clusters']}::INT,         -- dbsql_num_clusters
        '{scenario['vm_pricing_tier']}'::VARCHAR,-- dbsql_vm_pricing_tier
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
        '{scenario['vm_payment_option']}'::VARCHAR -- dbsql_vm_payment_option
    )
    """)

full_query = " UNION ALL ".join(sql_parts) + ";"

print(f"🔧 Executing {len(test_scenarios)} function calls...")
results_df = execute_query(full_query)

# Convert Decimal columns to float for easier handling
numeric_cols = ['hours_per_month', 'dbu_per_month', 'dbu_price', 'dbu_cost_per_month', 
                'vm_cost_per_month', 'cost_per_month']
for col in numeric_cols:
    if col in results_df.columns:
        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

print(f"✅ Retrieved {len(results_df)} results")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Display Results

# COMMAND ----------

# Select columns to display
display_cols = ['scenario_id', 'cloud', 'region', 'tier', 'warehouse_size', 'num_clusters',
                'vm_pricing_tier', 'vm_payment_option', 'hours_per_month', 
                'dbu_price', 'dbu_per_month', 'dbu_cost_per_month',
                'vm_cost_per_month', 'cost_per_month']

available_cols = [col for col in display_cols if col in results_df.columns]

print("=" * 80)
print("DBSQL CLASSIC TEST RESULTS")
print("=" * 80)
display(results_df[available_cols])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation

# COMMAND ----------

print("=" * 80)
print("VALIDATION CHECKS")
print("=" * 80)

# Check 1: No zero DBU costs
zero_dbu_cost = results_df[results_df['dbu_cost_per_month'] == 0]
if len(zero_dbu_cost) == 0:
    print("✅ PASS: All scenarios have positive DBU costs")
else:
    print(f"❌ FAIL: {len(zero_dbu_cost)} scenarios have $0 DBU costs!")
    display(zero_dbu_cost[available_cols])

# Check 2: No zero VM costs
zero_vm_cost = results_df[results_df['vm_cost_per_month'] == 0]
if len(zero_vm_cost) == 0:
    print("✅ PASS: All scenarios have positive VM costs")
else:
    print(f"❌ FAIL: {len(zero_vm_cost)} scenarios have $0 VM costs!")
    display(zero_vm_cost[available_cols])

# Check 3: Total cost = DBU cost + VM cost
results_df['calculated_total'] = results_df['dbu_cost_per_month'] + results_df['vm_cost_per_month']
results_df['cost_diff'] = abs(results_df['cost_per_month'] - results_df['calculated_total'])
mismatched_costs = results_df[results_df['cost_diff'] > 0.01]
if len(mismatched_costs) == 0:
    print("✅ PASS: Total cost = DBU cost + VM cost for all scenarios")
else:
    print(f"❌ FAIL: {len(mismatched_costs)} scenarios have cost calculation mismatches!")
    display(mismatched_costs[available_cols + ['calculated_total', 'cost_diff']])

# Check 4: Different warehouse sizes have different costs
for cloud in clouds:
    for tier in ['STANDARD', 'PREMIUM', 'ENTERPRISE']:
        if cloud == 'AZURE' and tier == 'ENTERPRISE':
            continue
        subset = results_df[(results_df['cloud'] == cloud) & (results_df['tier'] == tier)]
        if len(subset) > 0:
            unique_costs = subset.groupby('warehouse_size')['cost_per_month'].mean()
            if len(unique_costs.unique()) == len(warehouse_sizes):
                print(f"✅ PASS: {cloud} {tier} - Different costs for different warehouse sizes")
            else:
                print(f"⚠️  WARNING: {cloud} {tier} - Same costs for different warehouse sizes")

# Check 5: AWS payment options have different costs
aws_results = results_df[results_df['cloud'] == 'AWS']
if len(aws_results) > 0:
    # For reserved instances, check if payment options differ
    reserved_results = aws_results[aws_results['vm_pricing_tier'].isin(['reserved_1y', 'reserved_3y'])]
    if len(reserved_results) > 0:
        unique_payment_costs = reserved_results.groupby('vm_payment_option')['cost_per_month'].mean()
        if len(unique_payment_costs.unique()) > 1:
            print(f"✅ PASS: AWS reserved instances have different costs for different payment options")
        else:
            print(f"⚠️  WARNING: AWS reserved instances have same costs for all payment options")

print("=" * 80)
print("DBSQL CLASSIC TEST COMPLETE")
print("=" * 80)
