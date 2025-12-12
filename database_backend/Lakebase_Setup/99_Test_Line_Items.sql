-- =============================================================================
-- TEST DATA: Sample Line Items for Each Workload Type
-- =============================================================================
-- This script inserts one line item for each workload scenario to test
-- the v_line_items_with_costs view and verify cost calculations.
--
-- Prerequisites:
-- 1. Run lakemeter_erd.sql to create tables and views
-- 2. Sync pricing data to sync_* tables
-- =============================================================================

-- First, create a test user
INSERT INTO users (user_id, email, full_name, role, is_active)
VALUES 
('00000000-0000-0000-0000-000000000001', 'test.user@example.com', 'Test User', 'SA', true)
ON CONFLICT (user_id) DO NOTHING;

-- Create a test estimate
INSERT INTO estimates (
    estimate_id, estimate_name, owner_user_id, customer_sfdc_id, customer_name,
    cloud, region, tier, status
)
VALUES (
    '10000000-0000-0000-0000-000000000001',
    'Test Estimate - All Workload Types',
    '00000000-0000-0000-0000-000000000001',
    '0011234567890ABCDE',
    'Test Customer Inc',
    'AWS',
    'us-east-1',
    'PREMIUM',
    'draft'
)
ON CONFLICT (estimate_id) DO NOTHING;

-- =============================================================================
-- 1. JOBS - Classic Compute (with Photon)
-- =============================================================================
INSERT INTO line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, serverless_mode, photon_enabled,
    driver_node_type, worker_node_type, num_workers,
    runs_per_day, avg_runtime_minutes, days_per_month,
    vm_pricing_tier, vm_payment_option
) VALUES (
    '20000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    1,
    'Daily ETL Pipeline (Classic)',
    'JOBS',
    false,  -- Classic compute
    NULL,   -- No serverless mode
    true,   -- Photon enabled
    'i3.xlarge',
    'i3.2xlarge',
    8,
    4,      -- 4 runs per day
    45,     -- 45 minutes per run
    30,
    'on_demand',
    'N/A'
);

-- =============================================================================
-- 2. JOBS - Serverless (Standard Mode)
-- =============================================================================
INSERT INTO line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, serverless_mode, photon_enabled,
    driver_node_type, worker_node_type, num_workers,
    runs_per_day, avg_runtime_minutes, days_per_month
) VALUES (
    '20000000-0000-0000-0000-000000000002',
    '10000000-0000-0000-0000-000000000001',
    2,
    'Hourly Data Processing (Serverless Standard)',
    'JOBS',
    true,       -- Serverless
    'standard', -- Standard mode (1x multiplier)
    true,       -- Auto-enabled
    'i3.xlarge',   -- For sizing reference only
    'i3.2xlarge',  -- For sizing reference only
    4,             -- For sizing reference only
    24,     -- 24 runs per day (hourly)
    30,     -- 30 minutes per run
    30
);

-- =============================================================================
-- 3. JOBS - Serverless (Performance Mode)
-- =============================================================================
INSERT INTO line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, serverless_mode, photon_enabled,
    driver_node_type, worker_node_type, num_workers,
    runs_per_day, avg_runtime_minutes, days_per_month
) VALUES (
    '20000000-0000-0000-0000-000000000003',
    '10000000-0000-0000-0000-000000000001',
    3,
    'Real-time Jobs (Serverless Performance)',
    'JOBS',
    true,         -- Serverless
    'performance', -- Performance mode (2x multiplier)
    true,         -- Auto-enabled
    'i3.xlarge',
    'i3.2xlarge',
    4,
    48,    -- 48 runs per day (every 30 min)
    15,    -- 15 minutes per run
    30
);

-- =============================================================================
-- 4. ALL_PURPOSE - Classic Compute
-- =============================================================================
INSERT INTO line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, serverless_mode, photon_enabled,
    driver_node_type, worker_node_type, num_workers,
    runs_per_day, avg_runtime_minutes, days_per_month,
    vm_pricing_tier
) VALUES (
    '20000000-0000-0000-0000-000000000004',
    '10000000-0000-0000-0000-000000000001',
    4,
    'Data Science Notebook Cluster',
    'ALL_PURPOSE',
    false,  -- Classic
    NULL,   -- No serverless mode for classic
    true,   -- Photon enabled
    'r5.xlarge',
    'r5.2xlarge',
    6,
    1,      -- Running daily
    480,    -- 8 hours per day
    22,     -- 22 working days
    'on_demand'
);

