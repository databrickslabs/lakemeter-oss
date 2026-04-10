# MAGIC %md
# MAGIC # Serverless Compute DBU Calculator
# MAGIC
# MAGIC **Purpose:** Calculate DBU per hour for Serverless compute workloads
# MAGIC
# MAGIC **Workload Types:** JOBS Serverless, ALL_PURPOSE Serverless, DLT Serverless
# MAGIC
# MAGIC **Formula:** (driver_dbu + worker_dbu × num_workers) × photon_multiplier × serverless_mode_multiplier
# MAGIC
# MAGIC **Serverless Modes:**
# MAGIC - `standard`: 1x multiplier
# MAGIC - `performance`: 2x multiplier
# MAGIC
# MAGIC **Function Created:**
# MAGIC - `calculate_serverless_compute_dbu()` - Returns DBU per hour for serverless workloads

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
# MAGIC ## Function: calculate_serverless_compute_dbu()

# COMMAND ----------

print("=" * 100)
print("CREATING FUNCTION: calculate_serverless_compute_dbu")
print("=" * 100)

# Drop old function signature first (if exists)
drop_old_function_sql = """
DROP FUNCTION IF EXISTS lakemeter.calculate_serverless_compute_dbu(
    VARCHAR, VARCHAR, VARCHAR, INT, VARCHAR
);
"""

try:
    execute_query(drop_old_function_sql, fetch=False)
    print("\n✅ Dropped old function signature (5 parameters)")
except Exception as e:
    print(f"\n⚠️  Note: {e}")

create_function_sql = """
CREATE OR REPLACE FUNCTION lakemeter.calculate_serverless_compute_dbu(
    p_cloud VARCHAR,
    p_driver_node_type VARCHAR,
    p_worker_node_type VARCHAR,
    p_num_workers INT,
    p_workload_type VARCHAR DEFAULT 'JOBS',
    p_serverless_mode VARCHAR DEFAULT 'standard'
)
RETURNS DECIMAL(18,4)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_driver_dbu DECIMAL(18,4);
    v_worker_dbu DECIMAL(18,4);
    v_photon_multiplier DECIMAL(10,4);
    v_mode_multiplier DECIMAL(10,4);
    v_total_dbu DECIMAL(18,4);
BEGIN
    -- Get driver DBU rate (used for sizing estimation)
    SELECT dbu_rate INTO v_driver_dbu
    FROM lakemeter.sync_ref_instance_dbu_rates
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(instance_type) = UPPER(p_driver_node_type)
    LIMIT 1;
    
    -- Get worker DBU rate (used for sizing estimation)
    SELECT dbu_rate INTO v_worker_dbu
    FROM lakemeter.sync_ref_instance_dbu_rates
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(instance_type) = UPPER(p_worker_node_type)
    LIMIT 1;
    
    -- Get Photon multiplier (Photon is MANDATORY for serverless, but multiplier still applies)
    v_photon_multiplier := lakemeter.get_photon_multiplier(
        p_cloud,
        p_workload_type,
        NULL,  -- dlt_edition not needed for serverless
        TRUE,  -- photon_enabled = TRUE (always for serverless)
        TRUE   -- serverless_enabled = TRUE
    );
    
    -- Serverless mode multiplier (standard vs performance)
    v_mode_multiplier := CASE 
        WHEN LOWER(COALESCE(p_serverless_mode, 'standard')) = 'performance' THEN 2.0
        ELSE 1.0
    END;
    
    -- Calculate total DBU
    -- Formula: (base DBU) × photon_multiplier × mode_multiplier
    v_total_dbu := (
        COALESCE(v_driver_dbu, 0) + 
        (COALESCE(v_worker_dbu, 0) * COALESCE(p_num_workers, 0))
    ) * v_photon_multiplier * v_mode_multiplier;
    
    RETURN v_total_dbu;
END;
$$;

COMMENT ON FUNCTION lakemeter.calculate_serverless_compute_dbu IS 
'Calculate DBU per hour for serverless compute workloads (JOBS/ALL_PURPOSE/DLT Serverless).
Formula: (driver_dbu + worker_dbu × num_workers) × photon_multiplier × serverless_mode_multiplier
Photon is MANDATORY for serverless, and the multiplier still applies.
Serverless mode: standard (1x) or performance (2x)';
"""

