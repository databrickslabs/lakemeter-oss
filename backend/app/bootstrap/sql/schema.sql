-- Generated from scripts/install_lakemeter.py for Marketplace bootstrap.
-- Regenerate when the canonical fresh-install schema changes.
CREATE SCHEMA IF NOT EXISTS lakemeter

-- LAKEMETER_STATEMENT_BOUNDARY

CREATE TABLE IF NOT EXISTS lakemeter.users (
            user_id UUID PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            full_name VARCHAR(255),
            role VARCHAR(50),
            is_active BOOLEAN DEFAULT true,
            last_login_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )

-- LAKEMETER_STATEMENT_BOUNDARY

CREATE TABLE IF NOT EXISTS lakemeter.templates (
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
        )

-- LAKEMETER_STATEMENT_BOUNDARY

CREATE TABLE IF NOT EXISTS lakemeter.ref_cloud_tiers (
            cloud VARCHAR(20) NOT NULL,
            tier VARCHAR(50) NOT NULL,
            display_name VARCHAR(100),
            description TEXT,
            display_order INT DEFAULT 0,
            is_active BOOLEAN DEFAULT true,
            PRIMARY KEY (cloud, tier)
        )

-- LAKEMETER_STATEMENT_BOUNDARY

CREATE TABLE IF NOT EXISTS lakemeter.ref_workload_types (
            workload_type VARCHAR(50) PRIMARY KEY,
            display_name VARCHAR(100),
            description TEXT,
            show_compute_config BOOLEAN DEFAULT false,
            show_serverless_toggle BOOLEAN DEFAULT false,
            show_serverless_performance_mode BOOLEAN DEFAULT false,
            show_photon_toggle BOOLEAN DEFAULT false,
            show_dlt_config BOOLEAN DEFAULT false,
            show_dbsql_config BOOLEAN DEFAULT false,
            show_serverless_product BOOLEAN DEFAULT false,
            show_fmapi_config BOOLEAN DEFAULT false,
            show_lakebase_config BOOLEAN DEFAULT false,
            show_vector_search_mode BOOLEAN DEFAULT false,
            show_vm_pricing BOOLEAN DEFAULT false,
            show_usage_hours BOOLEAN DEFAULT false,
            show_usage_runs BOOLEAN DEFAULT false,
            show_usage_tokens BOOLEAN DEFAULT false,
            sku_product_type_standard VARCHAR(100),
            sku_product_type_photon VARCHAR(100),
            sku_product_type_serverless VARCHAR(100),
            display_order INT
        )

-- LAKEMETER_STATEMENT_BOUNDARY

CREATE TABLE IF NOT EXISTS lakemeter.estimates (
            estimate_id UUID PRIMARY KEY,
            estimate_name VARCHAR(500),
            owner_user_id UUID REFERENCES lakemeter.users(user_id),
            sfdc_account_id VARCHAR(255),
            customer_name VARCHAR(255),
            uco_id VARCHAR(255),
            opportunity_id VARCHAR(255),
            cloud VARCHAR(20),
            region VARCHAR(50),
            tier VARCHAR(20),
            status VARCHAR(20) DEFAULT 'draft',
            version INT DEFAULT 1,
            template_id UUID REFERENCES lakemeter.templates(template_id),
            original_prompt TEXT,
            is_deleted BOOLEAN DEFAULT false,
            discount_config JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by UUID REFERENCES lakemeter.users(user_id)
        )

-- LAKEMETER_STATEMENT_BOUNDARY

