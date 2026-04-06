# Databricks notebook source
# MAGIC %md
# MAGIC # VM Cost Calculators
# MAGIC
# MAGIC **Purpose:** Calculate VM infrastructure costs for classic compute workloads
# MAGIC
# MAGIC **Functions Created:**
# MAGIC 1. `calculate_classic_vm_costs()` - Classic compute (JOBS/ALL_PURPOSE/DLT)
# MAGIC 2. `calculate_dbsql_vm_costs()` - DBSQL Classic & Pro
# MAGIC
# MAGIC **Note:** Serverless workloads have NO VM costs (infrastructure managed by Databricks)

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
# MAGIC ## Function 1: calculate_classic_vm_costs()

# COMMAND ----------

print("=" * 100)
print("CREATING FUNCTION: calculate_classic_vm_costs")
print("=" * 100)

# First, let's see what signatures exist
print("\n🔍 Checking existing function signatures...")
check_sql = """
SELECT 
    p.proname as function_name,
    pg_get_function_identity_arguments(p.oid) as arguments
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'lakemeter' 
  AND p.proname = 'calculate_classic_vm_costs';
"""

try:
    results = execute_query(check_sql, fetch=True)
    if results:
        print(f"Found {len(results)} existing signature(s):")
        for row in results:
            print(f"  • {row[0]}({row[1]})")
    else:
        print("  No existing signatures found.")
except Exception as e:
    print(f"  Could not check: {e}")

# Drop ALL possible old signatures (brute force approach)
print("\n🗑️  Dropping all possible old signatures...")

drop_variations = [
    # Original signature with payment_option in middle
    "DROP FUNCTION IF EXISTS lakemeter.calculate_classic_vm_costs(VARCHAR, VARCHAR, VARCHAR, VARCHAR, INT, VARCHAR, VARCHAR, VARCHAR, VARCHAR, DECIMAL);",
    # Without defaults (8 params)
    "DROP FUNCTION IF EXISTS lakemeter.calculate_classic_vm_costs(VARCHAR, VARCHAR, VARCHAR, VARCHAR, INT, VARCHAR, VARCHAR, DECIMAL);",
    # With all 10 params, new order
    "DROP FUNCTION IF EXISTS lakemeter.calculate_classic_vm_costs(VARCHAR, VARCHAR, VARCHAR, VARCHAR, INT, VARCHAR, VARCHAR, DECIMAL, VARCHAR, VARCHAR);",
]

for i, drop_sql in enumerate(drop_variations, 1):
    try:
        execute_query(drop_sql)
        print(f"  ✓ Variant {i} dropped (if existed)")
    except Exception as e:
        print(f"  Note on variant {i}: {e}")

