-- Generated from the canonical installer function sources.
-- Regenerate when scripts/functions changes.
-- Source: scripts/functions/01_Utility_Functions.py
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

-- LAKEMETER_STATEMENT_BOUNDARY

-- Source: scripts/functions/01_Utility_Functions.py
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

-- LAKEMETER_STATEMENT_BOUNDARY

-- Source: scripts/functions/01_Utility_Functions.py
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

        WHEN 'DATABRICKS_APPS' THEN
            v_product_type := 'ALL_PURPOSE_SERVERLESS_COMPUTE';

        WHEN 'AI_PARSE' THEN
            v_product_type := 'SERVERLESS_REAL_TIME_INFERENCE';

        WHEN 'AI_EXTRACT' THEN
            v_product_type := 'SERVERLESS_REAL_TIME_INFERENCE';

        WHEN 'AI_CLASSIFY' THEN
            v_product_type := 'SERVERLESS_REAL_TIME_INFERENCE';

        WHEN 'AI_GATEWAY' THEN
            v_product_type := 'SERVERLESS_REAL_TIME_INFERENCE';

        WHEN 'AGENT_EVALUATION' THEN
            v_product_type := 'SERVERLESS_REAL_TIME_INFERENCE';

        WHEN 'AI_RUNTIME' THEN
            v_product_type := 'MODEL_TRAINING';

        WHEN 'GENERAL_STORAGE' THEN
            v_product_type := 'DATABRICKS_STORAGE';

        WHEN 'ZEROBUS' THEN
            v_product_type := 'JOBS_SERVERLESS_COMPUTE';

        WHEN 'SHUTTERSTOCK_IMAGEAI' THEN
            v_product_type := 'SERVERLESS_REAL_TIME_INFERENCE';

        WHEN 'LAKEFLOW_CONNECT' THEN
            v_product_type := 'JOBS_SERVERLESS_COMPUTE';
        
        ELSE
            RAISE EXCEPTION 'Unsupported workload type: %', p_workload_type
                USING ERRCODE = '22023';
    END CASE;
    
    RETURN v_product_type;
END;
$$;

-- LAKEMETER_STATEMENT_BOUNDARY

-- Source: scripts/functions/01_Utility_Functions.py
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

-- LAKEMETER_STATEMENT_BOUNDARY

-- Source: scripts/functions/01_Utility_Functions.py
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

-- LAKEMETER_STATEMENT_BOUNDARY

-- Source: scripts/functions/02_DBU_Calculators_Classic.py
CREATE OR REPLACE FUNCTION lakemeter.calculate_classic_compute_dbu(
    p_cloud VARCHAR,
    p_driver_node_type VARCHAR,
    p_worker_node_type VARCHAR,
    p_num_workers INT,
    p_photon_enabled BOOLEAN,
    p_workload_type VARCHAR,
    p_dlt_edition VARCHAR DEFAULT NULL
)
RETURNS DECIMAL(18,4)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_driver_dbu DECIMAL(18,4);
    v_worker_dbu DECIMAL(18,4);
    v_photon_multiplier DECIMAL(10,4);
    v_total_dbu DECIMAL(18,4);
BEGIN
    -- Get driver DBU rate
    SELECT dbu_rate INTO v_driver_dbu
    FROM lakemeter.sync_ref_instance_dbu_rates
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(instance_type) = UPPER(p_driver_node_type)
    LIMIT 1;
    
    -- Get worker DBU rate
    SELECT dbu_rate INTO v_worker_dbu
    FROM lakemeter.sync_ref_instance_dbu_rates
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(instance_type) = UPPER(p_worker_node_type)
    LIMIT 1;
    
    -- Get Photon multiplier
    v_photon_multiplier := lakemeter.get_photon_multiplier(
        p_cloud,
        p_workload_type,
        p_dlt_edition,
        p_photon_enabled,
        FALSE  -- serverless_enabled = FALSE for classic
    );
    
    -- Calculate total DBU
    v_total_dbu := (
        COALESCE(v_driver_dbu, 0) + 
        (COALESCE(v_worker_dbu, 0) * COALESCE(p_num_workers, 0))
    ) * v_photon_multiplier;
    
    RETURN v_total_dbu;
END;
$$;

