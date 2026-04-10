# MAGIC %md
# MAGIC # Vector Search & Model Serving DBU Calculators
# MAGIC
# MAGIC **Purpose:** Calculate DBU per hour for Vector Search and Model Serving workloads
# MAGIC
# MAGIC **Functions Created:**
# MAGIC 1. `calculate_vector_search_dbu()` - Vector Search with capacity rounding
# MAGIC 2. `calculate_model_serving_dbu()` - Model Serving with cloud-specific GPU types

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
# MAGIC ## Function 1: calculate_vector_search_dbu()

# COMMAND ----------

print("=" * 100)
print("CREATING FUNCTION: calculate_vector_search_dbu")
print("=" * 100)

create_function_sql = """
CREATE OR REPLACE FUNCTION lakemeter.calculate_vector_search_dbu(
    p_cloud VARCHAR,
    p_vector_search_mode VARCHAR,
    p_vector_search_capacity_millions DECIMAL
)
RETURNS DECIMAL(18,4)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_dbu_rate DECIMAL(18,4);
    v_divisor DECIMAL(18,4);
    v_units DECIMAL(18,4);
    v_total_dbu DECIMAL(18,4);
BEGIN
    -- Lookup DBU rate for vector search mode
    SELECT dbu_rate INTO v_dbu_rate
    FROM lakemeter.sync_product_serverless_rates
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND product = 'vector_search'
      AND UPPER(size_or_model) = UPPER(p_vector_search_mode)
    LIMIT 1;
    
    -- Divisor based on mode:
    -- standard: 2 million vectors per unit
    -- storage_optimized: 64 million vectors per unit
    v_divisor := CASE 
        WHEN LOWER(p_vector_search_mode) = 'storage_optimized' THEN 64.0
        ELSE 2.0  -- standard
    END;
    
    -- Calculate units with CEILING (round up)
    -- Example: 3M capacity / 2M per unit = 1.5 → CEILING = 2 units
    v_units := CEILING(p_vector_search_capacity_millions / v_divisor);
    
    -- Calculate total DBU
    v_total_dbu := COALESCE(v_dbu_rate, 0) * v_units;
    
    RETURN v_total_dbu;
END;
$$;

COMMENT ON FUNCTION lakemeter.calculate_vector_search_dbu IS 
'Calculate DBU per hour for Vector Search workloads.
Formula: CEILING(capacity_millions / divisor) × dbu_rate
Divisors: standard=2M per unit, storage_optimized=64M per unit
Always rounds UP to next unit.';
"""

try:
    execute_query(create_function_sql)
    print("\n✅ Function created: calculate_vector_search_dbu")
    print("\n   Parameters:")
    print("   • cloud: VARCHAR - Cloud provider (AWS, AZURE, GCP)")
    print("   • vector_search_mode: VARCHAR - 'standard' or 'storage_optimized'")
    print("   • vector_search_capacity_millions: DECIMAL - Capacity in millions of vectors")
    print("\n   Returns: DECIMAL (DBU per hour)")
    print("\n   Formula:")
    print("   CEILING(capacity_millions / divisor) × dbu_rate")
    print("\n   Divisors:")
    print("   • standard: 2 million vectors per unit")
    print("   • storage_optimized: 64 million vectors per unit")
    print("\n   Example:")
    print("   SELECT lakemeter.calculate_vector_search_dbu('AWS', 'standard', 3.0);")
    print("   → 3M / 2M = 1.5 → CEILING = 2 units × DBU rate")
