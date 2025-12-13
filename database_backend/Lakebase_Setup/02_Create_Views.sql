-- =============================================================================
-- LAKEBASE VIEWS - Cost Calculation & Aggregation
-- =============================================================================
-- FILE: 02_Create_Views.sql
-- PURPOSE: Create v_line_items_with_costs and v_estimates_with_totals views
-- 
-- ⚠️  PREREQUISITE: Run 01_Create_Tables.sql FIRST!
-- ⚠️  PREREQUISITE: The following sync_* tables MUST exist before running:
--   - sync_ref_instance_dbu_rates
--   - sync_ref_dbu_multipliers
--   - sync_pricing_dbu_rates
--   - sync_pricing_vm_costs (uses pricing_vm_costs VIEW, not direct table)
--   - sync_product_dbsql_rates
--   - sync_product_serverless_rates
--   - sync_product_fmapi_databricks
--   - sync_product_fmapi_proprietary
-- 
-- To create sync tables, run notebooks in Pricing_Sync folder first!
-- =============================================================================

-- =============================================================================
-- DROP EXISTING VIEWS (required when changing column order/names)
-- =============================================================================

DROP VIEW IF EXISTS v_estimates_with_totals CASCADE;
DROP VIEW IF EXISTS v_line_items_with_costs CASCADE;

-- =============================================================================
-- VIEW 1: v_line_items_with_costs
-- =============================================================================
-- Calculates DBU and VM costs for each line item using pricing data
-- Handles all workload types: JOBS, ALL_PURPOSE, DLT, DBSQL, VECTOR_SEARCH,
--   MODEL_SERVING, FMAPI_DATABRICKS, FMAPI_PROPRIETARY, LAKEBASE
-- =============================================================================

