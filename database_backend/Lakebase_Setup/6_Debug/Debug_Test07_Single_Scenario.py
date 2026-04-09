# Databricks notebook source
# MAGIC %md
# MAGIC # 🐛 DEBUG: Test_Func_07 Single Reserved Scenario
# MAGIC
# MAGIC Test EXACTLY what Test_Func_07 does for ONE reserved instance scenario

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
        df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test scenario: AWS us-east-1 STANDARD 2X-Large 1cl reserved_1y all_upfront

# COMMAND ----------

# This mimics EXACTLY what Test_Func_07 generates
scenario = {
    'cloud': 'AWS',
    'region': 'us-east-1',
    'tier': 'STANDARD',
    'warehouse_size': '2X-Large',
    'num_clusters': 1,
    'vm_pricing_tier': 'reserved_1y',
    'vm_payment_option': 'all_upfront',
    'hours_per_day': 8,
    'days_per_month': 30
}

print("📋 Test Scenario:")
for key, value in scenario.items():
    print(f"   {key}: {value}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate SQL query EXACTLY like Test_Func_07 does

# COMMAND ----------

# This is THE EXACT query generation from Test_Func_07
sql_query = f"""
    SELECT 
        1 as scenario_id,
        'AWS us-east-1 STANDARD 2X-Large 1cl reserved_1y all_upfront'::VARCHAR as label,
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
    );
"""

print("🔍 Generated SQL:")
print("=" * 100)
print(sql_query)
print("=" * 100)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Execute the query

# COMMAND ----------

print("\n🚀 Executing query...")
result = execute_query(sql_query)

print(f"\n📊 Results:")
display(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check the results

# COMMAND ----------

vm_cost = float(result['vm_cost_per_month'].iloc[0])
total_cost = float(result['cost_per_month'].iloc[0])

print(f"💰 COSTS:")
print(f"   VM cost per month: ${vm_cost:,.2f}")
print(f"   Total cost per month: ${total_cost:,.2f}")
print("")

if vm_cost == 0:
    print("❌ FAILED: VM cost is $0!")
    print("\n🔍 This means:")
    print("   • The query was generated correctly")
    print("   • But the function returned $0")
    print("   • Even though Debug_Reserved_Lookup showed it working!")
    print("\n💡 Possible causes:")
    print("   1. Different function being called (check schema/function name)")
    print("   2. Parameter order mismatch")
    print("   3. String vs. type conversion issue")
else:
    print(f"✅ SUCCESS: VM cost is ${vm_cost:,.2f}")
    print("\n🎉 The function works when called this way!")
    print("   → Test_Func_07 should also work")
    print("   → If Test_Func_07 still fails, there's a different issue")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Count parameters

# COMMAND ----------

# Count how many parameters we're passing
import re
params = re.findall(r'::[A-Z]+', sql_query)
print(f"📊 Total parameters being passed: {len(params)}")
print("\nExpected: 35 parameters (including dbsql_vm_payment_option)")

if len(params) == 35:
    print("✅ Correct parameter count!")
else:
    print(f"❌ Wrong parameter count! Expected 35, got {len(params)}")



