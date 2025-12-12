-- =============================================================================
-- LAKEMETER DATABASE SCHEMA - APPLICATION TABLES
-- =============================================================================
-- Creates all application tables for the Lakemeter cost estimation app.
-- 
-- IDEMPOTENT: Safe to run multiple times.
-- - Tables: DROP TABLE IF EXISTS + CREATE TABLE
-- - Indexes: DROP INDEX IF EXISTS + CREATE INDEX
-- - Inserts: INSERT ... ON CONFLICT DO NOTHING
--
-- NOTE: This script creates TABLES ONLY.
-- VIEWS are in a separate section at the bottom and require sync_* tables.
-- Run PART 1 first, then PART 2 after sync tables exist.
-- =============================================================================

-- =============================================================================
-- DROP EXISTING OBJECTS (in dependency order - views first, then tables)
-- =============================================================================

-- Drop views first (they depend on tables)
DROP VIEW IF EXISTS v_estimates_with_totals CASCADE;
DROP VIEW IF EXISTS v_line_items_with_costs CASCADE;

-- Drop application tables only (synced tables are managed separately)
DROP TABLE IF EXISTS decision_records CASCADE;
DROP TABLE IF EXISTS conversation_messages CASCADE;
DROP TABLE IF EXISTS sharing CASCADE;
DROP TABLE IF EXISTS line_items CASCADE;
DROP TABLE IF EXISTS estimates CASCADE;
DROP TABLE IF EXISTS templates CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS ref_workload_types CASCADE;

