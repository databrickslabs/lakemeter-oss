# Databricks notebook source
# MAGIC %md
# MAGIC # Sync Salesforce Tables to Azure Storage (Direct Sync)
# MAGIC
# MAGIC **Run this notebook in LOGFOOD workspace** (`adb-2548836972759138.18.azuredatabricks.net`)
# MAGIC
# MAGIC This notebook:
# MAGIC 1. Reads Salesforce tables from Unity Catalog
# MAGIC 2. Applies transformations (dedup, distinct)
# MAGIC 3. Writes directly to Azure Storage as Parquet
# MAGIC
# MAGIC **Next Step:** Run `02_Import_From_Storage` in **Lakemeter workspace**

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# Azure Storage Configuration (using secrets)
STORAGE_ACCOUNT = "lakemeterprodsteven"
CONTAINER = "lakemeter"

# Get storage key from secrets (recommended) or fallback to direct value
try:
    STORAGE_KEY = dbutils.secrets.get(scope="lakemeter-credentials", key="azure-storage-key")
    print("✅ Using storage key from secrets")
except:
    # Fallback to direct key (not recommended for production)
    STORAGE_KEY = "PDNtAAtkRNecLvKSpgbzVYUBauufOkCzdg3K1050PRFkffKhTIFrw0nUn2PMiuyGtYvayaTS6l9y+ASt8SD+bA=="
    print("⚠️  Using hardcoded storage key")

# Storage path
STORAGE_PATH = f"abfss://{CONTAINER}@{STORAGE_ACCOUNT}.dfs.core.windows.net"
TABLE_PREFIX = "sf_"

# Number of output files (partitions)
NUM_OUTPUT_FILES = 4

