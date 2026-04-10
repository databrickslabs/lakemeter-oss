# MAGIC %md
# MAGIC # Utility Functions for Cost Calculation
# MAGIC
# MAGIC **Purpose:** Core utility functions used across all cost calculators
# MAGIC
# MAGIC **Functions Created:**
# MAGIC 1. `calculate_hours_per_month()` - Calculate usage hours
# MAGIC 2. `get_product_type_for_pricing()` - Map workload → product_type
# MAGIC 3. `get_dbu_price()` - Lookup DBU price
# MAGIC 4. `get_photon_multiplier()` - Get Photon multiplier

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
# MAGIC ## Function 1: calculate_hours_per_month()

# COMMAND ----------

print("=" * 100)
print("CREATING FUNCTION: calculate_hours_per_month")
print("=" * 100)

# Drop all existing signatures first
print("\n🗑️  Dropping all existing signatures...")
drop_sql = """
DO $$ 
DECLARE
    r RECORD;
BEGIN
    FOR r IN 
        SELECT p.oid::regprocedure
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'lakemeter' 
          AND p.proname = 'calculate_hours_per_month'
    LOOP
        EXECUTE 'DROP FUNCTION ' || r.oid::regprocedure;
        RAISE NOTICE 'Dropped: %', r.oid::regprocedure;
    END LOOP;
END $$;
"""

try:
    execute_query(drop_sql)
    print("  ✓ All existing signatures dropped")
except Exception as e:
    print(f"  Note: {e}")

create_function_sql = """
CREATE OR REPLACE FUNCTION lakemeter.calculate_hours_per_month(
    p_workload_type VARCHAR,
    p_runs_per_day INT,
    p_avg_runtime_minutes INT,
    p_days_per_month INT,
    p_fmapi_rate_type VARCHAR DEFAULT NULL,
    p_hours_per_month DECIMAL DEFAULT NULL
)
RETURNS DECIMAL(18,4)
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    v_hours DECIMAL(18,4);
BEGIN
    -- If explicit hours provided, use it directly
    IF p_hours_per_month IS NOT NULL THEN
        RETURN p_hours_per_month::DECIMAL(18,4);
    END IF;

    -- 24/7 workloads (continuous availability)
    IF p_workload_type IN ('VECTOR_SEARCH', 'MODEL_SERVING', 'LAKEBASE') THEN
        v_hours := 24.0 * COALESCE(p_days_per_month, 30);
    
    -- FMAPI batch_inference (hourly charges)
    ELSIF p_workload_type IN ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY') 
       AND COALESCE(p_fmapi_rate_type, 'input_token') = 'batch_inference' THEN
        v_hours := COALESCE(p_runs_per_day, 0) * (COALESCE(p_avg_runtime_minutes, 0) / 60.0) * COALESCE(p_days_per_month, 30);
    
    -- Token-based FMAPI (no hourly charges - input_token, output_token, cache_read, cache_write)
    ELSIF p_workload_type IN ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY') THEN
        v_hours := 0;
    
    -- All other workload types (usage-based)
    ELSE
        v_hours := COALESCE(p_runs_per_day, 0) * (COALESCE(p_avg_runtime_minutes, 0) / 60.0) * COALESCE(p_days_per_month, 30);
    END IF;
    
    RETURN v_hours;
END;
$$;
"""

try:
    execute_query(create_function_sql)
    print("\n✅ Function created: calculate_hours_per_month")
    print("\n   Parameters:")
    print("   • workload_type: VARCHAR")
    print("   • runs_per_day: INT")
    print("   • avg_runtime_minutes: INT")
    print("   • days_per_month: INT")
    print("   • fmapi_rate_type: VARCHAR (optional)")
    print("   • hours_per_month: INT (optional) - override auto-calculation")
    print("\n   Returns: DECIMAL (hours per month)")
    print("\n   Examples:")
    print("   SELECT lakemeter.calculate_hours_per_month('JOBS', 8, 60, 30, NULL, NULL);")
    print("   → Returns: 240.0000 (8 runs × 60 min / 60 × 30 days)")
    print("\n   SELECT lakemeter.calculate_hours_per_month('VECTOR_SEARCH', 0, 0, 30, NULL, 720);")
    print("   → Returns: 720.0000 (explicit override for 24/7)")
