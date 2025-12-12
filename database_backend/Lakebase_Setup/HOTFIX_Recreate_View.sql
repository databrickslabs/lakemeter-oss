-- ============================================================================
-- HOTFIX: Recreate v_line_items_with_costs with Cloud Join Fix
-- ============================================================================
-- Run this in Lakebase SQL Editor to update the view with the multiplier fix
-- ============================================================================

-- Drop the old view
DROP VIEW IF EXISTS lakemeter.v_line_items_with_costs CASCADE;

-- Recreate with the fix
CREATE OR REPLACE VIEW lakemeter.v_line_items_with_costs AS

-- Step 1: Calculate hours per month from usage patterns
WITH hours_calc AS (
    SELECT 
        c.line_item_id,
        c.estimate_id,
        c.display_order,
        c.workload_name,
        c.workload_type,
        c.serverless_enabled,
        c.serverless_mode,
        c.driver_node_type,
        c.worker_node_type,
        c.num_workers,
        c.autoscale_enabled,
        c.autoscale_min_workers,
        c.autoscale_max_workers,
        c.photon_enabled,
        c.dlt_edition,
        c.dlt_pipeline_mode,
        c.dbsql_warehouse_type,
        c.dbsql_warehouse_size,
        c.dbsql_num_clusters,
        c.serverless_product,
        c.serverless_size,
        c.vector_search_mode,
        c.fmapi_provider,
        c.fmapi_model,
        c.fmapi_endpoint_type,
        c.fmapi_context_length,
        c.fmapi_input_tokens_per_month,
        c.fmapi_output_tokens_per_month,
        c.lakebase_cu,
        c.lakebase_storage_gb,
        c.lakebase_ha_enabled,
        c.lakebase_backup_retention_days,
        c.runs_per_day,
        c.avg_runtime_minutes,
        c.days_per_month,
        c.vm_pricing_tier,
        c.vm_payment_option,
        c.spot_percentage,
        c.notes,
        c.created_at,
        c.updated_at,
        
        -- Estimate context
        e.cloud,
        e.region,
        e.tier,
        
        -- Calculate hours per month
        COALESCE(c.runs_per_day, 0) * (COALESCE(c.avg_runtime_minutes, 0) / 60.0) * COALESCE(c.days_per_month, 30) as hours_per_month
    FROM lakemeter.line_items c
    JOIN lakemeter.estimates e ON e.estimate_id = c.estimate_id
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
        ON h.serverless_enabled = FALSE  -- Only join multiplier for classic
        AND m.cloud = h.cloud  -- ✅ CRITICAL FIX: Match by cloud!
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
        
        -- Determine which product_type to use for DBU pricing
        CASE 
            -- FMAPI: use endpoint-specific product types
            WHEN c.workload_type = 'FMAPI_PROPRIETARY' THEN 
                CASE 
                    WHEN c.fmapi_provider = 'openai' THEN 'OPENAI_MODEL_SERVING'
                    WHEN c.fmapi_provider = 'anthropic' THEN 'ANTHROPIC_MODEL_SERVING'
                    WHEN c.fmapi_provider = 'google' THEN 'GOOGLE_MODEL_SERVING'
                    ELSE 'SERVERLESS_REAL_TIME_INFERENCE'
                END
            WHEN c.workload_type = 'FMAPI_DATABRICKS' THEN 'SERVERLESS_REAL_TIME_INFERENCE'
            
            -- Serverless workloads: use serverless product types
            WHEN c.serverless_enabled AND c.workload_type = 'JOBS' THEN 'JOBS_SERVERLESS_COMPUTE'
            WHEN c.serverless_enabled AND c.workload_type = 'ALL_PURPOSE' THEN 'INTERACTIVE_SERVERLESS_COMPUTE'
            WHEN c.serverless_enabled AND c.workload_type = 'DLT' THEN 'DELTA_LIVE_TABLES_SERVERLESS'
            WHEN c.workload_type = 'DBSQL' AND c.dbsql_warehouse_type = 'SERVERLESS' THEN 'SERVERLESS_SQL_COMPUTE'
            WHEN c.workload_type = 'VECTOR_SEARCH' THEN 'VECTOR_SEARCH_ENDPOINT'
            WHEN c.workload_type = 'MODEL_SERVING' THEN 'SERVERLESS_REAL_TIME_INFERENCE'
            WHEN c.workload_type = 'LAKEBASE' THEN 'DATABASE_SERVERLESS_COMPUTE'
            
            -- Classic workloads: apply photon suffix if enabled
            WHEN c.workload_type = 'JOBS' AND c.photon_enabled THEN 'JOBS_COMPUTE_(PHOTON)'
            WHEN c.workload_type = 'JOBS' THEN 'JOBS_COMPUTE'
            WHEN c.workload_type = 'ALL_PURPOSE' AND c.photon_enabled THEN 'ALL_PURPOSE_COMPUTE_(PHOTON)'
            WHEN c.workload_type = 'ALL_PURPOSE' THEN 'ALL_PURPOSE_COMPUTE'
            WHEN c.workload_type = 'DLT' THEN 
                CASE 
                    WHEN c.dlt_edition = 'PRO' THEN 'DLT_PRO_COMPUTE' || CASE WHEN c.photon_enabled THEN '_(PHOTON)' ELSE '' END
                    WHEN c.dlt_edition = 'ADVANCED' THEN 'DLT_ADVANCED_COMPUTE' || CASE WHEN c.photon_enabled THEN '_(PHOTON)' ELSE '' END
                    ELSE 'DLT_CORE_COMPUTE' || CASE WHEN c.photon_enabled THEN '_(PHOTON)' ELSE '' END
                END
            WHEN c.workload_type = 'DBSQL' THEN 
                CASE c.dbsql_warehouse_type
                    WHEN 'PRO' THEN 'SQL_PRO_COMPUTE'
                    ELSE 'SQL_COMPUTE'
                END
            ELSE 'JOBS_COMPUTE'
        END as product_type_for_pricing,
        
        -- Calculate DBU per hour for hourly workloads
        CASE 
            -- Standard compute: (driver + workers) * photon_multiplier
            WHEN c.workload_type IN ('JOBS', 'ALL_PURPOSE') AND NOT c.serverless_enabled THEN
                (COALESCE(c.driver_dbu_rate, 0) + 
                 (COALESCE(c.worker_dbu_rate, 0) * COALESCE(c.num_workers, 0))) * 
                c.photon_multiplier
            
            -- Serverless JOBS/ALL_PURPOSE/DLT: use worker DBU rate as base unit
            WHEN c.serverless_enabled AND c.workload_type IN ('JOBS', 'ALL_PURPOSE', 'DLT') THEN
                COALESCE(c.worker_dbu_rate, 0) * COALESCE(c.num_workers, 0) * 
                CASE WHEN COALESCE(c.serverless_mode, 'standard') = 'performance' THEN 2 ELSE 1 END
            
            -- DLT (classic): same as standard compute
            WHEN c.workload_type = 'DLT' AND NOT c.serverless_enabled THEN
                (COALESCE(c.driver_dbu_rate, 0) + 
                 (COALESCE(c.worker_dbu_rate, 0) * COALESCE(c.num_workers, 0))) * 
                c.photon_multiplier
            
            -- DBSQL: warehouse_size + num_clusters
            WHEN c.workload_type = 'DBSQL' THEN
                CASE 
                    WHEN c.dbsql_warehouse_size = '2X-Small' THEN 1
                    WHEN c.dbsql_warehouse_size = 'X-Small' THEN 2
                    WHEN c.dbsql_warehouse_size = 'Small' THEN 4
                    WHEN c.dbsql_warehouse_size = 'Medium' THEN 8
                    WHEN c.dbsql_warehouse_size = 'Large' THEN 16
                    WHEN c.dbsql_warehouse_size = 'X-Large' THEN 32
                    WHEN c.dbsql_warehouse_size = '2X-Large' THEN 64
                    WHEN c.dbsql_warehouse_size = '3X-Large' THEN 128
                    WHEN c.dbsql_warehouse_size = '4X-Large' THEN 256
                    ELSE 0
                END * COALESCE(c.dbsql_num_clusters, 1)
            
            -- Vector Search / Model Serving: from serverless rate table
            WHEN c.workload_type IN ('VECTOR_SEARCH', 'MODEL_SERVING') THEN
                COALESCE(s.dbu_rate, 0)
            
            -- Lakebase: CU = DBU (1:1 mapping)
            WHEN c.workload_type = 'LAKEBASE' THEN
                COALESCE(c.lakebase_cu, 0)
            
            ELSE 0
        END as dbu_per_hour
        
    FROM classic_compute c
    LEFT JOIN lakemeter.sync_product_serverless_rates s
        ON s.cloud = c.cloud
        AND s.product = CASE 
            WHEN c.workload_type = 'VECTOR_SEARCH' THEN 'vector_search'
            WHEN c.workload_type = 'MODEL_SERVING' THEN 'model_serving'
            ELSE NULL
        END
        AND s.size_or_model = c.serverless_size
),

