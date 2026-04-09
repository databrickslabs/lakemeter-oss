# Databricks notebook source
# MAGIC %md
# MAGIC # 🔍 Debug Why DBU Price is $0 for DBSQL Pro

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2
import pandas as pd

def get_connection():
    """Create and return a PostgreSQL connection"""
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DB,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD
    )

def execute_query(query, params=None, fetch=True):
    """Execute a query and optionally fetch results"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch:
                columns = [desc[0] for desc in cur.description] if cur.description else []
                results = cur.fetchall()
                conn.commit()
                return pd.DataFrame(results, columns=columns) if results else pd.DataFrame()
            else:
                conn.commit()
                return None
    finally:
        conn.close()

# COMMAND ----------

print("=" * 100)
print("STEP 1: What product_type does get_product_type_for_pricing() return for DBSQL Pro?")
print("=" * 100)

test_cases = [
    ("UPPERCASE 'PRO'", "'PRO'"),
    ("LOWERCASE 'pro'", "'pro'"),
    ("Mixed case 'Pro'", "'Pro'"),
]

for label, warehouse_type_value in test_cases:
    print(f"\n🔎 Testing {label}:")
    
    product_type_sql = f"""
    SELECT lakemeter.get_product_type_for_pricing(
        'DBSQL'::VARCHAR,
        FALSE::BOOLEAN,
        FALSE::BOOLEAN,
        NULL::VARCHAR,
        {warehouse_type_value}::VARCHAR,
        NULL::VARCHAR
    ) as product_type;
    """
    
    try:
        result = execute_query(product_type_sql)
        if not result.empty:
            product_type = result.iloc[0]['product_type']
            print(f"   Product type: {product_type}")
        else:
            print("   ❌ No result")
    except Exception as e:
        print(f"   ❌ Error: {e}")

# COMMAND ----------

print("\n" + "=" * 100)
print("STEP 2: What SQL-related product types exist in sync_pricing_dbu_rates?")
print("=" * 100)

check_sql_products = """
SELECT DISTINCT 
    product_type,
    COUNT(*) as price_count
FROM lakemeter.sync_pricing_dbu_rates
WHERE product_type LIKE '%SQL%'
GROUP BY product_type
ORDER BY product_type;
"""

try:
    sql_products = execute_query(check_sql_products)
    print(f"\n✅ Found {len(sql_products)} SQL product types:")
    display(sql_products)
except Exception as e:
    print(f"❌ Error: {e}")

# COMMAND ----------

print("\n" + "=" * 100)
print("STEP 3: Try to get DBU price for SQL_PRO_COMPUTE")
print("=" * 100)

test_clouds = ['AWS', 'AZURE', 'GCP']
test_regions = {
    'AWS': 'us-east-1',
    'AZURE': 'eastus',
    'GCP': 'us-central1'
}
test_tiers = ['STANDARD', 'PREMIUM', 'ENTERPRISE']

for cloud in test_clouds:
    for tier in test_tiers:
        if cloud == 'AZURE' and tier == 'ENTERPRISE':
            continue
            
        region = test_regions[cloud]
        
        get_price_sql = f"""
        SELECT lakemeter.get_dbu_price(
            '{cloud}'::VARCHAR,
            '{region}'::VARCHAR,
            '{tier}'::VARCHAR,
            'SQL_PRO_COMPUTE'::VARCHAR
        ) as dbu_price;
        """
        
        try:
            result = execute_query(get_price_sql)
            if not result.empty:
                price = result.iloc[0]['dbu_price']
                if price == 0:
                    print(f"❌ {cloud} {tier}: $0")
                else:
                    print(f"✅ {cloud} {tier}: ${price}")
        except Exception as e:
            print(f"❌ {cloud} {tier}: Error - {e}")

# COMMAND ----------

print("\n" + "=" * 100)
print("STEP 4: Check pricing table directly for SQL_PRO_COMPUTE")
print("=" * 100)

direct_check = """
SELECT 
    cloud,
    region,
    tier,
    product_type,
    price_per_dbu
FROM lakemeter.sync_pricing_dbu_rates
WHERE product_type = 'SQL_PRO_COMPUTE'
ORDER BY cloud, tier
LIMIT 20;
"""

try:
    direct_result = execute_query(direct_check)
    if direct_result.empty:
        print("❌ NO pricing found for SQL_PRO_COMPUTE!")
        print("\n🔍 Let me check what SQL product types DO exist...")
        
        alt_check = """
        SELECT DISTINCT product_type
        FROM lakemeter.sync_pricing_dbu_rates
        WHERE product_type LIKE '%PRO%' OR product_type LIKE '%SQL%'
        ORDER BY product_type;
        """
        
        alt_result = execute_query(alt_check)
        print("\nSQL/PRO related product types in the table:")
        display(alt_result)
    else:
        print(f"✅ Found {len(direct_result)} pricing records:")
        display(direct_result)
except Exception as e:
    print(f"❌ Error: {e}")

# COMMAND ----------

print("\n" + "=" * 100)
print("🎯 DIAGNOSIS")
print("=" * 100)

print("\nIf SQL_PRO_COMPUTE does NOT exist in pricing table:")
print("  → The pricing sync didn't load DBSQL Pro rates")
print("  → OR the product type name is different")
print("")
print("Check the output above to see:")
print("  1. What product_type the function returns (should be 'SQL_PRO_COMPUTE')")
print("  2. What SQL product types exist in the pricing table")
print("  3. If SQL_PRO_COMPUTE has pricing data")
print("")
print("If product type names don't match, we need to fix the function!")



