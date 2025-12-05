# Databricks notebook source
# MAGIC %md
# MAGIC # Sync Salesforce Tables to Lakemeter
# MAGIC 
# MAGIC Syncs the following tables from source workspace to Lakebase:
# MAGIC - `main.metric_store.dim_salesforce_account`
# MAGIC - `main.metric_store.fct_salesforce_use_case__core`
# MAGIC - `main.sfdc_bronze.hourly_opportunity`
# MAGIC 
# MAGIC **Source Workspace:** `adb-2548836972759138.18.azuredatabricks.net`
# MAGIC **Target:** Lakebase (lakemeter-db)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup: Run 00_Setup_Secrets First
# MAGIC 
# MAGIC Run `00_Setup_Secrets` notebook to store the Logfood PAT token in:
# MAGIC - **Scope:** `lakemeter-credentials`
# MAGIC - **Key:** `logfood-pat-token`

# COMMAND ----------

# Configuration
SOURCE_WORKSPACE_HOST = "https://adb-2548836972759138.18.azuredatabricks.net"
SOURCE_WORKSPACE_PAT = dbutils.secrets.get("lakemeter-credentials", "logfood-pat-token")

# Tables to sync
TABLES_TO_SYNC = [
    {
        "source_catalog": "main",
        "source_schema": "metric_store", 
        "source_table": "dim_salesforce_account",
        "target_table": "sync_dim_salesforce_account"
    },
    {
        "source_catalog": "main",
        "source_schema": "metric_store",
        "source_table": "fct_salesforce_use_case__core",
        "target_table": "sync_fct_salesforce_use_case"
    },
    {
        "source_catalog": "main",
        "source_schema": "sfdc_bronze",
        "source_table": "hourly_opportunity",
        "target_table": "sync_hourly_opportunity"
    }
]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Fetch Tables using REST API

# COMMAND ----------

import requests
import pandas as pd
import time

WAREHOUSE_ID = "071969b1ec9a91ca"

def execute_sql(query: str) -> dict:
    """Execute SQL on remote workspace using Statement Execution API"""
    headers = {
        "Authorization": f"Bearer {SOURCE_WORKSPACE_PAT}",
        "Content-Type": "application/json"
    }
    
    # Submit query
    response = requests.post(
        f"{SOURCE_WORKSPACE_HOST}/api/2.0/sql/statements",
        headers=headers,
        json={
            "warehouse_id": WAREHOUSE_ID,
            "statement": query,
            "wait_timeout": "50s"
        }
    )
    
    if response.status_code != 200:
        raise Exception(f"API Error: {response.status_code} - {response.text}")
    
    result = response.json()
    
    # Poll for completion
    while result.get("status", {}).get("state") in ["PENDING", "RUNNING"]:
        time.sleep(2)
        statement_id = result["statement_id"]
        response = requests.get(
            f"{SOURCE_WORKSPACE_HOST}/api/2.0/sql/statements/{statement_id}",
            headers=headers
        )
        result = response.json()
    
    if result.get("status", {}).get("state") == "SUCCEEDED":
        return result
    else:
        raise Exception(f"Query failed: {result.get('status', {}).get('error', {}).get('message', 'Unknown error')}")

def fetch_table_from_source(catalog: str, schema: str, table: str, limit: int = None) -> pd.DataFrame:
    """Fetch table from source workspace using REST API"""
    
    query = f"SELECT * FROM {catalog}.{schema}.{table}"
    if limit:
        query += f" LIMIT {limit}"
    
    print(f"   Executing: {query[:80]}...")
    result = execute_sql(query)
    
    columns = [col["name"] for col in result["manifest"]["schema"]["columns"]]
    data = result["result"]["data_array"]
    
    return pd.DataFrame(data, columns=columns)


# COMMAND ----------

# MAGIC %md
# MAGIC ## Sync Tables to Lakebase

# COMMAND ----------

# Lakebase connection
LAKEBASE_HOST = "lakemeter-db"  # Your Lakebase instance
LAKEBASE_CATALOG = "lakemeter_pricing"

# COMMAND ----------

def sync_table_to_lakebase(table_config: dict):
    """Sync a single table from source to Lakebase"""
    
    source_full_name = f"{table_config['source_catalog']}.{table_config['source_schema']}.{table_config['source_table']}"
    target_table = table_config['target_table']
    
    print(f"📥 Fetching: {source_full_name}")
    
    # Fetch from source
    df = fetch_table_from_source(
        table_config['source_catalog'],
        table_config['source_schema'],
        table_config['source_table']
    )
    
    print(f"   Rows fetched: {len(df)}")
    
    # Convert to Spark DataFrame
    spark_df = spark.createDataFrame(df)
    
    # Write to Unity Catalog (which syncs to Lakebase)
    spark_df.write \
        .mode("overwrite") \
        .saveAsTable(f"{LAKEBASE_CATALOG}.{target_table}")
    
    print(f"✅ Synced to: {LAKEBASE_CATALOG}.{target_table}")
    
    return len(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run Sync

# COMMAND ----------

# Sync all tables
results = []
for table_config in TABLES_TO_SYNC:
    try:
        row_count = sync_table_to_lakebase(table_config)
        results.append({
            "table": table_config['target_table'],
            "status": "✅ Success",
            "rows": row_count
        })
    except Exception as e:
        results.append({
            "table": table_config['target_table'],
            "status": f"❌ Failed: {str(e)[:50]}",
            "rows": 0
        })

# Display results
display(spark.createDataFrame(results))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Sync

# COMMAND ----------

# Check synced tables
for table_config in TABLES_TO_SYNC:
    target_table = table_config['target_table']
    try:
        count = spark.table(f"{LAKEBASE_CATALOG}.{target_table}").count()
        print(f"✅ {target_table}: {count} rows")
    except Exception as e:
        print(f"❌ {target_table}: {e}")