-- Calculate FMAPI monthly DBU usage (token-based, not hourly)
fmapi_calc AS (
    SELECT 
        d.*,
        -- FMAPI: calculate monthly DBU from tokens
        CASE 
            WHEN d.workload_type = 'FMAPI_DATABRICKS' THEN
                COALESCE(
                    (d.fmapi_input_tokens_per_month / NULLIF(fm.input_divisor, 0) * fm.dbu_rate) +
                    (d.fmapi_output_tokens_per_month / NULLIF(fm.output_divisor, 0) * fm.dbu_rate),
                    0
                )
            WHEN d.workload_type = 'FMAPI_PROPRIETARY' THEN
                COALESCE(
                    (d.fmapi_input_tokens_per_month / NULLIF(fp.input_divisor, 0) * fp.input_dbu_rate) +
                    (d.fmapi_output_tokens_per_month / NULLIF(fp.input_divisor, 0) * fp.output_dbu_rate),
                    0
                )
            ELSE 0
        END as fmapi_dbu_per_month
    FROM dbu_calc d
    LEFT JOIN lakemeter.sync_product_fmapi_databricks fm
        ON d.workload_type = 'FMAPI_DATABRICKS'
        AND fm.model = d.fmapi_model
    LEFT JOIN lakemeter.sync_product_fmapi_proprietary fp
        ON d.workload_type = 'FMAPI_PROPRIETARY'
        AND fp.cloud = d.cloud
        AND fp.provider = d.fmapi_provider
        AND fp.model = d.fmapi_model
        AND fp.endpoint_type = d.fmapi_endpoint_type
        AND fp.context_length = d.fmapi_context_length
        AND fp.rate_type = 'input_token'
),

