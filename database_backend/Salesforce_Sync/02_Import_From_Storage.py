# Databricks notebook source
# MAGIC %md
# MAGIC # Import Salesforce Data via UC Volume
# MAGIC 
# MAGIC **Strategy:** Download parquet → Upload to UC Volume → Read with Spark

# COMMAND ----------

# MAGIC %pip install azure-storage-blob

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# Azure Storage
STORAGE_ACCOUNT = "lakemeter"
CONTAINER = "lakemeter"
STORAGE_KEY = "wR3j2JLw79dVMBM734A4WcojQuDye6dVJCMgy8BMLlQWo5d3aKhZ78GHLLDZfycwnmwB7aI/L7rI+AStIbJbtA=="
TABLE_PREFIX = "sf_"

# UC Volume path
VOLUME_PATH = "/Volumes/lakemeter_catalog/lakemeter/salesforce"

# Tables to sync
TABLES = ["dim_salesforce_account", "fct_salesforce_use_case", "hourly_opportunity"]

print(f"✅ Volume: {VOLUME_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Connect to Azure Storage

# COMMAND ----------

from azure.storage.blob import BlobServiceClient

connection_string = f"DefaultEndpointsProtocol=https;AccountName={STORAGE_ACCOUNT};AccountKey={STORAGE_KEY};EndpointSuffix=core.windows.net"
blob_service_client = BlobServiceClient.from_connection_string(connection_string)
container_client = blob_service_client.get_container_client(CONTAINER)

print("✅ Connected to Azure Storage")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Download Parquet Files to UC Volume

# COMMAND ----------

import os
import shutil

for table_name in TABLES:
    prefix = f"{TABLE_PREFIX}{table_name}/"
    target_dir = f"{VOLUME_PATH}/{table_name}"
    
    print(f"\n📥 {table_name}:")
    
    # Clear and recreate target directory (always overwrite)
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
        print(f"   🗑️ Cleared existing folder")
    os.makedirs(target_dir, exist_ok=True)
    
    # List parquet files
    blobs = list(container_client.list_blobs(name_starts_with=prefix))
    parquet_blobs = [b for b in blobs if b.name.endswith('.parquet') and b.size > 0]
    
    print(f"   Found {len(parquet_blobs)} parquet files")
    
    # Download each file
    for i, blob in enumerate(parquet_blobs):
        filename = blob.name.split('/')[-1]
        target_path = f"{target_dir}/{filename}"
        
        # Download
        blob_client = container_client.get_blob_client(blob.name)
        data = blob_client.download_blob().readall()
        
        # Write to volume
        with open(target_path, 'wb') as f:
            f.write(data)
        
        if (i + 1) % 50 == 0 or i == 0:
            print(f"   Downloaded {i+1}/{len(parquet_blobs)} files")
    
    print(f"   ✅ Done: {len(parquet_blobs)} files → {target_dir}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Files in Volume

# COMMAND ----------

print("📁 Files in volume:")
for table_name in TABLES:
    target_dir = f"{VOLUME_PATH}/{table_name}"
    try:
        files = os.listdir(target_dir)
        parquet_files = [f for f in files if f.endswith('.parquet')]
        total_size = sum(os.path.getsize(f"{target_dir}/{f}") for f in parquet_files) / (1024*1024)
        print(f"   {table_name}: {len(parquet_files)} files, {total_size:.1f} MB")
    except Exception as e:
        print(f"   {table_name}: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Read from Volume and Create Tables

# COMMAND ----------

TARGET_CATALOG = "lakemeter_catalog"
TARGET_SCHEMA = "lakemeter"

for table_name in TABLES:
    source_path = f"{VOLUME_PATH}/{table_name}"
    full_table_name = f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{table_name}"
    
    print(f"\n📤 Creating table: {full_table_name}")
    
    try:
        # Read parquet from volume
        df = spark.read.parquet(source_path)
        row_count = df.count()
        print(f"   Read {row_count:,} rows")
        
        # Write as managed table
        df.write.mode("overwrite").saveAsTable(full_table_name)
        print(f"   ✅ Created: {full_table_name}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Tables

# COMMAND ----------

print("📋 Verifying tables:")
for table_name in TABLES:
    full_table_name = f"{TARGET_CATALOG}.{TARGET_SCHEMA}.{table_name}"
    try:
        count = spark.table(full_table_name).count()
        print(f"   ✅ {full_table_name}: {count:,} rows")
    except Exception as e:
        print(f"   ❌ {full_table_name}: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Done!
# MAGIC 
# MAGIC Tables created:
# MAGIC - `lakemeter_catalog.lakemeter.dim_salesforce_account`
# MAGIC - `lakemeter_catalog.lakemeter.fct_salesforce_use_case`
# MAGIC - `lakemeter_catalog.lakemeter.hourly_opportunity`