-- =============================================================================
-- 5. ALL_PURPOSE - Serverless
-- =============================================================================
INSERT INTO line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, serverless_mode, photon_enabled,
    driver_node_type, worker_node_type, num_workers,
    runs_per_day, avg_runtime_minutes, days_per_month
) VALUES (
    '20000000-0000-0000-0000-000000000005',
    '10000000-0000-0000-0000-000000000001',
    5,
    'Serverless Notebooks',
    'ALL_PURPOSE',
    true,   -- Serverless
    NULL,   -- ALL_PURPOSE doesn't have performance mode, only standard
    true,   -- Auto-enabled
    'r5.xlarge',   -- Sizing reference
    'r5.2xlarge',  -- Sizing reference
    4,             -- Sizing reference
    1,
    360,    -- 6 hours per day
    22
);

-- =============================================================================
-- 6. DLT - Classic (PRO Edition with Photon)
-- =============================================================================
INSERT INTO line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, serverless_mode, photon_enabled,
    dlt_edition, dlt_pipeline_mode,
    driver_node_type, worker_node_type, num_workers,
    runs_per_day, avg_runtime_minutes, days_per_month,
    vm_pricing_tier
) VALUES (
    '20000000-0000-0000-0000-000000000006',
    '10000000-0000-0000-0000-000000000001',
    6,
    'DLT Streaming Pipeline (Classic PRO)',
    'DLT',
    false,       -- Classic
    NULL,        -- No serverless mode for classic
    true,        -- Photon enabled
    'PRO',
    'CONTINUOUS',
    'r5.xlarge',
    'r5.2xlarge',
    4,
    1,
    1440,   -- 24 hours (continuous)
    30,
    'on_demand'
);

-- =============================================================================
-- 7. DLT - Serverless (Standard Mode)
-- =============================================================================
INSERT INTO line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, serverless_mode, photon_enabled,
    dlt_edition, dlt_pipeline_mode,
    driver_node_type, worker_node_type, num_workers,
    runs_per_day, avg_runtime_minutes, days_per_month
) VALUES (
    '20000000-0000-0000-0000-000000000007',
    '10000000-0000-0000-0000-000000000001',
    7,
    'DLT Serverless Pipeline (Standard)',
    'DLT',
    true,       -- Serverless
    'standard', -- Standard mode
    true,       -- Auto-enabled
    'PRO',
    'TRIGGERED',
    'r5.xlarge',   -- Sizing reference
    'r5.2xlarge',  -- Sizing reference
    4,             -- Sizing reference
    4,      -- 4 runs per day
    60,     -- 1 hour per run
    30
);

-- =============================================================================
-- 8. DBSQL - Serverless Warehouse
-- =============================================================================
INSERT INTO line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, serverless_mode,
    dbsql_warehouse_type, dbsql_warehouse_size, dbsql_num_clusters,
    runs_per_day, avg_runtime_minutes, days_per_month
) VALUES (
    '20000000-0000-0000-0000-000000000008',
    '10000000-0000-0000-0000-000000000001',
    8,
    'SQL Analytics Warehouse',
    'DBSQL',
    NULL,   -- Not applicable for DBSQL
    NULL,   -- Not applicable
    'serverless',
    'Medium',
    2,      -- 2 clusters for scaling
    1,
    480,    -- 8 hours per day
    22      -- Business days only
);

-- =============================================================================
-- 9. VECTOR_SEARCH - Serverless Endpoint
-- =============================================================================
INSERT INTO line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, serverless_mode,
    serverless_product, serverless_size,
    runs_per_day, avg_runtime_minutes, days_per_month
) VALUES (
    '20000000-0000-0000-0000-000000000009',
    '10000000-0000-0000-0000-000000000001',
    9,
    'RAG Vector Search',
    'VECTOR_SEARCH',
    NULL,   -- Not applicable
    NULL,   -- Not applicable
    'vector_search',
    'standard',
    1,
    1440,   -- 24/7 always on
    30
);

