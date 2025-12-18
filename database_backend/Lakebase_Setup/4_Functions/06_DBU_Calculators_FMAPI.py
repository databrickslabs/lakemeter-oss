# Databricks notebook source
# MAGIC %md
# MAGIC # FMAPI DBU Calculators
# MAGIC
# MAGIC **Purpose:** Calculate DBU for Foundation Model API workloads
# MAGIC
# MAGIC **Functions Created:**
# MAGIC 1. `calculate_fmapi_databricks_dbu()` - Databricks-hosted models (token + provisioned)
# MAGIC 2. `calculate_fmapi_proprietary_dbu()` - Proprietary models (OpenAI, Anthropic, Google)
# MAGIC
# MAGIC **Pricing Models:**
# MAGIC - **Token-based:** Pay per million tokens (input and output have separate rates)
# MAGIC - **Provisioned throughput:** Hourly charges (entry, scaling)

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
# MAGIC ## Function 1: calculate_fmapi_databricks_dbu()

# COMMAND ----------

print("=" * 100)
print("CREATING FUNCTION: calculate_fmapi_databricks_dbu")
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
          AND p.proname = 'calculate_fmapi_databricks_dbu'
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
CREATE OR REPLACE FUNCTION lakemeter.calculate_fmapi_databricks_dbu(
    p_cloud VARCHAR,
    p_fmapi_model VARCHAR,
    p_fmapi_rate_type VARCHAR DEFAULT 'input_token',
    p_fmapi_quantity BIGINT DEFAULT 0
)
RETURNS DECIMAL(18,4)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_dbu_rate DECIMAL(18,4);
    v_divisor BIGINT;
    v_is_hourly BOOLEAN;
    v_total_dbu DECIMAL(18,4);
BEGIN
    -- Query pricing rate (ONE query - much simpler!)
    SELECT 
        dbu_rate,
        COALESCE(input_divisor, 1) as divisor,
        COALESCE(is_hourly, FALSE) as is_hourly
    INTO v_dbu_rate, v_divisor, v_is_hourly
    FROM lakemeter.sync_product_fmapi_databricks
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(model) = UPPER(p_fmapi_model)
      AND rate_type = p_fmapi_rate_type
    LIMIT 1;
    
    -- Calculate based on whether it's hourly or token-based
    IF v_is_hourly THEN
        -- Hourly pricing (provisioned_entry, provisioned_scaling): quantity = hours
        v_total_dbu := p_fmapi_quantity * COALESCE(v_dbu_rate, 0);
    ELSE
        -- Token-based pricing: quantity = tokens, divide by divisor (usually 1M)
        v_total_dbu := (p_fmapi_quantity / v_divisor::DECIMAL) * COALESCE(v_dbu_rate, 0);
    END IF;
    
    RETURN v_total_dbu;
END;
$$;

COMMENT ON FUNCTION lakemeter.calculate_fmapi_databricks_dbu IS 
'Calculate DBU for Databricks FMAPI models.
Supports all rate_types: input_token, output_token, provisioned_entry, provisioned_scaling.
ONE line item = ONE rate_type for clean cost breakdown.
Token-based: quantity = tokens, divided by 1M.
Provisioned: quantity = hours, multiplied by hourly rate.';
"""

try:
    execute_query(create_function_sql)
    print("\n✅ Function created: calculate_fmapi_databricks_dbu (SIMPLIFIED!)")
    print("\n   Parameters:")
    print("   • cloud: VARCHAR - Cloud provider")
    print("   • fmapi_model: VARCHAR - Model name (e.g., 'llama-3-1-8b')")
    print("   • fmapi_rate_type: VARCHAR - Direct from pricing table:")
    print("       ◦ 'input_token', 'output_token' (token-based)")
    print("       ◦ 'provisioned_entry', 'provisioned_scaling' (hourly)")
    print("   • fmapi_quantity: BIGINT - Quantity (tokens for token-based, hours for provisioned)")
    print("\n   Returns: DECIMAL (DBU)")
    print("\n   Design: ONE line item = ONE rate_type (clean cost breakdown!)")
    print("\n   Formula:")
    print("   • Token-based: (quantity / 1M) × dbu_rate")
    print("   • Hourly-based: quantity × dbu_rate")
except Exception as e:
    print(f"\n❌ Error creating function: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Function 2: calculate_fmapi_proprietary_dbu()

# COMMAND ----------

print("\n" + "=" * 100)
print("CREATING FUNCTION: calculate_fmapi_proprietary_dbu")
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
          AND p.proname = 'calculate_fmapi_proprietary_dbu'
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
CREATE OR REPLACE FUNCTION lakemeter.calculate_fmapi_proprietary_dbu(
    p_cloud VARCHAR,
    p_fmapi_provider VARCHAR,
    p_fmapi_model VARCHAR,
    p_fmapi_endpoint_type VARCHAR DEFAULT 'global',
    p_fmapi_context_length VARCHAR DEFAULT 'all',
    p_fmapi_rate_type VARCHAR DEFAULT 'input_token',
    p_fmapi_quantity BIGINT DEFAULT 0
)
RETURNS DECIMAL(18,4)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_dbu_rate DECIMAL(18,4);
    v_divisor BIGINT;
    v_is_hourly BOOLEAN;
    v_total_dbu DECIMAL(18,4);
BEGIN
    -- Query pricing rate (ONE query - much simpler!)
    SELECT 
        dbu_rate,
        COALESCE(input_divisor, 1) as divisor,
        COALESCE(is_hourly, FALSE) as is_hourly
    INTO v_dbu_rate, v_divisor, v_is_hourly
    FROM lakemeter.sync_product_fmapi_proprietary
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(provider) = UPPER(p_fmapi_provider)
      AND UPPER(model) = UPPER(p_fmapi_model)
      AND rate_type = p_fmapi_rate_type
      AND LOWER(endpoint_type) = LOWER(COALESCE(p_fmapi_endpoint_type, 'global'))
      AND LOWER(context_length) = LOWER(COALESCE(p_fmapi_context_length, 'all'))
    LIMIT 1;
    
    -- Calculate based on whether it's hourly or token-based
    IF v_is_hourly THEN
        -- Hourly pricing (batch_inference): quantity = hours
        v_total_dbu := p_fmapi_quantity * COALESCE(v_dbu_rate, 0);
    ELSE
        -- Token-based pricing: quantity = tokens, divide by divisor (usually 1M)
        v_total_dbu := (p_fmapi_quantity / v_divisor::DECIMAL) * COALESCE(v_dbu_rate, 0);
    END IF;
    
    RETURN v_total_dbu;
END;
$$;

COMMENT ON FUNCTION lakemeter.calculate_fmapi_proprietary_dbu IS 
'Calculate DBU for proprietary FMAPI models (OpenAI, Anthropic, Google).
Supports all rate_types: input_token, output_token, cache_read, cache_write, batch_inference.
ONE line item = ONE rate_type for clean cost breakdown.
Filters by: cloud, provider, model, endpoint_type, context_length, rate_type.
Note: Different providers use different context_length values:
  - OpenAI: "all"
  - Anthropic: "short", "long", or "all" (model-specific)
  - Google: "short", "long"';
"""

