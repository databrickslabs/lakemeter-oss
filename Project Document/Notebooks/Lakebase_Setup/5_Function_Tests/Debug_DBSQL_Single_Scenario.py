# Databricks notebook source
# MAGIC %md
# MAGIC # 🐛 DEBUG: Single DBSQL Classic Scenario
# MAGIC
# MAGIC Test just ONE scenario to see the full error message

# COMMAND ----------

import sys
sys.path.append('/Workspace/Users/steven.tan@databricks.com/lakemeter/Lakebase_Setup')

from config import get_lakebase_connection
import pandas as pd
import psycopg2

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🔌 Connect to Lakebase

# COMMAND ----------

conn_params = get_lakebase_connection()
print(f"✅ Connecting to: {conn_params['host']}:{conn_params['port']}/{conn_params['database']}")

conn = psycopg2.connect(**conn_params)
print("✅ Connected to Lakebase")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 🧪 Test Single Scenario: AWS us-east-1 STANDARD 2X-Large

# COMMAND ----------

test_sql = """
SELECT 
    'AWS us-east-1 STANDARD 2X-Large 1cl on_demand'::VARCHAR as test_label,
    *
FROM lakemeter.calculate_line_item_costs(
    'DBSQL'::VARCHAR,                        -- workload_type
    'AWS'::VARCHAR,                          -- cloud
    'us-east-1'::VARCHAR,                    -- region
    'STANDARD'::VARCHAR,                     -- tier
    FALSE::BOOLEAN,                          -- serverless_enabled
    FALSE::BOOLEAN,                          -- photon_enabled
    NULL::VARCHAR,                           -- dlt_edition
    NULL::VARCHAR,                           -- driver_node_type
    NULL::VARCHAR,                           -- worker_node_type
    0::INT,                                  -- num_workers
    'NA'::VARCHAR,                           -- driver_pricing_tier
    'NA'::VARCHAR,                           -- worker_pricing_tier
    8::INT,                                  -- runs_per_day
    60::INT,                                 -- avg_runtime_minutes
    30::INT,                                 -- days_per_month
    'standard'::VARCHAR,                     -- serverless_mode
    'classic'::VARCHAR,                      -- dbsql_warehouse_type
    '2X-Large'::VARCHAR,                     -- dbsql_warehouse_size
    1::INT,                                  -- dbsql_num_clusters
    'on_demand'::VARCHAR,                    -- dbsql_vm_pricing_tier
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
);
"""

print("🔍 Testing single DBSQL Classic scenario...")
print("=" * 100)

try:
    result = pd.read_sql_query(test_sql, conn)
    print("✅ SUCCESS! Function executed without errors.")
    print("\nResult:")
    display(result)
    
    # Check for NULL/0 costs
    if result['dbu_cost_per_month'].iloc[0] == 0:
        print("\n⚠️  WARNING: DBU cost is $0")
    if result['cost_per_month'].iloc[0] == 0:
        print("\n⚠️  WARNING: Total cost is $0")
    else:
        print(f"\n✅ Total cost: ${result['cost_per_month'].iloc[0]:,.2f}/month")
        
except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}")
    print(f"\n{str(e)}")
    print("\n" + "=" * 100)
    print("FULL ERROR DETAILS:")
    print("=" * 100)
    import traceback
    traceback.print_exc()

finally:
    conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📋 Next Steps
# MAGIC
# MAGIC - If this works, the issue might be with the large UNION ALL query
# MAGIC - If this fails, we'll see the FULL error message
# MAGIC - Check if it's a function signature mismatch or data issue




