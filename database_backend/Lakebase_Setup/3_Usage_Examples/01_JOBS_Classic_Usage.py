# Databricks notebook source
# MAGIC %md
# MAGIC # 📘 Usage Guide: JOBS Classic
# MAGIC
# MAGIC **Workload Type:** `JOBS`  
# MAGIC **Compute Mode:** Classic (user-managed clusters)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 🧮 Cost Formula
# MAGIC
# MAGIC ```
# MAGIC Total Cost = DBU Cost + VM Cost
# MAGIC
# MAGIC WHERE:
# MAGIC   DBU Cost = (Driver DBU/hour + Worker DBU/hour × num_workers) 
# MAGIC              × Photon Multiplier (from sync_ref_dbu_multipliers)
# MAGIC              × hours_per_month 
# MAGIC              × DBU Price ($/DBU from sync_pricing_dbu_rates)
# MAGIC
# MAGIC   VM Cost = (Driver VM $/hour + Worker VM $/hour × num_workers) 
# MAGIC             × hours_per_month
# MAGIC
# MAGIC   hours_per_month = runs_per_day × (avg_runtime_minutes / 60) × days_per_month
# MAGIC ```
# MAGIC
# MAGIC **Key Components:**
# MAGIC - **DBU rates:** Queried from `sync_ref_instance_dbu_rates` by cloud and instance type
# MAGIC - **Photon multiplier:** **OPTIONAL for Classic** - set `photon_enabled = TRUE` to apply multiplier from `sync_ref_dbu_multipliers`, or `FALSE` for 1.0x (no multiplier)
# MAGIC - **DBU price:** Queried from `sync_pricing_dbu_rates` by cloud, region, tier, and product type
# MAGIC - **VM costs:** Queried from `sync_pricing_vm_costs` by cloud, region, instance type, pricing tier, and payment option
# MAGIC - **Driver and worker:** Can have different pricing tiers and payment options
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## ✅ How to Validate Your Inputs
# MAGIC
# MAGIC **Validation Tables:** `lakemeter.sync_ref_instance_dbu_rates` + `lakemeter.sync_pricing_vm_costs`
# MAGIC
# MAGIC **What to validate:**
# MAGIC - Instance Type has DBU rates defined (for compute cost)
# MAGIC - Instance Type has VM costs defined for Cloud + Region + Pricing Tier + Payment Option
# MAGIC
# MAGIC **Validation queries:**
# MAGIC ```sql
# MAGIC -- Check DBU rates exist for instance type
# MAGIC SELECT * FROM lakemeter.sync_ref_instance_dbu_rates
# MAGIC WHERE UPPER(cloud) = UPPER('AWS')
# MAGIC   AND UPPER(instance_type) = UPPER('i3.xlarge');
# MAGIC
# MAGIC -- Check VM costs exist for region + pricing tier + payment option
# MAGIC SELECT * FROM lakemeter.sync_pricing_vm_costs
# MAGIC WHERE UPPER(cloud) = UPPER('AWS')
# MAGIC   AND UPPER(region) = UPPER('us-east-1')
# MAGIC   AND UPPER(instance_type) = UPPER('i3.xlarge')
# MAGIC   AND UPPER(pricing_tier) = UPPER('on_demand')
# MAGIC   AND UPPER(payment_option) = UPPER('NA');
# MAGIC ```
# MAGIC
# MAGIC **Note:** `pricing_tier` = on_demand/spot/reserved_1y/reserved_3y, `payment_option` = NA/no_upfront/partial_upfront/all_upfront
# MAGIC
# MAGIC If this query returns rows → Valid combination ✅  
# MAGIC If this query returns 0 rows → Invalid combination ❌ (will result in $0 VM cost)
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📋 Required Parameters (36 total)
# MAGIC
# MAGIC | Position | Parameter | Type | Description | Example |
# MAGIC |----------|-----------|------|-------------|---------|
# MAGIC | 1 | `p_workload_type` | VARCHAR | Workload type | `'JOBS'` |
# MAGIC | 2 | `p_cloud` | VARCHAR | Cloud provider | `'AWS'` |
# MAGIC | 3 | `p_region` | VARCHAR | Cloud region | `'us-east-1'` |
# MAGIC | 4 | `p_tier` | VARCHAR | Pricing tier | `'PREMIUM'` |
# MAGIC | 5 | `p_serverless_enabled` | BOOLEAN | Serverless mode | `FALSE` (Classic) |
# MAGIC | 6 | `p_photon_enabled` | BOOLEAN | Photon enabled | `TRUE` |
# MAGIC | 7 | `p_dlt_edition` | VARCHAR | DLT edition | `NULL` (N/A for Jobs) |
# MAGIC | 8 | `p_driver_node_type` | VARCHAR | Driver instance | `'i3.xlarge'` |
# MAGIC | 9 | `p_worker_node_type` | VARCHAR | Worker instance | `'i3.2xlarge'` |
# MAGIC | 10 | `p_num_workers` | INT | Number of workers | `4` |
# MAGIC | 11 | `p_driver_pricing_tier` | VARCHAR | Driver VM tier | `'on_demand'` |
# MAGIC | 12 | `p_worker_pricing_tier` | VARCHAR | Worker VM tier | `'reserved_1y_no_upfront'` |
# MAGIC | 13 | `p_runs_per_day` | INT | Job runs per day | `8` |
# MAGIC | 14 | `p_avg_runtime_minutes` | INT | Avg runtime (min) | `60` |
# MAGIC | 15 | `p_days_per_month` | INT | Days per month | `30` |
# MAGIC | 16 | `p_hours_per_month` | INT | Override hours | `NULL` (auto-calc) |
# MAGIC | 17 | `p_serverless_mode` | VARCHAR | Serverless mode | `NULL` (N/A) |
# MAGIC | 18 | `p_dbsql_warehouse_type` | VARCHAR | DBSQL type | `NULL` (N/A) |
# MAGIC | 19 | `p_dbsql_warehouse_size` | VARCHAR | DBSQL size | `NULL` (N/A) |
# MAGIC | 20 | `p_dbsql_num_clusters` | INT | DBSQL clusters | `1` (default) |
# MAGIC | 21 | `p_dbsql_vm_pricing_tier` | VARCHAR | DBSQL VM tier | `'NA'` |
# MAGIC | 22 | `p_vector_search_mode` | VARCHAR | VS mode | `NULL` (N/A) |
# MAGIC | 23 | `p_vector_search_capacity_millions` | DECIMAL | VS capacity | `0` (N/A) |
# MAGIC | 24 | `p_model_serving_gpu_type` | VARCHAR | Model serving GPU | `NULL` (N/A) |
# MAGIC | 25 | `p_fmapi_model` | VARCHAR | FMAPI model | `NULL` (N/A) |
# MAGIC | 26 | `p_fmapi_provider` | VARCHAR | FMAPI provider | `NULL` (N/A) |
# MAGIC | 27 | `p_fmapi_endpoint_type` | VARCHAR | FMAPI endpoint | `'global'` (default) |
# MAGIC | 28 | `p_fmapi_context_length` | VARCHAR | FMAPI context | `'all'` (default) |
# MAGIC | 29 | `p_fmapi_rate_type` | VARCHAR | FMAPI rate type | `'input_token'` (default) |
# MAGIC | 30 | `p_fmapi_quantity` | BIGINT | Token/hour quantity | `0` (N/A) |
# MAGIC | 31 | `p_lakebase_cu` | INT | Lakebase CU | `0` (N/A) |
# MAGIC | 32 | `p_lakebase_ha_nodes` | INT | Lakebase HA nodes | `1` (default) |
# MAGIC | 33 | `p_driver_payment_option` | VARCHAR | Driver payment | `'NA'` (AWS only) |
# MAGIC | 34 | `p_worker_payment_option` | VARCHAR | Worker payment | `'reserved_1y_no_upfront'` |
# MAGIC | 35 | `p_dbsql_vm_payment_option` | VARCHAR | DBSQL payment | `'NA'` |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 💡 Example Usage
# MAGIC
# MAGIC ### Example 1: Basic Job - On-Demand VMs, Photon Enabled

