# Databricks notebook source
# MAGIC %md
# MAGIC # 🔍 Check: What DBSQL Product Types Exist?

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd

conn = psycopg2.connect(
    host=LAKEBASE_HOST,
    port=LAKEBASE_PORT,
    database=LAKEBASE_DATABASE,
    user=LAKEBASE_USER,
    password=LAKEBASE_PASSWORD,
    sslmode='require'
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1️⃣ All product types containing "SQL"

# COMMAND ----------

query1 = """
SELECT DISTINCT 
    product_type,
    COUNT(*) as count
FROM lakemeter.sync_pricing_dbu_rates
WHERE product_type LIKE '%SQL%'
GROUP BY product_type
ORDER BY product_type;
"""

result1 = pd.read_sql_query(query1, conn)
print("📋 All SQL-related product types:")
display(result1)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2️⃣ Check for SERVERLESS product types

# COMMAND ----------

query2 = """
SELECT DISTINCT 
    product_type,
    COUNT(*) as count
FROM lakemeter.sync_pricing_dbu_rates
WHERE product_type LIKE '%SERVERLESS%'
GROUP BY product_type
ORDER BY product_type;
"""

result2 = pd.read_sql_query(query2, conn)
print("📋 All SERVERLESS product types:")
display(result2)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3️⃣ Sample pricing for each SQL product type

# COMMAND ----------

sql_products = result1['product_type'].tolist()

for product in sql_products:
    query = f"""
    SELECT 
        cloud,
        tier,
        product_type,
        price_per_dbu
    FROM lakemeter.sync_pricing_dbu_rates
    WHERE product_type = '{product}'
      AND cloud = 'AWS'
    ORDER BY tier
    LIMIT 5;
    """
    
    sample = pd.read_sql_query(query, conn)
    print(f"\n📊 Sample pricing for: {product}")
    display(sample)

conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📋 Expected Product Types
# MAGIC
# MAGIC Based on Databricks pricing, DBSQL should have:
# MAGIC - `SQL_COMPUTE` or `DBSQL_COMPUTE` - Classic DBSQL
# MAGIC - `SQL_PRO_COMPUTE` or `DBSQL_PRO_COMPUTE` - DBSQL Pro
# MAGIC - `SQL_SERVERLESS_COMPUTE` or `DBSQL_SERVERLESS_COMPUTE` - DBSQL Serverless
# MAGIC
# MAGIC If DBSQL_SERVERLESS doesn't exist, we need to:
# MAGIC 1. Check the pricing sync notebooks
# MAGIC 2. OR update the function to map to whatever serverless product type exists




