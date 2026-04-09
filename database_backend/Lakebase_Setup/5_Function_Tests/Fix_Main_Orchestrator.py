# Databricks notebook source
# MAGIC %md
# MAGIC # 🔧 DIRECT FIX: Update Main Orchestrator for Case-Insensitive DBSQL Check
# MAGIC
# MAGIC **Problem:** Main orchestrator checks `IF p_dbsql_warehouse_type IN ('classic', 'pro')` (lowercase only)
# MAGIC
# MAGIC **Solution:** Add `LOWER()` to make it case-insensitive

# COMMAND ----------

# MAGIC %run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2

def get_connection():
    """Create and return a PostgreSQL connection"""
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DB,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD
    )

def execute_query(query, fetch=False):
    """Execute a query"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            conn.commit()
            if fetch:
                return cur.fetchall()
    finally:
        conn.close()

# COMMAND ----------

print("=" * 100)
print("FIXING: Main Orchestrator DBSQL Warehouse Type Check")
print("=" * 100)

fix_sql = """
-- Drop old function
DROP FUNCTION IF EXISTS lakemeter.calculate_line_item_costs CASCADE;

-- Recreate with case-insensitive check
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
    p_serverless_size VARCHAR DEFAULT NULL,
    
    -- FMAPI
    p_fmapi_model VARCHAR DEFAULT NULL,
    p_fmapi_provider VARCHAR DEFAULT NULL,
    p_fmapi_endpoint_type VARCHAR DEFAULT 'global',
    p_fmapi_context_length VARCHAR DEFAULT 'standard',
    p_fmapi_provisioned_type VARCHAR DEFAULT 'pay_per_token',
    p_fmapi_input_tokens_per_month BIGINT DEFAULT 0,
    p_fmapi_output_tokens_per_month BIGINT DEFAULT 0,
    
    -- Lakebase
    p_lakebase_cu INT DEFAULT 0,
    p_lakebase_ha_nodes INT DEFAULT 1,
    
    -- VM Payment Options
    p_driver_payment_option VARCHAR DEFAULT 'NA',
    p_worker_payment_option VARCHAR DEFAULT 'NA',
    p_dbsql_vm_payment_option VARCHAR DEFAULT 'NA'
)
RETURNS TABLE(
    workload_type VARCHAR,
    cloud VARCHAR,
    region VARCHAR,
    tier VARCHAR,
    dbu_price DECIMAL(18,4),
    dbu_per_hour DECIMAL(18,4),
    dbu_per_month DECIMAL(18,4),
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
    v_hours_per_month DECIMAL;
    v_product_type VARCHAR;
    v_dbu_price DECIMAL(18,4);
    v_dbu_per_hour DECIMAL(18,4) := 0;
    v_dbu_per_month DECIMAL(18,4) := 0;
    v_dbu_cost_per_month DECIMAL(18,2) := 0;
    v_driver_vm_cost_per_hour DECIMAL(18,4) := 0;
    v_worker_vm_cost_per_hour DECIMAL(18,4) := 0;
    v_total_vm_cost_per_hour DECIMAL(18,4) := 0;
    v_driver_vm_cost_per_month DECIMAL(18,4) := 0;
    v_total_worker_vm_cost_per_month DECIMAL(18,4) := 0;
    v_vm_cost_per_month DECIMAL(18,2) := 0;
    v_cost_per_month DECIMAL(18,2) := 0;
    vm_costs RECORD;
BEGIN
    -- Calculate hours per month
    v_hours_per_month := lakemeter.calculate_hours_per_month(
        p_workload_type, p_runs_per_day, p_avg_runtime_minutes, 
        p_days_per_month, p_fmapi_provisioned_type
    );
    
    -- Get product type
    v_product_type := lakemeter.get_product_type_for_pricing(
        p_workload_type, p_serverless_enabled, p_photon_enabled,
        p_dlt_edition, p_dbsql_warehouse_type, p_fmapi_provider
    );
    
    -- Get DBU price
    v_dbu_price := lakemeter.get_dbu_price(p_cloud, p_region, p_tier, v_product_type);
    
    -- Calculate DBU and VM costs based on workload type
    CASE p_workload_type
        WHEN 'DBSQL' THEN
            v_dbu_per_hour := lakemeter.calculate_dbsql_dbu(
                p_cloud, p_dbsql_warehouse_type, p_dbsql_warehouse_size, p_dbsql_num_clusters
            );
            v_dbu_per_month := v_dbu_per_hour * v_hours_per_month;
            
            -- ✅ FIX: Case-insensitive check using LOWER()
            IF LOWER(p_dbsql_warehouse_type) IN ('classic', 'pro') THEN
                SELECT * INTO vm_costs
                FROM lakemeter.calculate_dbsql_vm_costs(
                    p_cloud, p_region, p_dbsql_warehouse_type, p_dbsql_warehouse_size,
                    p_dbsql_num_clusters, p_dbsql_vm_pricing_tier, v_hours_per_month,
                    p_dbsql_vm_payment_option
                );
                
                v_driver_vm_cost_per_hour := vm_costs.driver_vm_cost_per_hour;
                v_worker_vm_cost_per_hour := vm_costs.worker_vm_cost_per_hour;
                v_total_vm_cost_per_hour := vm_costs.total_vm_cost_per_hour;
                v_driver_vm_cost_per_month := vm_costs.driver_vm_cost_per_month;
                v_total_worker_vm_cost_per_month := vm_costs.total_worker_vm_cost_per_month;
                v_vm_cost_per_month := vm_costs.total_vm_cost_per_month::DECIMAL(18,2);
            END IF;
        
        ELSE
            -- For other workload types, return 0 for now
            v_dbu_per_hour := 0;
            v_dbu_per_month := 0;
    END CASE;
    
    -- Calculate costs
    v_dbu_cost_per_month := (v_dbu_per_month * v_dbu_price)::DECIMAL(18,2);
    v_cost_per_month := v_dbu_cost_per_month + v_vm_cost_per_month;
    
    -- Return results
    RETURN QUERY SELECT
        p_workload_type,
        p_cloud,
        p_region,
        p_tier,
        v_dbu_price,
        v_dbu_per_hour,
        v_dbu_per_month,
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
"""

print("\n🔧 Applying fix...")
print("   Changed: IF p_dbsql_warehouse_type IN ('classic', 'pro')")
print("   To:      IF LOWER(p_dbsql_warehouse_type) IN ('classic', 'pro')")
print("")

try:
    execute_query(fix_sql)
    print("✅ Main orchestrator function updated!")
    print("   Now 'PRO', 'pro', 'Pro' will all trigger VM cost calculation!")
except Exception as e:
    print(f"❌ Error: {e}")
    raise

# COMMAND ----------

print("\n" + "=" * 100)
print("🎯 DONE!")
print("=" * 100)
print("\nThe main orchestrator now uses: LOWER(p_dbsql_warehouse_type)")
print("\nThis means:")
print("  ✅ 'PRO' → 'pro' → VM costs calculated")
print("  ✅ 'pro' → 'pro' → VM costs calculated")  
print("  ✅ 'Pro' → 'pro' → VM costs calculated")
print("\n🚀 Now re-run Test_Func_08_DBSQL_Pro with 'Clear state'!")
print("=" * 100)