try:
    execute_query(create_function_sql)
    print("\n✅ Function created: calculate_fmapi_proprietary_dbu (SIMPLIFIED!)")
    print("\n   Parameters:")
    print("   • cloud: VARCHAR - Cloud provider")
    print("   • fmapi_provider: VARCHAR - 'openai', 'anthropic', 'google'")
    print("   • fmapi_model: VARCHAR - Model name (e.g., 'gpt-4o', 'claude-sonnet-4')")
    print("   • fmapi_endpoint_type: VARCHAR - 'global' or 'in_geo' (default: 'global')")
    print("   • fmapi_context_length: VARCHAR - Context length (provider-specific, default: 'all')")
    print("   • fmapi_rate_type: VARCHAR - Direct from pricing table:")
    print("       ◦ 'input_token', 'output_token', 'cache_read', 'cache_write', 'batch_inference'")
    print("   • fmapi_quantity: BIGINT - Quantity (tokens for token-based, hours for batch)")
    print("\n   Returns: DECIMAL (DBU)")
    print("\n   Design: ONE line item = ONE rate_type (clean cost breakdown!)")
    print("\n   Formula:")
    print("   • Token-based: (quantity / 1M) × dbu_rate")
    print("   • Hourly-based: quantity × dbu_rate")
except Exception as e:
    print(f"\n❌ Error creating function: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Functions

# COMMAND ----------

print("\n" + "=" * 100)
print("TESTING: FMAPI Calculators")
print("=" * 100)

test_query = """
SELECT 'FMAPI DB Test 1: Token-based' as test_case,
       lakemeter.calculate_fmapi_databricks_dbu(
           'AWS', 'llama-3-1-8b', 'pay_per_token', 10000000, 5000000, 0
       ) as dbu_per_month
UNION ALL
SELECT 'FMAPI DB Test 2: Provisioned entry',
       lakemeter.calculate_fmapi_databricks_dbu(
           'AWS', 'llama-3-3-70b', 'provisioned_entry', 0, 0, 720
       )
UNION ALL
SELECT 'FMAPI Prop Test 1: OpenAI',
       lakemeter.calculate_fmapi_proprietary_dbu(
           'AWS', 'openai', 'gpt-5', 'global', 'all', 10000000, 5000000
       )
UNION ALL
SELECT 'FMAPI Prop Test 2: Anthropic',
       lakemeter.calculate_fmapi_proprietary_dbu(
           'AWS', 'anthropic', 'claude-sonnet-4', 'global', 'short', 10000000, 5000000
       );
"""

try:
    results = execute_query(test_query, fetch=True)
    print("\n✅ Test results:")
    for row in results:
        print(f"   {row[0]}: {row[1]} DBU/month")
except Exception as e:
    print(f"\n⚠️  Test skipped (requires pricing data): {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n" + "=" * 100)
print("✅ FMAPI DBU CALCULATORS CREATED")
print("=" * 100)

print("\n📋 Functions created:")
print("   ✅ calculate_fmapi_databricks_dbu")
print("   ✅ calculate_fmapi_proprietary_dbu")

print("\n🎯 FMAPI Databricks:")
print("   • Token-based: (input_tokens/1M × input_rate) + (output_tokens/1M × output_rate)")
print("   • Provisioned: hourly_rate × hours_per_month")
print("   • Cloud-specific filtering")

print("\n🎯 FMAPI Proprietary:")
print("   • Token-based only")
print("   • Complex filtering: provider, model, endpoint, context")
print("   • Context length is MODEL-SPECIFIC (not just provider)")

print("\n📝 Next step: Run 07_DBU_Calculators_Lakebase.py")
print("=" * 100)
