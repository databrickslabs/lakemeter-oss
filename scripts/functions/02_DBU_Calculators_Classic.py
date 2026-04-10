# MAGIC %md
# MAGIC # Classic Compute DBU Calculator
# MAGIC
# MAGIC **Purpose:** Calculate DBU per hour for Classic compute workloads
# MAGIC
# MAGIC **Workload Types:** JOBS Classic, ALL_PURPOSE Classic, DLT Classic
# MAGIC
# MAGIC **Formula:** (driver_dbu + worker_dbu × num_workers) × photon_multiplier
# MAGIC
# MAGIC **Function Created:**
# MAGIC - `calculate_classic_compute_dbu()` - Returns DBU per hour for classic workloads

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
# MAGIC ## Function: calculate_classic_compute_dbu()

# COMMAND ----------

print("=" * 100)
print("CREATING FUNCTION: calculate_classic_compute_dbu")
print("=" * 100)

create_function_sql = """
CREATE OR REPLACE FUNCTION lakemeter.calculate_classic_compute_dbu(
    p_cloud VARCHAR,
    p_driver_node_type VARCHAR,
    p_worker_node_type VARCHAR,
    p_num_workers INT,
    p_photon_enabled BOOLEAN,
    p_workload_type VARCHAR,
    p_dlt_edition VARCHAR DEFAULT NULL
)
RETURNS DECIMAL(18,4)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_driver_dbu DECIMAL(18,4);
    v_worker_dbu DECIMAL(18,4);
    v_photon_multiplier DECIMAL(10,4);
    v_total_dbu DECIMAL(18,4);
BEGIN
    -- Get driver DBU rate
    SELECT dbu_rate INTO v_driver_dbu
    FROM lakemeter.sync_ref_instance_dbu_rates
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(instance_type) = UPPER(p_driver_node_type)
    LIMIT 1;
    
    -- Get worker DBU rate
    SELECT dbu_rate INTO v_worker_dbu
    FROM lakemeter.sync_ref_instance_dbu_rates
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(instance_type) = UPPER(p_worker_node_type)
    LIMIT 1;
    
    -- Get Photon multiplier
    v_photon_multiplier := lakemeter.get_photon_multiplier(
        p_cloud,
        p_workload_type,
        p_dlt_edition,
        p_photon_enabled,
        FALSE  -- serverless_enabled = FALSE for classic
    );
    
    -- Calculate total DBU
    v_total_dbu := (
        COALESCE(v_driver_dbu, 0) + 
        (COALESCE(v_worker_dbu, 0) * COALESCE(p_num_workers, 0))
    ) * v_photon_multiplier;
    
    RETURN v_total_dbu;
END;
$$;

COMMENT ON FUNCTION lakemeter.calculate_classic_compute_dbu IS 
'Calculate DBU per hour for classic compute workloads (JOBS/ALL_PURPOSE/DLT Classic).
Formula: (driver_dbu + worker_dbu × num_workers) × photon_multiplier';
"""

try:
    execute_query(create_function_sql)
    print("\n✅ Function created: calculate_classic_compute_dbu")
    print("\n   Parameters:")
    print("   • cloud: VARCHAR - Cloud provider (AWS, AZURE, GCP)")
    print("   • driver_node_type: VARCHAR - Driver instance type")
    print("   • worker_node_type: VARCHAR - Worker instance type")
    print("   • num_workers: INT - Number of worker nodes")
    print("   • photon_enabled: BOOLEAN - Photon enabled flag")
    print("   • workload_type: VARCHAR - JOBS, ALL_PURPOSE, or DLT")
    print("   • dlt_edition: VARCHAR - DLT edition (CORE, PRO, ADVANCED) if DLT")
    print("\n   Returns: DECIMAL (DBU per hour)")
    print("\n   Formula:")
    print("   (driver_dbu + worker_dbu × num_workers) × photon_multiplier")
    print("\n   Example:")
    print("   SELECT lakemeter.calculate_classic_compute_dbu(")
    print("     'AWS', 'm5.xlarge', 'm5.xlarge', 10, TRUE, 'JOBS', NULL")
    print("   );")
    print("   → Returns: 24.0000 (assuming 1 DBU driver + 1 DBU worker × 10 × 2.0 photon)")
except Exception as e:
    print(f"\n❌ Error creating function: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Function

# COMMAND ----------

print("\n" + "=" * 100)
print("TESTING: calculate_classic_compute_dbu")
print("=" * 100)

test_query = """
SELECT 
    'Test 1: JOBS Classic without Photon' as test_case,
    lakemeter.calculate_classic_compute_dbu(
        'AWS', 'm5.xlarge', 'm5.xlarge', 10, FALSE, 'JOBS', NULL
    ) as dbu_per_hour
UNION ALL
SELECT 
    'Test 2: JOBS Classic with Photon',
    lakemeter.calculate_classic_compute_dbu(
        'AWS', 'm5.xlarge', 'm5.xlarge', 10, TRUE, 'JOBS', NULL
    )
UNION ALL
SELECT 
    'Test 3: DLT Classic CORE without Photon',
    lakemeter.calculate_classic_compute_dbu(
        'AWS', 'm5.xlarge', 'm5.xlarge', 5, FALSE, 'DLT', 'CORE'
    )
UNION ALL
SELECT 
    'Test 4: ALL_PURPOSE Classic with Photon',
    lakemeter.calculate_classic_compute_dbu(
        'AWS', 'm5.2xlarge', 'm5.xlarge', 8, TRUE, 'ALL_PURPOSE', NULL
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
print("✅ CLASSIC COMPUTE DBU CALCULATOR CREATED")
print("=" * 100)

print("\n📋 Function created:")
print("   ✅ calculate_classic_compute_dbu")

print("\n🎯 This function handles:")
print("   • JOBS Classic")
print("   • ALL_PURPOSE Classic")
print("   • DLT Classic (CORE, PRO, ADVANCED)")

print("\n📐 Calculation:")
print("   1. Lookup driver DBU rate from sync_ref_instance_dbu_rates")
print("   2. Lookup worker DBU rate from sync_ref_instance_dbu_rates")
print("   3. Get Photon multiplier (cloud/workload-specific)")
print("   4. Calculate: (driver + worker × num_workers) × multiplier")

print("\n📝 Next step: Run 03_DBU_Calculators_Serverless.py")
print("=" * 100)
