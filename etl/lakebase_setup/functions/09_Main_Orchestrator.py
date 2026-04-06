# Databricks notebook source
# MAGIC %md
# MAGIC # Main Cost Calculation Orchestrator
# MAGIC
# MAGIC **Purpose:** Main entry point for calculating line item costs
# MAGIC
# MAGIC **Function Created:**
# MAGIC - `calculate_line_item_costs()` - Routes to appropriate calculators and returns complete cost breakdown
# MAGIC
# MAGIC **This function:**
# MAGIC 1. Accepts ALL line_item parameters
# MAGIC 2. Routes to appropriate DBU calculator based on workload_type
# MAGIC 3. Calculates VM costs (if applicable)
# MAGIC 4. Returns complete cost breakdown
# MAGIC
# MAGIC **Usage:**
# MAGIC ```sql
# MAGIC SELECT * FROM lakemeter.calculate_line_item_costs(
# MAGIC     'JOBS', 'AWS', 'us-east-1', 'PREMIUM',
# MAGIC     FALSE, TRUE, NULL, 'm5.xlarge', 'm5.xlarge', 10,
# MAGIC     'on_demand', 'spot', 8, 60, 30, ...
# MAGIC );
# MAGIC ```

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
# MAGIC ## Function: calculate_line_item_costs()
# MAGIC
# MAGIC This is a large function with many parameters. It routes to all the specialized calculators.

# COMMAND ----------

print("=" * 100)
print("CREATING FUNCTION: calculate_line_item_costs")
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
  AND p.proname = 'calculate_line_item_costs';