COMMENT ON FUNCTION lakemeter.calculate_classic_compute_dbu IS 
'Calculate DBU per hour for classic compute workloads (JOBS/ALL_PURPOSE/DLT Classic).
Formula: (driver_dbu + worker_dbu × num_workers) × photon_multiplier';

-- LAKEMETER_STATEMENT_BOUNDARY

-- Source: scripts/functions/03_DBU_Calculators_Serverless.py
CREATE OR REPLACE FUNCTION lakemeter.calculate_serverless_compute_dbu(
    p_cloud VARCHAR,
    p_driver_node_type VARCHAR,
    p_worker_node_type VARCHAR,
    p_num_workers INT,
    p_workload_type VARCHAR DEFAULT 'JOBS',
    p_serverless_mode VARCHAR DEFAULT 'standard'
)
RETURNS DECIMAL(18,4)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_driver_dbu DECIMAL(18,4);
    v_worker_dbu DECIMAL(18,4);
    v_photon_multiplier DECIMAL(10,4);
    v_mode_multiplier DECIMAL(10,4);
    v_total_dbu DECIMAL(18,4);
BEGIN
    -- Get driver DBU rate (used for sizing estimation)
    SELECT dbu_rate INTO v_driver_dbu
    FROM lakemeter.sync_ref_instance_dbu_rates
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(instance_type) = UPPER(p_driver_node_type)
    LIMIT 1;
    
    -- Get worker DBU rate (used for sizing estimation)
    SELECT dbu_rate INTO v_worker_dbu
    FROM lakemeter.sync_ref_instance_dbu_rates
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(instance_type) = UPPER(p_worker_node_type)
    LIMIT 1;
    
    -- Get Photon multiplier (Photon is MANDATORY for serverless, but multiplier still applies)
    v_photon_multiplier := lakemeter.get_photon_multiplier(
        p_cloud,
        p_workload_type,
        NULL,  -- dlt_edition not needed for serverless
        TRUE,  -- photon_enabled = TRUE (always for serverless)
        TRUE   -- serverless_enabled = TRUE
    );
    
    -- Interactive notebooks do not support Standard mode, so All-Purpose
    -- Serverless always uses the Performance Optimized multiplier.
    v_mode_multiplier := CASE
        WHEN UPPER(COALESCE(p_workload_type, '')) = 'ALL_PURPOSE' THEN 2.0
        WHEN LOWER(COALESCE(p_serverless_mode, 'standard')) = 'performance' THEN 2.0
        ELSE 1.0
    END;
    
    -- Calculate total DBU
    -- Formula: (base DBU) × photon_multiplier × mode_multiplier
    v_total_dbu := (
        COALESCE(v_driver_dbu, 0) + 
        (COALESCE(v_worker_dbu, 0) * COALESCE(p_num_workers, 0))
    ) * v_photon_multiplier * v_mode_multiplier;
    
    RETURN v_total_dbu;
END;
$$;

COMMENT ON FUNCTION lakemeter.calculate_serverless_compute_dbu IS 
'Calculate DBU per hour for serverless compute workloads (JOBS/ALL_PURPOSE/DLT Serverless).
Formula: (driver_dbu + worker_dbu × num_workers) × photon_multiplier × serverless_mode_multiplier
Photon is MANDATORY for serverless, and the multiplier still applies.
Serverless mode: All-Purpose always uses performance (2x); Jobs and DLT use
standard (1x) or performance (2x) according to the selected mode';

-- LAKEMETER_STATEMENT_BOUNDARY

-- Source: scripts/functions/04_DBU_Calculators_DBSQL.py
CREATE OR REPLACE FUNCTION lakemeter.calculate_dbsql_dbu(
    p_cloud VARCHAR,
    p_dbsql_warehouse_type VARCHAR,
    p_dbsql_warehouse_size VARCHAR,
    p_dbsql_num_clusters INT DEFAULT 1
)
RETURNS DECIMAL(18,4)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_dbu_per_hour DECIMAL(18,4);
    v_total_dbu DECIMAL(18,4);
BEGIN
    -- Lookup DBU per hour from warehouse configuration
    SELECT dbu_per_hour INTO v_dbu_per_hour
    FROM lakemeter.sync_product_dbsql_rates
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND warehouse_type = LOWER(p_dbsql_warehouse_type)
      AND UPPER(warehouse_size) = UPPER(p_dbsql_warehouse_size)
    LIMIT 1;
    
    -- Calculate total DBU (DBU per warehouse × number of clusters)
    v_total_dbu := COALESCE(v_dbu_per_hour, 0) * COALESCE(p_dbsql_num_clusters, 1);
    
    RETURN v_total_dbu;
