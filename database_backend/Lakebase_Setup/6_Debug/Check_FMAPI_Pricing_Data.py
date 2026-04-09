# Databricks notebook source
# MAGIC %md
# MAGIC # 🔍 Check FMAPI Pricing Data
# MAGIC
# MAGIC Simple check to see if sync_product_fmapi_databricks table exists and has data

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import pandas as pd
import psycopg2

print("✅ Config loaded")
print(f"   Host: {LAKEBASE_HOST}")
print(f"   Database: {LAKEBASE_DATABASE}")

# COMMAND ----------

def get_connection():
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DATABASE,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD
    )

def execute_query(query):
    conn = get_connection()
    try:
        df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()

# COMMAND ----------

print("=" * 80)
print("STEP 1: Check if table exists")
print("=" * 80)

query = """
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema = 'lakemeter'
  AND table_name LIKE '%fmapi%'
ORDER BY table_name;
"""

try:
    tables = execute_query(query)
    if len(tables) > 0:
        print(f"\n✅ Found {len(tables)} FMAPI table(s):")
        for _, row in tables.iterrows():
            print(f"   • {row['table_schema']}.{row['table_name']}")
    else:
        print("\n❌ NO FMAPI TABLES FOUND!")
        print("   You need to run the Pricing_Sync notebooks first!")
except Exception as e:
    print(f"\n❌ Error: {e}")

# COMMAND ----------

print("\n" + "=" * 80)
print("STEP 2: Check table row count")
print("=" * 80)

query = """
SELECT COUNT(*) as row_count
FROM lakemeter.sync_product_fmapi_databricks;
"""

try:
    result = execute_query(query)
    row_count = result.iloc[0]['row_count']
    print(f"\n✅ Table has {row_count} rows")
    
    if row_count == 0:
        print("\n❌ TABLE IS EMPTY!")
        print("   You need to run: Pricing_Sync/11_Load_FMAPI_Databricks_Rates")
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("   Table might not exist!")

# COMMAND ----------

print("\n" + "=" * 80)
print("STEP 3: Show sample data (first 20 rows)")
print("=" * 80)

query = """
SELECT *
FROM lakemeter.sync_product_fmapi_databricks
ORDER BY cloud, model, rate_type
LIMIT 20;
"""

try:
    result = execute_query(query)
    if len(result) > 0:
        print(f"\n✅ Retrieved {len(result)} sample rows:")
        display(result)
    else:
        print("\n❌ NO DATA!")
except Exception as e:
    print(f"\n❌ Error: {e}")

# COMMAND ----------

print("\n" + "=" * 80)
print("STEP 4: Check available models")
print("=" * 80)

query = """
SELECT 
    cloud,
    model,
    COUNT(*) as rate_count
FROM lakemeter.sync_product_fmapi_databricks
GROUP BY cloud, model
ORDER BY cloud, model;
"""

try:
    result = execute_query(query)
    if len(result) > 0:
        print(f"\n✅ Found {len(result)} model(s):")
        display(result)
        
        # Check for dbrx-instruct specifically
        dbrx = result[(result['cloud'] == 'AWS') & (result['model'] == 'dbrx-instruct')]
        if len(dbrx) > 0:
            print("\n✅ dbrx-instruct is available for AWS")
        else:
            print("\n⚠️  dbrx-instruct NOT found for AWS")
            print("   Available AWS models:")
            aws_models = result[result['cloud'] == 'AWS']['model'].tolist()
            for model in aws_models:
                print(f"     • {model}")
    else:
        print("\n❌ NO MODELS FOUND!")
except Exception as e:
    print(f"\n❌ Error: {e}")

# COMMAND ----------

print("\n" + "=" * 80)
print("STEP 5: Check dbrx-instruct rates for AWS")
print("=" * 80)

query = """
SELECT 
    cloud,
    model,
    rate_type,
    dbu_rate,
    input_divisor,
    is_hourly
FROM lakemeter.sync_product_fmapi_databricks
WHERE cloud = 'AWS'
  AND model = 'dbrx-instruct'
ORDER BY rate_type;
"""

try:
    result = execute_query(query)
    if len(result) > 0:
        print(f"\n✅ Found {len(result)} rate(s) for dbrx-instruct:")
        display(result)
    else:
        print("\n❌ NO RATES found for dbrx-instruct on AWS")
        print("   Try a different model from Step 4")
except Exception as e:
    print(f"\n❌ Error: {e}")

# COMMAND ----------

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print("\n✅ If you see data above, the pricing table is populated correctly.")
print("✅ If empty, run: Pricing_Sync/11_Load_FMAPI_Databricks_Rates")
print("✅ Then retry Test_Func_12_FMAPI_Databricks")