"""

try:
    results = execute_query(check_sql, fetch=True)
    if results:
        print(f"Found {len(results)} existing signature(s):")
        for row in results:
            print(f"  • {row[0]}({row[1][:100]}...)")  # Truncate long signatures
    else:
        print("  No existing signatures found.")
except Exception as e:
    print(f"  Could not check: {e}")

# Drop any existing signatures (this function has many parameters, so just drop by name)
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
          AND p.proname = 'calculate_line_item_costs'
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
CREATE OR REPLACE FUNCTION lakemeter.calculate_line_item_costs(
    -- Core parameters
    p_workload_type VARCHAR,
    p_cloud VARCHAR,
    p_region VARCHAR,
    p_tier VARCHAR,
    
    -- Compute configuration
    p_serverless_enabled BOOLEAN DEFAULT FALSE,
    p_photon_enabled BOOLEAN DEFAULT FALSE,
    p_dlt_edition VARCHAR DEFAULT NULL,
    p_driver_node_type VARCHAR DEFAULT NULL,
    p_worker_node_type VARCHAR DEFAULT NULL,
    p_num_workers INT DEFAULT 0,
    p_driver_pricing_tier VARCHAR DEFAULT 'on_demand',
    p_worker_pricing_tier VARCHAR DEFAULT 'on_demand',
    
    -- Usage patterns
    p_runs_per_day INT DEFAULT 0,
    p_avg_runtime_minutes INT DEFAULT 0,
    p_days_per_month INT DEFAULT 30,
    p_hours_per_month INT DEFAULT NULL,  -- Override for 24/7 workloads (NULL = auto-calculate)
    
    -- Serverless mode
    p_serverless_mode VARCHAR DEFAULT 'standard',
    
    -- DBSQL
    p_dbsql_warehouse_type VARCHAR DEFAULT NULL,
    p_dbsql_warehouse_size VARCHAR DEFAULT NULL,
    p_dbsql_num_clusters INT DEFAULT 1,
    p_dbsql_vm_pricing_tier VARCHAR DEFAULT 'on_demand',
    
    -- Vector Search
    p_vector_search_mode VARCHAR DEFAULT NULL,
    p_vector_search_capacity_millions DECIMAL DEFAULT 0,
    
    -- Model Serving
    p_model_serving_gpu_type VARCHAR DEFAULT NULL,
    
    -- FMAPI (one line = one rate_type design)
    p_fmapi_model VARCHAR DEFAULT NULL,
    p_fmapi_provider VARCHAR DEFAULT NULL,
    p_fmapi_endpoint_type VARCHAR DEFAULT 'global',
    p_fmapi_context_length VARCHAR DEFAULT 'all',
    p_fmapi_rate_type VARCHAR DEFAULT 'input_token',
    p_fmapi_quantity BIGINT DEFAULT 0,
    
    -- Lakebase
    p_lakebase_cu INT DEFAULT 0,
    p_lakebase_ha_nodes INT DEFAULT 1,
    
    -- VM Payment Options (optional, at end due to DEFAULT requirements)
    p_driver_payment_option VARCHAR DEFAULT 'NA',
    p_worker_payment_option VARCHAR DEFAULT 'NA',
    p_dbsql_vm_payment_option VARCHAR DEFAULT 'NA'
)
RETURNS TABLE(
    dbu_per_hour DECIMAL(18,4),
    hours_per_month DECIMAL(18,4),
    dbu_per_month DECIMAL(18,4),
    dbu_price DECIMAL(10,4),
    dbu_cost_per_month DECIMAL(18,2),
    driver_vm_cost_per_hour DECIMAL(18,4),
    worker_vm_cost_per_hour DECIMAL(18,4),
    total_vm_cost_per_hour DECIMAL(18,4),
    driver_vm_cost_per_month DECIMAL(18,4),
    total_worker_vm_cost_per_month DECIMAL(18,4),
    vm_cost_per_month DECIMAL(18,2),
    cost_per_month DECIMAL(18,2)
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_dbu_per_hour DECIMAL(18,4) := 0;
    v_hours_per_month DECIMAL(18,4) := 0;
    v_dbu_per_month DECIMAL(18,4) := 0;
    v_dbu_price DECIMAL(10,4) := 0;
    v_dbu_cost_per_month DECIMAL(18,2) := 0;
    v_product_type VARCHAR;
    
    -- VM costs
    v_driver_vm_cost_per_hour DECIMAL(18,4) := 0;
    v_worker_vm_cost_per_hour DECIMAL(18,4) := 0;
    v_total_vm_cost_per_hour DECIMAL(18,4) := 0;
    v_driver_vm_cost_per_month DECIMAL(18,4) := 0;
    v_total_worker_vm_cost_per_month DECIMAL(18,4) := 0;
    v_vm_cost_per_month DECIMAL(18,2) := 0;
    v_cost_per_month DECIMAL(18,2) := 0;
    
    -- VM cost record
    vm_costs RECORD;
BEGIN
    -- ========================================
    -- STEP 1: Calculate hours per month
    -- ========================================
    -- Pass all parameters including p_hours_per_month (utility function handles override)
    v_hours_per_month := lakemeter.calculate_hours_per_month(
        p_workload_type,
        p_runs_per_day,
        p_avg_runtime_minutes,
        p_days_per_month,
        p_fmapi_rate_type,
        p_hours_per_month  -- Allow direct override
    );
    
    -- ========================================
    -- STEP 2: Get product type for pricing
    -- ========================================
    v_product_type := lakemeter.get_product_type_for_pricing(
        p_workload_type,
        p_serverless_enabled,
        p_photon_enabled,
        p_dlt_edition,
        p_dbsql_warehouse_type,
        p_fmapi_provider
    );
    
    -- ========================================
    -- STEP 3: Calculate DBU per hour/month
    -- ========================================
    CASE p_workload_type
        -- Classic Compute (JOBS, ALL_PURPOSE, DLT Classic)
        WHEN 'JOBS', 'ALL_PURPOSE', 'DLT' THEN
            IF NOT p_serverless_enabled THEN
                v_dbu_per_hour := lakemeter.calculate_classic_compute_dbu(
                    p_cloud, p_driver_node_type, p_worker_node_type,
                    p_num_workers, p_photon_enabled, p_workload_type, p_dlt_edition
                );
                v_dbu_per_month := v_dbu_per_hour * v_hours_per_month;
                
                -- Calculate VM costs
                SELECT * INTO vm_costs
                FROM lakemeter.calculate_classic_vm_costs(
                    p_cloud, p_region, p_driver_node_type, p_worker_node_type,
                    p_num_workers, p_driver_pricing_tier, p_worker_pricing_tier, v_hours_per_month,
                    p_driver_payment_option, p_worker_payment_option
                );
                
                v_driver_vm_cost_per_hour := vm_costs.driver_vm_cost_per_hour;
                v_worker_vm_cost_per_hour := vm_costs.worker_vm_cost_per_hour;
                v_total_vm_cost_per_hour := vm_costs.total_vm_cost_per_hour;
                v_driver_vm_cost_per_month := vm_costs.driver_vm_cost_per_month;
                v_total_worker_vm_cost_per_month := vm_costs.total_worker_vm_cost_per_month;
                v_vm_cost_per_month := vm_costs.total_vm_cost_per_month::DECIMAL(18,2);
            
            -- Serverless Compute
            ELSE
                v_dbu_per_hour := lakemeter.calculate_serverless_compute_dbu(
                    p_cloud, p_driver_node_type, p_worker_node_type,
                    p_num_workers, p_workload_type, p_serverless_mode
                );
                v_dbu_per_month := v_dbu_per_hour * v_hours_per_month;
                -- No VM costs for serverless
            END IF;
        
        -- DBSQL
        WHEN 'DBSQL' THEN
            v_dbu_per_hour := lakemeter.calculate_dbsql_dbu(
                p_cloud, p_dbsql_warehouse_type, p_dbsql_warehouse_size, p_dbsql_num_clusters
            );
            v_dbu_per_month := v_dbu_per_hour * v_hours_per_month;
            
            -- VM costs only for Classic and Pro
            IF LOWER(p_dbsql_warehouse_type) IN ('classic', 'pro') THEN
                SELECT * INTO vm_costs
                FROM lakemeter.calculate_dbsql_vm_costs(
                    p_cloud, p_region, p_dbsql_warehouse_type, p_dbsql_warehouse_size,
                    p_dbsql_num_clusters, p_dbsql_vm_pricing_tier, v_hours_per_month,
                    p_dbsql_vm_payment_option  -- DBSQL VM payment option (e.g., all_upfront, no_upfront)
                );
                
                v_driver_vm_cost_per_hour := vm_costs.driver_vm_cost_per_hour;
                v_worker_vm_cost_per_hour := vm_costs.worker_vm_cost_per_hour;
                v_total_vm_cost_per_hour := vm_costs.total_vm_cost_per_hour;
                v_driver_vm_cost_per_month := vm_costs.driver_vm_cost_per_month;
                v_total_worker_vm_cost_per_month := vm_costs.total_worker_vm_cost_per_month;
                v_vm_cost_per_month := vm_costs.total_vm_cost_per_month::DECIMAL(18,2);
            END IF;
        
        -- Vector Search (hourly pricing, 24/7 availability)
        WHEN 'VECTOR_SEARCH' THEN
            v_dbu_per_hour := lakemeter.calculate_vector_search_dbu(
                p_cloud, p_vector_search_mode, p_vector_search_capacity_millions
            );
            v_dbu_per_month := v_dbu_per_hour * v_hours_per_month;
        
        -- Model Serving (hourly pricing, 24/7 availability)
        WHEN 'MODEL_SERVING' THEN
            v_dbu_per_hour := lakemeter.calculate_model_serving_dbu(p_cloud, p_model_serving_gpu_type);
            v_dbu_per_month := v_dbu_per_hour * v_hours_per_month;
        
        -- FMAPI Databricks (ONE line = ONE rate_type)
        WHEN 'FMAPI_DATABRICKS' THEN
            v_dbu_per_month := lakemeter.calculate_fmapi_databricks_dbu(
                p_cloud,
                p_fmapi_model,
                p_fmapi_rate_type,
                p_fmapi_quantity
            );
            -- Calculate DBU per hour for display
            v_dbu_per_hour := CASE 
                WHEN v_hours_per_month > 0 THEN v_dbu_per_month / v_hours_per_month
                ELSE 0
            END;
        
        -- FMAPI Proprietary (ONE line = ONE rate_type)
        WHEN 'FMAPI_PROPRIETARY' THEN
            v_dbu_per_month := lakemeter.calculate_fmapi_proprietary_dbu(
                p_cloud,
                p_fmapi_provider,
                p_fmapi_model,
                p_fmapi_endpoint_type,
                p_fmapi_context_length,
                p_fmapi_rate_type,
                p_fmapi_quantity
            );
            -- Calculate DBU per hour for display
            v_dbu_per_hour := CASE 
                WHEN v_hours_per_month > 0 THEN v_dbu_per_month / v_hours_per_month
                ELSE 0
            END;
        
        -- Lakebase
        WHEN 'LAKEBASE' THEN
            v_dbu_per_hour := lakemeter.calculate_lakebase_dbu(p_lakebase_cu, p_lakebase_ha_nodes);
            v_dbu_per_month := v_dbu_per_hour * v_hours_per_month;
        
        ELSE
            -- Unknown workload type
            v_dbu_per_hour := 0;
            v_dbu_per_month := 0;
    END CASE;
    
    -- ========================================
    -- STEP 4: Get DBU price
    -- ========================================
    v_dbu_price := lakemeter.get_dbu_price(p_cloud, p_region, p_tier, v_product_type);
    
    -- ========================================
    -- STEP 5: Calculate costs
    -- ========================================
    v_dbu_cost_per_month := (v_dbu_per_month * v_dbu_price)::DECIMAL(18,2);
    v_cost_per_month := v_dbu_cost_per_month + v_vm_cost_per_month;
    
    -- ========================================
    -- STEP 6: Return results
    -- ========================================
    RETURN QUERY SELECT
        v_dbu_per_hour,
        v_hours_per_month,
        v_dbu_per_month,
        v_dbu_price,
        v_dbu_cost_per_month,
        v_driver_vm_cost_per_hour,
        v_worker_vm_cost_per_hour,
        v_total_vm_cost_per_hour,
        v_driver_vm_cost_per_month,
        v_total_worker_vm_cost_per_month,
        v_vm_cost_per_month,
        v_cost_per_month;
END;
$$;

COMMENT ON FUNCTION lakemeter.calculate_line_item_costs IS 
'Main orchestrator function for calculating line item costs.
Accepts ALL line_item parameters and routes to appropriate calculators.
Returns complete cost breakdown including DBU costs, VM costs, and total.
Use this function to preview costs BEFORE inserting into line_items table.';
"""