CREATE TABLE IF NOT EXISTS lakemeter.line_items (
            line_item_id UUID PRIMARY KEY,
            estimate_id UUID REFERENCES lakemeter.estimates(estimate_id),
            display_order INT,
            workload_name VARCHAR(255),
            workload_type VARCHAR(50) NOT NULL,
            cloud VARCHAR(20),
            serverless_enabled BOOLEAN DEFAULT false,
            serverless_mode VARCHAR(20),
            photon_enabled BOOLEAN DEFAULT false,
            driver_node_type VARCHAR(100),
            worker_node_type VARCHAR(100),
            num_workers INT,
            dlt_edition VARCHAR(20),
            dbsql_warehouse_type VARCHAR(20),
            dbsql_warehouse_size VARCHAR(20),
            dbsql_num_clusters INT DEFAULT 1,
            dbsql_vm_pricing_tier VARCHAR(20) DEFAULT 'on_demand',
            dbsql_vm_payment_option VARCHAR(20) DEFAULT 'NA',
            vector_search_mode VARCHAR(50),
            vector_capacity_millions DECIMAL(10,2),
            vector_search_storage_gb DECIMAL(10,2),
            model_serving_gpu_type VARCHAR(50),
            model_serving_concurrency INT DEFAULT 4,
            model_serving_scale_out VARCHAR(20),
            model_servings_number_endpoints INT,
            fmapi_provider VARCHAR(50),
            fmapi_model VARCHAR(100),
            fmapi_endpoint_type VARCHAR(20),
            fmapi_context_length VARCHAR(20),
            fmapi_rate_type VARCHAR(20),
            fmapi_quantity BIGINT,
            databricks_apps_size VARCHAR(20),
            databricks_apps_hours_per_month NUMERIC(12,2),
            databricks_apps_num_apps INT,
            ai_parse_calculation_method VARCHAR(20),
            ai_parse_mode VARCHAR(20),
            ai_parse_complexity VARCHAR(20),
            ai_parse_dbu_quantity NUMERIC(12,2),
            ai_parse_num_pages NUMERIC(12,2),
            ai_parse_pages_thousands NUMERIC(12,2),
            shutterstock_imageai_num_images INTEGER,
            shutterstock_images INTEGER,
            databricks_support_tier VARCHAR(50),
            databricks_support_annual_commit NUMERIC(18,2),
            lakeflow_connect_connector_type VARCHAR(50),
            lakeflow_connect_pipeline_driver_node_type VARCHAR(100),
            lakeflow_connect_pipeline_worker_node_type VARCHAR(100),
            lakeflow_connect_pipeline_num_workers INT,
            lakeflow_connect_pipeline_serverless_mode VARCHAR(20),
            lakeflow_connect_pipeline_runs_per_day INT,
            lakeflow_connect_pipeline_avg_runtime_minutes INT,
            lakeflow_connect_pipeline_hours_per_month NUMERIC(12,2),
            lakeflow_connect_gateway_cloud VARCHAR(50),
            lakeflow_connect_gateway_instance_type VARCHAR(100),
            lakeflow_connect_gateway_num_workers INT,
            lakeflow_connect_gateway_hours_per_month NUMERIC(12,2),
            lakeflow_connect_pipeline_mode VARCHAR(20),
            lakeflow_connect_gateway_enabled BOOLEAN,
            lakeflow_connect_gateway_instance VARCHAR(100),
            lakebase_cu NUMERIC(5,1),
            lakebase_storage_gb INT,
            lakebase_ha_nodes INT DEFAULT 1,
            lakebase_backup_retention_days INT DEFAULT 7,
            lakebase_pitr_gb INT,
            lakebase_snapshot_gb INT,
            runs_per_day INT,
            avg_runtime_minutes INT,
            days_per_month INT DEFAULT 30,
            hours_per_month DECIMAL(10,2),
            driver_pricing_tier VARCHAR(20),
            worker_pricing_tier VARCHAR(20),
            driver_payment_option VARCHAR(20) DEFAULT 'NA',
            worker_payment_option VARCHAR(20) DEFAULT 'NA',
            workload_config JSON,
            notes TEXT,
            cost_calculation_response JSON,
            calculation_completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )

-- LAKEMETER_STATEMENT_BOUNDARY

CREATE TABLE IF NOT EXISTS lakemeter.conversation_messages (
            message_id UUID PRIMARY KEY,
            estimate_id UUID REFERENCES lakemeter.estimates(estimate_id),
            message_role VARCHAR(20),
            message_content TEXT,
            message_sequence INT,
            message_type VARCHAR(50),
            tokens_used INT,
            model_used VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )

-- LAKEMETER_STATEMENT_BOUNDARY