try:
    execute_query(create_function_sql)
    print("\n✅ Function created: calculate_serverless_compute_dbu")
    print("\n   Parameters:")
    print("   • cloud: VARCHAR - Cloud provider (AWS, AZURE, GCP)")
    print("   • driver_node_type: VARCHAR - Driver instance type (for sizing)")
    print("   • worker_node_type: VARCHAR - Worker instance type (for sizing)")
    print("   • num_workers: INT - Number of worker nodes")
    print("   • workload_type: VARCHAR - 'JOBS', 'ALL_PURPOSE', or 'DLT' (default: 'JOBS')")
    print("   • serverless_mode: VARCHAR - 'standard' or 'performance' (default: 'standard')")
    print("\n   Returns: DECIMAL (DBU per hour)")
    print("\n   Formula:")
    print("   (driver_dbu + worker_dbu × num_workers) × photon_multiplier × serverless_mode_multiplier")
    print("   • Photon multiplier: Cloud-specific (e.g., 2.0 for AWS)")
    print("   • Standard mode: 1x multiplier")
    print("   • Performance mode: 2x multiplier")
    print("\n   Note: Photon is MANDATORY for serverless, multiplier STILL APPLIES")
    print("\n   Example:")
    print("   SELECT lakemeter.calculate_serverless_compute_dbu(")
    print("     'AWS', 'm5.xlarge', 'm5.xlarge', 10, 'JOBS', 'standard'")
    print("   );")
    print("   → Returns: 22.0000 (11 base DBU × 2.0 photon × 1 standard)")
    print("\n   SELECT lakemeter.calculate_serverless_compute_dbu(")
    print("     'AWS', 'm5.xlarge', 'm5.xlarge', 10, 'JOBS', 'performance'")
    print("   );")
    print("   → Returns: 44.0000 (11 base DBU × 2.0 photon × 2 performance)")
except Exception as e:
    print(f"\n❌ Error creating function: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Function

# COMMAND ----------

print("\n" + "=" * 100)
print("TESTING: calculate_serverless_compute_dbu")
print("=" * 100)

test_query = """
SELECT 
    'Test 1: JOBS Serverless (standard mode)' as test_case,
    lakemeter.calculate_serverless_compute_dbu(
        'AWS', 'm5.xlarge', 'm5.xlarge', 10, 'JOBS', 'standard'
    ) as dbu_per_hour
UNION ALL
SELECT 
    'Test 2: JOBS Serverless (performance mode)',
    lakemeter.calculate_serverless_compute_dbu(
        'AWS', 'm5.xlarge', 'm5.xlarge', 10, 'JOBS', 'performance'
    )
UNION ALL
SELECT 
    'Test 3: DLT Serverless (standard)',
    lakemeter.calculate_serverless_compute_dbu(
        'AWS', 'm5.xlarge', 'm5.xlarge', 5, 'DLT', 'standard'
    )
UNION ALL
SELECT 
    'Test 4: ALL_PURPOSE Serverless (performance)',
    lakemeter.calculate_serverless_compute_dbu(
        'AWS', 'm5.2xlarge', 'm5.xlarge', 8, 'ALL_PURPOSE', 'performance'
    );
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
print("✅ SERVERLESS COMPUTE DBU CALCULATOR CREATED")
print("=" * 100)

print("\n📋 Function created:")
print("   ✅ calculate_serverless_compute_dbu")

print("\n🎯 This function handles:")
print("   • JOBS Serverless")
print("   • ALL_PURPOSE Serverless")
print("   • DLT Serverless")

print("\n📐 Calculation:")
print("   1. Lookup driver/worker DBU rates (for sizing estimation)")
print("   2. Get Photon multiplier (cloud-specific)")
print("   3. Determine serverless mode multiplier:")
print("      • standard: 1x")
print("      • performance: 2x")
print("   4. Calculate: (driver + worker × num_workers) × photon_multiplier × mode_multiplier")
print("   5. Note: Photon is MANDATORY for serverless, multiplier STILL APPLIES")

print("\n💡 Key Difference vs Classic:")
print("   • Photon is MANDATORY (not optional)")
print("   • Photon multiplier STILL APPLIES")
print("   • Has ADDITIONAL serverless mode multiplier")

print("\n📝 Next step: Run 04_DBU_Calculators_DBSQL.py")
print("=" * 100)