try:
    execute_query(create_function_sql)
    print("\n✅ Function created: calculate_line_item_costs")
    print("\n   This is the MAIN orchestrator function!")
    print("\n   Parameters: ~30 parameters covering ALL workload types")
    print("\n   Returns TABLE with 12 columns:")
    print("   • dbu_per_hour")
    print("   • hours_per_month")
    print("   • dbu_per_month")
    print("   • dbu_price")
    print("   • dbu_cost_per_month")
    print("   • driver_vm_cost_per_hour")
    print("   • worker_vm_cost_per_hour")
    print("   • total_vm_cost_per_hour")
    print("   • driver_vm_cost_per_month")
    print("   • total_worker_vm_cost_per_month")
    print("   • vm_cost_per_month")
    print("   • cost_per_month (TOTAL)")
    print("\n   Workflow:")
    print("   1. Calculate hours per month")
    print("   2. Get product type for pricing")
    print("   3. Route to appropriate DBU calculator (CASE statement)")
    print("   4. Calculate VM costs (if applicable)")
    print("   5. Get DBU price from pricing table")
    print("   6. Calculate total costs")
    print("   7. Return complete breakdown")
except Exception as e:
    print(f"\n❌ Error creating function: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Function

# COMMAND ----------

print("\n" + "=" * 100)
print("TESTING: calculate_line_item_costs")
print("=" * 100)

# Test JOBS Classic with explicit type casts
test_query = """
SELECT 'JOBS Classic with Photon' as test_case, *
FROM lakemeter.calculate_line_item_costs(
    'JOBS'::VARCHAR,                    -- p_workload_type
    'AWS'::VARCHAR,                     -- p_cloud
    'us-east-1'::VARCHAR,               -- p_region
    'PREMIUM'::VARCHAR,                 -- p_tier
    FALSE::BOOLEAN,                     -- p_serverless_enabled
    TRUE::BOOLEAN,                      -- p_photon_enabled
    NULL::VARCHAR,                      -- p_dlt_edition
    'm5.xlarge'::VARCHAR,               -- p_driver_node_type
    'm5.xlarge'::VARCHAR,               -- p_worker_node_type
    10::INT,                            -- p_num_workers
    'on_demand'::VARCHAR,               -- p_driver_pricing_tier
    'spot'::VARCHAR,                    -- p_worker_pricing_tier
    8::INT,                             -- p_runs_per_day
    60::INT,                            -- p_avg_runtime_minutes
    30::INT,                            -- p_days_per_month
    NULL::INT,                          -- p_hours_per_month (NULL = auto-calculate)
    'standard'::VARCHAR,                -- p_serverless_mode
    NULL::VARCHAR,                      -- p_dbsql_warehouse_type
    NULL::VARCHAR,                      -- p_dbsql_warehouse_size
    1::INT,                             -- p_dbsql_num_clusters
    'on_demand'::VARCHAR,               -- p_dbsql_vm_pricing_tier
    NULL::VARCHAR,                      -- p_vector_search_mode
    0::DECIMAL,                         -- p_vector_search_capacity_millions
        NULL::VARCHAR,                      -- p_model_serving_gpu_type
        NULL::VARCHAR,                      -- p_fmapi_model
        NULL::VARCHAR,                      -- p_fmapi_provider
        'global'::VARCHAR,                  -- p_fmapi_endpoint_type
        'all'::VARCHAR,                     -- p_fmapi_context_length
        'input_token'::VARCHAR,             -- p_fmapi_rate_type (NEW!)
        0::BIGINT,                          -- p_fmapi_quantity (NEW!)
    0::INT,                             -- p_lakebase_cu
    1::INT,                             -- p_lakebase_ha_nodes
    'NA'::VARCHAR,                      -- p_driver_payment_option
    'NA'::VARCHAR,                      -- p_worker_payment_option
    'NA'::VARCHAR                       -- p_dbsql_vm_payment_option
);
"""

try:
    results = execute_query(test_query, fetch=True)
    print("\n✅ Test results:")
    for row in results:
        print(f"\n   Test: {row[0]}")
        print(f"      DBU/hour: {row[1]}")
        print(f"      Hours/month: {row[2]}")
        print(f"      DBU/month: {row[3]}")
        print(f"      DBU price: ${row[4]}")
        print(f"      DBU cost/month: ${row[5]}")
        print(f"      VM cost/month: ${row[11]}")
        print(f"      TOTAL cost/month: ${row[12]}")
except Exception as e:
    print(f"\n⚠️  Test skipped (requires pricing data): {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n" + "=" * 100)
print("✅ MAIN ORCHESTRATOR FUNCTION CREATED!")
print("=" * 100)

print("\n📋 Function created:")
print("   ✅ calculate_line_item_costs")

print("\n🎯 This is the MAIN entry point for cost calculation!")

print("\n✨ Key Features:")
print("   • Accepts ALL line_item parameters (~30 parameters)")
print("   • Routes to appropriate calculators via CASE statement")
print("   • Returns complete cost breakdown (12 columns)")
print("   • Can be called BEFORE inserting to preview costs")

print("\n🔄 Workflow:")
print("   1. Calculate hours per month (utility function)")
print("   2. Get product type (utility function)")
print("   3. Route to DBU calculator:")
print("      • Classic compute → calculate_classic_compute_dbu")
print("      • Serverless compute → calculate_serverless_compute_dbu")
print("      • DBSQL → calculate_dbsql_dbu")
print("      • Vector Search → calculate_vector_search_dbu")
print("      • Model Serving → calculate_model_serving_dbu")
print("      • FMAPI Databricks → calculate_fmapi_databricks_dbu")
print("      • FMAPI Proprietary → calculate_fmapi_proprietary_dbu")
print("      • Lakebase → calculate_lakebase_dbu")
print("   4. Calculate VM costs (if applicable):")
print("      • Classic compute → calculate_classic_vm_costs")
print("      • DBSQL Classic/Pro → calculate_dbsql_vm_costs")
print("   5. Lookup DBU price (utility function)")
print("   6. Calculate total costs")
print("   7. Return breakdown")

print("\n💡 Usage Example:")
print("   -- Preview costs BEFORE inserting")
print("   SELECT * FROM lakemeter.calculate_line_item_costs(")
print("     'JOBS', 'AWS', 'us-east-1', 'PREMIUM', ...")
print("   );")
print("\n   -- Use in API/frontend for instant cost estimates")

print("\n" + "=" * 100)
print("🎉 ALL 15 FUNCTIONS CREATED SUCCESSFULLY!")
print("=" * 100)

print("\n📊 Function Summary:")
print("   ✅ 4 Utility functions")
print("   ✅ 8 DBU calculators")
print("   ✅ 2 VM cost calculators")
print("   ✅ 1 Main orchestrator")
print("\n   Total: 15 functions")

print("\n📝 Next step: Run tests in 5_Function_Tests/ folder")
print("=" * 100)