-- =============================================================================
-- 10. MODEL_SERVING - Serverless Endpoint (GPU Medium)
-- =============================================================================
INSERT INTO line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, serverless_mode,
    serverless_product, serverless_size,
    runs_per_day, avg_runtime_minutes, days_per_month
) VALUES (
    '20000000-0000-0000-0000-000000000010',
    '10000000-0000-0000-0000-000000000001',
    10,
    'ML Model Serving (GPU)',
    'MODEL_SERVING',
    NULL,   -- Not applicable
    NULL,   -- Not applicable
    'model_serving',
    'gpu_medium',
    1,
    720,    -- 12 hours per day
    30
);

-- =============================================================================
-- 11. FMAPI_DATABRICKS - Llama Model
-- =============================================================================
INSERT INTO line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, serverless_mode,
    fmapi_provider, fmapi_model,
    fmapi_input_tokens_per_month, fmapi_output_tokens_per_month
) VALUES (
    '20000000-0000-0000-0000-000000000011',
    '10000000-0000-0000-0000-000000000001',
    11,
    'Chatbot with Llama',
    'FMAPI_DATABRICKS',
    NULL,   -- Not applicable
    NULL,   -- Not applicable
    'databricks',
    'llama-3.1-70b-instruct',
    50000000,   -- 50M input tokens
    10000000    -- 10M output tokens
);

-- =============================================================================
-- 12. FMAPI_PROPRIETARY - Claude Sonnet 4
-- =============================================================================
INSERT INTO line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    serverless_enabled, serverless_mode,
    fmapi_provider, fmapi_model, fmapi_endpoint_type, fmapi_context_length,
    fmapi_input_tokens_per_month, fmapi_output_tokens_per_month
) VALUES (
    '20000000-0000-0000-0000-000000000012',
    '10000000-0000-0000-0000-000000000001',
    12,
    'Customer Support Bot (Claude)',
    'FMAPI_PROPRIETARY',
    NULL,   -- Not applicable
    NULL,   -- Not applicable
    'anthropic',
    'claude-sonnet-4-20250514',
    'global',
    'standard',
    100000000,  -- 100M input tokens
    20000000    -- 20M output tokens
);

-- =============================================================================
-- 13. LAKEBASE - 4 CU with HA
-- =============================================================================
INSERT INTO line_items (
    line_item_id, estimate_id, display_order, workload_name, workload_type,
    lakebase_cu, lakebase_storage_gb, lakebase_ha_enabled, lakebase_backup_retention_days,
    runs_per_day, avg_runtime_minutes, days_per_month
) VALUES (
    '20000000-0000-0000-0000-000000000013',
    '10000000-0000-0000-0000-000000000001',
    13,
    'Operational Database',
    'LAKEBASE',
    4,      -- 4 CU = 4 DBU/hour
    500,    -- 500 GB storage
    true,   -- High availability enabled
    14,     -- 14 days backup retention
    1,
    1440,   -- 24/7 always on
    30
);

-- =============================================================================
-- VERIFICATION: Query the cost calculation view
-- =============================================================================
-- After inserting, run this query to see calculated costs for all line items:

/*
SELECT 
    display_order,
    workload_name,
    workload_type,
    serverless_enabled,
    serverless_mode,
    dbu_per_hour,
    hours_per_month,
    dbu_per_month,
    dbu_cost_per_month,
    vm_cost_per_month,
    cost_per_month,
    price_per_dbu
FROM v_line_items_with_costs
WHERE estimate_id = '10000000-0000-0000-0000-000000000001'
ORDER BY display_order;
*/

-- =============================================================================
-- CLEANUP (Optional - run this to remove test data)
-- =============================================================================
/*
DELETE FROM line_items WHERE estimate_id = '10000000-0000-0000-0000-000000000001';
DELETE FROM estimates WHERE estimate_id = '10000000-0000-0000-0000-000000000001';
DELETE FROM users WHERE user_id = '00000000-0000-0000-0000-000000000001';
*/

