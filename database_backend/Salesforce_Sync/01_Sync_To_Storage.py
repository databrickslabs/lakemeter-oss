# Databricks notebook source
# MAGIC %md
# MAGIC # Sync Materialized Views to Azure Storage
# MAGIC
# MAGIC **Run this notebook in LOGFOOD workspace** (`adb-2548836972759138`)
# MAGIC
# MAGIC This notebook:
# MAGIC 1. Reads from materialized views created by the LDP (01_Salesforce_LDP.sql)
# MAGIC 2. Writes to Azure Storage (lakemeter container) as Parquet
# MAGIC
# MAGIC **Changed from v1:** Now reads from MVs instead of raw tables for better performance and consistency
# MAGIC
# MAGIC Then run `02_Import_From_Storage` in **Lakemeter workspace** to load into Lakebase.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# Azure Storage Configuration
STORAGE_ACCOUNT = "lakemeterprodsteven"
CONTAINER = "lakemeter"
STORAGE_KEY = "PDNtAAtkRNecLvKSpgbzVYUBauufOkCzdg3K1050PRFkffKhTIFrw0nUn2PMiuyGtYvayaTS6l9y+ASt8SD+bA=="

# Storage path - write directly to container root with sf_ prefix
STORAGE_PATH = f"abfss://{CONTAINER}@{STORAGE_ACCOUNT}.dfs.core.windows.net"

# Table prefix to avoid conflicts
TABLE_PREFIX = "sf_"

# Materialized views to sync (created by 01_Salesforce_LDP.sql)
# MVs are already pre-processed (deduplicated, distinct, transformed)
# Schema: Adjust if MVs are in different schema
MV_SCHEMA = "users.steven_tan"  # Change if MVs are in different schema

TABLES_TO_SYNC = [
    {
        "source": f"{MV_SCHEMA}.mv_dim_salesforce_account",
        "target": "dim_salesforce_account",
        "columns": ["salesforce_account_id", "salesforce_account_name"],
        "all_columns": False  # Select specific columns
    },
    {
        "source": f"{MV_SCHEMA}.mv_fct_salesforce_use_case",
        "target": "fct_salesforce_use_case",
        "columns": ["customer_id", "salesforce_use_case_id", "dim_canonical_customer_name", "dim_salesforce_use_case_id", "salesforce_use_case_name"],
        "all_columns": False
    },
    {
        "source": f"{MV_SCHEMA}.mv_hourly_opportunity",
        "target": "hourly_opportunity",
        "columns": ["id", "name", "accountid"],
        "all_columns": False
    },
    {
        "source": f"{MV_SCHEMA}.mv_baseline_consumption",
        "target": "baseline_consumption",
        "columns": None,  # Will use all columns
        "all_columns": True  # Use all 106 columns
    }
]

# Number of output files (partitions)
NUM_OUTPUT_FILES = 4  # Reasonable number for Spark to read

