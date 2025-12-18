# Databricks notebook source
# MAGIC %md
# MAGIC # 🔍 Debug Why DBSQL Serverless DBU is 0

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

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
        with conn.cursor() as cur:
            cur.execute(query)
            columns = [desc[0] for desc in cur.description] if cur.description else []
            results = cur.fetchall()
            conn.commit()
            return pd.DataFrame(results, columns=columns) if results else pd.DataFrame()
    finally:
        conn.close()

# COMMAND ----------

print("=" * 100)
print("STEP 1: What warehouse types exist in sync_product_dbsql_rates?")
print("=" * 100)

check_types = """
SELECT DISTINCT 
    cloud,
    warehouse_type,
    COUNT(*) as size_count
FROM lakemeter.sync_product_dbsql_rates
GROUP BY cloud, warehouse_type
ORDER BY cloud, warehouse_type;
"""

types_result = execute_query(check_types)
print("\n✅ Warehouse types in the table:")
display(types_result)

# COMMAND ----------

print("\n" + "=" * 100)
print("STEP 2: What warehouse sizes exist for SERVERLESS?")
print("=" * 100)

check_serverless_sizes = """
SELECT 
    cloud,
    warehouse_type,
    warehouse_size,
    dbu_per_hour
FROM lakemeter.sync_product_dbsql_rates
WHERE warehouse_type = 'serverless'
ORDER BY cloud, warehouse_size
LIMIT 50;
"""

serverless_result = execute_query(check_serverless_sizes)
if serverless_result.empty:
    print("❌ NO serverless data found!")
    print("\n🔍 Checking with different case...")
    
    alt_check = """
    SELECT 
        cloud,
        warehouse_type,
        warehouse_size,
        dbu_per_hour
    FROM lakemeter.sync_product_dbsql_rates
    WHERE LOWER(warehouse_type) LIKE '%server%'
    ORDER BY cloud, warehouse_size
    LIMIT 50;
    """
    alt_result = execute_query(alt_check)
    if alt_result.empty:
        print("❌ Still no serverless data!")
    else:
        print("✅ Found with different case:")
        display(alt_result)
else:
    print("✅ Serverless data found:")
    display(serverless_result)

# COMMAND ----------

print("\n" + "=" * 100)
print("STEP 3: Test calculate_dbsql_dbu() for SERVERLESS")
print("=" * 100)

test_cases = [
    ("UPPERCASE SERVERLESS, X-SMALL", "'SERVERLESS'", "'X-SMALL'"),
    ("lowercase serverless, X-SMALL", "'serverless'", "'X-SMALL'"),
    ("UPPERCASE SERVERLESS, X-Small", "'SERVERLESS'", "'X-Small'"),
    ("lowercase serverless, x-small", "'serverless'", "'x-small'"),
]

for label, wh_type, wh_size in test_cases:
    print(f"\n🔎 Testing {label}:")
    
    test_sql = f"""
    SELECT lakemeter.calculate_dbsql_dbu(
        'AWS'::VARCHAR,
        {wh_type}::VARCHAR,
        {wh_size}::VARCHAR,
        1::INT
    ) as dbu_per_hour;
    """
    
    try:
        result = execute_query(test_sql)
        if not result.empty:
            dbu = result.iloc[0]['dbu_per_hour']
            if dbu == 0:
                print(f"   ❌ DBU: 0")
            else:
                print(f"   ✅ DBU: {dbu}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

# COMMAND ----------

print("\n" + "=" * 100)
print("STEP 4: Check actual data with exact match")
print("=" * 100)

exact_check = """
SELECT 
    cloud,
    warehouse_type,
    warehouse_size,
    dbu_per_hour
FROM lakemeter.sync_product_dbsql_rates
WHERE cloud = 'AWS'
  AND warehouse_type = 'serverless'
  AND warehouse_size IN ('X-SMALL', 'X-Small', 'x-small', 'SMALL', 'MEDIUM')
ORDER BY warehouse_size;
"""

exact_result = execute_query(exact_check)
if exact_result.empty:
    print("❌ NO match for these sizes!")
    print("\n🔍 Let me show ALL warehouse_size values for serverless:")
    
    all_sizes = """
    SELECT DISTINCT warehouse_size
    FROM lakemeter.sync_product_dbsql_rates
    WHERE cloud = 'AWS' AND LOWER(warehouse_type) = 'serverless'
    ORDER BY warehouse_size;
    """
    
    sizes_result = execute_query(all_sizes)
    print("\nAvailable warehouse_size values:")
    display(sizes_result)
else:
    print("✅ Found matching records:")
    display(exact_result)

# COMMAND ----------

print("\n" + "=" * 100)
print("🎯 DIAGNOSIS")
print("=" * 100)

print("\nIf NO serverless data:")
print("  → sync_product_dbsql_rates table is missing serverless rates")
print("  → Need to run pricing sync notebooks")
print("")
print("If serverless data exists but sizes don't match:")
print("  → Table has: 'X-Small' but test uses 'X-SMALL'")
print("  → Need to make warehouse_size lookup case-insensitive")
print("  → OR need to match exact case in test")