# COMMAND ----------

# Load Lakebase config
%run ../00_Lakebase_Config

# COMMAND ----------

import psycopg2

def get_connection():
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DB,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD
    )

def execute_query(query, params=None, fetch=True):
    import pandas as pd
    conn = get_connection()
    try:
        if fetch:
            return pd.read_sql(query, conn, params=params)
        else:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            cursor.close()
    finally:
        conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 📋 Example Scenario
# MAGIC
# MAGIC **Use Case:** A scheduled ETL job running on AWS in PREMIUM tier
# MAGIC
# MAGIC **Scenario Details:**
# MAGIC - Job runs 8 times per day, each run takes 60 minutes
# MAGIC - Uses 1 driver node (i3.xlarge) + 4 worker nodes (i3.2xlarge)
# MAGIC - Photon acceleration enabled for better performance
# MAGIC - All VMs use on-demand pricing
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 📊 Parameter Values Explained
# MAGIC
# MAGIC | Parameter | Value | What It Represents |
# MAGIC |-----------|-------|-------------------|
# MAGIC | **Core Identifiers** | | |
# MAGIC | `p_workload_type` | `'JOBS'` | Jobs workload (batch/scheduled processing) |
# MAGIC | `p_cloud` | `'AWS'` | Amazon Web Services |
# MAGIC | `p_region` | `'us-east-1'` | US East (N. Virginia) region |
# MAGIC | `p_tier` | `'PREMIUM'` | Databricks pricing tier (STANDARD/PREMIUM/ENTERPRISE) |
# MAGIC | **Compute Configuration** | | |
# MAGIC | `p_serverless_enabled` | `FALSE` | Classic compute (not serverless) |
# MAGIC | `p_photon_enabled` | `TRUE` | Photon acceleration ON (optional for classic) |
# MAGIC | `p_dlt_edition` | `NULL` | N/A for Jobs workload |
# MAGIC | `p_driver_node_type` | `'i3.xlarge'` | Driver instance type |
# MAGIC | `p_worker_node_type` | `'i3.2xlarge'` | Worker instance type (larger than driver) |
# MAGIC | `p_num_workers` | `4` | 4 worker nodes in cluster |
# MAGIC | **VM Pricing** | | |
# MAGIC | `p_driver_pricing_tier` | `'on_demand'` | Driver uses on-demand pricing |
# MAGIC | `p_worker_pricing_tier` | `'on_demand'` | Workers use on-demand pricing |
# MAGIC | **Usage Pattern** | | |
# MAGIC | `p_runs_per_day` | `8` | Job executes 8 times daily |
# MAGIC | `p_avg_runtime_minutes` | `60` | Each run takes 60 minutes (1 hour) |
# MAGIC | `p_days_per_month` | `30` | Calculated over 30 days |
# MAGIC | `p_hours_per_month` | `NULL` | Auto-calculated: 8 runs × 1 hour × 30 days = 240 hours |
# MAGIC | **Serverless Mode** | | |
# MAGIC | `p_serverless_mode` | `NULL` | N/A for classic compute |
# MAGIC | **DBSQL** | | |
# MAGIC | `p_dbsql_warehouse_type` | `NULL` | N/A for Jobs workload |
# MAGIC | `p_dbsql_warehouse_size` | `NULL` | N/A for Jobs workload |
# MAGIC | `p_dbsql_num_clusters` | `1` | Default value |
# MAGIC | `p_dbsql_vm_pricing_tier` | `'on_demand'` | Default value |
# MAGIC | **Vector Search** | | |
# MAGIC | `p_vector_search_mode` | `NULL` | N/A for Jobs workload |
# MAGIC | `p_vector_search_capacity_millions` | `0` | N/A for Jobs workload |
# MAGIC | **Model Serving** | | |
# MAGIC | `p_model_serving_gpu_type` | `NULL` | N/A for Jobs workload |
# MAGIC | **FMAPI** | | |
# MAGIC | `p_fmapi_model` | `NULL` | N/A for Jobs workload |
# MAGIC | `p_fmapi_provider` | `NULL` | N/A for Jobs workload |
# MAGIC | `p_fmapi_endpoint_type` | `'global'` | Default value |
# MAGIC | `p_fmapi_context_length` | `'all'` | Default value |
# MAGIC | `p_fmapi_rate_type` | `'input_token'` | Default value |
# MAGIC | `p_fmapi_quantity` | `0` | N/A for Jobs workload |
# MAGIC | **Lakebase** | | |
# MAGIC | `p_lakebase_cu` | `0` | N/A for Jobs workload |
# MAGIC | `p_lakebase_ha_nodes` | `1` | Default value |
# MAGIC | **Payment Options** | | |
# MAGIC | `p_driver_payment_option` | `'NA'` | Not AWS reserved (on-demand) |
# MAGIC | `p_worker_payment_option` | `'NA'` | Not AWS reserved (on-demand) |
# MAGIC | `p_dbsql_vm_payment_option` | `'NA'` | N/A for Jobs workload |
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ## 💻 Function Call

