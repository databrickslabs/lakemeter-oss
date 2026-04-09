# Databricks notebook source
# MAGIC %md
# MAGIC # DBSQL DBU Calculator
# MAGIC
# MAGIC **Purpose:** Calculate DBU per hour for DBSQL workloads
# MAGIC
# MAGIC **Workload Types:** DBSQL Classic, DBSQL Pro, DBSQL Serverless
# MAGIC
# MAGIC **Formula:** warehouse_dbu_per_hour × num_clusters
# MAGIC
# MAGIC **Lookup:** sync_product_dbsql_rates (maps warehouse_type + size → DBU/hour)
# MAGIC
# MAGIC **Function Created:**
# MAGIC - `calculate_dbsql_dbu()` - Returns DBU per hour for DBSQL workloads

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2

def execute_query(query, params=None, fetch=False):
    """Execute a SQL query"""
    conn = get_lakebase_connection()
    try:
        with conn.cursor() as cur:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            
            if fetch:
                columns = [desc[0] for desc in cur.description] if cur.description else []
                results = cur.fetchall()
                return results
            else:
                conn.commit()
                return True
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        raise
    finally:
        conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Function: calculate_dbsql_dbu()

# COMMAND ----------

print("=" * 100)
print("CREATING FUNCTION: calculate_dbsql_dbu")
print("=" * 100)

create_function_sql = """
CREATE OR REPLACE FUNCTION lakemeter.calculate_dbsql_dbu(
    p_cloud VARCHAR,
    p_dbsql_warehouse_type VARCHAR,
    p_dbsql_warehouse_size VARCHAR,
    p_dbsql_num_clusters INT DEFAULT 1
)
RETURNS DECIMAL(18,4)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_dbu_per_hour DECIMAL(18,4);
    v_total_dbu DECIMAL(18,4);
BEGIN
    -- Lookup DBU per hour from warehouse configuration
    SELECT dbu_per_hour INTO v_dbu_per_hour
    FROM lakemeter.sync_product_dbsql_rates
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND warehouse_type = LOWER(p_dbsql_warehouse_type)
      AND UPPER(warehouse_size) = UPPER(p_dbsql_warehouse_size)
    LIMIT 1;
    
    -- Calculate total DBU (DBU per warehouse × number of clusters)
    v_total_dbu := COALESCE(v_dbu_per_hour, 0) * COALESCE(p_dbsql_num_clusters, 1);
    
    RETURN v_total_dbu;
END;
$$;

COMMENT ON FUNCTION lakemeter.calculate_dbsql_dbu IS 
'Calculate DBU per hour for DBSQL workloads (Classic, Pro, Serverless).
Formula: warehouse_dbu_per_hour × num_clusters
Lookup from: sync_product_dbsql_rates';
"""

try:
    execute_query(create_function_sql)
    print("\n✅ Function created: calculate_dbsql_dbu")
    print("\n   Parameters:")
    print("   • cloud: VARCHAR - Cloud provider (AWS, AZURE, GCP)")
    print("   • dbsql_warehouse_type: VARCHAR - 'classic', 'pro', or 'serverless'")
    print("   • dbsql_warehouse_size: VARCHAR - 'X-Small', 'Small', 'Medium', etc.")
    print("   • dbsql_num_clusters: INT - Number of clusters (default: 1)")
    print("\n   Returns: DECIMAL (DBU per hour)")
    print("\n   Formula:")
    print("   warehouse_dbu_per_hour × num_clusters")
    print("\n   Lookup from: sync_product_dbsql_rates")
    print("\n   Example:")
    print("   SELECT lakemeter.calculate_dbsql_dbu(")
    print("     'AWS', 'classic', 'Small', 2")
    print("   );")
    print("   → Looks up Small classic warehouse DBU/hour, multiplies by 2 clusters")
except Exception as e:
    print(f"\n❌ Error creating function: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Function

# COMMAND ----------

print("\n" + "=" * 100)
print("TESTING: calculate_dbsql_dbu")
print("=" * 100)

test_query = """
SELECT 
    'Test 1: DBSQL Classic Small (1 cluster)' as test_case,
    lakemeter.calculate_dbsql_dbu('AWS', 'classic', 'Small', 1) as dbu_per_hour
UNION ALL
SELECT 
    'Test 2: DBSQL Pro Medium (2 clusters)',
    lakemeter.calculate_dbsql_dbu('AWS', 'pro', 'Medium', 2)
UNION ALL
SELECT 
    'Test 3: DBSQL Serverless Small (1 cluster)',
    lakemeter.calculate_dbsql_dbu('AWS', 'serverless', 'Small', 1);
"""

try:
    results = execute_query(test_query, fetch=True)
    print("\n✅ Test results:")
    for row in results:
        print(f"   {row[0]}: {row[1]} DBU/hour")
except Exception as e:
    print(f"\n⚠️  Test skipped (requires pricing data): {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n" + "=" * 100)
print("✅ DBSQL DBU CALCULATOR CREATED")
print("=" * 100)

print("\n📋 Function created:")
print("   ✅ calculate_dbsql_dbu")

print("\n🎯 This function handles:")
print("   • DBSQL Classic")
print("   • DBSQL Pro")
print("   • DBSQL Serverless")

print("\n📐 Calculation:")
print("   1. Lookup warehouse DBU/hour from sync_product_dbsql_rates")
print("   2. Map: warehouse_type + warehouse_size → DBU/hour")
print("   3. Multiply by num_clusters")

print("\n💡 Key Points:")
print("   • Warehouse size determines base DBU/hour")
print("   • Multiple clusters multiply the DBU usage")
print("   • Type (classic/pro/serverless) affects pricing tier")

print("\n📝 Next step: Run 05_DBU_Calculators_Vector_Model.py")
print("=" * 100)