END;
$$;

COMMENT ON FUNCTION lakemeter.calculate_dbsql_dbu IS 
'Calculate DBU per hour for DBSQL workloads (Classic, Pro, Serverless).
Formula: warehouse_dbu_per_hour × num_clusters
Lookup from: sync_product_dbsql_rates';

-- LAKEMETER_STATEMENT_BOUNDARY

-- Source: scripts/functions/05_DBU_Calculators_Vector_Model.py
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
    -- Lookup DBU rate for AI Search mode
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
'Calculate DBU per hour for AI Search workloads.
Formula: CEILING(capacity_millions / divisor) × dbu_rate
Divisors: standard=2M per unit, storage_optimized=64M per unit
Always rounds UP to next unit.';

-- LAKEMETER_STATEMENT_BOUNDARY

-- Source: scripts/functions/05_DBU_Calculators_Vector_Model.py
CREATE OR REPLACE FUNCTION lakemeter.calculate_model_serving_dbu(
    p_cloud VARCHAR,
    p_serverless_size VARCHAR,
    p_concurrency INT DEFAULT 4
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
    
    RETURN COALESCE(v_dbu_rate, 0) * CASE
        WHEN LOWER(COALESCE(p_serverless_size, 'cpu')) LIKE 'cpu%'
            THEN COALESCE(p_concurrency, 4)
        ELSE COALESCE(p_concurrency, 4) / 4.0
    END;
END;
$$;

COMMENT ON FUNCTION lakemeter.calculate_model_serving_dbu IS 
'Calculate DBU per hour for Model Serving workloads.
CPU rates are billed per concurrency unit. GPU rates are billed per replica,
with one replica provisioned for every four concurrency units.
Lookup from: sync_product_serverless_rates';

-- LAKEMETER_STATEMENT_BOUNDARY

-- Source: scripts/functions/06_DBU_Calculators_FMAPI.py
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

-- LAKEMETER_STATEMENT_BOUNDARY

-- Source: scripts/functions/06_DBU_Calculators_FMAPI.py
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

-- LAKEMETER_STATEMENT_BOUNDARY

-- Source: scripts/functions/06_DBU_Calculators_FMAPI.py
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

-- LAKEMETER_STATEMENT_BOUNDARY

-- Source: scripts/functions/06_DBU_Calculators_FMAPI.py
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

-- LAKEMETER_STATEMENT_BOUNDARY

-- Source: scripts/functions/08_VM_Cost_Calculators.py
CREATE OR REPLACE FUNCTION lakemeter.calculate_classic_vm_costs(
    p_cloud VARCHAR,
    p_region VARCHAR,
    p_driver_node_type VARCHAR,
    p_worker_node_type VARCHAR,
    p_num_workers INT,
    p_driver_pricing_tier VARCHAR,
    p_worker_pricing_tier VARCHAR,
    p_hours_per_month DECIMAL,
    p_driver_payment_option VARCHAR DEFAULT 'NA',
    p_worker_payment_option VARCHAR DEFAULT 'NA'
)
RETURNS TABLE(
    driver_vm_cost_per_hour DECIMAL(18,4),
    worker_vm_cost_per_hour DECIMAL(18,4),
    total_vm_cost_per_hour DECIMAL(18,4),
    driver_vm_cost_per_month DECIMAL(18,4),
    total_worker_vm_cost_per_month DECIMAL(18,4),
    total_vm_cost_per_month DECIMAL(18,4)
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_driver_cost_per_hour DECIMAL(18,4);
    v_worker_cost_per_hour DECIMAL(18,4);
    v_total_cost_per_hour DECIMAL(18,4);
    v_driver_cost_per_month DECIMAL(18,4);
    v_worker_cost_per_month DECIMAL(18,4);
    v_total_cost_per_month DECIMAL(18,4);
BEGIN
    -- Lookup driver VM cost (driver can ONLY be on-demand or reserved, NEVER spot)
    SELECT cost_per_hour INTO v_driver_cost_per_hour
    FROM lakemeter.sync_pricing_vm_costs
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(region) = UPPER(p_region)
      AND UPPER(instance_type) = UPPER(p_driver_node_type)
      AND UPPER(pricing_tier) = UPPER(p_driver_pricing_tier)
      AND UPPER(payment_option) = UPPER(COALESCE(p_driver_payment_option, 'NA'))
      AND UPPER(pricing_tier) != 'SPOT'  -- Enforce: driver cannot be spot
    LIMIT 1;
    
    -- Lookup worker VM cost
    SELECT cost_per_hour INTO v_worker_cost_per_hour
    FROM lakemeter.sync_pricing_vm_costs
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(region) = UPPER(p_region)
      AND UPPER(instance_type) = UPPER(p_worker_node_type)
      AND UPPER(pricing_tier) = UPPER(p_worker_pricing_tier)
      AND UPPER(payment_option) = UPPER(COALESCE(p_worker_payment_option, 'NA'))
    LIMIT 1;
    
    -- Calculate costs
    v_driver_cost_per_hour := COALESCE(v_driver_cost_per_hour, 0);
    v_worker_cost_per_hour := COALESCE(v_worker_cost_per_hour, 0) * COALESCE(p_num_workers, 0);
    v_total_cost_per_hour := v_driver_cost_per_hour + v_worker_cost_per_hour;
    
    v_driver_cost_per_month := v_driver_cost_per_hour * COALESCE(p_hours_per_month, 0);
    v_worker_cost_per_month := v_worker_cost_per_hour * COALESCE(p_hours_per_month, 0);
    v_total_cost_per_month := v_total_cost_per_hour * COALESCE(p_hours_per_month, 0);
    
    -- Return as table
    RETURN QUERY SELECT 
        v_driver_cost_per_hour,
        v_worker_cost_per_hour,
        v_total_cost_per_hour,
        v_driver_cost_per_month,
        v_worker_cost_per_month,
        v_total_cost_per_month;
END;
$$;

COMMENT ON FUNCTION lakemeter.calculate_classic_vm_costs IS 
'Calculate VM costs for classic compute workloads (JOBS/ALL_PURPOSE/DLT Classic).
Returns detailed breakdown: driver, worker, total (per hour and per month).
Driver constraint: CANNOT be spot (on-demand or reserved only).
Worker: Can be on-demand, spot, or reserved.';

-- LAKEMETER_STATEMENT_BOUNDARY

-- Source: scripts/functions/08_VM_Cost_Calculators.py
CREATE OR REPLACE FUNCTION lakemeter.calculate_dbsql_vm_costs(
    p_cloud VARCHAR,
    p_region VARCHAR,
    p_dbsql_warehouse_type VARCHAR,
    p_dbsql_warehouse_size VARCHAR,
    p_dbsql_num_clusters INT,
    p_vm_pricing_tier VARCHAR,
    p_hours_per_month DECIMAL,
    p_vm_payment_option VARCHAR DEFAULT 'NA'
)
RETURNS TABLE(
    driver_vm_cost_per_hour DECIMAL(18,4),
    worker_vm_cost_per_hour DECIMAL(18,4),
    total_vm_cost_per_hour DECIMAL(18,4),
    driver_vm_cost_per_month DECIMAL(18,4),
    total_worker_vm_cost_per_month DECIMAL(18,4),
    total_vm_cost_per_month DECIMAL(18,4)
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_warehouse_type VARCHAR;
    v_driver_instance VARCHAR;
    v_worker_instance VARCHAR;
    v_num_workers INT;
    v_driver_cost_per_hour DECIMAL(18,4);
    v_worker_cost_per_hour DECIMAL(18,4);
    v_total_cost_per_hour DECIMAL(18,4);
    v_driver_cost_per_month DECIMAL(18,4);
    v_worker_cost_per_month DECIMAL(18,4);
    v_total_cost_per_month DECIMAL(18,4);
BEGIN
    -- Normalize string inputs to LOWERCASE for case-insensitive matching
    -- Note: sync_ref_dbsql_warehouse_config uses lowercase values (classic, pro, serverless)
    v_warehouse_type := LOWER(p_dbsql_warehouse_type);
    
    -- Lookup warehouse configuration (instance types and counts)
    SELECT driver_instance_type, worker_instance_type, worker_count
    INTO v_driver_instance, v_worker_instance, v_num_workers
    FROM lakemeter.sync_ref_dbsql_warehouse_config
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND LOWER(warehouse_type) = LOWER(v_warehouse_type)
      AND UPPER(warehouse_size) = UPPER(p_dbsql_warehouse_size)
    LIMIT 1;
    
    -- Lookup driver VM cost
    SELECT cost_per_hour INTO v_driver_cost_per_hour
    FROM lakemeter.sync_pricing_vm_costs
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(region) = UPPER(p_region)
      AND UPPER(instance_type) = UPPER(v_driver_instance)
      AND UPPER(pricing_tier) = UPPER(p_vm_pricing_tier)
      AND UPPER(payment_option) = UPPER(COALESCE(p_vm_payment_option, 'NA'))
      AND UPPER(pricing_tier) != 'SPOT'  -- Driver cannot be spot
    LIMIT 1;
    
    -- Lookup worker VM cost
    SELECT cost_per_hour INTO v_worker_cost_per_hour
    FROM lakemeter.sync_pricing_vm_costs
    WHERE UPPER(cloud) = UPPER(p_cloud)
      AND UPPER(region) = UPPER(p_region)
      AND UPPER(instance_type) = UPPER(v_worker_instance)
      AND UPPER(pricing_tier) = UPPER(p_vm_pricing_tier)
      AND UPPER(payment_option) = UPPER(COALESCE(p_vm_payment_option, 'NA'))
    LIMIT 1;
    
    -- Calculate costs
    v_driver_cost_per_hour := COALESCE(v_driver_cost_per_hour, 0) * COALESCE(p_dbsql_num_clusters, 1);
    v_worker_cost_per_hour := COALESCE(v_worker_cost_per_hour, 0) * COALESCE(v_num_workers, 0) * COALESCE(p_dbsql_num_clusters, 1);
    v_total_cost_per_hour := v_driver_cost_per_hour + v_worker_cost_per_hour;
    
    v_driver_cost_per_month := v_driver_cost_per_hour * COALESCE(p_hours_per_month, 0);
    v_worker_cost_per_month := v_worker_cost_per_hour * COALESCE(p_hours_per_month, 0);
    v_total_cost_per_month := v_total_cost_per_hour * COALESCE(p_hours_per_month, 0);
    
    -- Return as table
    RETURN QUERY SELECT 
        v_driver_cost_per_hour,
        v_worker_cost_per_hour,
        v_total_cost_per_hour,
        v_driver_cost_per_month,
        v_worker_cost_per_month,
        v_total_cost_per_month;
END;
$$;

COMMENT ON FUNCTION lakemeter.calculate_dbsql_vm_costs IS 
'Calculate VM costs for DBSQL Classic and Pro workloads.
Maps warehouse_type + size → instance types → VM costs.
Multiplies by num_clusters.
Returns detailed breakdown: driver, worker, total (per hour and per month).';

-- LAKEMETER_STATEMENT_BOUNDARY

-- Source: scripts/functions/09_Main_Orchestrator.py
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

-- LAKEMETER_STATEMENT_BOUNDARY

-- Source: scripts/functions/09_Main_Orchestrator.py
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
    
    -- AI Search
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
    p_dbsql_vm_payment_option VARCHAR DEFAULT 'NA',
    p_model_serving_concurrency INT DEFAULT 4
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
        
        -- AI Search (hourly pricing, 24/7 availability)
        WHEN 'VECTOR_SEARCH' THEN
            v_dbu_per_hour := lakemeter.calculate_vector_search_dbu(
                p_cloud, p_vector_search_mode, p_vector_search_capacity_millions
            );
            v_dbu_per_month := v_dbu_per_hour * v_hours_per_month;
        
        -- Model Serving (hourly pricing, 24/7 availability)
        WHEN 'MODEL_SERVING' THEN
            v_dbu_per_hour := lakemeter.calculate_model_serving_dbu(
                p_cloud,
                p_model_serving_gpu_type,
                p_model_serving_concurrency
            );
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

-- LAKEMETER_STATEMENT_BOUNDARY

-- Marketplace bootstrap helper
CREATE OR REPLACE FUNCTION lakemeter.calculate_lakebase_dbu(
    p_lakebase_cu INT DEFAULT 0,
    p_lakebase_ha_nodes INT DEFAULT 1
)
RETURNS DECIMAL(18,4)
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    RETURN (COALESCE(p_lakebase_cu, 0) * COALESCE(p_lakebase_ha_nodes, 1))::DECIMAL(18,4);
END;
$$;