-- Get DBU price per unit (varies by cloud, region, tier, product_type)
pricing AS (
    SELECT 
        f.*,
        COALESCE(p.price_per_dbu, 0) as price_per_dbu
    FROM fmapi_calc f
    LEFT JOIN lakemeter.sync_pricing_dbu_rates p
        ON p.cloud = f.cloud
        AND p.region = f.region
        AND p.tier = f.tier
        AND p.product_type = f.product_type_for_pricing
),

-- Get VM costs (only for classic compute)
vm_costs AS (
    SELECT 
        pr.*,
        -- Driver VM cost
        CASE 
            WHEN pr.serverless_enabled THEN 0  -- Serverless: no VM cost
            ELSE COALESCE(vm_driver.cost_per_hour, 0)
        END as driver_vm_cost_per_hour,
        
        -- Worker VM cost (adjusted for spot if applicable)
        CASE 
            WHEN pr.serverless_enabled THEN 0  -- Serverless: no VM cost
            WHEN pr.vm_payment_option = 'spot' THEN
                -- Spot: blend spot + on-demand based on spot_percentage
                COALESCE(vm_worker_spot.cost_per_hour, 0) * (COALESCE(pr.spot_percentage, 0) / 100.0) +
                COALESCE(vm_worker_demand.cost_per_hour, 0) * (1 - COALESCE(pr.spot_percentage, 0) / 100.0)
            WHEN pr.vm_payment_option = 'reserved_1y' THEN
                COALESCE(vm_worker_res1y.cost_per_hour, 0)
            WHEN pr.vm_payment_option = 'reserved_3y' THEN
                COALESCE(vm_worker_res3y.cost_per_hour, 0)
            ELSE
                COALESCE(vm_worker_demand.cost_per_hour, 0)
        END as worker_vm_cost_per_hour
        
    FROM pricing pr
    LEFT JOIN lakemeter.pricing_vm_costs vm_driver
        ON pr.serverless_enabled = FALSE
        AND vm_driver.cloud = pr.cloud
        AND vm_driver.region = pr.region
        AND vm_driver.instance_type = pr.driver_node_type
        AND vm_driver.pricing_tier = COALESCE(pr.vm_pricing_tier, 'on_demand')
        AND vm_driver.payment_option = 'on_demand'
    LEFT JOIN lakemeter.pricing_vm_costs vm_worker_demand
        ON pr.serverless_enabled = FALSE
        AND vm_worker_demand.cloud = pr.cloud
        AND vm_worker_demand.region = pr.region
        AND vm_worker_demand.instance_type = pr.worker_node_type
        AND vm_worker_demand.pricing_tier = COALESCE(pr.vm_pricing_tier, 'on_demand')
        AND vm_worker_demand.payment_option = 'on_demand'
    LEFT JOIN lakemeter.pricing_vm_costs vm_worker_spot
        ON pr.vm_payment_option = 'spot'
        AND vm_worker_spot.cloud = pr.cloud
        AND vm_worker_spot.region = pr.region
        AND vm_worker_spot.instance_type = pr.worker_node_type
        AND vm_worker_spot.pricing_tier = COALESCE(pr.vm_pricing_tier, 'on_demand')
        AND vm_worker_spot.payment_option = 'spot'
    LEFT JOIN lakemeter.pricing_vm_costs vm_worker_res1y
        ON pr.vm_payment_option = 'reserved_1y'
        AND vm_worker_res1y.cloud = pr.cloud
        AND vm_worker_res1y.region = pr.region
        AND vm_worker_res1y.instance_type = pr.worker_node_type
        AND vm_worker_res1y.pricing_tier = COALESCE(pr.vm_pricing_tier, 'on_demand')
        AND vm_worker_res1y.payment_option = 'reserved_1y'
    LEFT JOIN lakemeter.pricing_vm_costs vm_worker_res3y
        ON pr.vm_payment_option = 'reserved_3y'
        AND vm_worker_res3y.cloud = pr.cloud
        AND vm_worker_res3y.region = pr.region
        AND vm_worker_res3y.instance_type = pr.worker_node_type
        AND vm_worker_res3y.pricing_tier = COALESCE(pr.vm_pricing_tier, 'on_demand')
        AND vm_worker_res3y.payment_option = 'reserved_3y'
),

