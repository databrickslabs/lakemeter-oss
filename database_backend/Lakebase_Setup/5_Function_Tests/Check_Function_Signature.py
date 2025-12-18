# Databricks notebook source
# MAGIC %md
# MAGIC # Check calculate_line_item_costs Function Signature
# MAGIC 
# MAGIC **Purpose:** Verify the actual function signature in PostgreSQL

# COMMAND ----------

%run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd

def get_connection():
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DB,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD
    )

def execute_query(query):
    conn = get_connection()
    try:
        df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()

print("✅ Connection setup complete!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check Function Signature

# COMMAND ----------

query = """
SELECT 
    p.proname as function_name,
    pg_get_function_arguments(p.oid) as parameters,
    pg_get_function_result(p.oid) as return_type
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'lakemeter'
  AND p.proname = 'calculate_line_item_costs'
ORDER BY p.proname;
"""

result = execute_query(query)

if len(result) > 0:
    print("✅ Function EXISTS in database\n")
    print("=" * 100)
    print("FUNCTION SIGNATURE:")
    print("=" * 100)
    
    params = result.iloc[0]['parameters']
    print(f"\nParameters:\n{params}\n")
    
    # Split and number the parameters
    param_list = params.split(', ')
    print("=" * 100)
    print(f"Total parameters: {len(param_list)}")
    print("=" * 100)
    for i, param in enumerate(param_list, 1):
        print(f"{i:3}. {param}")
else:
    print("❌ Function NOT FOUND in database!")
    print("\nYou need to run: 4_Functions/09_Main_Orchestrator")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Compare with Expected Signature

# COMMAND ----------

expected_params = [
    "p_workload_type",
    "p_cloud",
    "p_region",
    "p_tier",
    "p_serverless_enabled",
    "p_photon_enabled",
    "p_dlt_edition",
    "p_driver_node_type",
    "p_worker_node_type",
    "p_num_workers",
    "p_driver_pricing_tier",
    "p_worker_pricing_tier",
    "p_runs_per_day",  # NEW!
    "p_avg_runtime_minutes",  # NEW!
    "p_days_per_month",  # MOVED!
    "p_serverless_mode",
    "p_dbsql_warehouse_type",
    "p_dbsql_warehouse_size",
    "p_dbsql_num_clusters",
    "p_dbsql_vm_pricing_tier",
    "p_vector_search_mode",
    "p_vector_search_capacity_millions",
    "p_serverless_size",
    "p_fmapi_model",
    "p_fmapi_provider",
    "p_fmapi_endpoint_type",
    "p_fmapi_context_length",
    "p_fmapi_provisioned_type",
    "p_fmapi_input_tokens_per_month",
    "p_fmapi_output_tokens_per_month",
    "p_lakebase_cu",
    "p_lakebase_ha_nodes",
    "p_driver_payment_option",
    "p_worker_payment_option",
    "p_dbsql_vm_payment_option"
]

print("=" * 100)
print("EXPECTED SIGNATURE (from 09_Main_Orchestrator.py):")
print("=" * 100)
print(f"\nTotal parameters: {len(expected_params)}\n")
for i, param in enumerate(expected_params, 1):
    print(f"{i:3}. {param}")
