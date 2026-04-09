# Databricks notebook source
# MAGIC %md
# MAGIC # 🔍 Check Valid Configurations for claude-sonnet-4-5

# COMMAND ----------

%run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd

def get_connection():
    return psycopg2.connect(host=LAKEBASE_HOST, port=LAKEBASE_PORT, database=LAKEBASE_DB, user=LAKEBASE_USER, password=LAKEBASE_PASSWORD)

def execute_query(query):
    conn = get_connection()
    try:
        return pd.read_sql(query, conn)
    finally:
        conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check if claude-sonnet-4-5 exists

# COMMAND ----------

check_model = """
SELECT 
    provider,
    model,
    endpoint_type,
    context_length,
    rate_type,
    dbu_rate,
    input_divisor
FROM lakemeter.sync_product_fmapi_proprietary
WHERE UPPER(model) = UPPER('claude-sonnet-4-5')
ORDER BY endpoint_type, context_length, rate_type;
"""

result = execute_query(check_model)
print(f"✅ Found {len(result)} row(s) for claude-sonnet-4-5")
display(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check all Anthropic models

# COMMAND ----------

check_anthropic = """
SELECT DISTINCT
    model,
    endpoint_type,
    context_length
FROM lakemeter.sync_product_fmapi_proprietary
WHERE UPPER(provider) = 'ANTHROPIC'
ORDER BY model, endpoint_type, context_length;
"""

result = execute_query(check_anthropic)
print(f"✅ Found {len(result)} Anthropic model configuration(s)")
display(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test the function call with different combinations

# COMMAND ----------

# Try with the configuration from the usage example
test_query = """
SELECT * FROM lakemeter.calculate_line_item_costs(
    'FMAPI_PROPRIETARY'::VARCHAR,
    'AWS'::VARCHAR,
    'us-east-1'::VARCHAR,
    'PREMIUM'::VARCHAR,
    FALSE::BOOLEAN, FALSE::BOOLEAN, NULL::VARCHAR,
    NULL::VARCHAR, NULL::VARCHAR, 0::INT,
    'NA'::VARCHAR, 'NA'::VARCHAR,
    1::INT, 60::INT, 30::INT, NULL::INT, NULL::VARCHAR,
    NULL::VARCHAR, NULL::VARCHAR, 1::INT, 'NA'::VARCHAR,
    NULL::VARCHAR, 0::DECIMAL, NULL::VARCHAR,
    'claude-sonnet-4-5'::VARCHAR,            -- fmapi_model
    'anthropic'::VARCHAR,                    -- fmapi_provider
    'global'::VARCHAR,                       -- fmapi_endpoint_type
    'all'::VARCHAR,                          -- fmapi_context_length
    'pay_per_token'::VARCHAR,                -- fmapi_provisioned_type
    2000000::BIGINT,                         -- fmapi_input_tokens_per_month
    500000::BIGINT,                          -- fmapi_output_tokens_per_month
    0::INT, 1::INT,
    'NA'::VARCHAR, 'NA'::VARCHAR, 'NA'::VARCHAR
);
"""

result = execute_query(test_query)
print("📊 Function result:")
display(result)