except Exception as e:
    print(f"\n❌ Error creating function: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Function 2: get_product_type_for_pricing()

# COMMAND ----------

print("\n" + "=" * 100)
print("CREATING FUNCTION: get_product_type_for_pricing")
print("=" * 100)

create_function_sql = """
CREATE OR REPLACE FUNCTION lakemeter.get_product_type_for_pricing(
    p_workload_type VARCHAR,
    p_serverless_enabled BOOLEAN DEFAULT FALSE,
    p_photon_enabled BOOLEAN DEFAULT FALSE,
    p_dlt_edition VARCHAR DEFAULT NULL,
    p_dbsql_warehouse_type VARCHAR DEFAULT NULL,
    p_fmapi_provider VARCHAR DEFAULT NULL
)
RETURNS VARCHAR
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    v_product_type VARCHAR;
    v_workload_type VARCHAR;
    v_dlt_edition VARCHAR;
    v_dbsql_warehouse_type VARCHAR;
    v_fmapi_provider VARCHAR;
BEGIN
    -- Normalize string inputs to UPPERCASE for case-insensitive matching
    v_workload_type := UPPER(p_workload_type);
    v_dlt_edition := UPPER(p_dlt_edition);
    v_dbsql_warehouse_type := UPPER(p_dbsql_warehouse_type);
    v_fmapi_provider := UPPER(p_fmapi_provider);
    
    CASE v_workload_type
        -- JOBS: Classic vs Serverless
        WHEN 'JOBS' THEN
            IF p_serverless_enabled THEN
                v_product_type := 'JOBS_SERVERLESS_COMPUTE';
            ELSIF p_photon_enabled THEN
                v_product_type := 'JOBS_COMPUTE_(PHOTON)';
            ELSE
                v_product_type := 'JOBS_COMPUTE';
            END IF;
        
        -- ALL_PURPOSE: Classic vs Serverless
        WHEN 'ALL_PURPOSE' THEN
            IF p_serverless_enabled THEN
                v_product_type := 'ALL_PURPOSE_SERVERLESS_COMPUTE';
            ELSIF p_photon_enabled THEN
                v_product_type := 'ALL_PURPOSE_COMPUTE_(PHOTON)';
            ELSE
                v_product_type := 'ALL_PURPOSE_COMPUTE';
            END IF;
        
        -- DLT: Classic vs Serverless (with edition)
        WHEN 'DLT' THEN
            IF p_serverless_enabled THEN
                v_product_type := 'JOBS_SERVERLESS_COMPUTE';  -- DLT Serverless uses same as JOBS Serverless
            ELSE
                v_product_type := 'DLT_' || COALESCE(v_dlt_edition, 'CORE') || '_COMPUTE';
                IF p_photon_enabled THEN
                    v_product_type := v_product_type || '_(PHOTON)';
                END IF;
            END IF;
        
        -- DBSQL: Uses warehouse_type for serverless
        WHEN 'DBSQL' THEN
            CASE v_dbsql_warehouse_type
                WHEN 'SERVERLESS' THEN v_product_type := 'SERVERLESS_SQL_COMPUTE';
                WHEN 'PRO' THEN v_product_type := 'SQL_PRO_COMPUTE';
                ELSE v_product_type := 'SQL_COMPUTE';
            END CASE;
        
        -- Serverless-only products
        WHEN 'VECTOR_SEARCH' THEN
            v_product_type := 'SERVERLESS_REAL_TIME_INFERENCE';
        
        WHEN 'MODEL_SERVING' THEN
            v_product_type := 'SERVERLESS_REAL_TIME_INFERENCE';
        
        WHEN 'FMAPI_DATABRICKS' THEN
            v_product_type := 'SERVERLESS_REAL_TIME_INFERENCE';
        
        WHEN 'FMAPI_PROPRIETARY' THEN
            -- Special case: Google uses GEMINI_MODEL_SERVING
            IF v_fmapi_provider = 'GOOGLE' THEN
                v_product_type := 'GEMINI_MODEL_SERVING';
            ELSE
                v_product_type := v_fmapi_provider || '_MODEL_SERVING';
            END IF;
        
        WHEN 'LAKEBASE' THEN
            v_product_type := 'DATABASE_SERVERLESS_COMPUTE';
        
        -- Default
        ELSE
            v_product_type := 'JOBS_COMPUTE';
    END CASE;
    
    RETURN v_product_type;
END;
$$;
"""

try:
    execute_query(create_function_sql)
    print("\n✅ Function created: get_product_type_for_pricing")
    print("\n   Parameters:")
    print("   • workload_type: VARCHAR")
    print("   • serverless_enabled: BOOLEAN (default FALSE)")
    print("   • photon_enabled: BOOLEAN (default FALSE)")
    print("   • dlt_edition: VARCHAR (optional)")
    print("   • dbsql_warehouse_type: VARCHAR (optional)")
    print("   • fmapi_provider: VARCHAR (optional)")
    print("\n   Returns: VARCHAR (product_type for pricing lookup)")
    print("\n   Examples:")
    print("   SELECT lakemeter.get_product_type_for_pricing('JOBS', FALSE, TRUE, NULL, NULL, NULL);")
    print("   → Returns: 'JOBS_COMPUTE_(PHOTON)'")
    print("\n   SELECT lakemeter.get_product_type_for_pricing('FMAPI_PROPRIETARY', NULL, NULL, NULL, NULL, 'google');")
    print("   → Returns: 'GEMINI_MODEL_SERVING'")
except Exception as e:
    print(f"\n❌ Error creating function: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Function 3: get_dbu_price()

# COMMAND ----------

print("\n" + "=" * 100)
print("CREATING FUNCTION: get_dbu_price")
print("=" * 100)

create_function_sql = """
CREATE OR REPLACE FUNCTION lakemeter.get_dbu_price(
    p_cloud VARCHAR,
    p_region VARCHAR,
    p_tier VARCHAR,
    p_product_type VARCHAR
)
RETURNS DECIMAL(10,4)
LANGUAGE plpgsql
STABLE  -- STABLE because it reads from database
AS $$
DECLARE
    v_price DECIMAL(10,4);
BEGIN
    -- Try sku_name first (OSS schema), then product_type (legacy schema)
    SELECT price_per_dbu INTO v_price
    FROM lakemeter.sync_pricing_dbu_rates
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(region) = UPPER(p_region)
      AND UPPER(tier) = UPPER(p_tier)
      AND (UPPER(sku_name) = UPPER(p_product_type) OR UPPER(COALESCE(product_type, '')) = UPPER(p_product_type))
    LIMIT 1;
    
    RETURN COALESCE(v_price, 0);
END;
$$;
"""

try:
    execute_query(create_function_sql)
    print("\n✅ Function created: get_dbu_price")
    print("\n   Parameters:")
    print("   • cloud: VARCHAR")
    print("   • region: VARCHAR")
    print("   • tier: VARCHAR")
    print("   • product_type: VARCHAR")
    print("\n   Returns: DECIMAL (price per DBU)")
    print("\n   Example:")
    print("   SELECT lakemeter.get_dbu_price('AWS', 'us-east-1', 'PREMIUM', 'JOBS_COMPUTE');")
    print("   → Returns: 0.0700")
except Exception as e:
    print(f"\n❌ Error creating function: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Function 4: get_photon_multiplier()

# COMMAND ----------

print("\n" + "=" * 100)
print("CREATING FUNCTION: get_photon_multiplier")
print("=" * 100)

create_function_sql = """
CREATE OR REPLACE FUNCTION lakemeter.get_photon_multiplier(
    p_cloud VARCHAR,
    p_workload_type VARCHAR,
    p_dlt_edition VARCHAR DEFAULT NULL,
    p_photon_enabled BOOLEAN DEFAULT FALSE,
    p_serverless_enabled BOOLEAN DEFAULT FALSE
)
RETURNS DECIMAL(10,4)
LANGUAGE plpgsql
STABLE  -- STABLE because it reads from database
AS $$
DECLARE
    v_multiplier DECIMAL(10,4);
    v_sku_type VARCHAR;
BEGIN
    -- Classic without Photon: multiplier = 1.0
    IF NOT p_photon_enabled AND NOT p_serverless_enabled THEN
        RETURN 1.0;
    END IF;
    
    -- Classic with Photon: lookup multiplier
    -- Determine SKU type
    CASE p_workload_type
        WHEN 'DLT' THEN
            v_sku_type := 'DLT_' || UPPER(COALESCE(p_dlt_edition, 'CORE')) || '_COMPUTE';
        WHEN 'JOBS' THEN
            v_sku_type := 'JOBS_COMPUTE';
        WHEN 'ALL_PURPOSE' THEN
            v_sku_type := 'ALL_PURPOSE_COMPUTE';
        ELSE
            v_sku_type := 'JOBS_COMPUTE';
    END CASE;
    
    -- Lookup multiplier
    SELECT multiplier INTO v_multiplier
    FROM lakemeter.sync_ref_dbu_multipliers
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(sku_type) = UPPER(v_sku_type)
      AND feature = 'photon'
    LIMIT 1;
    
    RETURN COALESCE(v_multiplier, 1.0);
END;
$$;
"""

try:
    execute_query(create_function_sql)
    print("\n✅ Function created: get_photon_multiplier")
    print("\n   Parameters:")
    print("   • cloud: VARCHAR")
    print("   • workload_type: VARCHAR")
    print("   • dlt_edition: VARCHAR (optional)")
    print("   • photon_enabled: BOOLEAN (default FALSE)")
    print("   • serverless_enabled: BOOLEAN (default FALSE)")
    print("\n   Returns: DECIMAL (multiplier value)")
    print("\n   Examples:")
    print("   SELECT lakemeter.get_photon_multiplier('AWS', 'JOBS', NULL, TRUE, FALSE);")
    print("   → Returns: 2.0 (classic with Photon)")
    print("\n   SELECT lakemeter.get_photon_multiplier('AWS', 'JOBS', NULL, TRUE, TRUE);")
    print("   → Returns: 2.0 (serverless, Photon mandatory, multiplier still applies)")
    print("\n   SELECT lakemeter.get_photon_multiplier('AWS', 'JOBS', NULL, FALSE, FALSE);")
    print("   → Returns: 1.0 (classic without Photon)")
except Exception as e:
    print(f"\n❌ Error creating function: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n" + "=" * 100)
print("✅ ALL UTILITY FUNCTIONS CREATED SUCCESSFULLY")
print("=" * 100)

print("\n📋 Functions created:")
print("   1. ✅ calculate_hours_per_month")
print("   2. ✅ get_product_type_for_pricing")
print("   3. ✅ get_dbu_price")
print("   4. ✅ get_photon_multiplier")

print("\n🎯 These utility functions are now available for:")
print("   • DBU calculators (02-07)")
print("   • VM cost calculators (08)")
print("   • Main orchestrator (09)")

print("\n📝 Next step: Run 02_DBU_Calculators_Classic.py")
print("=" * 100)