create_function_sql = """
CREATE OR REPLACE FUNCTION lakemeter.calculate_classic_vm_costs(
    p_cloud VARCHAR,
    p_region VARCHAR,
    p_driver_node_type VARCHAR,
    p_worker_node_type VARCHAR,
    p_num_workers INT,
    p_driver_pricing_tier VARCHAR,
    p_worker_pricing_tier VARCHAR,
    p_hours_per_month DECIMAL,
    p_driver_payment_option VARCHAR DEFAULT 'NA',
    p_worker_payment_option VARCHAR DEFAULT 'NA'
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
    v_driver_cost_per_hour DECIMAL(18,4);
    v_worker_cost_per_hour DECIMAL(18,4);
    v_total_cost_per_hour DECIMAL(18,4);
    v_driver_cost_per_month DECIMAL(18,4);
    v_worker_cost_per_month DECIMAL(18,4);
    v_total_cost_per_month DECIMAL(18,4);
BEGIN
    -- Lookup driver VM cost (driver can ONLY be on-demand or reserved, NEVER spot)
    SELECT cost_per_hour INTO v_driver_cost_per_hour
    FROM lakemeter.sync_pricing_vm_costs
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(region) = UPPER(p_region)
      AND UPPER(instance_type) = UPPER(p_driver_node_type)
      AND UPPER(pricing_tier) = UPPER(p_driver_pricing_tier)
      AND UPPER(payment_option) = UPPER(COALESCE(p_driver_payment_option, 'NA'))
      AND UPPER(pricing_tier) != 'SPOT'  -- Enforce: driver cannot be spot
    LIMIT 1;
    
    -- Lookup worker VM cost
    SELECT cost_per_hour INTO v_worker_cost_per_hour
    FROM lakemeter.sync_pricing_vm_costs
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(region) = UPPER(p_region)
      AND UPPER(instance_type) = UPPER(p_worker_node_type)
      AND UPPER(pricing_tier) = UPPER(p_worker_pricing_tier)
      AND UPPER(payment_option) = UPPER(COALESCE(p_worker_payment_option, 'NA'))
    LIMIT 1;
    
    -- Calculate costs
    v_driver_cost_per_hour := COALESCE(v_driver_cost_per_hour, 0);
    v_worker_cost_per_hour := COALESCE(v_worker_cost_per_hour, 0) * COALESCE(p_num_workers, 0);
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

COMMENT ON FUNCTION lakemeter.calculate_classic_vm_costs IS 
'Calculate VM costs for classic compute workloads (JOBS/ALL_PURPOSE/DLT Classic).
Returns detailed breakdown: driver, worker, total (per hour and per month).
Driver constraint: CANNOT be spot (on-demand or reserved only).
Worker: Can be on-demand, spot, or reserved.';
"""

try:
    execute_query(create_function_sql)
    print("\n✅ Function created: calculate_classic_vm_costs")
    print("\n   Parameters:")
    print("   • cloud: VARCHAR - Cloud provider")
    print("   • region: VARCHAR - Cloud region")
    print("   • driver_node_type: VARCHAR - Driver instance type")
    print("   • worker_node_type: VARCHAR - Worker instance type")
    print("   • num_workers: INT - Number of workers")
    print("   • driver_pricing_tier: VARCHAR - Driver pricing tier (on_demand, reserved_1y, reserved_3y)")
    print("   • driver_payment_option: VARCHAR - Driver payment option (all_upfront, no_upfront, partial_upfront, NA)")
    print("   • worker_pricing_tier: VARCHAR - Worker pricing tier (on_demand, spot, reserved_1y, reserved_3y)")
    print("   • worker_payment_option: VARCHAR - Worker payment option (all_upfront, no_upfront, partial_upfront, NA)")
    print("   • hours_per_month: DECIMAL - Usage hours")
    print("\n   Pricing Tiers:")
    print("   • on_demand, spot, reserved_1y, reserved_3y")
    print("\n   Payment Options (AWS only, others use 'NA'):")
    print("   • all_upfront - Pay 100% upfront")
    print("   • partial_upfront - Pay ~50% upfront")
    print("   • no_upfront - Pay monthly")
    print("   • NA - For on_demand, spot, or non-AWS clouds")
    print("\n   Returns: TABLE with 6 columns:")
    print("   • driver_vm_cost_per_hour")
    print("   • worker_vm_cost_per_hour (total for all workers)")
    print("   • total_vm_cost_per_hour")
    print("   • driver_vm_cost_per_month")
    print("   • total_worker_vm_cost_per_month")
    print("   • total_vm_cost_per_month")
    print("\n   Constraint: Driver CANNOT be spot (enforced by query)")
