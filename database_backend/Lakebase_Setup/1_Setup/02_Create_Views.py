# Databricks notebook source
# MAGIC %md
# MAGIC # Lakemeter - Create Cost Calculation Views
# MAGIC 
# MAGIC **Purpose:** Creates views for cost calculation and aggregation
# MAGIC 
# MAGIC **Connects to:** Lakebase (PostgreSQL)
# MAGIC 
# MAGIC **Views Created:**
# MAGIC - `v_line_items_with_costs` - Calculates DBU and VM costs for each line item
# MAGIC - `v_estimates_with_totals` - Aggregates costs per estimate
# MAGIC 
# MAGIC **Prerequisites:**
# MAGIC 1. ✅ 01_Create_Tables must be run first
# MAGIC 2. ✅ Pricing_Sync notebooks must be run (creates sync_* tables)
# MAGIC 3. ✅ 04_Add_Sync_Constraints (optional - for region/instance validation)
# MAGIC 
# MAGIC **Run Order:**
# MAGIC 1. 01_Create_Tables.py
# MAGIC 2. Pricing_Sync notebooks
# MAGIC 3. 04_Add_Sync_Constraints.py (optional)
# MAGIC 4. **This notebook**

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Install Dependencies & Connect to Lakebase

# COMMAND ----------

# Install required packages
%pip install psycopg2-binary --quiet
dbutils.library.restartPython()

# COMMAND ----------

import psycopg2
from datetime import datetime

# Lakebase connection details
LAKEBASE_HOST = "instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com"
LAKEBASE_PORT = 5432
LAKEBASE_DATABASE = "lakemeter_pricing"
LAKEBASE_USER = "lakemeter_sync_role"
LAKEBASE_PASSWORD = dbutils.secrets.get(scope="lakemeter-credentials", key="lakebase-password")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Helper Functions

# COMMAND ----------

def get_connection():
    """Create PostgreSQL connection"""
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DATABASE,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD,
        sslmode='require'
    )

def execute_sql(sql_statement, description="SQL", show_error=True):
    """Execute SQL statement and return success/failure"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql_statement)
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ {description}")
        return True
    except Exception as e:
        if show_error:
            print(f"❌ {description}")
            print(f"   Error: {str(e)}")
        else:
            print(f"⚠️  {description} - {str(e)[:50]}...")
        return False

def query_sql(sql_statement):
    """Execute query and return results"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql_statement)
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Test Connection

# COMMAND ----------

try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    cur.close()
    conn.close()
    print("✅ Connected to Lakebase!")
    print(f"   PostgreSQL version: {version[:50]}...")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Check Prerequisites

# COMMAND ----------

print("=" * 80)
print("🔍 CHECKING PREREQUISITES")
print("=" * 80)

required_tables = [
    ('lakemeter.estimates', 'Application table'),
    ('lakemeter.line_items', 'Application table'),
    ('lakemeter.sync_ref_instance_dbu_rates', 'Pricing sync table'),
    ('lakemeter.sync_ref_dbu_multipliers', 'Pricing sync table'),
    ('lakemeter.sync_pricing_dbu_rates', 'Pricing sync table'),
    ('lakemeter.sync_pricing_vm_costs', 'Pricing sync table'),
    ('lakemeter.sync_product_dbsql_rates', 'Pricing sync table'),
    ('lakemeter.sync_product_serverless_rates', 'Pricing sync table'),
    ('lakemeter.sync_product_fmapi_databricks', 'Pricing sync table'),
    ('lakemeter.sync_product_fmapi_proprietary', 'Pricing sync table'),
]

all_tables_exist = True

for table_name, table_type in required_tables:
    schema, table = table_name.split('.')
    check_sql = f"""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = '{schema}' 
        AND table_name = '{table}'
    );
    """
    result = query_sql(check_sql)
    exists = result[0][0] if result else False
    
    if exists:
        print(f"   ✅ {table_name} ({table_type})")
    else:
        print(f"   ❌ {table_name} ({table_type}) - MISSING!")
        all_tables_exist = False

if not all_tables_exist:
    print("\n" + "=" * 80)
    print("❌ ERROR: Required tables are missing!")
    print("=" * 80)
    print("\n📋 Next Steps:")
    print("   1. Run 01_Create_Tables.py if application tables are missing")
    print("   2. Run Pricing_Sync notebooks if sync_* tables are missing")
    print("=" * 80)
    raise Exception("Prerequisites not met. Cannot create views.")