CREATE TABLE IF NOT EXISTS lakemeter.decision_records (
            record_id UUID PRIMARY KEY,
            line_item_id UUID REFERENCES lakemeter.line_items(line_item_id),
            record_type VARCHAR(50),
            user_input TEXT,
            agent_response TEXT,
            assumptions JSON,
            calculations JSON,
            reasoning TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )

-- LAKEMETER_STATEMENT_BOUNDARY

CREATE TABLE IF NOT EXISTS lakemeter.sharing (
            share_id UUID PRIMARY KEY,
            estimate_id UUID REFERENCES lakemeter.estimates(estimate_id),
            share_type VARCHAR(20),
            shared_with_user_id UUID REFERENCES lakemeter.users(user_id),
            share_link VARCHAR(255) UNIQUE,
            permission VARCHAR(20),
            expires_at TIMESTAMP,
            access_count INT DEFAULT 0,
            last_accessed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )

-- LAKEMETER_STATEMENT_BOUNDARY

CREATE INDEX IF NOT EXISTS idx_line_items_estimate ON lakemeter.line_items(estimate_id)

-- LAKEMETER_STATEMENT_BOUNDARY

CREATE INDEX IF NOT EXISTS idx_line_items_workload_type ON lakemeter.line_items(workload_type)

-- LAKEMETER_STATEMENT_BOUNDARY