except Exception as e:
    print(f"\n❌ Error creating function: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Function 2: calculate_dbsql_vm_costs()

# COMMAND ----------

print("\n" + "=" * 100)
print("CREATING FUNCTION: calculate_dbsql_vm_costs")
print("=" * 100)

# First, let's see what signatures exist
print("\n🔍 Checking existing function signatures...")
check_sql = """
SELECT 
    p.proname as function_name,
    pg_get_function_identity_arguments(p.oid) as arguments
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'lakemeter' 
  AND p.proname = 'calculate_dbsql_vm_costs';
"""

try:
    results = execute_query(check_sql, fetch=True)
    if results:
        print(f"Found {len(results)} existing signature(s):")
        for row in results:
            print(f"  • {row[0]}({row[1]})")
    else:
        print("  No existing signatures found.")
except Exception as e:
    print(f"  Could not check: {e}")

# Drop ALL possible old signatures (brute force approach)
print("\n🗑️  Dropping all possible old signatures...")

drop_variations = [
    # Original signature with payment_option in middle
    "DROP FUNCTION IF EXISTS lakemeter.calculate_dbsql_vm_costs(VARCHAR, VARCHAR, VARCHAR, VARCHAR, INT, VARCHAR, VARCHAR, DECIMAL);",
    # Without payment option (7 params)
    "DROP FUNCTION IF EXISTS lakemeter.calculate_dbsql_vm_costs(VARCHAR, VARCHAR, VARCHAR, VARCHAR, INT, VARCHAR, DECIMAL);",
    # With payment option at end (8 params)
    "DROP FUNCTION IF EXISTS lakemeter.calculate_dbsql_vm_costs(VARCHAR, VARCHAR, VARCHAR, VARCHAR, INT, VARCHAR, DECIMAL, VARCHAR);",
]

for i, drop_sql in enumerate(drop_variations, 1):
    try:
        execute_query(drop_sql)
        print(f"  ✓ Variant {i} dropped (if existed)")
    except Exception as e:
        print(f"  Note on variant {i}: {e}")

create_function_sql = """
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
    -- Normalize string inputs to LOWERCASE for case-insensitive matching
    -- Note: sync_ref_dbsql_warehouse_config uses lowercase values (classic, pro, serverless)
    v_warehouse_type := LOWER(p_dbsql_warehouse_type);
    
    -- Lookup warehouse configuration (instance types and counts)
    SELECT driver_instance_type, worker_instance_type, worker_count
    INTO v_driver_instance, v_worker_instance, v_num_workers
    FROM lakemeter.sync_ref_dbsql_warehouse_config
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND LOWER(warehouse_type) = LOWER(v_warehouse_type)
      AND UPPER(warehouse_size) = UPPER(p_dbsql_warehouse_size)
    LIMIT 1;
    
    -- Lookup driver VM cost
    SELECT cost_per_hour INTO v_driver_cost_per_hour
    FROM lakemeter.sync_pricing_vm_costs
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(region) = UPPER(p_region)
      AND UPPER(instance_type) = UPPER(v_driver_instance)
      AND UPPER(pricing_tier) = UPPER(p_vm_pricing_tier)
      AND UPPER(payment_option) = UPPER(COALESCE(p_vm_payment_option, 'NA'))
      AND UPPER(pricing_tier) != 'SPOT'  -- Driver cannot be spot
    LIMIT 1;
    
    -- Lookup worker VM cost
    SELECT cost_per_hour INTO v_worker_cost_per_hour
    FROM lakemeter.sync_pricing_vm_costs
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(region) = UPPER(p_region)
      AND UPPER(instance_type) = UPPER(v_worker_instance)
      AND UPPER(pricing_tier) = UPPER(p_vm_pricing_tier)
      AND UPPER(payment_option) = UPPER(COALESCE(p_vm_payment_option, 'NA'))
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

COMMENT ON FUNCTION lakemeter.calculate_dbsql_vm_costs IS 
'Calculate VM costs for DBSQL Classic and Pro workloads.
Maps warehouse_type + size → instance types → VM costs.
Multiplies by num_clusters.
Returns detailed breakdown: driver, worker, total (per hour and per month).';
"""

try:
    execute_query(create_function_sql)
    print("\n✅ Function created: calculate_dbsql_vm_costs")
    print("\n   Parameters:")
    print("   • cloud: VARCHAR - Cloud provider")
    print("   • region: VARCHAR - Cloud region")
    print("   • dbsql_warehouse_type: VARCHAR - 'classic' or 'pro'")
    print("   • dbsql_warehouse_size: VARCHAR - 'X-Small', 'Small', etc.")
    print("   • dbsql_num_clusters: INT - Number of clusters")
    print("   • vm_pricing_tier: VARCHAR - Pricing tier (on_demand, spot, reserved_1y, reserved_3y)")
    print("   • vm_payment_option: VARCHAR - Payment option (all_upfront, no_upfront, partial_upfront, NA)")
    print("   • hours_per_month: DECIMAL - Usage hours")
    print("\n   Pricing Tiers & Payment Options: (same as classic VM costs)")
    print("   • Pricing tier: on_demand, spot, reserved_1y, reserved_3y")
    print("   • Payment option (AWS only): all_upfront, no_upfront, partial_upfront")
    print("   • AZURE/GCP: Use 'NA' for payment_option")
    print("\n   Returns: TABLE with 6 columns:")
    print("   • driver_vm_cost_per_hour")
    print("   • worker_vm_cost_per_hour")
    print("   • total_vm_cost_per_hour")
    print("   • driver_vm_cost_per_month")
    print("   • total_worker_vm_cost_per_month")
    print("   • total_vm_cost_per_month")
    print("\n   Logic:")
    print("   1. Lookup instance types from sync_ref_dbsql_warehouse_config")
    print("   2. Lookup VM costs from sync_pricing_vm_costs")
    print("   3. Multiply by num_clusters")
except Exception as e:
    print(f"\n❌ Error creating function: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Functions

# COMMAND ----------

print("\n" + "=" * 100)
print("TESTING: VM Cost Calculators")
print("=" * 100)

test_query = """
SELECT 'Classic VM Test' as test_case, * 
FROM lakemeter.calculate_classic_vm_costs(
    'AWS', 'us-east-1', 'm5.xlarge', 'm5.xlarge', 10, 
    'on_demand', 'spot', 240
)
UNION ALL
SELECT 'DBSQL VM Test', * 
FROM lakemeter.calculate_dbsql_vm_costs(
    'AWS', 'us-east-1', 'classic', 'Small', 2, 'on_demand', 240
);
"""

try:
    results = execute_query(test_query, fetch=True)
    print("\n✅ Test results:")
    for row in results:
        print(f"\n   {row[0]}:")
        print(f"      Driver $/hr: {row[1]}")
        print(f"      Worker $/hr: {row[2]}")
        print(f"      Total $/hr: {row[3]}")
        print(f"      Driver $/mo: {row[4]}")
        print(f"      Worker $/mo: {row[5]}")
        print(f"      Total $/mo: {row[6]}")
except Exception as e:
    print(f"\n⚠️  Test skipped (requires pricing data): {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n" + "=" * 100)
print("✅ VM COST CALCULATORS CREATED")
print("=" * 100)

print("\n📋 Functions created:")
print("   ✅ calculate_classic_vm_costs")
print("   ✅ calculate_dbsql_vm_costs")

print("\n🎯 VM Cost Calculators:")
print("   • TWO separate parameters for filtering:")
print("     1. pricing_tier: on_demand, spot, reserved_1y, reserved_3y")
print("     2. payment_option: all_upfront, partial_upfront, no_upfront, NA")
print("   • AWS has payment_option for reserved instances")
print("   • AZURE/GCP: Always use 'NA' for payment_option")
print("   • Driver + worker can have different tiers/options")
print("   • Driver CANNOT use 'spot' pricing_tier")

print("\n🎯 DBSQL VM Costs:")
print("   • Warehouse size → instance type mapping")
print("   • Multiplied by num_clusters")
print("   • Same detailed breakdown")

print("\n⚠️  Serverless Workloads:")
print("   • NO VM costs (infrastructure managed by Databricks)")
print("   • These functions return 0 for serverless")

print("\n📝 Next step: Run 09_Main_Orchestrator.py")
print("=" * 100)