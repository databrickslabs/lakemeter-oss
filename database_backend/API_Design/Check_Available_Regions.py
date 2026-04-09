# Databricks notebook source
# MAGIC %md
# MAGIC # Check Available Regions by Cloud
# MAGIC
# MAGIC Query the database to see what regions are available for each cloud provider.

# COMMAND ----------

%run ../Lakebase_Setup/00_Lakebase_Config

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
        return pd.read_sql(query, conn)
    finally:
        conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Check Regions in sync_ref_sku_region_map

# COMMAND ----------

query = """
SELECT 
    cloud,
    COUNT(DISTINCT region_code) as region_count,
    STRING_AGG(DISTINCT region_code, ', ' ORDER BY region_code) as regions
FROM lakemeter.sync_ref_sku_region_map
GROUP BY cloud
ORDER BY cloud;
"""

result = execute_query(query)
print("Regions by Cloud (from sync_ref_sku_region_map):")
display(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Detailed Region List by Cloud

# COMMAND ----------

query = """
SELECT 
    cloud,
    region_code,
    region_name,
    COUNT(DISTINCT tier) as tier_count,
    STRING_AGG(DISTINCT tier, ', ' ORDER BY tier) as available_tiers
FROM lakemeter.sync_ref_sku_region_map
GROUP BY cloud, region_code, region_name
ORDER BY cloud, region_code;
"""

result = execute_query(query)
print("Detailed Regions:")
display(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Check Regions in sync_pricing_vm_costs

# COMMAND ----------

query = """
SELECT 
    cloud,
    COUNT(DISTINCT region_code) as region_count,
    STRING_AGG(DISTINCT region_code, ', ' ORDER BY region_code) as regions
FROM lakemeter.sync_pricing_vm_costs
GROUP BY cloud
ORDER BY cloud;
"""

result = execute_query(query)
print("Regions with VM Pricing Data:")
display(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Compare: Which regions have SKU data but NO VM pricing?

# COMMAND ----------

query = """
SELECT 
    s.cloud,
    s.region_code,
    s.region_name,
    CASE WHEN v.region_code IS NULL THEN 'Missing VM Pricing' ELSE 'Has VM Pricing' END as pricing_status
FROM (
    SELECT DISTINCT cloud, region_code, region_name
    FROM lakemeter.sync_ref_sku_region_map
) s
LEFT JOIN (
    SELECT DISTINCT cloud, region_code
    FROM lakemeter.sync_pricing_vm_costs
) v ON s.cloud = v.cloud AND s.region_code = v.region_code
ORDER BY s.cloud, s.region_code;
"""

result = execute_query(query)
print("Region Coverage Check:")
display(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. AWS Regions Detail

# COMMAND ----------

query = """
SELECT 
    region_code,
    region_name,
    tier,
    COUNT(*) as sku_count
FROM lakemeter.sync_ref_sku_region_map
WHERE cloud = 'AWS'
GROUP BY region_code, region_name, tier
ORDER BY region_code, tier;
"""

result = execute_query(query)
print("AWS Regions Detail:")
display(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Azure Regions Detail

# COMMAND ----------

query = """
SELECT 
    region_code,
    region_name,
    tier,
    COUNT(*) as sku_count
FROM lakemeter.sync_ref_sku_region_map
WHERE cloud = 'AZURE'
GROUP BY region_code, region_name, tier
ORDER BY region_code, tier;
"""

result = execute_query(query)
print("Azure Regions Detail:")
display(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. GCP Regions Detail

# COMMAND ----------

query = """
SELECT 
    region_code,
    region_name,
    tier,
    COUNT(*) as sku_count
FROM lakemeter.sync_ref_sku_region_map
WHERE cloud = 'GCP'
GROUP BY region_code, region_name, tier
ORDER BY region_code, tier;
"""

result = execute_query(query)
print("GCP Regions Detail:")
display(result)