CREATE TABLE IF NOT EXISTS lakemeter.sync_pricing_dbu_rates (
            sku_name TEXT, cloud TEXT, tier TEXT, product_type TEXT,
            sku_region TEXT, region TEXT, usage_unit TEXT,
            price_per_dbu DOUBLE PRECISION, currency_code TEXT,
            pricing_type TEXT, fetched_at TEXT
        );
        CREATE TABLE IF NOT EXISTS lakemeter.sync_pricing_vm_costs (
            cloud TEXT, region TEXT, instance_type TEXT, pricing_tier TEXT,
            payment_option TEXT, cost_per_hour DOUBLE PRECISION,
            currency TEXT, source TEXT, fetched_at TEXT,
            updated_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS lakemeter.sync_product_dbsql_rates (
            cloud TEXT, warehouse_type TEXT, warehouse_size TEXT,
            sku_product_type TEXT, dbu_per_hour DOUBLE PRECISION,
            includes_compute BOOLEAN, updated_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS lakemeter.sync_product_fmapi_databricks (
            cloud TEXT, model TEXT, rate_type TEXT,
            dbu_rate DOUBLE PRECISION, input_divisor TEXT,
            is_hourly BOOLEAN, sku_product_type TEXT,
            updated_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS lakemeter.sync_product_fmapi_proprietary (
            provider TEXT, model TEXT, endpoint_type TEXT,
            context_length TEXT, rate_type TEXT,
            dbu_rate DOUBLE PRECISION, input_divisor TEXT,
            is_hourly BOOLEAN, sku_product_type TEXT,
            cloud TEXT, updated_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS lakemeter.sync_product_serverless_rates (
            cloud TEXT, product TEXT, size_or_model TEXT,
            rate_type TEXT, dbu_rate DOUBLE PRECISION,
            input_divisor TEXT, is_hourly BOOLEAN,
            sku_product_type TEXT, description TEXT,
            updated_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS lakemeter.sync_ref_dbsql_warehouse_config (
            cloud TEXT, warehouse_size TEXT, worker_count TEXT,
            driver_instance_type TEXT, worker_instance_type TEXT,
            warehouse_type TEXT, updated_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS lakemeter.sync_ref_dbu_multipliers (
            cloud TEXT, sku_type TEXT, feature TEXT,
            multiplier DOUBLE PRECISION, category TEXT,
            updated_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS lakemeter.sync_ref_instance_dbu_rates (
            cloud TEXT, instance_type TEXT, vcpus DOUBLE PRECISION,
            memory_gb DOUBLE PRECISION, dbu_rate DOUBLE PRECISION,
            instance_family TEXT, is_active BOOLEAN DEFAULT TRUE,
            source TEXT, updated_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS lakemeter.sync_ref_sku_region_map (
            cloud TEXT, sku_region TEXT, region_code TEXT
        );
        CREATE TABLE IF NOT EXISTS lakemeter.ref_fmapi_databricks_models (
            model_name VARCHAR PRIMARY KEY, description TEXT, is_active BOOLEAN DEFAULT TRUE
        );
        CREATE TABLE IF NOT EXISTS lakemeter.ref_fmapi_proprietary_models (
            provider VARCHAR, model_name VARCHAR, description TEXT, is_active BOOLEAN DEFAULT TRUE,
            PRIMARY KEY (provider, model_name)
        );
        CREATE TABLE IF NOT EXISTS lakemeter.ref_model_serving_gpu_types (
            cloud VARCHAR, gpu_type VARCHAR, description TEXT, is_active BOOLEAN DEFAULT TRUE,
            PRIMARY KEY (cloud, gpu_type)
        );

-- LAKEMETER_STATEMENT_BOUNDARY

CREATE TABLE IF NOT EXISTS lakemeter.sku_discount_mapping (
    sku TEXT PRIMARY KEY,
    sku_display_name TEXT,
    discount_category TEXT NOT NULL
        CHECK (discount_category IN ('dbu', 'storage', 'support', 'network', 'excluded')),
    cross_service_eligible BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT,
    workload_group TEXT,
    description TEXT
);
CREATE INDEX IF NOT EXISTS idx_sku_discount_category
    ON lakemeter.sku_discount_mapping(discount_category);
ALTER TABLE lakemeter.sku_discount_mapping
    ADD COLUMN IF NOT EXISTS workload_group TEXT;
ALTER TABLE lakemeter.sku_discount_mapping
    ADD COLUMN IF NOT EXISTS description TEXT;
CREATE TABLE IF NOT EXISTS lakemeter.app_bootstrap_state (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
    app_version TEXT NOT NULL,
    pricing_checksum TEXT NOT NULL,
    bootstrapped_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS lakemeter.ref_fmapi_databricks_models (
    model_name VARCHAR PRIMARY KEY, description TEXT, is_active BOOLEAN DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS lakemeter.ref_fmapi_proprietary_models (
    provider VARCHAR, model_name VARCHAR, description TEXT, is_active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (provider, model_name)
);
CREATE TABLE IF NOT EXISTS lakemeter.ref_model_serving_gpu_types (
    cloud VARCHAR, gpu_type VARCHAR, description TEXT, is_active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (cloud, gpu_type)
);
ALTER TABLE lakemeter.estimates
    ADD COLUMN IF NOT EXISTS display_order INT DEFAULT 0;
ALTER TABLE lakemeter.sync_pricing_dbu_rates
    ADD COLUMN IF NOT EXISTS dbu_price DOUBLE PRECISION;
ALTER TABLE lakemeter.sync_pricing_dbu_rates
    ADD COLUMN IF NOT EXISTS dbu_per_hour DOUBLE PRECISION;
ALTER TABLE lakemeter.sync_product_dbsql_rates
    ADD COLUMN IF NOT EXISTS min_clusters INT;
ALTER TABLE lakemeter.sync_product_dbsql_rates
    ADD COLUMN IF NOT EXISTS max_clusters INT;
ALTER TABLE lakemeter.sync_product_fmapi_databricks
    ADD COLUMN IF NOT EXISTS price_per_million DOUBLE PRECISION;
ALTER TABLE lakemeter.sync_product_fmapi_databricks
    ADD COLUMN IF NOT EXISTS dbu_per_million DOUBLE PRECISION;
ALTER TABLE lakemeter.sync_product_fmapi_proprietary
    ADD COLUMN IF NOT EXISTS price_per_million DOUBLE PRECISION;
ALTER TABLE lakemeter.sync_product_fmapi_proprietary
    ADD COLUMN IF NOT EXISTS dbu_per_million DOUBLE PRECISION;
ALTER TABLE lakemeter.sync_product_serverless_rates
    ADD COLUMN IF NOT EXISTS dbu_per_hour DOUBLE PRECISION;
ALTER TABLE lakemeter.sync_ref_dbsql_warehouse_config
    ADD COLUMN IF NOT EXISTS driver_count INT;
ALTER TABLE lakemeter.sync_ref_dbsql_warehouse_config
    ADD COLUMN IF NOT EXISTS instance_type VARCHAR;