CREATE VIEW v_line_items_with_costs AS
WITH 
-- Calculate hours per month for each line item
hours_calc AS (
    SELECT 
        li.*,
        e.cloud,
        e.region,
        e.tier,
        -- Hours calculation: runs_per_day * (avg_runtime_minutes / 60) * days_per_month
        -- Consistent formula for all hourly workloads
        CASE 
            WHEN li.workload_type NOT IN ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY') THEN
                COALESCE(li.runs_per_day, 0) * (COALESCE(li.avg_runtime_minutes, 0) / 60.0) * COALESCE(li.days_per_month, 30)
            ELSE 0
        END as hours_per_month
    FROM line_items li
    JOIN estimates e ON li.estimate_id = e.estimate_id
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
    LEFT JOIN sync_ref_instance_dbu_rates d 
        ON d.cloud = h.cloud AND d.instance_type = h.driver_node_type
    LEFT JOIN sync_ref_instance_dbu_rates w 
        ON w.cloud = h.cloud AND w.instance_type = h.worker_node_type
    LEFT JOIN sync_ref_dbu_multipliers m 
        ON h.serverless_enabled = FALSE  -- Only join multiplier for classic
        AND m.cloud = h.cloud  -- ✅ CRITICAL: Match by cloud (multipliers vary by cloud!)
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
            -- Classic compute (serverless_enabled = false): (driver + workers) × multiplier
            WHEN c.workload_type IN ('ALL_PURPOSE', 'JOBS', 'DLT') AND c.serverless_enabled = FALSE THEN
                (c.driver_dbu_rate + (c.worker_dbu_rate * COALESCE(c.num_workers, 0))) * c.photon_multiplier
            
            -- Serverless compute: Calculate DBU from nodes, then apply serverless mode multiplier
            -- Standard mode: 1x multiplier, Performance mode: 2x multiplier
            WHEN c.workload_type IN ('ALL_PURPOSE', 'JOBS', 'DLT') AND c.serverless_enabled = TRUE THEN
                (c.driver_dbu_rate + (c.worker_dbu_rate * COALESCE(c.num_workers, 0))) * c.photon_multiplier *
                CASE WHEN COALESCE(c.serverless_mode, 'standard') = 'performance' THEN 2 ELSE 1 END
            
            -- DBSQL: lookup from product_dbsql_rates * num_clusters
            WHEN c.workload_type = 'DBSQL' THEN
                COALESCE((SELECT dbu_per_hour FROM sync_product_dbsql_rates 
                          WHERE cloud = c.cloud 
                          AND warehouse_type = LOWER(c.dbsql_warehouse_type)
                          AND warehouse_size = c.dbsql_warehouse_size), 0)
                * COALESCE(c.dbsql_num_clusters, 1)
            
            -- Serverless products: lookup from product_serverless_rates
            WHEN c.workload_type IN ('VECTOR_SEARCH', 'MODEL_SERVING') THEN
                COALESCE((SELECT dbu_rate FROM sync_product_serverless_rates 
                          WHERE cloud = c.cloud 
                          AND product = LOWER(c.serverless_product)
                          AND size_or_model = c.serverless_size), 0)
            
            -- LAKEBASE: Direct CU to DBU conversion (1 CU = 1 DBU per hour)
            WHEN c.workload_type = 'LAKEBASE' THEN
                COALESCE(c.lakebase_cu, 0)  -- Simple: CU value IS the DBU per hour
            
            -- FMAPI: calculated from tokens, not hourly (handled separately)
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
                    FROM sync_product_fmapi_databricks f 
                    WHERE f.model = d.fmapi_model AND f.rate_type = 'input_token'
                ), 0) +
                COALESCE((
                    SELECT (d.fmapi_output_tokens_per_month / COALESCE(f.input_divisor, 1000000) * f.dbu_rate)
                    FROM sync_product_fmapi_databricks f 
                    WHERE f.model = d.fmapi_model AND f.rate_type = 'output_token'
                ), 0)
            
            WHEN d.workload_type = 'FMAPI_PROPRIETARY' THEN
                COALESCE((
                    SELECT (d.fmapi_input_tokens_per_month / COALESCE(f.input_divisor, 1000000) * f.dbu_rate)
                    FROM sync_product_fmapi_proprietary f 
                    WHERE f.cloud = d.cloud 
                    AND f.provider = d.fmapi_provider 
                    AND f.model = d.fmapi_model 
                    AND f.rate_type = 'input_token'
                    AND f.endpoint_type = COALESCE(d.fmapi_endpoint_type, 'global')
                    AND f.context_length = COALESCE(d.fmapi_context_length, 'standard')
                ), 0) +
                COALESCE((
                    SELECT (d.fmapi_output_tokens_per_month / COALESCE(f.input_divisor, 1000000) * f.dbu_rate)
                    FROM sync_product_fmapi_proprietary f 
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
            -- JOBS: Classic vs Serverless
            WHEN f.workload_type = 'JOBS' THEN
                CASE 
                    WHEN f.serverless_enabled THEN 'JOBS_SERVERLESS_COMPUTE'
                    WHEN f.photon_enabled THEN 'JOBS_COMPUTE_(PHOTON)'
                    ELSE 'JOBS_COMPUTE'
                END
            
            -- ALL_PURPOSE: Classic vs Serverless
            WHEN f.workload_type = 'ALL_PURPOSE' THEN
                CASE 
                    WHEN f.serverless_enabled THEN 'INTERACTIVE_SERVERLESS_COMPUTE'
                    WHEN f.photon_enabled THEN 'ALL_PURPOSE_COMPUTE_(PHOTON)'
                    ELSE 'ALL_PURPOSE_COMPUTE'
                END
            
            -- DLT: Classic vs Serverless (with edition)
            WHEN f.workload_type = 'DLT' THEN
                CASE 
                    WHEN f.serverless_enabled THEN 'DELTA_LIVE_TABLES_SERVERLESS'
                    ELSE 'DLT_' || COALESCE(f.dlt_edition, 'CORE') || '_COMPUTE' || 
                         CASE WHEN f.photon_enabled THEN '_(PHOTON)' ELSE '' END
                END
            
            -- DBSQL: Uses warehouse_type for serverless
            WHEN f.workload_type = 'DBSQL' THEN
                CASE f.dbsql_warehouse_type
                    WHEN 'SERVERLESS' THEN 'SERVERLESS_SQL_COMPUTE'
                    WHEN 'PRO' THEN 'SQL_PRO_COMPUTE'
                    ELSE 'SQL_COMPUTE'
                END
            
            -- Serverless-only products
            WHEN f.workload_type = 'VECTOR_SEARCH' THEN 'VECTOR_SEARCH_ENDPOINT'
            WHEN f.workload_type = 'MODEL_SERVING' THEN 'SERVERLESS_REAL_TIME_INFERENCE'
            WHEN f.workload_type = 'FMAPI_DATABRICKS' THEN 'SERVERLESS_REAL_TIME_INFERENCE'
            WHEN f.workload_type = 'FMAPI_PROPRIETARY' THEN 
                UPPER(f.fmapi_provider) || '_MODEL_SERVING'  -- e.g., ANTHROPIC_MODEL_SERVING
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
            SELECT price_per_dbu FROM sync_pricing_dbu_rates 
            WHERE cloud = p.cloud AND region = p.region AND tier = p.tier
            AND product_type = p.product_type_for_pricing
            LIMIT 1
        ), 0) as price_per_dbu,
        
        -- VM costs (ONLY for classic compute - NOT serverless)
        -- When serverless_enabled = true, VM cost is $0 (no VMs charged)
        
        -- DRIVER: Uses driver_pricing_tier (or falls back to vm_pricing_tier)
        -- Driver CANNOT use spot - if spot specified, defaults to on_demand
        CASE WHEN p.workload_type IN ('ALL_PURPOSE', 'JOBS', 'DLT') 
              AND p.serverless_enabled = FALSE THEN
            COALESCE((
                SELECT cost_per_hour FROM sync_pricing_vm_costs 
                WHERE cloud = p.cloud AND region = p.region 
                AND instance_type = p.driver_node_type
                AND pricing_tier = CASE 
                    -- Use driver_pricing_tier if set, else fall back to vm_pricing_tier
                    WHEN COALESCE(p.driver_pricing_tier, p.vm_pricing_tier, 'on_demand') = 'spot' 
                        THEN 'on_demand'  -- Driver cannot be spot
                    ELSE COALESCE(p.driver_pricing_tier, p.vm_pricing_tier, 'on_demand')
                END
                LIMIT 1
            ), 0)
        ELSE 0 END as driver_vm_cost_per_hour,
        
        -- WORKER: Uses worker_pricing_tier (or falls back to vm_pricing_tier)
        -- Worker CAN use spot pricing
        CASE WHEN p.workload_type IN ('ALL_PURPOSE', 'JOBS', 'DLT') 
              AND p.serverless_enabled = FALSE THEN
            COALESCE((
                SELECT cost_per_hour FROM sync_pricing_vm_costs 
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
    -- Original line item fields
    line_item_id,
    estimate_id,
    display_order,
    workload_name,
    workload_type,
    serverless_enabled,
    serverless_mode,
    driver_node_type,
    worker_node_type,
    num_workers,
    autoscale_enabled,
    autoscale_min_workers,
    autoscale_max_workers,
    photon_enabled,
    dlt_edition,
    dlt_pipeline_mode,
    dbsql_warehouse_type,
    dbsql_warehouse_size,
    dbsql_num_clusters,
    serverless_product,
    serverless_size,
    vector_search_mode,
    fmapi_provider,
    fmapi_model,
    fmapi_endpoint_type,
    fmapi_context_length,
    fmapi_input_tokens_per_month,
    fmapi_output_tokens_per_month,
    lakebase_cu,
    lakebase_storage_gb,
    lakebase_ha_enabled,
    lakebase_backup_retention_days,
    runs_per_day,
    avg_runtime_minutes,
    days_per_month,
    driver_pricing_tier,
    worker_pricing_tier,
    vm_pricing_tier,
    vm_payment_option,
    spot_percentage,
    notes,
    created_at,
    updated_at,
    
    -- Estimate context
    cloud,
    region,
    tier,
    
    -- CALCULATED FIELDS - Usage
    hours_per_month,
    
    -- CALCULATED FIELDS - DBU Rates (for auditability)
    driver_dbu_rate,
    worker_dbu_rate,
    photon_multiplier,
    
    -- CALCULATED FIELDS - DBU Calculation
    dbu_per_hour,
    
    -- DBU per month (hourly workloads vs token-based)
    CASE 
        WHEN workload_type IN ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY') THEN fmapi_dbu_per_month
        ELSE dbu_per_hour * hours_per_month
    END as dbu_per_month,
    
    -- CALCULATED FIELDS - Pricing
    price_per_dbu,
    product_type_for_pricing,
    
    -- DBU cost per month
    CASE 
        WHEN workload_type IN ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY') THEN fmapi_dbu_per_month * price_per_dbu
        ELSE dbu_per_hour * hours_per_month * price_per_dbu
    END as dbu_cost_per_month,
    
    -- CALCULATED FIELDS - VM Costs (for auditability)
    driver_vm_cost_per_hour,
    worker_vm_cost_per_hour,
    
    -- VM cost breakdown - per hour
    worker_vm_cost_per_hour * COALESCE(num_workers, 0) as total_worker_vm_cost_per_hour,
    driver_vm_cost_per_hour + (worker_vm_cost_per_hour * COALESCE(num_workers, 0)) as total_vm_cost_per_hour,
    
    -- VM cost breakdown - per month
    driver_vm_cost_per_hour * hours_per_month as driver_vm_cost_per_month,
    (worker_vm_cost_per_hour * COALESCE(num_workers, 0)) * hours_per_month as total_worker_vm_cost_per_month,
    (driver_vm_cost_per_hour + (worker_vm_cost_per_hour * COALESCE(num_workers, 0))) * hours_per_month as vm_cost_per_month,
    
    -- CALCULATED FIELDS - Total Cost
    CASE 
        WHEN workload_type IN ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY') THEN 
            fmapi_dbu_per_month * price_per_dbu
        ELSE 
            (dbu_per_hour * hours_per_month * price_per_dbu) +
            ((driver_vm_cost_per_hour + (worker_vm_cost_per_hour * COALESCE(num_workers, 0))) * hours_per_month)
    END as cost_per_month,
    
    -- CALCULATED FIELDS - FMAPI Token-based (for auditability)
    fmapi_dbu_per_month

FROM final_calc;

-- =============================================================================
-- VIEW 2: v_estimates_with_totals
-- =============================================================================
-- Aggregates costs from line items. MUST be created AFTER v_line_items_with_costs.
-- Usage: SELECT * FROM v_estimates_with_totals WHERE owner_user_id = :user_id
-- =============================================================================

CREATE VIEW v_estimates_with_totals AS
SELECT 
    e.*,
    COALESCE(t.total_dbu_per_month, 0) as total_dbu_per_month,
    COALESCE(t.total_cost_per_month, 0) as total_cost_per_month,
    COALESCE(t.line_item_count, 0) as line_item_count
FROM estimates e
LEFT JOIN (
    SELECT 
        estimate_id,
        SUM(cost_per_month) as total_cost_per_month,
        SUM(dbu_per_month) as total_dbu_per_month,
        COUNT(*) as line_item_count
    FROM v_line_items_with_costs
    GROUP BY estimate_id
) t ON e.estimate_id = t.estimate_id;

-- =============================================================================
-- VIEWS CREATED SUCCESSFULLY
-- =============================================================================
-- ✅ v_line_items_with_costs: Calculates costs for each line item
-- ✅ v_estimates_with_totals: Aggregates costs per estimate
-- 
-- To verify:
--   SELECT * FROM v_line_items_with_costs LIMIT 5;
--   SELECT * FROM v_estimates_with_totals LIMIT 5;
-- =============================================================================