-- =============================================================================
-- APPLICATION TABLES (Blue: #E3F2FD)
-- =============================================================================

CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE templates (
    template_id UUID PRIMARY KEY,
    template_name VARCHAR(255) NOT NULL,
    workload_type VARCHAR(100),
    file_path VARCHAR(500),
    file_format VARCHAR(10),
    mandatory_fields JSON,
    optional_fields JSON,
    description TEXT,
    version INT DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE estimates (
    estimate_id UUID PRIMARY KEY,
    estimate_name VARCHAR(500),
    owner_user_id UUID REFERENCES users(user_id),
    customer_sfdc_id VARCHAR(18),
    customer_name VARCHAR(255),
    uco_opportunity_id VARCHAR(18),
    cloud VARCHAR(20),
    region VARCHAR(50),
    tier VARCHAR(20),
    status VARCHAR(20) DEFAULT 'draft',
    version INT DEFAULT 1,
    template_id UUID REFERENCES templates(template_id),
    original_prompt TEXT,
    -- total_dbu_per_month: REMOVED - calculate from SUM(line_items.dbu_per_month)
    -- total_cost_per_month: REMOVED - calculate from SUM(line_items.cost_per_month)
    is_deleted BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- created_by: REMOVED - owner_user_id IS the creator
    updated_by UUID REFERENCES users(user_id)  -- Tracks who last edited (for audit)
);

-- =============================================================================
-- LINE_ITEMS: Redesigned for Dynamic Form UI (like Azure Calculator)
-- =============================================================================
-- Each workload type uses different columns. Unused columns are NULL.
-- The UI shows/hides form fields based on workload_type selection.
-- =============================================================================

CREATE TABLE line_items (
    line_item_id UUID PRIMARY KEY,
    estimate_id UUID REFERENCES estimates(estimate_id),
    display_order INT,
    
    -- =========================================================================
    -- SECTION 1: WORKLOAD IDENTITY (Always shown)
    -- =========================================================================
    workload_name VARCHAR(255),               -- User-defined name
    workload_type VARCHAR(50) NOT NULL,       -- Dropdown: JOBS, ALL_PURPOSE, DLT, DBSQL, etc.
    
    -- =========================================================================
    -- SECTION 2: COMPUTE CONFIG (Show for JOBS, ALL_PURPOSE, DLT)
    -- VM config always shown for sizing estimation, even when serverless
    -- =========================================================================
    serverless_enabled BOOLEAN DEFAULT false, -- Toggle: Serverless (if true, photon must be true)
    serverless_mode VARCHAR(20),              -- Dropdown: standard, performance (for JOBS/DLT serverless only)
    photon_enabled BOOLEAN DEFAULT false,     -- Toggle: Photon (auto-true when serverless)
    driver_node_type VARCHAR(100),            -- Dropdown: for sizing estimation (even for serverless)
    worker_node_type VARCHAR(100),            -- Dropdown: for sizing estimation (even for serverless)
    num_workers INT,                          -- Number input: 0-1000 (for sizing estimation)
    autoscale_enabled BOOLEAN DEFAULT false,  -- Toggle
    autoscale_min_workers INT,                -- Number input (if autoscale)
    autoscale_max_workers INT,                -- Number input (if autoscale)
    
    -- =========================================================================
    -- SECTION 3: DLT CONFIG (Show when workload_type = 'DLT')
    -- =========================================================================
    dlt_edition VARCHAR(20),                  -- Dropdown: CORE, PRO, ADVANCED
    dlt_pipeline_mode VARCHAR(20),            -- Dropdown: TRIGGERED, CONTINUOUS
    
    -- =========================================================================
    -- SECTION 4: DBSQL CONFIG (Show when workload_type = 'DBSQL')
    -- =========================================================================
    dbsql_warehouse_type VARCHAR(20),         -- Dropdown: CLASSIC, PRO, SERVERLESS
    dbsql_warehouse_size VARCHAR(20),         -- Dropdown: 2X-Small to 4X-Large
    dbsql_num_clusters INT DEFAULT 1,         -- Number of clusters (1-100, for scaling)
    
    -- =========================================================================
    -- SECTION 5: SERVERLESS PRODUCTS (Show for Vector Search, Model Serving)
    -- =========================================================================
    serverless_product VARCHAR(50),           -- Dropdown: vector_search, model_serving
    serverless_size VARCHAR(50),              -- Dropdown: cpu, gpu_small, gpu_medium, etc.
    
    -- =========================================================================
    -- SECTION 6: FMAPI CONFIG (Show when workload_type = 'FMAPI')
    -- =========================================================================
    fmapi_provider VARCHAR(50),               -- Dropdown: databricks, openai, anthropic, google
    fmapi_model VARCHAR(100),                 -- Dropdown: gpt-4o, claude-sonnet-4, llama-3.1-70b
    fmapi_endpoint_type VARCHAR(20),          -- Dropdown: global, in_geo (for proprietary)
    fmapi_context_length VARCHAR(20),         -- Dropdown: standard, long (for proprietary)
    fmapi_input_tokens_per_month BIGINT,      -- Number input: estimated input tokens
    fmapi_output_tokens_per_month BIGINT,     -- Number input: estimated output tokens
    
    -- =========================================================================
    -- SECTION 7: USAGE / FREQUENCY (Consistent for all hourly workloads)
    -- =========================================================================
    -- hours_per_month = runs_per_day * (avg_runtime_minutes / 60) * days_per_month
    runs_per_day INT,                         -- Number of runs per day
    avg_runtime_minutes INT,                  -- Average runtime per run (in minutes)
    days_per_month INT DEFAULT 30,            -- Days per month (default 30)
    
    -- =========================================================================
    -- SECTION 8: PRICING OPTIONS (Show for classic compute with VMs)
    -- =========================================================================
    vm_pricing_tier VARCHAR(20) DEFAULT 'on_demand',  -- Dropdown: on_demand, spot, reserved_1y, reserved_3y
    vm_payment_option VARCHAR(20),            -- Dropdown (if reserved): no_upfront, partial_upfront, all_upfront
    spot_percentage INT,                      -- If using spot: what % of workers are spot (0-100)
    
    -- =========================================================================
    -- SECTION 9: EXTENSIBLE CONFIG (For future workload types)
    -- =========================================================================
    -- Use this JSON column for NEW workload types without schema changes
    -- Example: {"pages_per_month": 100000, "model": "docai-v2", "output_format": "json"}
    workload_config JSON,
    
    -- =========================================================================
    -- SECTION 10: METADATA
    -- =========================================================================
    -- NOTE: No created_by/updated_by here - derive from estimates table
    -- Get via: SELECT e.owner_user_id FROM estimates e WHERE e.estimate_id = line_items.estimate_id
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast lookups (idempotent)
DROP INDEX IF EXISTS idx_line_items_estimate;
DROP INDEX IF EXISTS idx_line_items_workload_type;
CREATE INDEX idx_line_items_estimate ON line_items(estimate_id);
CREATE INDEX idx_line_items_workload_type ON line_items(workload_type);

-- =============================================================================
-- WORKLOAD_TYPES: Reference table for UI form configuration
-- =============================================================================
-- This table tells the UI which form sections/fields to show for each workload type
-- MUST be created BEFORE views (views reference this table)

CREATE TABLE ref_workload_types (
    workload_type VARCHAR(50) PRIMARY KEY,
    display_name VARCHAR(100),
    description TEXT,
    
    -- Which form sections to show (TRUE = show, FALSE = hide)
    show_compute_config BOOLEAN DEFAULT false,     -- Driver/worker nodes (always for sizing)
    show_serverless_toggle BOOLEAN DEFAULT false,  -- Serverless ON/OFF toggle
    show_serverless_mode BOOLEAN DEFAULT false,    -- Serverless mode dropdown (standard/performance) - JOBS/DLT only
    show_photon_toggle BOOLEAN DEFAULT false,      -- Photon toggle (disabled when serverless=ON)
    show_dlt_config BOOLEAN DEFAULT false,         -- DLT edition (Core/Pro/Advanced)
    show_dbsql_config BOOLEAN DEFAULT false,       -- Warehouse type/size
    show_serverless_product BOOLEAN DEFAULT false, -- Serverless product config (Vector Search, Model Serving)
    show_fmapi_config BOOLEAN DEFAULT false,       -- FMAPI model selection
    show_vm_pricing BOOLEAN DEFAULT false,         -- VM pricing tier (hidden when serverless=ON)
    show_usage_hours BOOLEAN DEFAULT false,        -- Hours per day/month
    show_usage_runs BOOLEAN DEFAULT false,         -- Runs per day, runtime
    show_usage_tokens BOOLEAN DEFAULT false,       -- Input/output tokens
    
    -- Which product_type to use for DBU pricing lookup
    sku_product_type_standard VARCHAR(100),        -- Classic without Photon
    sku_product_type_photon VARCHAR(100),          -- Classic with Photon
    sku_product_type_serverless VARCHAR(100),      -- Serverless (always Photon)
    
    display_order INT
);

-- Populate workload types (idempotent - skips if exists)
-- JOBS: Batch jobs (Classic or Serverless)
INSERT INTO ref_workload_types VALUES
('JOBS', 'Jobs Compute', 'Scheduled batch jobs (Classic or Serverless)', 
 true, true, true, true, false, false, false, false, true, false, true, false,
 'JOBS_COMPUTE', 'JOBS_COMPUTE_(PHOTON)', 'JOBS_SERVERLESS_COMPUTE', 1)
ON CONFLICT (workload_type) DO NOTHING;

-- ALL_PURPOSE: Interactive notebooks (Classic or Serverless)
INSERT INTO ref_workload_types VALUES
('ALL_PURPOSE', 'All-Purpose Compute', 'Interactive clusters for notebooks (Classic or Serverless)', 
 true, true, false, true, false, false, false, false, true, true, false, false,
 'ALL_PURPOSE_COMPUTE', 'ALL_PURPOSE_COMPUTE_(PHOTON)', 'INTERACTIVE_SERVERLESS_COMPUTE', 2)
ON CONFLICT (workload_type) DO NOTHING;

-- DLT: Delta Live Tables (Classic or Serverless)
INSERT INTO ref_workload_types VALUES
('DLT', 'Delta Live Tables', 'Declarative ETL pipelines (Classic or Serverless)',
 true, true, true, true, true, false, false, false, true, true, false, false,
 'DLT_CORE_COMPUTE', 'DLT_CORE_COMPUTE_(PHOTON)', 'DELTA_LIVE_TABLES_SERVERLESS', 3)
ON CONFLICT (workload_type) DO NOTHING;

-- DBSQL: SQL Analytics (has its own warehouse_type for serverless)
INSERT INTO ref_workload_types VALUES
('DBSQL', 'Databricks SQL', 'SQL analytics warehouse (Classic/Pro/Serverless)',
 false, false, false, false, false, true, false, false, false, true, false, false,
 'SQL_COMPUTE', 'SQL_PRO_COMPUTE', 'SERVERLESS_SQL_COMPUTE', 4)
ON CONFLICT (workload_type) DO NOTHING;

-- VECTOR_SEARCH: Serverless only
INSERT INTO ref_workload_types VALUES
('VECTOR_SEARCH', 'Vector Search', 'Vector search endpoints for RAG',
 false, false, false, false, false, false, true, false, false, true, false, false,
 NULL, NULL, 'VECTOR_SEARCH_ENDPOINT', 5)
ON CONFLICT (workload_type) DO NOTHING;

-- MODEL_SERVING: Serverless only
INSERT INTO ref_workload_types VALUES
('MODEL_SERVING', 'Model Serving', 'Real-time model inference endpoints',
 false, false, false, false, false, false, true, false, false, true, false, false,
 NULL, NULL, 'SERVERLESS_REAL_TIME_INFERENCE', 6)
ON CONFLICT (workload_type) DO NOTHING;

-- FMAPI_DATABRICKS: Databricks-hosted LLMs (Serverless only)
INSERT INTO ref_workload_types VALUES
('FMAPI_DATABRICKS', 'Foundation Models (Databricks)', 'Databricks-hosted LLMs (Llama, DBRX)',
 false, false, false, false, false, false, false, true, false, false, false, true,
 NULL, NULL, 'SERVERLESS_REAL_TIME_INFERENCE', 7)
ON CONFLICT (workload_type) DO NOTHING;

-- FMAPI_PROPRIETARY: Proprietary LLMs served by Databricks (OpenAI, Anthropic, Google)
INSERT INTO ref_workload_types VALUES
('FMAPI_PROPRIETARY', 'Foundation Models (Proprietary)', 'OpenAI, Anthropic, Google models served by Databricks',
 false, false, false, false, false, false, false, true, false, false, false, true,
 NULL, NULL, NULL, 8)  -- sku_product_type determined by provider dynamically
ON CONFLICT (workload_type) DO NOTHING;

-- Add FK constraint: line_items.workload_type → ref_workload_types.workload_type
ALTER TABLE line_items 
ADD CONSTRAINT fk_line_items_workload_type 
FOREIGN KEY (workload_type) REFERENCES ref_workload_types(workload_type);

-- =============================================================================
-- PART 1 COMPLETE - Tables created successfully!
-- =============================================================================
-- You can stop here if sync_* tables don't exist yet.
-- Run PART 2 below AFTER the sync tables are created.
-- =============================================================================


-- =============================================================================
-- PART 2: VIEWS (Requires sync_* tables to exist first!)
-- =============================================================================
-- ⚠️  PREREQUISITE: The following sync_* tables MUST exist before running:
--   - sync_ref_instance_dbu_rates
--   - sync_ref_dbu_multipliers
--   - sync_pricing_dbu_rates
--   - sync_pricing_vm_costs
--   - sync_product_dbsql_rates
--   - sync_product_serverless_rates
--   - sync_product_fmapi_databricks
--   - sync_product_fmapi_proprietary
-- 
-- To create sync tables, run notebooks in Pricing_Sync folder first!
-- =============================================================================

CREATE OR REPLACE VIEW v_line_items_with_costs AS
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
        CASE WHEN p.workload_type IN ('ALL_PURPOSE', 'JOBS', 'DLT') 
              AND p.serverless_enabled = FALSE THEN
            COALESCE((
                SELECT cost_per_hour FROM sync_pricing_vm_costs 
                WHERE cloud = p.cloud AND region = p.region 
                AND instance_type = p.driver_node_type
                AND pricing_tier = COALESCE(p.vm_pricing_tier, 'on_demand')
                LIMIT 1
            ), 0)
        ELSE 0 END as driver_vm_cost_per_hour,
        
        CASE WHEN p.workload_type IN ('ALL_PURPOSE', 'JOBS', 'DLT') 
              AND p.serverless_enabled = FALSE THEN
            COALESCE((
                SELECT cost_per_hour FROM sync_pricing_vm_costs 
                WHERE cloud = p.cloud AND region = p.region 
                AND instance_type = p.worker_node_type
                AND pricing_tier = COALESCE(p.vm_pricing_tier, 'on_demand')
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
    fmapi_provider,
    fmapi_model,
    fmapi_endpoint_type,
    fmapi_context_length,
    fmapi_input_tokens_per_month,
    fmapi_output_tokens_per_month,
    runs_per_day,
    avg_runtime_minutes,
    days_per_month,
    vm_pricing_tier,
    vm_payment_option,
    spot_percentage,
    notes,
    created_at,
    updated_at,
    -- created_by/updated_by removed - derive from estimates.owner_user_id
    
    -- Estimate context
    cloud,
    region,
    tier,
    
    -- CALCULATED FIELDS
    hours_per_month,
    dbu_per_hour,
    
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
    worker_vm_cost_per_hour,
    photon_multiplier,
    product_type_for_pricing

FROM final_calc;

-- =============================================================================
-- VIEW: v_estimates_with_totals
-- =============================================================================
-- Aggregates costs from line items. MUST be created AFTER v_line_items_with_costs.
-- Usage: SELECT * FROM v_estimates_with_totals WHERE owner_user_id = :user_id
-- =============================================================================

CREATE OR REPLACE VIEW v_estimates_with_totals AS
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
-- HOW TO ADD A NEW WORKLOAD TYPE (e.g., AI_PARSE_DOCUMENT)
-- =============================================================================
-- 
-- The design is EXTENSIBLE. Adding new workloads does NOT break existing estimates.
-- 
-- OPTION A: Use workload_config JSON (NO SCHEMA CHANGE)
-- ─────────────────────────────────────────────────────
-- 1. Add row to ref_workload_types:
--    INSERT INTO ref_workload_types VALUES (
--        'AI_PARSE_DOCUMENT', 'AI Document Parsing', 'Extract data from docs',
--        false, false, false, false, false, false, false, false, true,
--        'DOCUMENT_AI_PARSE', NULL, 11
--    );
-- 
-- 2. Store workload-specific fields in workload_config JSON:
--    INSERT INTO line_items (workload_type, workload_config, ...) VALUES (
--        'AI_PARSE_DOCUMENT',
--        '{"pages_per_month": 100000, "model": "docai-v2", "output_format": "json"}',
--        ...
--    );
-- 
-- 3. Update v_line_items_with_costs view to handle new type:
--    WHEN workload_type = 'AI_PARSE_DOCUMENT' THEN
--        (workload_config->>'pages_per_month')::bigint / 1000 * rate
-- 
-- OPTION B: Add dedicated columns (SCHEMA CHANGE)
-- ─────────────────────────────────────────────────────
-- 1. ALTER TABLE line_items ADD COLUMN ai_parse_pages_per_month BIGINT;
-- 2. Existing rows get NULL (no impact)
-- 3. Update ref_workload_types
-- 4. Update v_line_items_with_costs view
-- 
-- WHY EXISTING ESTIMATES ARE SAFE:
-- ─────────────────────────────────────────────────────
-- - New columns default to NULL for existing rows
-- - workload_type determines which fields are used
-- - Cost calculation only looks at relevant fields per type
-- - Old estimates with old workload_types work unchanged
-- 
-- =============================================================================

-- =============================================================================
-- WORKLOAD COVERAGE SUMMARY
-- =============================================================================
-- All 8 workload types are covered by line_items columns:
--
-- Usage Pattern:
--   - Hourly workloads: runs_per_day, avg_runtime_minutes, days_per_month
--   - Token workloads:  fmapi_input_tokens_per_month, fmapi_output_tokens_per_month
--
-- | Workload Type     | Config Fields                                            |
-- |-------------------|----------------------------------------------------------|
-- | JOBS              | serverless_enabled, photon_enabled,                      |
-- |                   | driver_node_type, worker_node_type, num_workers,         |
-- |                   | runs_per_day, avg_runtime_minutes, days_per_month,       |
-- |                   | vm_pricing_tier, vm_payment_option, spot_percentage      |
-- |-------------------|----------------------------------------------------------|
-- | ALL_PURPOSE       | serverless_enabled, photon_enabled,                      |
-- |                   | driver_node_type, worker_node_type, num_workers,         |
-- |                   | runs_per_day, avg_runtime_minutes, days_per_month,       |
-- |                   | vm_pricing_tier                                          |
-- |-------------------|----------------------------------------------------------|
-- | DLT               | serverless_enabled, photon_enabled,                      |
-- |                   | dlt_edition, dlt_pipeline_mode,                          |
-- |                   | driver_node_type, worker_node_type, num_workers,         |
-- |                   | runs_per_day, avg_runtime_minutes, days_per_month,       |
-- |                   | vm_pricing_tier                                          |
-- |-------------------|----------------------------------------------------------|
-- | DBSQL             | dbsql_warehouse_type, dbsql_warehouse_size,              |
-- |                   | dbsql_num_clusters,                                      |
-- |                   | runs_per_day, avg_runtime_minutes, days_per_month        |
-- |-------------------|----------------------------------------------------------|
-- | VECTOR_SEARCH     | serverless_product, serverless_size,                     |
-- |                   | runs_per_day, avg_runtime_minutes, days_per_month        |
-- |-------------------|----------------------------------------------------------|
-- | MODEL_SERVING     | serverless_product, serverless_size,                     |
-- |                   | runs_per_day, avg_runtime_minutes, days_per_month        |
-- |-------------------|----------------------------------------------------------|
-- | FMAPI_DATABRICKS  | fmapi_model,                                             |
-- |                   | fmapi_input_tokens_per_month, fmapi_output_tokens_per_month |
-- |-------------------|----------------------------------------------------------|
-- | FMAPI_PROPRIETARY | fmapi_provider, fmapi_model, fmapi_endpoint_type,        |
-- |                   | fmapi_context_length,                                    |
-- |                   | fmapi_input_tokens_per_month, fmapi_output_tokens_per_month |
-- =============================================================================
--
-- Hours Calculation (for all hourly workloads):
--   hours_per_month = runs_per_day * (avg_runtime_minutes / 60) * days_per_month
--
-- Notes:
--   - JOBS/ALL_PURPOSE/DLT: VM fields used for sizing; ignored if serverless_enabled
--   - DBSQL: serverless via dbsql_warehouse_type = 'SERVERLESS'
-- =============================================================================

CREATE TABLE conversation_messages (
    message_id UUID PRIMARY KEY,
    estimate_id UUID REFERENCES estimates(estimate_id),
    message_role VARCHAR(20),              -- 'user' or 'assistant'
    message_content TEXT,
    message_sequence INT,
    message_type VARCHAR(50),
    tokens_used INT,
    model_used VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- created_by: REMOVED - derive from estimates.owner_user_id
    -- For 'user' role messages, the sender is always the estimate owner
);

CREATE TABLE decision_records (
    record_id UUID PRIMARY KEY,
    line_item_id UUID REFERENCES line_items(line_item_id),  -- Get estimate via: line_items.estimate_id
    record_type VARCHAR(50),
    user_input TEXT,
    agent_response TEXT,
    assumptions JSON,
    calculations JSON,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- estimate_id: REMOVED - derive from line_items.estimate_id
    -- created_by: REMOVED - derive from estimates.owner_user_id
);

CREATE TABLE sharing (
    share_id UUID PRIMARY KEY,
    estimate_id UUID REFERENCES estimates(estimate_id),
    share_type VARCHAR(20),
    shared_with_user_id UUID REFERENCES users(user_id),
    share_link VARCHAR(255) UNIQUE,
    permission VARCHAR(20),
    expires_at TIMESTAMP,
    access_count INT DEFAULT 0,
    last_accessed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- created_by: REMOVED - derive from estimates.owner_user_id
    -- The estimate owner is always the one who creates shares
);

-- =============================================================================
-- SCRIPT COMPLETE
-- =============================================================================
-- This script creates APPLICATION TABLES and VIEWS.
-- 
-- SYNCED TABLES (created by Lakebase sync, NOT in this script):
--   - sync_pricing_dbu_rates
--   - sync_pricing_vm_costs
--   - sync_product_dbsql_rates
--   - sync_product_serverless_rates
--   - sync_product_fmapi_databricks
--   - sync_product_fmapi_proprietary
--   - sync_ref_instance_dbu_rates
--   - sync_ref_dbu_multipliers
--   - sync_ref_sku_region_map
--   - sync_ref_dbsql_warehouse_config
-- 
-- IDEMPOTENT: Safe to run multiple times.
-- 
-- Execution order:
--   1. DROP application tables
--   2. CREATE application tables (users, templates, estimates, line_items)
--   3. CREATE views (v_line_items_with_costs, v_estimates_with_totals)
--   4. CREATE ref_workload_types with seed data
--   5. ADD FK constraint (line_items → ref_workload_types)
--   6. CREATE remaining tables (conversation_messages, decision_records, sharing)
--
-- PREREQUISITE: Synced tables (sync_*) must exist before views will work!
-- 
-- To run: psql -h <host> -d <database> -U <user> -f lakemeter_erd.sql
-- =============================================================================