-- Final calculation
final_calc AS (
    SELECT 
        v.*,
        -- For auditability: expose all intermediate fields
        v.driver_dbu_rate,
        v.worker_dbu_rate,
        v.photon_multiplier,
        v.dbu_per_hour,
        v.fmapi_dbu_per_month,
        v.product_type_for_pricing,
        v.price_per_dbu,
        v.driver_vm_cost_per_hour,
        v.worker_vm_cost_per_hour
    FROM vm_costs v
)

-- Final SELECT with all fields
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
    
    -- CALCULATED FIELDS (for auditability)
    hours_per_month,
    driver_dbu_rate,
    worker_dbu_rate,
    photon_multiplier,
    dbu_per_hour,
    fmapi_dbu_per_month,
    product_type_for_pricing,
    
    -- DBU per month (hourly workloads vs token-based)
    CASE 
        WHEN workload_type IN ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY') THEN fmapi_dbu_per_month
        ELSE dbu_per_hour * hours_per_month
    END as dbu_per_month,
    
    -- DBU cost per month
    CASE 
        WHEN workload_type IN ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY') THEN fmapi_dbu_per_month * price_per_dbu
        ELSE dbu_per_hour * hours_per_month * price_per_dbu
    END as dbu_cost_per_month,
    
    -- VM cost per month (only for classic compute)
    (driver_vm_cost_per_hour + (worker_vm_cost_per_hour * COALESCE(num_workers, 0))) * hours_per_month as vm_cost_per_month,
    
    -- Total cost per month
    CASE 
        WHEN workload_type IN ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY') THEN 
            fmapi_dbu_per_month * price_per_dbu
        ELSE 
            (dbu_per_hour * hours_per_month * price_per_dbu) +
            ((driver_vm_cost_per_hour + (worker_vm_cost_per_hour * COALESCE(num_workers, 0))) * hours_per_month)
    END as cost_per_month,
    
    -- Price details for transparency
    price_per_dbu,
    driver_vm_cost_per_hour,
    worker_vm_cost_per_hour

FROM final_calc;

-- Grant access
GRANT SELECT ON lakemeter.v_line_items_with_costs TO PUBLIC;

-- ============================================================================
-- DONE! View updated with cloud join fix
-- ============================================================================