print(f"✅ Storage Account: {STORAGE_ACCOUNT}")
print(f"✅ Container: {CONTAINER}")
print(f"✅ Output Path: {STORAGE_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Table Configuration

# COMMAND ----------

TABLES_TO_SYNC = [
    {
        "name": "dim_salesforce_account",
        "source": "main.metric_store.dim_salesforce_account",
        "target": "dim_salesforce_account",
        "columns": ["salesforce_account_id", "salesforce_account_name"],
        "transformation": "dedup",
        "dedup_by": "salesforce_account_name",
        "order_by": "ds"
    },
    {
        "name": "fct_salesforce_use_case",
        "source": "main.metric_store.fct_salesforce_use_case__core",
        "target": "fct_salesforce_use_case",
        "columns": ["customer_id", "salesforce_use_case_id", "dim_canonical_customer_name", 
                   "dim_salesforce_use_case_id", "salesforce_use_case_name"],
        "transformation": "distinct"
    },
    {
        "name": "hourly_opportunity",
        "source": "main.sfdc_bronze.hourly_opportunity",
        "target": "hourly_opportunity",
        "columns": ["id", "name", "accountid"],
        "transformation": "distinct"
    }
]

print(f"📋 Tables to sync: {len(TABLES_TO_SYNC)}")
for table in TABLES_TO_SYNC:
    print(f"   • {table['name']} ({table['transformation']})")

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

from datetime import datetime

# Test write access
try:
    test_df = spark.createDataFrame([("test", 1, datetime.now())], ["col1", "col2", "timestamp"])
    test_path = f"{STORAGE_PATH}/_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    test_df.write.mode("overwrite").parquet(test_path)
    
    # Read back
    result = spark.read.parquet(test_path)
    print(f"✅ Storage connection successful! Test rows: {result.count()}")
    
    # Cleanup test
    dbutils.fs.rm(test_path, recurse=True)
    print("✅ Test file cleaned up")
    
except Exception as e:
    print(f"❌ Storage connection failed: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Transformation Functions

# COMMAND ----------

from pyspark.sql.window import Window
from pyspark.sql import functions as F
import traceback

def apply_dedup_transformation(df, dedup_by, order_by, columns):
    """Deduplicate DataFrame by column, keeping record with max order_by value"""
    
    print(f"   🔄 Deduplicating by '{dedup_by}', keeping max '{order_by}'...")
    
    # Read with order_by column included for deduplication
    read_columns = columns + [order_by] if order_by not in columns else columns
    df_with_order = df.select(*read_columns)
    
    # Use window function to rank records
    window = Window.partitionBy(dedup_by).orderBy(F.col(order_by).desc())
    df_deduped = df_with_order.withColumn("_rank", F.row_number().over(window))
    df_deduped = df_deduped.filter(F.col("_rank") == 1).drop("_rank")
    
    # Select only the final output columns
    return df_deduped.select(*columns)

def apply_distinct_transformation(df, columns):
    """Apply DISTINCT to DataFrame"""
    
    print(f"   🔄 Applying DISTINCT...")
    return df.select(*columns).distinct()

def get_row_count(df):
    """Get row count with proper error handling"""
    try:
        return df.count()
    except Exception as e:
        print(f"   ⚠️  Could not get row count: {e}")
        return -1

# COMMAND ----------

# MAGIC %md
# MAGIC ## Clean Up Old Files

# COMMAND ----------

print("🗑️  Cleaning up old files...")
cleanup_results = []

for table_config in TABLES_TO_SYNC:
    target = table_config["target"]
    path = f"{STORAGE_PATH}/{TABLE_PREFIX}{target}"
    try:
        dbutils.fs.rm(path, recurse=True)
        cleanup_results.append({"table": target, "status": "✅ Deleted"})
        print(f"   ✅ Deleted: {TABLE_PREFIX}{target}")
    except Exception as e:
        cleanup_results.append({"table": target, "status": "⏭️  Not found"})
        print(f"   ⏭️  {TABLE_PREFIX}{target}: Not found (OK)")

print("✅ Cleanup complete\n")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sync Tables to Storage

# COMMAND ----------

def sync_table_to_storage(table_config):
    """
    Sync a single table from Unity Catalog to Azure Storage
    
    Returns:
        dict: Sync result with status, rows, and metadata
    """
    
    source = table_config["source"]
    target = table_config["target"]
    columns = table_config["columns"]
    transformation = table_config.get("transformation", "none")
    output_path = f"{STORAGE_PATH}/{TABLE_PREFIX}{target}"
    
    sync_start = datetime.now()
    
    print(f"\n{'='*80}")
    print(f"📥 SYNCING: {table_config['name']}")
    print(f"{'='*80}")
    print(f"   Source: {source}")
    print(f"   Target: {output_path}")
    print(f"   Columns: {len(columns)}")
    print(f"   Transformation: {transformation}")
    
    try:
        # Read from Unity Catalog
        print(f"\n   📖 Reading from Unity Catalog...")
        source_df = spark.table(source)
        
        # Apply transformation based on config
        if transformation == "dedup":
            dedup_by = table_config.get("dedup_by")
            order_by = table_config.get("order_by")
            if not dedup_by or not order_by:
                raise ValueError(f"dedup transformation requires 'dedup_by' and 'order_by' fields")
            df = apply_dedup_transformation(source_df, dedup_by, order_by, columns)
            
        elif transformation == "distinct":
            df = apply_distinct_transformation(source_df, columns)
            
        else:
            # No transformation, just select columns
            print(f"   🔄 Selecting columns...")
            df = source_df.select(*columns)
        
        # Get row count
        row_count = get_row_count(df)
        print(f"   ✅ Processed {row_count:,} rows")
        
        # Coalesce to fixed number of output files
        df = df.coalesce(NUM_OUTPUT_FILES)
        
        # Write to storage as Parquet
        print(f"\n   💾 Writing to storage ({NUM_OUTPUT_FILES} files)...")
        df.write \
            .mode("overwrite") \
            .format("parquet") \
            .save(output_path)
        
        sync_duration = (datetime.now() - sync_start).total_seconds()
        
        print(f"\n   ✅ SUCCESS!")
        print(f"   • Rows: {row_count:,}")
        print(f"   • Duration: {sync_duration:.2f}s")
        print(f"   • Path: {output_path}")
        
        return {
            "table": target,
            "status": "✅ Success",
            "rows": row_count,
            "duration_sec": round(sync_duration, 2),
            "path": output_path,
            "error": None
        }
        
    except Exception as e:
        sync_duration = (datetime.now() - sync_start).total_seconds()
        error_msg = str(e)
        
        print(f"\n   ❌ FAILED!")
        print(f"   Error: {error_msg}")
        print(f"\n   Full traceback:")
        print(traceback.format_exc())
        
        return {
            "table": target,
            "status": f"❌ Failed",
            "rows": 0,
            "duration_sec": round(sync_duration, 2),
            "path": output_path,
            "error": error_msg[:200]
        }

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run Sync for All Tables

# COMMAND ----------

print("🚀 Starting sync process...\n")

results = []
for i, table_config in enumerate(TABLES_TO_SYNC, 1):
    print(f"\n[{i}/{len(TABLES_TO_SYNC)}]")
    result = sync_table_to_storage(table_config)
    results.append(result)

print(f"\n{'='*80}")
print("🏁 SYNC COMPLETE")
print(f"{'='*80}\n")

# Display results
results_df = spark.createDataFrame(results)
display(results_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Files in Storage

# COMMAND ----------

print("📁 Verifying files in storage:\n")

verification_results = []

for table_config in TABLES_TO_SYNC:
    target = table_config["target"]
    path = f"{STORAGE_PATH}/{TABLE_PREFIX}{target}"
    
    try:
        files = dbutils.fs.ls(path)
        parquet_files = [f for f in files if f.name.endswith('.parquet')]
        total_size_mb = sum([f.size for f in files]) / (1024*1024)
        
        verification_results.append({
            "table": target,
            "files": len(parquet_files),
            "size_mb": round(total_size_mb, 2),
            "status": "✅ OK"
        })
        
        print(f"   ✅ {TABLE_PREFIX}{target}")
        print(f"      • Files: {len(parquet_files)} parquet")
        print(f"      • Size: {total_size_mb:.2f} MB\n")
        
    except Exception as e:
        verification_results.append({
            "table": target,
            "files": 0,
            "size_mb": 0,
            "status": f"❌ {str(e)[:50]}"
        })
        print(f"   ❌ {TABLE_PREFIX}{target}: {e}\n")

# Display verification results
verification_df = spark.createDataFrame(verification_results)
display(verification_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

# Calculate summary statistics
total_rows = sum([r["rows"] for r in results if r["rows"] > 0])
total_duration = sum([r["duration_sec"] for r in results])
success_count = sum([1 for r in results if r["status"] == "✅ Success"])
failed_count = len(results) - success_count

print("📊 SYNC SUMMARY")
print("="*80)
print(f"✅ Successful: {success_count}/{len(TABLES_TO_SYNC)}")
print(f"❌ Failed: {failed_count}/{len(TABLES_TO_SYNC)}")
print(f"📝 Total Rows: {total_rows:,}")
print(f"⏱️  Total Duration: {total_duration:.2f}s")
print(f"📍 Storage Path: {STORAGE_PATH}")
print("="*80)

if failed_count > 0:
    print("\n⚠️  WARNING: Some tables failed to sync!")
    for r in results:
        if r["status"] != "✅ Success":
            print(f"   ❌ {r['table']}: {r['error']}")
else:
    print("\n🎉 All tables synced successfully!")

print(f"\n📌 Next Step: Run '02_Import_From_Storage' in Lakemeter workspace")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Done!
# MAGIC
# MAGIC Data exported to Azure Storage as Parquet:
# MAGIC ```
# MAGIC abfss://lakemeter@lakemeterprodsteven.dfs.core.windows.net/
# MAGIC ├── sf_dim_salesforce_account/     (4 parquet files)
# MAGIC ├── sf_fct_salesforce_use_case/    (4 parquet files)
# MAGIC └── sf_hourly_opportunity/         (4 parquet files)
# MAGIC ```