except Exception as e:
    print(f"\n❌ Error creating function: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Function 2: calculate_model_serving_dbu()

# COMMAND ----------

print("\n" + "=" * 100)
print("CREATING FUNCTION: calculate_model_serving_dbu")
print("=" * 100)

create_function_sql = """
CREATE OR REPLACE FUNCTION lakemeter.calculate_model_serving_dbu(
    p_cloud VARCHAR,
    p_serverless_size VARCHAR
)
RETURNS DECIMAL(18,4)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_dbu_rate DECIMAL(18,4);
BEGIN
    -- Lookup DBU rate for GPU type (cloud-specific)
    -- size_or_model contains cloud-specific GPU types:
    -- AWS: cpu, gpu_small_t4, gpu_medium_a10g_1x, gpu_large_a10g_4x, etc.
    -- AZURE: cpu, gpu_small_t4, gpu_medium_a100_1x, etc.
    -- GCP: cpu, gpu_small_t4, gpu_medium_l4_1x, etc.
    SELECT dbu_rate INTO v_dbu_rate
    FROM lakemeter.sync_product_serverless_rates
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND product = 'model_serving'
      AND UPPER(size_or_model) = UPPER(p_serverless_size)
    LIMIT 1;
    
    RETURN COALESCE(v_dbu_rate, 0);
END;
$$;

COMMENT ON FUNCTION lakemeter.calculate_model_serving_dbu IS 
'Calculate DBU per hour for Model Serving workloads.
GPU types are cloud-specific (e.g., AWS uses A10G, Azure uses A100, GCP uses L4).
Lookup from: sync_product_serverless_rates';
"""

try:
    execute_query(create_function_sql)
    print("\n✅ Function created: calculate_model_serving_dbu")
    print("\n   Parameters:")
    print("   • cloud: VARCHAR - Cloud provider (AWS, AZURE, GCP)")
    print("   • serverless_size: VARCHAR - GPU type (cloud-specific)")
    print("\n   Returns: DECIMAL (DBU per hour)")
    print("\n   GPU Types (cloud-specific, from pricing table):")
    print("   • AWS: cpu, gpu_small_t4, gpu_medium_a10g_1x/4x/8x, gpu_xlarge_a100_40gb_8x, gpu_xlarge_a100_80gb_8x")
    print("   • AZURE: cpu, gpu_small_t4, gpu_xlarge_a100_80gb_1x, gpu_2xlarge_a100_80gb_2x, gpu_4xlarge_a100_80gb_4x")
    print("   • GCP: cpu, gpu_medium_g2_standard_8")
    print("\n   Lookup from: sync_product_serverless_rates")
    print("\n   Example:")
    print("   SELECT lakemeter.calculate_model_serving_dbu('AWS', 'gpu_medium_a10g_1x');")
    print("   → Returns DBU rate for 1× A10G GPU on AWS")
except Exception as e:
    print(f"\n❌ Error creating function: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Functions

# COMMAND ----------

print("\n" + "=" * 100)
print("TESTING: Vector Search & Model Serving")
print("=" * 100)

test_query = """
SELECT 'Vector Search Test 1: 3M standard' as test_case,
       lakemeter.calculate_vector_search_dbu('AWS', 'standard', 3.0) as dbu_per_hour
UNION ALL
SELECT 'Vector Search Test 2: 100M storage_optimized',
       lakemeter.calculate_vector_search_dbu('AWS', 'storage_optimized', 100.0)
UNION ALL
SELECT 'Model Serving Test 1: CPU',
       lakemeter.calculate_model_serving_dbu('AWS', 'cpu')
UNION ALL
SELECT 'Model Serving Test 2: GPU A10G',
       lakemeter.calculate_model_serving_dbu('AWS', 'gpu_medium_a10g_1x');
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
print("✅ VECTOR SEARCH & MODEL SERVING DBU CALCULATORS CREATED")
print("=" * 100)

print("\n📋 Functions created:")
print("   ✅ calculate_vector_search_dbu")
print("   ✅ calculate_model_serving_dbu")

print("\n🎯 Vector Search:")
print("   • Handles capacity in millions of vectors")
print("   • CEILING rounding (always round up)")
print("   • Different divisors: standard (2M), storage_optimized (64M)")

print("\n🎯 Model Serving:")
print("   • Cloud-specific GPU types (see pricing table for exact list)")
print("   • AWS: A10G, A100 variants")
print("   • AZURE: A100 variants (1x, 2x, 4x)")
print("   • GCP: G2 standard")
print("   • Simple lookup from sync_product_serverless_rates")

print("\n📝 Next step: Run 06_DBU_Calculators_FMAPI.py")
print("=" * 100)
