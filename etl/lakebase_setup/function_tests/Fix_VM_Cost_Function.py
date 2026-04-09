# Databricks notebook source
# MAGIC %md
# MAGIC # 🔧 DIRECT FIX: Force Update calculate_dbsql_vm_costs()
# MAGIC
# MAGIC This will DROP and RECREATE the function with case-insensitive logic.

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
print("STEP 1: DROP OLD FUNCTION")
print("=" * 100)

drop_sql = """
DROP FUNCTION IF EXISTS lakemeter.calculate_dbsql_vm_costs(VARCHAR, VARCHAR, VARCHAR, VARCHAR, INT, VARCHAR, DECIMAL, VARCHAR);
DROP FUNCTION IF EXISTS lakemeter.calculate_dbsql_vm_costs(VARCHAR, VARCHAR, VARCHAR, VARCHAR, INT, VARCHAR, DECIMAL);
"""

try:
    execute_query(drop_sql, fetch=False)
    print("✅ Old function(s) dropped")
except Exception as e:
    print(f"⚠️  Drop warning: {e}")

# COMMAND ----------

print("\n" + "=" * 100)
print("STEP 2: CREATE NEW FUNCTION WITH CASE-INSENSITIVE LOGIC")
print("=" * 100)

create_sql = """
CREATE OR REPLACE FUNCTION lakemeter.calculate_dbsql_vm_costs(
    p_cloud VARCHAR,
    p_region VARCHAR,
    p_dbsql_warehouse_type VARCHAR,
    p_dbsql_warehouse_size VARCHAR,
    p_dbsql_num_clusters INT,
    p_vm_pricing_tier VARCHAR,
    p_hours_per_month DECIMAL,
    p_vm_payment_option VARCHAR DEFAULT 'NA'
)
RETURNS TABLE(
    driver_vm_cost_per_hour DECIMAL(18,4),
    worker_vm_cost_per_hour DECIMAL(18,4),
    total_vm_cost_per_hour DECIMAL(18,4),
    driver_vm_cost_per_month DECIMAL(18,4),
    total_worker_vm_cost_per_month DECIMAL(18,4),
    total_vm_cost_per_month DECIMAL(18,4)
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_warehouse_type VARCHAR;
    v_driver_instance VARCHAR;
    v_worker_instance VARCHAR;
    v_num_workers INT;
    v_driver_cost_per_hour DECIMAL(18,4);
    v_worker_cost_per_hour DECIMAL(18,4);
    v_total_cost_per_hour DECIMAL(18,4);
    v_driver_cost_per_month DECIMAL(18,4);
    v_worker_cost_per_month DECIMAL(18,4);
    v_total_cost_per_month DECIMAL(18,4);
BEGIN
    -- ✅ CASE-INSENSITIVE: Convert to LOWERCASE for matching
    v_warehouse_type := LOWER(p_dbsql_warehouse_type);
    
    -- Lookup warehouse configuration (instance types and counts)
    SELECT driver_instance_type, worker_instance_type, worker_count
    INTO v_driver_instance, v_worker_instance, v_num_workers
    FROM lakemeter.sync_ref_dbsql_warehouse_config
    WHERE cloud = p_cloud
      AND warehouse_type = v_warehouse_type
      AND warehouse_size = p_dbsql_warehouse_size
    LIMIT 1;
    
    -- Lookup driver VM cost
    SELECT cost_per_hour INTO v_driver_cost_per_hour
    FROM lakemeter.sync_pricing_vm_costs
    WHERE cloud = p_cloud
      AND region = p_region
      AND instance_type = v_driver_instance
      AND pricing_tier = p_vm_pricing_tier
      AND payment_option = COALESCE(p_vm_payment_option, 'NA')
      AND pricing_tier != 'spot'
    LIMIT 1;
    
    -- Lookup worker VM cost
    SELECT cost_per_hour INTO v_worker_cost_per_hour
    FROM lakemeter.sync_pricing_vm_costs
    WHERE cloud = p_cloud
      AND region = p_region
      AND instance_type = v_worker_instance
      AND pricing_tier = p_vm_pricing_tier
      AND payment_option = COALESCE(p_vm_payment_option, 'NA')
    LIMIT 1;
    
    -- Calculate costs
    v_driver_cost_per_hour := COALESCE(v_driver_cost_per_hour, 0) * COALESCE(p_dbsql_num_clusters, 1);
    v_worker_cost_per_hour := COALESCE(v_worker_cost_per_hour, 0) * COALESCE(v_num_workers, 0) * COALESCE(p_dbsql_num_clusters, 1);
    v_total_cost_per_hour := v_driver_cost_per_hour + v_worker_cost_per_hour;
    
    v_driver_cost_per_month := v_driver_cost_per_hour * COALESCE(p_hours_per_month, 0);
    v_worker_cost_per_month := v_worker_cost_per_hour * COALESCE(p_hours_per_month, 0);
    v_total_cost_per_month := v_total_cost_per_hour * COALESCE(p_hours_per_month, 0);
    
    -- Return as table
    RETURN QUERY SELECT 
        v_driver_cost_per_hour,
        v_worker_cost_per_hour,
        v_total_cost_per_hour,
        v_driver_cost_per_month,
        v_worker_cost_per_month,
        v_total_cost_per_month;
END;
$$;
"""

try:
    execute_query(create_sql, fetch=False)
    print("✅ Function created: calculate_dbsql_vm_costs")
    print("   WITH case-insensitive logic: v_warehouse_type := LOWER(p_dbsql_warehouse_type)")
except Exception as e:
    print(f"❌ Error creating function: {e}")
    raise

# COMMAND ----------

print("\n" + "=" * 100)
print("STEP 3: TEST THE FUNCTION")
print("=" * 100)

test_cases = [
    ("UPPERCASE 'PRO'", "'PRO'"),
    ("LOWERCASE 'pro'", "'pro'"),
    ("Mixed case 'Pro'", "'Pro'"),
]

for label, warehouse_type_value in test_cases:
    print(f"\n🔎 Testing with {label}:")
    print("─" * 100)
    
    test_sql = f"""
    SELECT * FROM lakemeter.calculate_dbsql_vm_costs(
        'AWS'::VARCHAR,
        'us-east-1'::VARCHAR,
        {warehouse_type_value}::VARCHAR,
        '2X-Large'::VARCHAR,
        1::INT,
        'on_demand'::VARCHAR,
        240.0::DECIMAL,
        'NA'::VARCHAR
    );
    """
    
    try:
        result = execute_query(test_sql)
        if result.empty:
            print("   ❌ Function returned NO rows")
        else:
            vm_cost = result.iloc[0]['total_vm_cost_per_month']
            if vm_cost == 0:
                print(f"   ❌ VM cost is $0")
            else:
                print(f"   ✅ VM cost: ${vm_cost:,.2f}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

# COMMAND ----------

print("\n" + "=" * 100)
print("🎯 SUMMARY")
print("=" * 100)

print("\nThe function has been forcefully updated with case-insensitive logic!")
print("")
print("✅ All three test cases (PRO, pro, Pro) should show the same VM cost")
print("")
print("🚀 NEXT STEP:")
print("   Run Test_Func_08_DBSQL_Pro again (with 'Clear state and outputs')")
print("   VM costs should now appear!")
print("=" * 100)




