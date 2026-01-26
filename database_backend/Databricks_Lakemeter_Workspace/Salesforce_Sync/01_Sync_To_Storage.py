# Databricks notebook source
# MAGIC %md
# MAGIC # Sync Salesforce Tables to Azure Storage
# MAGIC
# MAGIC **Run this notebook in LOGFOOD workspace** (`adb-2548836972759138`)
# MAGIC
# MAGIC This notebook:
# MAGIC 1. Reads Salesforce tables from Unity Catalog
# MAGIC 2. Writes to Azure Storage (lakemeter container) as Parquet
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

# Tables to sync with specific columns
# For dedup_by: deduplicate by this column, keeping the record with max of order_by column
TABLES_TO_SYNC = [
    {
        "source": "main.metric_store.dim_salesforce_account",
        "target": "dim_salesforce_account",
        "columns": ["salesforce_account_id", "salesforce_account_name"],
        "distinct": False,
        "dedup_by": "salesforce_account_name",  # Keep one record per account name
        "order_by": "ds"  # Keep the one with max ds
    },
    {
        "source": "main.metric_store.fct_salesforce_use_case__core",
        "target": "fct_salesforce_use_case",
        "columns": ["customer_id", "salesforce_use_case_id", "dim_canonical_customer_name", "dim_salesforce_use_case_id", "salesforce_use_case_name"],
        "distinct": True
    },
    {
        "source": "main.sfdc_bronze.hourly_opportunity",
        "target": "hourly_opportunity",
        "columns": ["id", "name", "accountid"],
        "distinct": True
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
from pyspark.sql.window import Window
from pyspark.sql import functions as F

def sync_table_to_storage(table_config):
    """Sync a single table from Unity Catalog to Azure Storage"""
    
    source = table_config["source"]
    target = table_config["target"]
    columns = table_config["columns"]
    use_distinct = table_config.get("distinct", False)
    dedup_by = table_config.get("dedup_by", None)
    order_by = table_config.get("order_by", None)
    output_path = f"{STORAGE_PATH}/{TABLE_PREFIX}{target}"
    
    print(f"\n📥 Syncing: {source}")
    print(f"   Columns: {columns}")
    
    # Read from Unity Catalog
    print(f"   Reading from Unity Catalog...")
    
    if dedup_by and order_by:
        # Deduplicate by a column, keeping the record with max of order_by column
        print(f"   Deduplicating by '{dedup_by}', keeping max '{order_by}'...")
        
        # Read with order_by column included for deduplication
        read_columns = columns + [order_by] if order_by not in columns else columns
        df = spark.table(source).select(*read_columns)
        
        # Use window function to rank records
        window = Window.partitionBy(dedup_by).orderBy(F.col(order_by).desc())
        df = df.withColumn("_rank", F.row_number().over(window))
        df = df.filter(F.col("_rank") == 1).drop("_rank")
        
        # Select only the final output columns
        df = df.select(*columns)
    else:
        df = spark.table(source).select(*columns)
        
        # Apply distinct if needed
        if use_distinct:
            print(f"   Applying DISTINCT...")
            df = df.distinct()
    
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
# MAGIC abfss://lakemeter@lakemeter.dfs.core.windows.net/salesforce_sync/
# MAGIC ├── dim_salesforce_account/     (4 parquet files)
# MAGIC ├── fct_salesforce_use_case/    (4 parquet files)
# MAGIC └── hourly_opportunity/         (4 parquet files)
# MAGIC ```
# MAGIC
# MAGIC **Next Step:** Run `02_Import_From_Storage` in **Lakemeter workspace** to load into Lakebase.