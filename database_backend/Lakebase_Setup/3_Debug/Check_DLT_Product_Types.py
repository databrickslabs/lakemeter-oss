# Databricks notebook source
# MAGIC %md
# MAGIC # Quick Check: What are the exact DLT product_type names?
# MAGIC 
# MAGIC This notebook directly queries the pricing table to find the correct product_type for DLT Serverless.

# COMMAND ----------

import psycopg2
import pandas as pd

# Connection details
DB_HOST = "instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com"
DB_PORT = 5432
DB_NAME = "lakemeter_pricing"
DB_USER = "lakemeter_sync_role"
DB_PASSWORD = dbutils.secrets.get(scope="lakemeter-credentials", key="lakebase-password")

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        sslmode='require'
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Check ALL DLT-related product types

# COMMAND ----------

print("=" * 100)
print("🔍 CHECKING ALL DLT-RELATED PRODUCT TYPES IN PRICING TABLE")
print("=" * 100)

conn = get_connection()
cursor = conn.cursor()

# Query 1: All product types containing DLT or DELTA
sql1 = """
SELECT DISTINCT
    cloud,
    product_type
FROM lakemeter.sync_pricing_dbu_rates
WHERE product_type LIKE '%DLT%' OR product_type LIKE '%DELTA%'
ORDER BY cloud, product_type;
"""

cursor.execute(sql1)
results = cursor.fetchall()

print(f"\n📋 Found {len(results)} DLT-related product types:")
print("")
print("Cloud    | Product Type")
print("---------|-" + "-" * 60)

for row in results:
    cloud, product_type = row
    print(f"{cloud:8} | {product_type}")

cursor.close()
conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Check specific product_type we're looking for

# COMMAND ----------

print("\n" + "=" * 100)
print("🔍 CHECKING: JOBS_SERVERLESS_COMPUTE (current view logic)")
print("=" * 100)

conn = get_connection()
cursor = conn.cursor()

sql2 = """
SELECT 
    cloud,
    COUNT(DISTINCT region) as num_regions,
    COUNT(DISTINCT tier) as num_tiers,
    MIN(price_per_dbu) as min_price,
    MAX(price_per_dbu) as max_price
FROM lakemeter.sync_pricing_dbu_rates
WHERE product_type = 'JOBS_SERVERLESS_COMPUTE'
GROUP BY cloud;
"""

cursor.execute(sql2)
results = cursor.fetchall()

if len(results) > 0:
    print("\n✅ JOBS_SERVERLESS_COMPUTE EXISTS!")
    print("")
    print("Cloud    | Regions | Tiers | Min Price | Max Price")
    print("---------|---------| ------| ----------|-----------")
    for row in results:
        cloud, num_regions, num_tiers, min_price, max_price = row
        print(f"{cloud:8} | {num_regions:7} | {num_tiers:5} | ${float(min_price):8.4f} | ${float(max_price):8.4f}")
else:
    print("\n❌ JOBS_SERVERLESS_COMPUTE NOT FOUND!")
    print("   The view is looking for the wrong product_type!")

cursor.close()
conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Check alternative names

# COMMAND ----------

print("\n" + "=" * 100)
print("🔍 CHECKING ALTERNATIVE DLT SERVERLESS NAMES")
print("=" * 100)

conn = get_connection()
cursor = conn.cursor()

alternatives = [
    'JOBS_SERVERLESS_COMPUTE',
    'DLT_SERVERLESS_COMPUTE',
    'DLT_ADVANCED_SERVERLESS_COMPUTE',
    'DLT_PRO_SERVERLESS_COMPUTE',
    'DLT_CORE_SERVERLESS_COMPUTE',
    'DELTA_LIVE_TABLES_COMPUTE'
]

print("\nChecking which of these exist in pricing table:")
print("")

for product_type in alternatives:
    sql3 = """
    SELECT COUNT(*) as count
    FROM lakemeter.sync_pricing_dbu_rates
    WHERE product_type = %s;
    """
    
    cursor.execute(sql3, (product_type,))
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"  ✅ {product_type:45} → {count:4} rows")
    else:
        print(f"  ❌ {product_type:45} → NOT FOUND")

cursor.close()
conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Sample data for DLT serverless

# COMMAND ----------

print("\n" + "=" * 100)
print("📊 SAMPLE DLT SERVERLESS PRICING DATA")
print("=" * 100)

conn = get_connection()
cursor = conn.cursor()

sql4 = """
SELECT 
    cloud,
    region,
    tier,
    product_type,
    price_per_dbu
FROM lakemeter.sync_pricing_dbu_rates
WHERE product_type LIKE '%SERVERLESS%'
  AND (product_type LIKE '%DLT%' OR product_type LIKE '%DELTA%')
ORDER BY cloud, product_type, tier, region
LIMIT 20;
"""

cursor.execute(sql4)
results = cursor.fetchall()

if len(results) > 0:
    print(f"\n📋 Sample data ({len(results)} rows):")
    print("")
    print("Cloud    | Region       | Tier       | Product Type                          | Price")
    print("---------|--------------|------------|---------------------------------------|--------")
    
    for row in results:
        cloud, region, tier, product_type, price = row
        print(f"{cloud:8} | {region:12} | {tier:10} | {product_type:37} | ${float(price):6.4f}")
else:
    print("\n❌ NO DLT SERVERLESS PRICING DATA FOUND!")

cursor.close()
conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ SUMMARY
# MAGIC 
# MAGIC **Look at Section 1** to see ALL DLT product types available.
# MAGIC 
# MAGIC **The correct product_type name** is what you need to use in `1_Setup/02_Create_Views.py`
# MAGIC 
# MAGIC **Common fix needed:**
# MAGIC - If you see `DLT_ADVANCED_SERVERLESS_COMPUTE` instead of `JOBS_SERVERLESS_COMPUTE`
# MAGIC - Update line ~369 in `02_Create_Views.py`:
# MAGIC   ```python
# MAGIC   WHEN f.workload_type = 'DLT' THEN
# MAGIC       CASE 
# MAGIC           WHEN f.serverless_enabled THEN 'DLT_ADVANCED_SERVERLESS_COMPUTE'  # or whatever you found
# MAGIC   ```