print(f"✅ Storage Account: {STORAGE_ACCOUNT}")
print(f"✅ Container: {CONTAINER}")
print(f"✅ Output Path: {STORAGE_PATH}")
print(f"✅ Output Files: {NUM_OUTPUT_FILES}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configure Spark for Azure Storage

# COMMAND ----------

# Set Azure Storage credentials
spark.conf.set(f"fs.azure.account.key.{STORAGE_ACCOUNT}.blob.core.windows.net", STORAGE_KEY)
spark.conf.set(f"fs.azure.account.key.{STORAGE_ACCOUNT}.dfs.core.windows.net", STORAGE_KEY)

print("✅ Azure Storage configured")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Storage Connection

# COMMAND ----------

# Test write access
try:
    test_df = spark.createDataFrame([("test", 1)], ["col1", "col2"])
    test_path = f"{STORAGE_PATH}/_test"
    test_df.write.mode("overwrite").parquet(test_path)
    
    # Read back
    result = spark.read.parquet(test_path)
    print(f"✅ Storage connection successful! Test rows: {result.count()}")
    
    # Cleanup test
    dbutils.fs.rm(test_path, recurse=True)
    print("✅ Test file cleaned up")
    
except Exception as e:
    print(f"❌ Storage connection failed: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Clean Up Old Files

# COMMAND ----------

# Delete old files before writing (to avoid Delta vs Parquet conflicts)
print("🗑️ Cleaning up old files...")
for table_config in TABLES_TO_SYNC:
    target = table_config["target"]
    path = f"{STORAGE_PATH}/{TABLE_PREFIX}{target}"
    try:
        dbutils.fs.rm(path, recurse=True)
        print(f"   ✅ Deleted: {path}")
    except Exception as e:
        print(f"   ⏭️ {TABLE_PREFIX}{target}: {e}")

print("✅ Cleanup complete")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sync Tables to Storage

# COMMAND ----------

import traceback

def sync_table_to_storage(table_config):
    """Sync a single materialized view to Azure Storage"""
    
    source = table_config["source"]
    target = table_config["target"]
    columns = table_config.get("columns", None)
    all_columns = table_config.get("all_columns", False)
    output_path = f"{STORAGE_PATH}/{TABLE_PREFIX}{target}"
    
    print(f"\n📥 Syncing MV: {source}")
    
    # Read from materialized view (already pre-processed)
    print(f"   Reading from materialized view...")
    
    if all_columns:
        # Read all columns (for baseline_consumption with 106 columns)
        print(f"   Using ALL columns")
        df = spark.table(source)
    else:
        # Select specific columns
        print(f"   Columns: {columns}")
        df = spark.table(source).select(*columns)
    
    row_count = df.count()
    print(f"   Found {row_count:,} rows")
    
    # Coalesce to fixed number of output files
    df = df.coalesce(NUM_OUTPUT_FILES)
    
    # Write to storage as Parquet (overwrite mode)
    print(f"   Writing to: {output_path} ({NUM_OUTPUT_FILES} files)")
    df.write \
        .mode("overwrite") \
        .format("parquet") \
        .save(output_path)
    
    print(f"✅ Synced: {source} → {output_path} ({row_count:,} rows)")
    
    return {"table": target, "status": "Success", "rows": row_count, "path": output_path}

# COMMAND ----------

results = []
for table_config in TABLES_TO_SYNC:
    try:
        result = sync_table_to_storage(table_config)
        results.append(result)
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error syncing {table_config['target']}:")
        print(traceback.format_exc())
        results.append({
            "table": table_config["target"],
            "status": f"Error: {error_msg[:100]}",
            "rows": 0,
            "path": ""
        })

# Display results
display(spark.createDataFrame(results))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Files in Storage

# COMMAND ----------

print("📁 Files in storage:")
for table_config in TABLES_TO_SYNC:
    target = table_config["target"]
    path = f"{STORAGE_PATH}/{TABLE_PREFIX}{target}"
    try:
        files = dbutils.fs.ls(path)
        parquet_files = [f for f in files if f.name.endswith('.parquet')]
        size_mb = sum([f.size for f in files]) / (1024*1024)
        print(f"   ✅ {TABLE_PREFIX}{target}: {len(parquet_files)} parquet files, {size_mb:.2f} MB")
    except Exception as e:
        print(f"   ❌ {TABLE_PREFIX}{target}: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Done!
# MAGIC
# MAGIC Data exported to Azure Storage as Parquet:
# MAGIC ```
# MAGIC abfss://lakemeter@lakemeterprodsteven.dfs.core.windows.net/
# MAGIC ├── sf_dim_salesforce_account/     (4 parquet files, ~2 columns)
# MAGIC ├── sf_fct_salesforce_use_case/    (4 parquet files, ~5 columns)
# MAGIC ├── sf_hourly_opportunity/         (4 parquet files, ~3 columns)
# MAGIC └── sf_baseline_consumption/       (4 parquet files, 106 columns: 10 dims + 96 measures)
# MAGIC ```
# MAGIC
# MAGIC **Baseline Consumption Structure:**
# MAGIC - 10 dimensions: account, workspace, cloud, tier, product_type, region, shield_sku, usage_unit
# MAGIC - 96 measures: 6 metrics × 16 time periods (3m, 30d, 90d, 1m, m1-m12)
# MAGIC - ~100K rows (pre-aggregated)
# MAGIC
# MAGIC **Next Step:** Run `02_Import_From_Storage` in **Lakemeter workspace** to load into Lakebase.