# COMMAND ----------

query = """
SELECT * FROM lakemeter.calculate_line_item_costs(
    'JOBS'::VARCHAR,                         -- p_workload_type
    'AWS'::VARCHAR,                          -- p_cloud
    'us-east-1'::VARCHAR,                    -- p_region
    'PREMIUM'::VARCHAR,                      -- p_tier
    FALSE::BOOLEAN,                          -- p_serverless_enabled (Classic)
    TRUE::BOOLEAN,                           -- p_photon_enabled
    NULL::VARCHAR,                           -- p_dlt_edition
    'i3.xlarge'::VARCHAR,                    -- p_driver_node_type
    'i3.2xlarge'::VARCHAR,                   -- p_worker_node_type
    4::INT,                                  -- p_num_workers
    'on_demand'::VARCHAR,                    -- p_driver_pricing_tier
    'on_demand'::VARCHAR,                    -- p_worker_pricing_tier
    8::INT,                                  -- p_runs_per_day
    60::INT,                                 -- p_avg_runtime_minutes
    30::INT,                                 -- p_days_per_month
    NULL::INT,                               -- p_hours_per_month (auto-calc)
    NULL::VARCHAR,                           -- p_serverless_mode
    NULL::VARCHAR,                           -- p_dbsql_warehouse_type
    NULL::VARCHAR,                           -- p_dbsql_warehouse_size
    1::INT,                                  -- p_dbsql_num_clusters
    'on_demand'::VARCHAR,                    -- p_dbsql_vm_pricing_tier
    NULL::VARCHAR,                           -- p_vector_search_mode
    0::DECIMAL,                              -- p_vector_search_capacity_millions
    NULL::VARCHAR,                           -- p_model_serving_gpu_type
    NULL::VARCHAR,                           -- p_fmapi_model
    NULL::VARCHAR,                           -- p_fmapi_provider
    'global'::VARCHAR,                       -- p_fmapi_endpoint_type
    'all'::VARCHAR,                          -- p_fmapi_context_length
    'input_token'::VARCHAR,                  -- p_fmapi_rate_type
    0::BIGINT,                               -- p_fmapi_quantity
    0::INT,                                  -- p_lakebase_cu
    1::INT,                                  -- p_lakebase_ha_nodes
    'NA'::VARCHAR,                           -- p_driver_payment_option
    'NA'::VARCHAR,                           -- p_worker_payment_option
    'NA'::VARCHAR                            -- p_dbsql_vm_payment_option
);
"""

result = execute_query(query)
display(result)