else:
    print("\n✅ All prerequisites met!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Drop Existing Views

# COMMAND ----------

print("\n" + "=" * 80)
print("⚠️  DROP VIEWS SECTION DISABLED")
print("=" * 80)
print("✅ SKIPPED: Using CREATE OR REPLACE VIEW instead to prevent data loss.")
print("=" * 80)

# # ========================================================================
# # ⛔ COMMENTED OUT TO PREVENT ACCIDENTAL VIEW DROPS
# # ========================================================================
# # execute_sql(
# #     "DROP VIEW IF EXISTS lakemeter.v_estimates_with_totals CASCADE;",
# #     "Drop v_estimates_with_totals",
# #     show_error=False
# # )
# #
# # execute_sql(
# #     "DROP VIEW IF EXISTS lakemeter.v_line_items_with_costs CASCADE;",
# #     "Drop v_line_items_with_costs",
# #     show_error=False
# # )
# # ========================================================================

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Create View: v_line_items_with_costs

# COMMAND ----------

print("\n" + "=" * 80)
print("📊 CREATING VIEW: v_line_items_with_costs")
print("=" * 80)
print("This view calculates:")
print("  - DBU per hour (based on workload type)")
print("  - VM costs per hour (driver + workers)")
print("  - Total cost per month (DBU + VM)")
print("  - Handles all workload types (JOBS, DLT, DBSQL, etc.)")
print("=" * 80)

# COMMAND ----------

# The view SQL is large, so we'll define it in a multi-line string
create_view_line_items_sql = """
CREATE OR REPLACE VIEW lakemeter.v_line_items_with_costs AS
WITH 
-- Calculate hours per month for each line item
hours_calc AS (
    SELECT 
        li.*,
        -- Note: li.cloud is auto-synced from e.cloud via trigger, so we don't need e.cloud here
        -- Only get region and tier from estimates (not in line_items)
        e.region,
        e.tier,
        -- Hours calculation: runs_per_day * (avg_runtime_minutes / 60) * days_per_month
        -- Consistent formula for all hourly workloads
        CASE 
            WHEN li.workload_type NOT IN ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY') THEN
                COALESCE(li.runs_per_day, 0) * (COALESCE(li.avg_runtime_minutes, 0) / 60.0) * COALESCE(li.days_per_month, 30)
            ELSE 0
        END as hours_per_month
    FROM lakemeter.line_items li
    JOIN lakemeter.estimates e ON li.estimate_id = e.estimate_id
),

-- Get DBU rates for classic compute (driver + workers) - used for sizing estimation
classic_compute AS (
    SELECT 
        h.*,
        -- Instance DBU rates (used for sizing estimation even when serverless)
        COALESCE(d.dbu_rate, 0) as driver_dbu_rate,
        COALESCE(w.dbu_rate, 0) as worker_dbu_rate,
        -- Photon multiplier (only applies to classic, serverless always uses Photon)
        CASE 
            WHEN h.serverless_enabled THEN 1.0  -- Serverless: no multiplier (Photon included)
            ELSE COALESCE(m.multiplier, 1.0)    -- Classic: apply multiplier
        END as photon_multiplier
    FROM hours_calc h
    LEFT JOIN lakemeter.sync_ref_instance_dbu_rates d 
        ON d.cloud = h.cloud AND d.instance_type = h.driver_node_type
    LEFT JOIN lakemeter.sync_ref_instance_dbu_rates w 
        ON w.cloud = h.cloud AND w.instance_type = h.worker_node_type
    LEFT JOIN lakemeter.sync_ref_dbu_multipliers m 
        ON h.serverless_enabled = FALSE
        AND m.cloud = h.cloud
        AND m.feature = CASE WHEN h.photon_enabled THEN 'photon' ELSE 'standard' END
        AND m.sku_type = CASE 
            WHEN h.workload_type = 'DLT' THEN 'DLT_' || COALESCE(h.dlt_edition, 'CORE') || '_COMPUTE'
            WHEN h.workload_type = 'JOBS' THEN 'JOBS_COMPUTE'
            WHEN h.workload_type = 'ALL_PURPOSE' THEN 'ALL_PURPOSE_COMPUTE'
            ELSE 'JOBS_COMPUTE'
        END
),

-- Calculate DBU per hour based on workload type
dbu_calc AS (
    SELECT 
        c.*,
        CASE 
            -- Classic compute
            WHEN c.workload_type IN ('ALL_PURPOSE', 'JOBS', 'DLT') AND c.serverless_enabled = FALSE THEN
                (c.driver_dbu_rate + (c.worker_dbu_rate * COALESCE(c.num_workers, 0))) * c.photon_multiplier
            
            -- Serverless compute (standard/performance mode)
            WHEN c.workload_type IN ('ALL_PURPOSE', 'JOBS', 'DLT') AND c.serverless_enabled = TRUE THEN
                (c.driver_dbu_rate + (c.worker_dbu_rate * COALESCE(c.num_workers, 0))) * c.photon_multiplier *
                CASE WHEN COALESCE(c.serverless_mode, 'standard') = 'performance' THEN 2 ELSE 1 END
            
            -- DBSQL
            WHEN c.workload_type = 'DBSQL' THEN
                COALESCE((SELECT dbu_per_hour FROM lakemeter.sync_product_dbsql_rates 
                          WHERE cloud = c.cloud 
                          AND warehouse_type = LOWER(c.dbsql_warehouse_type)
                          AND warehouse_size = c.dbsql_warehouse_size), 0)
                * COALESCE(c.dbsql_num_clusters, 1)
            
            -- Serverless products
            WHEN c.workload_type IN ('VECTOR_SEARCH', 'MODEL_SERVING') THEN
                COALESCE((SELECT dbu_rate FROM lakemeter.sync_product_serverless_rates 
                          WHERE cloud = c.cloud 
                          AND product = LOWER(c.serverless_product)
                          AND size_or_model = c.serverless_size), 0)
            
            -- Lakebase
            WHEN c.workload_type = 'LAKEBASE' THEN
                COALESCE(c.lakebase_cu, 0)
            
            ELSE 0
        END as dbu_per_hour
    FROM classic_compute c
),

-- Calculate FMAPI token-based DBU
fmapi_calc AS (
    SELECT 
        d.*,
        CASE 
            WHEN d.workload_type = 'FMAPI_DATABRICKS' THEN
                COALESCE((
                    SELECT (d.fmapi_input_tokens_per_month / COALESCE(f.input_divisor, 1000000) * f.dbu_rate)
                    FROM lakemeter.sync_product_fmapi_databricks f 
                    WHERE f.model = d.fmapi_model AND f.rate_type = 'input_token'
                ), 0) +
                COALESCE((
                    SELECT (d.fmapi_output_tokens_per_month / COALESCE(f.input_divisor, 1000000) * f.dbu_rate)
                    FROM lakemeter.sync_product_fmapi_databricks f 
                    WHERE f.model = d.fmapi_model AND f.rate_type = 'output_token'
                ), 0)
            
            WHEN d.workload_type = 'FMAPI_PROPRIETARY' THEN
                COALESCE((
                    SELECT (d.fmapi_input_tokens_per_month / COALESCE(f.input_divisor, 1000000) * f.dbu_rate)
                    FROM lakemeter.sync_product_fmapi_proprietary f 
                    WHERE f.cloud = d.cloud 
                    AND f.provider = d.fmapi_provider 
                    AND f.model = d.fmapi_model 
                    AND f.rate_type = 'input_token'
                    AND f.endpoint_type = COALESCE(d.fmapi_endpoint_type, 'global')
                    AND f.context_length = COALESCE(d.fmapi_context_length, 'standard')
                ), 0) +
                COALESCE((
                    SELECT (d.fmapi_output_tokens_per_month / COALESCE(f.input_divisor, 1000000) * f.dbu_rate)
                    FROM lakemeter.sync_product_fmapi_proprietary f 
                    WHERE f.cloud = d.cloud 
                    AND f.provider = d.fmapi_provider 
                    AND f.model = d.fmapi_model 
                    AND f.rate_type = 'output_token'
                    AND f.endpoint_type = COALESCE(d.fmapi_endpoint_type, 'global')
                    AND f.context_length = COALESCE(d.fmapi_context_length, 'standard')
                ), 0)
            ELSE 0
        END as fmapi_dbu_per_month
    FROM dbu_calc d
),

-- Get product_type for DBU price lookup
product_type_calc AS (
    SELECT 
        f.*,
        CASE 
            WHEN f.workload_type = 'JOBS' THEN
                CASE 
                    WHEN f.serverless_enabled THEN 'JOBS_SERVERLESS_COMPUTE'
                    WHEN f.photon_enabled THEN 'JOBS_COMPUTE_(PHOTON)'
                    ELSE 'JOBS_COMPUTE'
                END
            WHEN f.workload_type = 'ALL_PURPOSE' THEN
                CASE 
                    WHEN f.serverless_enabled THEN 'ALL_PURPOSE_SERVERLESS_COMPUTE'
                    WHEN f.photon_enabled THEN 'ALL_PURPOSE_COMPUTE_(PHOTON)'
                    ELSE 'ALL_PURPOSE_COMPUTE'
                END
            WHEN f.workload_type = 'DLT' THEN
                CASE 
                    WHEN f.serverless_enabled THEN 'JOBS_SERVERLESS_COMPUTE'
                    ELSE 'DLT_' || COALESCE(f.dlt_edition, 'CORE') || '_COMPUTE' || 
                         CASE WHEN f.photon_enabled THEN '_(PHOTON)' ELSE '' END
                END
            WHEN f.workload_type = 'DBSQL' THEN
                CASE f.dbsql_warehouse_type
                    WHEN 'SERVERLESS' THEN 'SERVERLESS_SQL_COMPUTE'
                    WHEN 'PRO' THEN 'SQL_PRO_COMPUTE'
                    ELSE 'SQL_COMPUTE'
                END
            WHEN f.workload_type = 'VECTOR_SEARCH' THEN 'VECTOR_SEARCH_ENDPOINT'
            WHEN f.workload_type = 'MODEL_SERVING' THEN 'SERVERLESS_REAL_TIME_INFERENCE'
            WHEN f.workload_type = 'FMAPI_DATABRICKS' THEN 'SERVERLESS_REAL_TIME_INFERENCE'
            WHEN f.workload_type = 'FMAPI_PROPRIETARY' THEN 
                UPPER(f.fmapi_provider) || '_MODEL_SERVING'
            WHEN f.workload_type = 'LAKEBASE' THEN 'DATABASE_SERVERLESS_COMPUTE'
            ELSE 'JOBS_COMPUTE'
        END as product_type_for_pricing
    FROM fmapi_calc f
),

-- Get DBU price and VM costs
final_calc AS (
    SELECT 
        p.*,
        COALESCE((
            SELECT price_per_dbu FROM lakemeter.sync_pricing_dbu_rates 
            WHERE cloud = p.cloud AND region = p.region AND tier = p.tier
            AND product_type = p.product_type_for_pricing
            LIMIT 1
        ), 0) as price_per_dbu,
        
        -- DRIVER VM cost (cannot be spot)
        CASE WHEN p.workload_type IN ('ALL_PURPOSE', 'JOBS', 'DLT') 
              AND p.serverless_enabled = FALSE THEN
            COALESCE((
                SELECT cost_per_hour FROM lakemeter.sync_pricing_vm_costs 
                WHERE cloud = p.cloud AND region = p.region 
                AND instance_type = p.driver_node_type
                AND pricing_tier = CASE 
                    WHEN COALESCE(p.driver_pricing_tier, p.vm_pricing_tier, 'on_demand') = 'spot' 
                        THEN 'on_demand'
                    ELSE COALESCE(p.driver_pricing_tier, p.vm_pricing_tier, 'on_demand')
                END
                LIMIT 1
            ), 0)
        ELSE 0 END as driver_vm_cost_per_hour,
        
        -- WORKER VM cost (can be spot)
        CASE WHEN p.workload_type IN ('ALL_PURPOSE', 'JOBS', 'DLT') 
              AND p.serverless_enabled = FALSE THEN
            COALESCE((
                SELECT cost_per_hour FROM lakemeter.sync_pricing_vm_costs 
                WHERE cloud = p.cloud AND region = p.region 
                AND instance_type = p.worker_node_type
                AND pricing_tier = COALESCE(p.worker_pricing_tier, p.vm_pricing_tier, 'on_demand')
                LIMIT 1
            ), 0)
        ELSE 0 END as worker_vm_cost_per_hour
    FROM product_type_calc p
)

-- Final SELECT with all calculated costs
SELECT 
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, serverless_mode, driver_node_type, worker_node_type, num_workers,
    autoscale_enabled, autoscale_min_workers, autoscale_max_workers, photon_enabled,
    dlt_edition, dlt_pipeline_mode, dbsql_warehouse_type, dbsql_warehouse_size, dbsql_num_clusters,
    serverless_product, serverless_size, vector_search_mode,
    fmapi_provider, fmapi_model, fmapi_endpoint_type, fmapi_context_length,
    fmapi_input_tokens_per_month, fmapi_output_tokens_per_month,
    lakebase_cu, lakebase_storage_gb, lakebase_ha_enabled, lakebase_backup_retention_days,
    runs_per_day, avg_runtime_minutes, days_per_month,
    driver_pricing_tier, worker_pricing_tier, vm_pricing_tier, vm_payment_option, spot_percentage,
    notes, created_at, updated_at,
    cloud, region, tier,
    hours_per_month,
    driver_dbu_rate, worker_dbu_rate, photon_multiplier,
    dbu_per_hour,
    CASE 
        WHEN workload_type IN ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY') THEN fmapi_dbu_per_month
        ELSE dbu_per_hour * hours_per_month
    END as dbu_per_month,
    price_per_dbu, product_type_for_pricing,
    CASE 
        WHEN workload_type IN ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY') THEN fmapi_dbu_per_month * price_per_dbu
        ELSE dbu_per_hour * hours_per_month * price_per_dbu
    END as dbu_cost_per_month,
    driver_vm_cost_per_hour, worker_vm_cost_per_hour,
    worker_vm_cost_per_hour * COALESCE(num_workers, 0) as total_worker_vm_cost_per_hour,
    driver_vm_cost_per_hour + (worker_vm_cost_per_hour * COALESCE(num_workers, 0)) as total_vm_cost_per_hour,
    driver_vm_cost_per_hour * hours_per_month as driver_vm_cost_per_month,
    (worker_vm_cost_per_hour * COALESCE(num_workers, 0)) * hours_per_month as total_worker_vm_cost_per_month,
    (driver_vm_cost_per_hour + (worker_vm_cost_per_hour * COALESCE(num_workers, 0))) * hours_per_month as vm_cost_per_month,
    CASE 
        WHEN workload_type IN ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY') THEN 
            fmapi_dbu_per_month * price_per_dbu
        ELSE 
            (dbu_per_hour * hours_per_month * price_per_dbu) +
            ((driver_vm_cost_per_hour + (worker_vm_cost_per_hour * COALESCE(num_workers, 0))) * hours_per_month)
    END as cost_per_month,
    fmapi_dbu_per_month
FROM final_calc;
"""

execute_sql(create_view_line_items_sql, "Created v_line_items_with_costs")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Create View: v_estimates_with_totals

# COMMAND ----------

print("\n" + "=" * 80)
print("📊 CREATING VIEW: v_estimates_with_totals")
print("=" * 80)
print("This view aggregates:")
print("  - Total DBU per month (sum of all line items)")
print("  - Total cost per month (sum of all line items)")
print("  - Line item count")
print("=" * 80)

# COMMAND ----------

create_view_estimates_sql = """
CREATE OR REPLACE VIEW lakemeter.v_estimates_with_totals AS
SELECT 
    e.*,
    COALESCE(t.total_dbu_per_month, 0) as total_dbu_per_month,
    COALESCE(t.total_cost_per_month, 0) as total_cost_per_month,
    COALESCE(t.line_item_count, 0) as line_item_count
FROM lakemeter.estimates e
LEFT JOIN (
    SELECT 
        estimate_id,
        SUM(cost_per_month) as total_cost_per_month,
        SUM(dbu_per_month) as total_dbu_per_month,
        COUNT(*) as line_item_count
    FROM lakemeter.v_line_items_with_costs
    GROUP BY estimate_id
) t ON e.estimate_id = t.estimate_id;
"""

execute_sql(create_view_estimates_sql, "Created v_estimates_with_totals")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Verification

# COMMAND ----------

print("\n" + "=" * 80)
print("✅ VERIFICATION: Views Created")
print("=" * 80)

conn = get_connection()
cur = conn.cursor()

# Check views
cur.execute("""
SELECT table_name, view_definition 
FROM information_schema.views 
WHERE table_schema = 'lakemeter' 
AND table_name LIKE 'v_%'
ORDER BY table_name;
""")

views = cur.fetchall()
print(f"\n📊 Views created: {len(views)}")
for view_name, view_def in views:
    print(f"   ✅ {view_name} ({len(view_def)} chars)")

# Test view: v_line_items_with_costs
print("\n📋 Testing v_line_items_with_costs (checking columns):")
cur.execute("""
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'lakemeter' 
AND table_name = 'v_line_items_with_costs'
ORDER BY ordinal_position
LIMIT 10;
""")
columns = cur.fetchall()
for col_name, col_type in columns:
    print(f"   - {col_name} ({col_type})")
print(f"   ... and {len(columns)} more columns")

cur.close()
conn.close()

print("\n" + "=" * 80)
print("🎉 VIEWS CREATED SUCCESSFULLY!")
print("=" * 80)
print("\n📋 Created Views:")
print("   1. v_line_items_with_costs")
print("      - Calculates costs for each line item")
print("      - Includes DBU rates, VM costs, total cost")
print("      - Exposes all intermediate calculations for auditability")
print("")
print("   2. v_estimates_with_totals")
print("      - Aggregates costs per estimate")
print("      - Total DBU, total cost, line item count")
print("")
print("📋 Next Steps:")
print("   - Run test notebooks to validate calculations")
print("   - Query views to verify cost logic")
print("   - Add sample data to line_items table")
print("=" * 80)

