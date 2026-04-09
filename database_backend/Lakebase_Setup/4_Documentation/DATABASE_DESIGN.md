# Lakemeter - Database Design Document

| **Field** | **Details** |
|-----------|-------------|
| **Product** | Lakemeter - Databricks Sizing Tool |
| **Database** | Lakebase (Postgres) |
| **Author** | Steven Tan |
| **Date Created** | Nov 28, 2025 |
| **Last Updated** | Dec 4, 2025 |
| **Status** | In Progress |

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [ER Diagram](#er-diagram)
4. [Table Categories](#table-categories)
5. [Pricing Tables (Synced)](#pricing-tables-synced)
6. [Salesforce Tables (Synced)](#salesforce-tables-synced)
7. [Application Tables](#application-tables)
8. [Primary Keys & Indexes](#primary-keys--indexes)
9. [Sample Queries](#sample-queries)

---

## Overview

### Database Requirements

Lakemeter requires a **fast, transactional database** to support:
- **Sub-second query performance** for estimation retrieval
- **Concurrent access** from 10-20 SAs simultaneously
- **ACID compliance** for data integrity
- **Scalability** to 6,000+ estimates over 12 months

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **OLTP Database** | Lakebase (Postgres) | Application tables, low-latency queries |
| **OLAP Storage** | Delta Lake (Unity Catalog) | Source pricing data, analytics |
| **Sync Mechanism** | Sync Tables (CDC) | Auto-sync Delta → Postgres |
| **File Storage** | Databricks Volumes | Templates, exports |

---

## Architecture

### Lakebase Database: `lakemeter-db.lakemeter_pricing`

```

```

---

## ER Diagram

**📊 [View ERD in Lucidchart](https://lucid.app/lucidchart/d38242f3-5c41-470f-9516-f9d60aa95c04/edit?invitationId=inv_671bba44-88cb-4c9f-88f7-6b187beaa033&page=0_0#)**

---

## Table Categories

### Summary

| Category | Count | Sync | Purpose |
|----------|-------|------|---------|
| **Application** | 8 | No (native) | Core app functionality |
| **Pricing** | 2 | Yes (CDC) | DBU/VM prices |
| **Product Rates** | 4 | Yes (CDC) | Product-specific rates |
| **Reference** | 4 | Yes (CDC) | Lookup tables |
| **Salesforce** | 3 | Yes (UC) | Customer/Opportunity lookups |
| **Total** | 21 | - | - |

### Application Tables
| Table | Primary Key | Description |
|-------|-------------|-------------|
| `users` | `user_id` | User accounts |
| `templates` | `template_id` | Estimate templates |
| `estimates` | `estimate_id` | Cost estimates |
| `line_items` | `line_item_id` | Workload configurations |
| `ref_workload_types` | `workload_type` | UI form configuration |
| `conversation_messages` | `message_id` | AI chat history |
| `decision_records` | `record_id` | AI decision audit |
| `sharing` | `share_id` | Estimate sharing |

### Synced Tables (from Unity Catalog)
| Table | Primary Key | Description |
|-------|-------------|-------------|
| `sync_pricing_dbu_rates` | `cloud, region, tier, product_type, sku_name` | DBU prices |
| `sync_pricing_vm_costs` | `cloud, region, instance_type, pricing_tier, payment_option` | VM costs |
| `sync_product_dbsql_rates` | `cloud, warehouse_type, warehouse_size` | DBSQL rates |
| `sync_product_serverless_rates` | `cloud, product, size_or_model` | Serverless rates |
| `sync_product_fmapi_databricks` | `model, rate_type` | Databricks LLM rates |
| `sync_product_fmapi_proprietary` | `cloud, provider, model, rate_type, endpoint_type, context_length` | External LLM rates |
| `sync_ref_instance_dbu_rates` | `cloud, instance_type` | Instance DBU rates |
| `sync_ref_dbu_multipliers` | `sku_type, feature` | Photon multipliers |
| `sync_ref_sku_region_map` | `cloud, sku_region` | Region mapping |
| `sync_ref_dbsql_warehouse_config` | `cloud, warehouse_type, warehouse_size` | Warehouse config |

### Salesforce Tables (from Unity Catalog)
| Table | Primary Key | Description |
|-------|-------------|-------------|
| `sync_salesforce_account` | `salesforce_account_id` | Customer accounts |
| `sync_salesforce_usecase` | `salesforce_use_case_id` | Use cases linked to customers |
| `sync_salesforce_opportunity` | `id` | Opportunities linked to accounts |

---

## Database Constraints Summary

### Application Table Constraints

| Constraint Type | Count | Examples |
|----------------|:-----:|----------|
| **PRIMARY KEYS** | 9 | All tables have UUID or composite PKs |
| **FOREIGN KEYS** | 12 | estimates→users, line_items→estimates, etc. |
| **UNIQUE** | 3 | users.email, sharing.share_link, sync_ref_sku_region_map(cloud,region_code) |
| **CHECK (Business Logic)** | 8 | serverless_requires_photon, autoscale_min_max, positive_usage |
| **CHECK (Enums)** | 15 | cloud, status, warehouse_type, pricing_tier, etc. |
| **CHECK (Ranges)** | 6 | num_workers(0-1000), days_per_month(1-31), lakebase_storage(100-10000) |
| **NOT NULL** | 6 | workload_type, email, template_name, ref_cloud_tiers columns |
| **DEFAULTS** | 43 | timestamps, booleans, numeric values |
| **INDEXES** | 2 | line_items(estimate_id), line_items(workload_type) |

**Total Constraints: ~104**

### Key Validation Rules

1. **Cloud/Tier Validation:** `estimates(cloud, tier) → ref_cloud_tiers(cloud, tier)`
   - Prevents: Azure + ENTERPRISE (not supported)
   - Status: ✅ Always active (Part 1)

2. **Cloud/Region Validation:** `estimates(cloud, region) → sync_ref_sku_region_map(cloud, region_code)`
   - Prevents: AWS + eastus (Azure region), AZURE + us-east-1 (AWS region)
   - Status: ⚠️ Run after pricing sync (Part 1.5 or `04_Add_Sync_Constraints.sql`)

3. **Instance Type Validation:** `line_items(cloud, driver/worker_node_type) → sync_ref_instance_dbu_rates(cloud, instance_type)`
   - Prevents: AWS using Azure instances (Standard_D4s_v3), Azure using AWS instances (i3.xlarge)
   - How: `line_items.cloud` auto-synced from `estimates.cloud` via trigger
   - Status: ⚠️ Run after pricing sync (Part 1.5 or `04_Add_Sync_Constraints.sql`)

4. **Workload Type Validation:** `line_items(workload_type) → ref_workload_types(workload_type)`
   - Ensures only valid workload types
   - Status: ✅ Always active (Part 1)

5. **Serverless Logic:** When `serverless_enabled = TRUE`, `photon_enabled` MUST be `TRUE`
   - Status: ✅ Always active (Part 1)

6. **Range Validations:**
   - Workers: 0-1000
   - DBSQL clusters: 1-100  
   - Days per month: 1-31
   - Lakebase storage: 100-10000 GB
   - Lakebase backup: 1-35 days
   - Status: ✅ Always active (Part 1)

### Constraint Execution Order

```
PART 1: Run 01_Create_Tables.sql
  ✅ Creates all application tables
  ✅ Adds basic constraints (cloud/tier, enums, ranges, business logic)
  ✅ Creates triggers to sync line_items.cloud from estimates.cloud
  ✅ Constraints: ~100 constraints active

PART 1.5: Run after Pricing_Sync notebooks complete
  ⚠️ Uncomment code in 01_Create_Tables.sql (Part 1.5 section)
  OR run convenience script: 04_Add_Sync_Constraints.sql
  ✅ Adds cloud/region validation (2 constraints)
  ✅ Adds instance type validation (3 constraints)
  ✅ Constraints: ~105 total constraints active

PART 2: Run 02_Create_Views.sql
  ✅ Creates cost calculation views
  ✅ Views depend on sync_* tables
```

---

## Pricing Tables (Synced)

These tables are **synced from Unity Catalog Delta tables** to Lakebase via CDC. They are **read-only** in Lakebase.

### 1. `sync_pricing_dbu_rates`

**Purpose:** DBU prices by cloud, region, tier, and product type.

| Column | Type | PK | Description |
|--------|------|:--:|-------------|
| `cloud` | VARCHAR(20) | ✓ | AWS, AZURE, GCP |
| `region` | VARCHAR(50) | ✓ | Cloud region code (us-east-1, eastus) |
| `tier` | VARCHAR(20) | ✓ | PREMIUM, ENTERPRISE |
| `product_type` | VARCHAR(100) | ✓ | JOBS_COMPUTE, SQL_COMPUTE, etc. |
| `sku_name` | VARCHAR(200) | ✓ | Full SKU name |
| `sku_region` | VARCHAR(50) | | Original SKU region (NULL for global) |
| `price_per_dbu` | DECIMAL(10,6) | | Price in USD |
| `usage_unit` | VARCHAR(20) | | DBU |
| `currency_code` | VARCHAR(10) | | USD |
| `pricing_type` | VARCHAR(20) | | REGIONAL or GLOBAL |
| `fetched_at` | TIMESTAMP | | When data was fetched |

**Sample Data:** *(showing key columns)*

| cloud | region | tier | product_type | sku_name | sku_region | price_per_dbu | pricing_type |
|-------|--------|------|--------------|----------|------------|---------------|--------------|
| AWS | us-east-1 | PREMIUM | JOBS_COMPUTE | PREMIUM_JOBS_COMPUTE | NULL | 0.150000 | GLOBAL |
| AWS | us-east-1 | PREMIUM | JOBS_COMPUTE_(PHOTON) | PREMIUM_JOBS_COMPUTE_(PHOTON) | NULL | 0.150000 | GLOBAL |
| AWS | us-east-1 | PREMIUM | ALL_PURPOSE_COMPUTE | PREMIUM_ALL_PURPOSE_COMPUTE | NULL | 0.550000 | GLOBAL |
| AWS | us-east-1 | PREMIUM | SQL_COMPUTE | PREMIUM_SQL_COMPUTE | NULL | 0.220000 | GLOBAL |
| AWS | us-east-1 | PREMIUM | JOBS_SERVERLESS_COMPUTE | PREMIUM_JOBS_SERVERLESS_COMPUTE | US_EAST_N_VIRGINIA | 0.700000 | REGIONAL |
| AZURE | eastus | PREMIUM | SERVERLESS_SQL_COMPUTE | PREMIUM_SERVERLESS_SQL_COMPUTE | EASTUS | 0.700000 | REGIONAL |

> *Additional columns: `usage_unit` (DBU), `currency_code` (USD), `fetched_at` (timestamp)*

---

### 2. `sync_pricing_vm_costs`

**Purpose:** Cloud VM costs (on-demand, spot, reserved).

| Column | Type | PK | Description |
|--------|------|:--:|-------------|
| `cloud` | VARCHAR(20) | ✓ | AWS, AZURE, GCP |
| `region` | VARCHAR(50) | ✓ | Cloud region code (us-east-1, eastus) |
| `instance_type` | VARCHAR(100) | ✓ | Instance type (i3.xlarge, Standard_E8s_v4) |
| `pricing_tier` | VARCHAR(20) | ✓ | on_demand, spot, reserved_1y, reserved_3y |
| `payment_option` | VARCHAR(50) | ✓ | N/A, no_upfront, partial_upfront, all_upfront |
| `cost_per_hour` | DECIMAL(10,6) | | USD per hour |
| `currency` | VARCHAR(10) | | USD |
| `source` | VARCHAR(100) | | API source |
| `fetched_at` | TIMESTAMP | | When data was fetched |

**Sample Data:** *(showing key columns)*

| cloud | region | instance_type | pricing_tier | payment_option | cost_per_hour | currency |
|-------|--------|---------------|--------------|----------------|---------------|----------|
| AWS | us-east-1 | i3.xlarge | on_demand | N/A | 0.312000 | USD |
| AWS | us-east-1 | i3.2xlarge | on_demand | N/A | 0.624000 | USD |
| AWS | us-east-1 | i3.2xlarge | spot | N/A | 0.187200 | USD |
| AWS | us-east-1 | i3.2xlarge | reserved_1y | no_upfront | 0.436800 | USD |
| AWS | us-east-1 | i3.2xlarge | reserved_1y | partial_upfront | 0.405600 | USD |
| AWS | us-east-1 | i3.2xlarge | reserved_1y | all_upfront | 0.390000 | USD |
| AZURE | eastus | Standard_E8s_v4 | on_demand | N/A | 0.576000 | USD |
| AZURE | eastus | Standard_E8s_v4 | spot | N/A | 0.115200 | USD |
| GCP | us-central1 | n2-highmem-8 | on_demand | N/A | 0.520600 | USD |

> *Additional columns: `source` (API source), `fetched_at` (timestamp)*

---

### 3. `sync_product_dbsql_rates`

**Purpose:** DBSQL warehouse DBU rates (Classic/Pro/Serverless).

| Column | Type | PK | Description |
|--------|------|:--:|-------------|
| `cloud` | VARCHAR(20) | ✓ | AWS, AZURE, GCP |
| `warehouse_type` | VARCHAR(20) | ✓ | classic, pro, serverless |
| `warehouse_size` | VARCHAR(20) | ✓ | 2X-Small to 4X-Large |
| `dbu_per_hour` | DECIMAL(10,2) | | DBU consumed per hour |
| `sku_product_type` | VARCHAR(100) | | SKU for DBU price lookup |

**Sample Data:**

| cloud | warehouse_type | warehouse_size | dbu_per_hour | sku_product_type |
|-------|----------------|----------------|--------------|------------------|
| AWS | classic | 2X-Small | 2 | SQL_COMPUTE |
| AWS | classic | X-Small | 4 | SQL_COMPUTE |
| AWS | classic | Small | 8 | SQL_COMPUTE |
| AWS | classic | Medium | 16 | SQL_COMPUTE |
| AWS | classic | Large | 32 | SQL_COMPUTE |
| AWS | pro | 2X-Small | 2 | SQL_PRO_COMPUTE |
| AWS | pro | Small | 8 | SQL_PRO_COMPUTE |
| AWS | serverless | 2X-Small | 2 | SERVERLESS_SQL_COMPUTE |
| AWS | serverless | Small | 8 | SERVERLESS_SQL_COMPUTE |
| AZURE | serverless | Medium | 16 | SERVERLESS_SQL_COMPUTE |

---

### 4. `sync_product_serverless_rates`

**Purpose:** Serverless product rates (Vector Search, Model Serving).

| Column | Type | PK | Description |
|--------|------|:--:|-------------|
| `cloud` | VARCHAR(20) | ✓ | AWS, AZURE, GCP |
| `product` | VARCHAR(50) | ✓ | vector_search, model_serving |
| `size_or_model` | VARCHAR(100) | ✓ | cpu, gpu_small, standard |
| `dbu_rate` | DECIMAL(10,4) | | DBU per unit |
| `rate_type` | VARCHAR(20) | | hourly, per_token, per_request |
| `input_divisor` | BIGINT | | Divisor (1M for tokens) |
| `is_hourly` | BOOLEAN | | Is rate per hour? |
| `sku_product_type` | VARCHAR(100) | | SKU for DBU price lookup |
| `description` | TEXT | | Rate description |

**Sample Data:** *(showing key columns)*

| cloud | product | size_or_model | dbu_rate | rate_type | is_hourly | sku_product_type |
|-------|---------|---------------|----------|-----------|-----------|------------------|
| AWS | vector_search | standard | 0.07 | hourly | true | VECTOR_SEARCH_ENDPOINT |
| AWS | vector_search | storage_optimized | 0.10 | hourly | true | VECTOR_SEARCH_ENDPOINT |
| AWS | model_serving | cpu | 0.07 | hourly | true | SERVERLESS_REAL_TIME_INFERENCE |
| AWS | model_serving | gpu_small | 3.40 | hourly | true | SERVERLESS_REAL_TIME_INFERENCE |
| AWS | model_serving | gpu_medium | 10.20 | hourly | true | SERVERLESS_REAL_TIME_INFERENCE |
| AWS | model_serving | gpu_large | 40.80 | hourly | true | SERVERLESS_REAL_TIME_INFERENCE |
| AWS | ai_gateway | standard | 0.00 | per_request | false | EXTERNAL_FUNCTIONS_ACCESS |
| AZURE | vector_search | standard | 0.07 | hourly | true | VECTOR_SEARCH_ENDPOINT |

> *Additional columns: `input_divisor` (for tokens), `description`*

---

### 5. `sync_product_fmapi_databricks`

**Purpose:** Databricks-hosted FMAPI rates (Llama, DBRX, embeddings).

| Column | Type | PK | Description |
|--------|------|:--:|-------------|
| `model` | VARCHAR(100) | ✓ | llama-3.1-70b-instruct, dbrx-instruct |
| `rate_type` | VARCHAR(50) | ✓ | input_token, output_token |
| `dbu_rate` | DECIMAL(10,4) | | DBU rate per 1M tokens |
| `input_divisor` | BIGINT | | 1000000 for tokens |
| `is_hourly` | BOOLEAN | | Is rate per hour? (false for tokens) |
| `sku_product_type` | VARCHAR(100) | | SKU for DBU price lookup |

**Sample Data:**

| model | rate_type | dbu_rate | input_divisor | is_hourly | sku_product_type |
|-------|-----------|----------|---------------|-----------|------------------|
| llama-3.1-8b-instruct | input_token | 0.75 | 1000000 | false | SERVERLESS_REAL_TIME_INFERENCE |
| llama-3.1-8b-instruct | output_token | 1.00 | 1000000 | false | SERVERLESS_REAL_TIME_INFERENCE |
| llama-3.1-70b-instruct | input_token | 2.25 | 1000000 | false | SERVERLESS_REAL_TIME_INFERENCE |
| llama-3.1-70b-instruct | output_token | 3.00 | 1000000 | false | SERVERLESS_REAL_TIME_INFERENCE |
| llama-3.1-405b-instruct | input_token | 7.50 | 1000000 | false | SERVERLESS_REAL_TIME_INFERENCE |
| dbrx-instruct | input_token | 1.50 | 1000000 | false | SERVERLESS_REAL_TIME_INFERENCE |
| bge-large-en-v1.5 | input_token | 0.05 | 1000000 | false | SERVERLESS_REAL_TIME_INFERENCE |
| gte-large-en-v1.5 | input_token | 0.05 | 1000000 | false | SERVERLESS_REAL_TIME_INFERENCE |

---

### 6. `sync_product_fmapi_proprietary`

**Purpose:** Proprietary FMAPI rates (OpenAI, Anthropic, Google) served by Databricks.

> **Important:** These proprietary models (GPT, Claude, Gemini) are **served BY Databricks**, NOT via AI Gateway. Databricks hosts and manages access to these models directly.

| Column | Type | PK | Description |
|--------|------|:--:|-------------|
| `provider` | VARCHAR(50) | ✓ | openai, anthropic, google |
| `model` | VARCHAR(100) | ✓ | gpt-4o, claude-haiku-4-5, gemini-2.5-pro |
| `endpoint_type` | VARCHAR(20) | ✓ | global, in_geo |
| `context_length` | VARCHAR(20) | ✓ | all, standard, long |
| `input_divisor` | BIGINT | | 1000000 for tokens |
| `is_hourly` | BOOLEAN | | false (token-based) |
| `sku_product_type` | VARCHAR(100) | | ANTHROPIC_MODEL_SERVING, OPENAI_MODEL_SERVING, etc. |
| `rate_type` | VARCHAR(50) | ✓ | input_token, output_token, cache_read, cache_write |
| `dbu_rate` | DECIMAL(10,4) | | DBU rate per 1M tokens |
| `cloud` | VARCHAR(20) | ✓ | AWS, AZURE, GCP |
| `updated_at` | TIMESTAMP | | When data was last updated |

**Sample Data:** *(from actual table)*

| provider | model | endpoint_type | context_length | sku_product_type | rate_type | dbu_rate | cloud |
|----------|-------|---------------|----------------|------------------|-----------|----------|-------|
| anthropic | claude-haiku-4-5 | global | all | ANTHROPIC_MODEL_SERVING | cache_read | 1.429 | AWS |
| anthropic | claude-haiku-4-5 | in_geo | all | ANTHROPIC_MODEL_SERVING | cache_read | 1.572 | AWS |
| anthropic | claude-haiku-4-5 | global | all | ANTHROPIC_MODEL_SERVING | cache_write | 17.857 | AWS |
| anthropic | claude-haiku-4-5 | in_geo | all | ANTHROPIC_MODEL_SERVING | cache_write | 19.643 | AWS |
| anthropic | claude-haiku-4-5 | global | all | ANTHROPIC_MODEL_SERVING | input_token | 14.286 | AWS |
| anthropic | claude-haiku-4-5 | in_geo | all | ANTHROPIC_MODEL_SERVING | input_token | 15.715 | AWS |
| anthropic | claude-haiku-4-5 | global | all | ANTHROPIC_MODEL_SERVING | output_token | 71.429 | AWS |
| anthropic | claude-haiku-4-5 | in_geo | all | ANTHROPIC_MODEL_SERVING | output_token | 78.572 | AWS |

> *Additional columns: `input_divisor` (1000000), `is_hourly` (false), `updated_at`*

---

### 7. `sync_ref_instance_dbu_rates`

**Purpose:** Instance DBU rates for classic compute.

| Column | Type | PK | Description |
|--------|------|:--:|-------------|
| `cloud` | VARCHAR(20) | ✓ | AWS, AZURE, GCP |
| `instance_type` | VARCHAR(100) | ✓ | i3.xlarge, Standard_E8s_v4, n2-highmem-8 |
| `instance_family` | VARCHAR(50) | | General Purpose, Storage Optimized |
| `vcpus` | INT | | Number of vCPUs |
| `memory_gb` | DECIMAL(10,2) | | Memory in GB |
| `dbu_rate` | DECIMAL(10,4) | | DBU per hour |

**Sample Data:**

| cloud | instance_type | instance_family | vcpus | memory_gb | dbu_rate |
|-------|---------------|-----------------|-------|-----------|----------|
| AWS | i3.xlarge | Storage Optimized | 4 | 30.5 | 0.75 |
| AWS | i3.2xlarge | Storage Optimized | 8 | 61.0 | 1.50 |
| AWS | i3.4xlarge | Storage Optimized | 16 | 122.0 | 3.00 |
| AWS | r5.xlarge | Memory Optimized | 4 | 32.0 | 0.75 |
| AWS | r5.2xlarge | Memory Optimized | 8 | 64.0 | 1.50 |
| AZURE | Standard_E4s_v4 | Memory Optimized | 4 | 32.0 | 0.75 |
| AZURE | Standard_E8s_v4 | Memory Optimized | 8 | 64.0 | 1.50 |
| AZURE | Standard_L8s_v3 | Storage Optimized | 8 | 64.0 | 1.50 |
| GCP | n2-highmem-4 | Memory Optimized | 4 | 32.0 | 0.75 |
| GCP | n2-highmem-8 | Memory Optimized | 8 | 64.0 | 1.50 |

---

### 8. `sync_ref_sku_region_map`

**Purpose:** Maps SKU region names to cloud region codes.

| Column | Type | PK | Description |
|--------|------|:--:|-------------|
| `cloud` | VARCHAR(20) | ✓ | AWS, AZURE, GCP |
| `sku_region` | VARCHAR(50) | ✓ | US_EAST_N_VIRGINIA, EASTUS |
| `region_code` | VARCHAR(50) | | us-east-1, eastus |

**Sample Data:**

| cloud | sku_region | region_code |
|-------|------------|-------------|
| AWS | US_EAST_N_VIRGINIA | us-east-1 |
| AWS | US_EAST_OHIO | us-east-2 |
| AWS | US_WEST_OREGON | us-west-2 |
| AWS | EU_IRELAND | eu-west-1 |
| AWS | EU_FRANKFURT | eu-central-1 |
| AWS | AP_SINGAPORE | ap-southeast-1 |
| AZURE | EASTUS | eastus |
| AZURE | WESTUS2 | westus2 |
| AZURE | WESTEUROPE | westeurope |
| GCP | US_IOWA | us-central1 |
| GCP | US_OREGON | us-west1 |
| GCP | EUROPE_BELGIUM | europe-west1 |

---

### 9. `sync_ref_dbu_multipliers`

**Purpose:** Photon and feature multipliers.

| Column | Type | PK | Description |
|--------|------|:--:|-------------|
| `sku_type` | VARCHAR(50) | ✓ | JOBS_COMPUTE, ALL_PURPOSE_COMPUTE, DLT_*_COMPUTE |
| `feature` | VARCHAR(50) | ✓ | standard, photon |
| `multiplier` | DECIMAL(5,2) | | 1.0 for standard, 2.2-2.9 for photon |

**Sample Data:**

| sku_type | feature | multiplier |
|----------|---------|------------|
| JOBS_COMPUTE | standard | 1.00 |
| JOBS_COMPUTE | photon | 2.90 |
| ALL_PURPOSE_COMPUTE | standard | 1.00 |
| ALL_PURPOSE_COMPUTE | photon | 2.20 |
| DLT_CORE_COMPUTE | standard | 1.00 |
| DLT_CORE_COMPUTE | photon | 2.90 |
| DLT_PRO_COMPUTE | standard | 1.00 |
| DLT_PRO_COMPUTE | photon | 2.90 |
| DLT_ADVANCED_COMPUTE | standard | 1.00 |
| DLT_ADVANCED_COMPUTE | photon | 2.90 |

---

### 10. `sync_ref_dbsql_warehouse_config`

**Purpose:** DBSQL warehouse VM configurations.

| Column | Type | PK | Description |
|--------|------|:--:|-------------|
| `cloud` | VARCHAR(20) | ✓ | AWS, AZURE, GCP |
| `warehouse_type` | VARCHAR(20) | ✓ | classic, pro |
| `warehouse_size` | VARCHAR(20) | ✓ | 2X-Small to 4X-Large |
| `driver_instance_type` | VARCHAR(100) | | Driver node type |
| `driver_count` | INT | | Number of drivers |
| `worker_instance_type` | VARCHAR(100) | | Worker node type |
| `worker_count` | INT | | Number of workers |

**Sample Data:**

| cloud | warehouse_type | warehouse_size | driver_instance_type | driver_count | worker_instance_type | worker_count |
|-------|----------------|----------------|---------------------|--------------|---------------------|--------------|
| AWS | classic | 2X-Small | m5.xlarge | 1 | m5.xlarge | 0 |
| AWS | classic | X-Small | m5.xlarge | 1 | m5.xlarge | 1 |
| AWS | classic | Small | m5.2xlarge | 1 | m5.2xlarge | 1 |
| AWS | classic | Medium | m5.4xlarge | 1 | m5.2xlarge | 2 |
| AWS | classic | Large | m5.8xlarge | 1 | m5.4xlarge | 2 |
| AWS | pro | Small | r5.2xlarge | 1 | r5.2xlarge | 1 |
| AWS | pro | Medium | r5.4xlarge | 1 | r5.2xlarge | 2 |
| AZURE | classic | Small | Standard_E8s_v4 | 1 | Standard_E8s_v4 | 1 |
| AZURE | classic | Medium | Standard_E16s_v4 | 1 | Standard_E8s_v4 | 2 |
| GCP | classic | Small | n2-highmem-8 | 1 | n2-highmem-8 | 1 |

---

## Salesforce Tables (Synced)

These tables are **synced from Unity Catalog** (via Logfood workspace) to support customer/use case/opportunity selection when creating estimates.

### Sync Source

| Target Table | Source Table | Sync Frequency |
|--------------|--------------|----------------|
| `sync_salesforce_account` | `main.metric_store.dim_salesforce_account` | Daily |
| `sync_salesforce_usecase` | `main.metric_store.fct_salesforce_use_case__core` | Daily |
| `sync_salesforce_opportunity` | `main.sfdc_bronze.hourly_opportunity` | Daily |

---

### UI Workflow: Customer Selection

When SA creates/edits an estimate:

```
┌─────────────────────────────────────────────────────────────────┐
│  1. SELECT CUSTOMER                                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 🔍 Search: [Acme Corp                    ] ▼                ││
│  │    → Dropdown: sync_salesforce_account                      ││
│  │    → Display: salesforce_account_name                       ││
│  │    → Store: salesforce_account_id → estimates.customer_sfdc_id│
│  └─────────────────────────────────────────────────────────────┘│
│                              ↓                                   │
│  2. SELECT USE CASE OR OPPORTUNITY (filtered by customer)        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ ○ Use Case    ● Opportunity                                 ││
│  │ ┌───────────────────────────────────────────────────────┐   ││
│  │ │ If Use Case selected:                                 │   ││
│  │ │    → Dropdown: sync_salesforce_usecase (filtered)     │   ││
│  │ │      WHERE customer_id = selected_account.customer_id │   ││
│  │ │    → Store: estimates.salesforce_use_case_id          │   ││
│  │ │                                                        │   ││
│  │ │ If Opportunity selected:                              │   ││
│  │ │    → Dropdown: sync_salesforce_opportunity (filtered) │   ││
│  │ │      WHERE accountid = selected_account.salesforce_account_id│
│  │ │    → Store: estimates.salesforce_opportunity_id       │   ││
│  │ └───────────────────────────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

### 1. `sync_salesforce_account`

**Purpose:** Customer accounts from Salesforce for dropdown selection.

| Column | Type | PK | Description |
|--------|------|:--:|-------------|
| `salesforce_account_id` | VARCHAR(18) | ✓ | Salesforce Account ID (18-char) |
| `salesforce_account_name` | VARCHAR(255) | | Customer name for display |

**Sample Data:**

| salesforce_account_id | salesforce_account_name |
|-----------------------|-------------------------|
| 001ABC123DEF456GHI | Acme Corporation |
| 001DEF456GHI789JKL | TechStart Inc |
| 001GHI789JKL012MNO | FinServ Bank |
| 001JKL012MNO345PQR | RetailCo Ltd |
| 001MNO345PQR678STU | HealthCare Systems |

---

### 2. `sync_salesforce_usecase`

**Purpose:** Use cases linked to customers for dropdown selection (filtered by customer).

| Column | Type | PK | Description |
|--------|------|:--:|-------------|
| `salesforce_use_case_id` | VARCHAR(18) | ✓ | Salesforce Use Case ID |
| `customer_id` | VARCHAR(18) | | Link to customer (for filtering) |
| `dim_canonical_customer_name` | VARCHAR(255) | | Customer name (denormalized) |
| `dim_salesforce_use_case_id` | VARCHAR(50) | | Use case identifier |
| `salesforce_use_case_name` | VARCHAR(500) | | Use case name for display |

**Sample Data:**

| salesforce_use_case_id | customer_id | dim_canonical_customer_name | salesforce_use_case_name |
|------------------------|-------------|-----------------------------|--------------------------| 
| UC001ABC123 | 001ABC123DEF456GHI | Acme Corporation | Data Platform Modernization |
| UC002ABC456 | 001ABC123DEF456GHI | Acme Corporation | ML Pipeline for Fraud Detection |
| UC003DEF789 | 001DEF456GHI789JKL | TechStart Inc | Real-time Analytics Dashboard |
| UC004GHI012 | 001GHI789JKL012MNO | FinServ Bank | Customer 360 Lakehouse |

**Filtering Query:**
```sql
-- Get use cases for selected customer
SELECT salesforce_use_case_id, salesforce_use_case_name
FROM sync_salesforce_usecase
WHERE customer_id = :selected_customer_id
ORDER BY salesforce_use_case_name;
```

---

### 3. `sync_salesforce_opportunity`

**Purpose:** Opportunities linked to accounts for dropdown selection (filtered by account).

| Column | Type | PK | Description |
|--------|------|:--:|-------------|
| `id` | VARCHAR(18) | ✓ | Salesforce Opportunity ID |
| `name` | VARCHAR(255) | | Opportunity name for display |
| `accountid` | VARCHAR(18) | | Link to account (for filtering) |

**Sample Data:**

| id | name | accountid |
|----|------|-----------|
| 006ABC123DEF456 | Acme Corp - Enterprise Deal Q4 | 001ABC123DEF456GHI |
| 006DEF456GHI789 | Acme Corp - POC Extension | 001ABC123DEF456GHI |
| 006GHI789JKL012 | TechStart - Platform Expansion | 001DEF456GHI789JKL |
| 006JKL012MNO345 | FinServ - ML Workloads | 001GHI789JKL012MNO |

**Filtering Query:**
```sql
-- Get opportunities for selected account
SELECT id, name
FROM sync_salesforce_opportunity
WHERE accountid = :selected_salesforce_account_id
ORDER BY name;
```

---

## Application Tables

These tables are **created directly in Lakebase** and are **read-write**.

### 1. `users`

**Purpose:** User profiles for authentication and ownership tracking.

| Column | Type | PK | FK | Description |
|--------|------|:--:|:--:|-------------|
| `user_id` | UUID | ✓ | | Primary key |
| `email` | VARCHAR(255) | | | Databricks workspace email (UNIQUE, NOT NULL) |
| `full_name` | VARCHAR(255) | | | User's full name |
| `role` | VARCHAR(50) | | | SA, AE, Manager, Admin |
| `is_active` | BOOLEAN | | | Account status (default: true) |
| `last_login_at` | TIMESTAMP | | | Last login time |
| `created_at` | TIMESTAMP | | | Record creation |
| `updated_at` | TIMESTAMP | | | Last update |

**Sample Data:**

| user_id | email | full_name | role | is_active |
|---------|-------|-----------|------|-----------|
| 550e8400-e29b-41d4-a716-446655440001 | john.doe@databricks.com | John Doe | SA | true |
| 550e8400-e29b-41d4-a716-446655440002 | jane.smith@databricks.com | Jane Smith | SA | true |
| 550e8400-e29b-41d4-a716-446655440003 | mike.wilson@databricks.com | Mike Wilson | AE | true |
| 550e8400-e29b-41d4-a716-446655440004 | sarah.chen@databricks.com | Sarah Chen | Manager | true |
| 550e8400-e29b-41d4-a716-446655440005 | admin@databricks.com | System Admin | Admin | true |

---

### 2. `estimates`

**Purpose:** Estimation metadata and lifecycle.

| Column | Type | PK | FK | Description |
|--------|------|:--:|:--:|-------------|
| `estimate_id` | UUID | ✓ | | Primary key |
| `estimate_name` | VARCHAR(500) | | | User-defined name |
| `owner_user_id` | UUID | | ✓ users | Owner of the estimate |
| **Salesforce Linkage** *(select customer, then use case OR opportunity)* |
| `customer_sfdc_id` | VARCHAR(18) | | | Salesforce Account ID (from `sync_salesforce_account`) |
| `customer_name` | VARCHAR(255) | | | Customer name (denormalized for display) |
| `salesforce_use_case_id` | VARCHAR(18) | | | Use Case ID (from `sync_salesforce_usecase`) - NULL if opportunity selected |
| `salesforce_opportunity_id` | VARCHAR(18) | | | Opportunity ID (from `sync_salesforce_opportunity`) - NULL if use case selected |
| `cloud` | VARCHAR(20) | | | AWS, GCP, AZURE |
| `region` | VARCHAR(50) | | | Cloud region |
| `tier` | VARCHAR(20) | | | PREMIUM, ENTERPRISE |
| `status` | VARCHAR(20) | | | draft, finalized, archived (default: draft) |
| `version` | INT | | | Version number (default: 1) |
| `template_id` | UUID | | ✓ templates | Template used (optional) |
| `original_prompt` | TEXT | | | Free-form prompt |
| `is_deleted` | BOOLEAN | | | Soft delete flag (default: false) |
| `created_at` | TIMESTAMP | | | Record creation |
| `updated_at` | TIMESTAMP | | | Last update |
| `updated_by` | UUID | | ✓ users | Who last edited (audit trail) |

> **Notes:**
> - `total_dbu_per_month` and `total_cost_per_month` are **not stored** - use view `v_estimates_with_totals`.
> - **Salesforce constraint:** Either `salesforce_use_case_id` OR `salesforce_opportunity_id` should be set (not both). Enforced by app logic.

**Sample Data:**

| estimate_id | estimate_name | customer_sfdc_id | customer_name | salesforce_use_case_id | salesforce_opportunity_id | cloud | status |
|-------------|---------------|------------------|---------------|------------------------|---------------------------|-------|--------|
| a1b2c3d4-... | Acme Corp Data Platform | 001ABC123DEF456GHI | Acme Corporation | UC001ABC123 | NULL | AWS | draft |
| e5f6g7h8-... | TechStart ML Pipeline | 001DEF456GHI789JKL | TechStart Inc | NULL | 006GHI789JKL012 | GCP | finalized |
| i9j0k1l2-... | FinServ Analytics | 001GHI789JKL012MNO | FinServ Bank | UC004GHI012 | NULL | AZURE | draft |
| m3n4o5p6-... | RetailCo Lakehouse POC | 001JKL012MNO345PQR | RetailCo Ltd | NULL | 006JKL012MNO345 | AWS | archived |

> *Note: Each estimate links to either a use case OR an opportunity, not both.*

**To get totals, use the view:**
```sql
SELECT * FROM v_estimates_with_totals WHERE estimate_id = 'a1b2c3d4-...';
-- Returns: total_dbu_per_month, total_cost_per_month, line_item_count
```

---

### 3. `line_items`

**Purpose:** Individual workload line items with explicit columns for dynamic form UI (like Azure Calculator).

> **Design Note:** Uses explicit columns instead of JSON for better queryability. Unused columns are NULL. The UI shows/hides fields based on `workload_type`. **No calculated costs stored** - use `v_line_items_with_costs` view.

> **⚠️ Pricing Rule:** Driver nodes CANNOT use spot pricing (requires stability). Worker nodes CAN use spot pricing. Use `driver_pricing_tier` and `worker_pricing_tier` to specify independently.

> **🔄 Auto-Sync:** The `cloud` column is automatically synced from parent `estimates.cloud` via triggers. This enables instance type validation (ensures driver/worker instances match the estimate's cloud).

| Column | Type | PK | FK | Description |
|--------|------|:--:|:--:|-------------|
| `line_item_id` | UUID | ✓ | | Unique line item identifier |
| `estimate_id` | UUID | | ✓ estimates | Parent estimation |
| `display_order` | INT | | | Display order in UI |
| **Identity** |
| `workload_name` | VARCHAR(255) | | | User-defined workload name |
| `workload_type` | VARCHAR(50) | | ✓ ref_workload_types | Dropdown: JOBS, ALL_PURPOSE, DLT, DBSQL, etc. |
| `cloud` | VARCHAR(20) | | | Auto-synced from estimates.cloud (via trigger) |
| **Compute Config** *(JOBS, ALL_PURPOSE, DLT)* |
| `serverless_enabled` | BOOLEAN | | | Serverless toggle (**if true, photon_enabled must also be true**) |
| `serverless_mode` | VARCHAR(20) | | | Dropdown: standard, performance (**for JOBS/DLT serverless only**) |
| `photon_enabled` | BOOLEAN | | | Photon acceleration (auto-true when serverless) |
| `driver_node_type` | VARCHAR(100) | | | Instance type (for sizing estimation, even for serverless) |
| `worker_node_type` | VARCHAR(100) | | | Instance type (for sizing estimation, even for serverless) |
| `num_workers` | INT | | | Number of workers (0-1000) |
| **DLT Config** *(DLT only)* |
| `dlt_edition` | VARCHAR(20) | | | CORE, PRO, ADVANCED |
| **DBSQL Config** *(DBSQL only)* |
| `dbsql_warehouse_type` | VARCHAR(20) | | | CLASSIC, PRO, SERVERLESS |
| `dbsql_warehouse_size` | VARCHAR(20) | | | 2X-Small to 4X-Large |
| `dbsql_num_clusters` | INT | | | Number of clusters for scaling (1-100, default 1) |
| **Serverless Products** *(VECTOR_SEARCH, MODEL_SERVING)* |
| `vector_search_mode` | VARCHAR(50) | | | standard, storage_optimized (**for VECTOR_SEARCH only**) |
| `vector_capacity_millions` | DECIMAL(10,2) | | | Vector Search capacity in millions (supports fractional) |
| `model_serving_gpu_type` | VARCHAR(50) | | | GPU type: gpu_medium_a10g_1x, cpu_medium_2x (**for MODEL_SERVING only**) |
| **FMAPI Config** *(FMAPI_DATABRICKS, FMAPI_PROPRIETARY)* |
| `fmapi_provider` | VARCHAR(50) | | | databricks, openai, anthropic, google |
| `fmapi_model` | VARCHAR(100) | | | gpt-4o, claude-sonnet-4, llama-3.1-70b |
| `fmapi_endpoint_type` | VARCHAR(20) | | | global, in_geo |
| `fmapi_context_length` | VARCHAR(20) | | | all, short, long (provider-specific) |
| `fmapi_pricing_type` | VARCHAR(50) | | | pay_per_token, provisioned_entry, provisioned_scaling |
| `fmapi_rate_type` | VARCHAR(20) | | | Direct from pricing table: input_token, output_token, cache_read, cache_write, batch_inference, provisioned_entry, provisioned_scaling |
| `fmapi_quantity` | BIGINT | | | Quantity (tokens for token-based rates, hours for hourly rates like batch_inference or provisioned) |
| `fmapi_provisioned_units` | INT | | | Number of provisioned units (for provisioned throughput) |
| **Lakebase Config** *(LAKEBASE only)* |
| `lakebase_cu` | INT | | | Compute Units per node: 1, 2, 4, 8 (**1 CU = 1 DBU**) |
| `lakebase_storage_gb` | INT | | | Storage size in GB (100-10000) |
| `lakebase_ha_nodes` | INT | | | Total number of nodes (1=no HA, 2-3=HA enabled, max 3) |
| `lakebase_backup_retention_days` | INT | | | Backup retention days (0=no backup, 1-35 days, default 7) |
| **Usage/Frequency** *(Consistent for all hourly workloads)* |
| `runs_per_day` | INT | | | Number of runs per day |
| `avg_runtime_minutes` | INT | | | Average runtime per run (in minutes) |
| `days_per_month` | INT | | | Days per month (default 30) |
| `hours_per_month` | DECIMAL(10,2) | | | Total hours per month (optional: if NULL, auto-calculate from above fields; for 24/7 services, set to 720) |
| **VM Pricing** *(Classic compute only - ignored when serverless_enabled=true)* |
| `driver_pricing_tier` | VARCHAR(20) | | | Driver: on_demand, reserved_1y, reserved_3y (NEVER spot) |
| `worker_pricing_tier` | VARCHAR(20) | | | Worker: on_demand, spot, reserved_1y, reserved_3y |
| `driver_payment_option` | VARCHAR(20) | | | Driver: NA (Azure/GCP), no_upfront, partial_upfront, all_upfront (AWS reserved) |
| `worker_payment_option` | VARCHAR(20) | | | Worker: NA (Azure/GCP), no_upfront, partial_upfront, all_upfront (AWS reserved) |
| **Metadata** |
| `workload_config` | JSON | | | Extensible config for future workload types |
| `notes` | TEXT | | | SA custom notes |
| `created_at` | TIMESTAMP | | | Record creation |
| `updated_at` | TIMESTAMP | | | Last update |

> **Notes:**
> - `created_by`/`updated_by` removed - derive from `estimates.owner_user_id` via JOIN.
> - **Serverless constraint:** When `serverless_enabled = true`, `photon_enabled` must also be `true` (enforced by app/trigger).
> - VM config columns are still used when serverless is enabled for **sizing estimation** (to help estimate workload size), but VM costs are NOT calculated.

**Sample Data by Workload Type:**

#### Example 1: Jobs Classic (ETL Pipeline)
| Column | Value |
|--------|-------|
| workload_name | Daily ETL Pipeline |
| workload_type | `JOBS` |
| serverless_enabled | **false** |
| photon_enabled | true |
| driver_node_type | i3.xlarge |
| worker_node_type | i3.2xlarge |
| num_workers | 8 |
| runs_per_day | 4 |
| avg_runtime_minutes | 45 |
| driver_pricing_tier | on_demand |
| worker_pricing_tier | on_demand |

> Cost = DBU cost + VM cost (classic compute)

#### Example 1b: Jobs Classic with Mixed Pricing (Cost Optimized)
| Column | Value |
|--------|-------|
| workload_name | Cost-Optimized ETL |
| workload_type | `JOBS` |
| serverless_enabled | **false** |
| photon_enabled | true |
| driver_node_type | i3.xlarge |
| worker_node_type | i3.2xlarge |
| num_workers | 8 |
| runs_per_day | 4 |
| avg_runtime_minutes | 45 |
| driver_pricing_tier | **reserved_1y** *(stable, predictable)* |
| worker_pricing_tier | **spot** *(workers can be interrupted)* |
| vm_payment_option | partial_upfront |

> **Cost Optimization:** Driver uses reserved for stability, workers use spot for cost savings.  
> This is a common pattern for production ETL workloads.

#### Example 2: Jobs Serverless (ETL Pipeline)
| Column | Value |
|--------|-------|
| workload_name | Serverless ETL Pipeline |
| workload_type | `JOBS` |
| serverless_enabled | **true** |
| serverless_mode | **standard** *(or performance for faster execution)* |
| photon_enabled | **true** *(auto-set)* |
| driver_node_type | i3.xlarge *(sizing reference only)* |
| worker_node_type | i3.2xlarge *(sizing reference only)* |
| num_workers | 8 *(sizing reference only)* |
| runs_per_day | 4 |
| avg_runtime_minutes | 45 |
| vm_pricing_tier | *(ignored)* |

> Cost = DBU cost only (serverless - no VM cost)

#### Example 3: All Purpose Serverless (Interactive Notebook)
| Column | Value |
|--------|-------|
| workload_name | Data Science Exploration |
| workload_type | `ALL_PURPOSE` |
| serverless_enabled | **true** |
| photon_enabled | **true** *(auto-set)* |
| driver_node_type | r5.2xlarge *(sizing reference only)* |
| worker_node_type | r5.2xlarge *(sizing reference only)* |
| num_workers | 4 *(sizing reference only)* |
| hours_per_day | 8 |
| days_per_month | 22 |

> Cost = DBU cost only (serverless - no VM cost)

#### Example 4: DLT Pro Pipeline (Classic)
| Column | Value |
|--------|-------|
| workload_name | Customer 360 Pipeline |
| workload_type | `DLT` |
| serverless_enabled | **false** |
| photon_enabled | true |
| dlt_edition | PRO |
| dlt_pipeline_mode | TRIGGERED |
| driver_node_type | r5.xlarge |
| worker_node_type | r5.2xlarge |
| num_workers | 4 |
| hours_per_day | 6 |
| driver_pricing_tier | reserved_1y |
| worker_pricing_tier | reserved_1y |
| vm_payment_option | partial_upfront |

> Cost = DBU cost + VM cost (classic compute)

#### Example 5: DLT Serverless
| Column | Value |
|--------|-------|
| workload_name | Streaming Ingestion |
| workload_type | `DLT` |
| serverless_enabled | **true** |
| serverless_mode | **performance** *(or standard for cost optimization)* |
| photon_enabled | **true** *(auto-set)* |
| dlt_edition | PRO |
| dlt_pipeline_mode | CONTINUOUS |
| driver_node_type | r5.xlarge *(sizing reference only)* |
| worker_node_type | r5.2xlarge *(sizing reference only)* |
| num_workers | 4 *(sizing reference only)* |
| hours_per_day | 24 |

> Cost = DBU cost only (serverless - no VM cost)

#### Example 6: DBSQL Serverless
| Column | Value |
|--------|-------|
| workload_name | BI Dashboard Queries |
| workload_type | `DBSQL` |
| dbsql_warehouse_type | SERVERLESS |
| dbsql_warehouse_size | Medium |
| dbsql_num_clusters | 2 |
| runs_per_day | 1 |
| avg_runtime_minutes | 600 *(10 hours)* |
| days_per_month | 22 |

> Cost = DBU cost only (DBSQL has its own serverless toggle via warehouse_type)

#### Example 7: FMAPI Proprietary (Claude served by Databricks)
| Column | Value |
|--------|-------|
| workload_name | Customer Support Bot |
| workload_type | `FMAPI_PROPRIETARY` |
| fmapi_provider | anthropic |
| fmapi_model | claude-sonnet-4-20250514 |
| fmapi_endpoint_type | global |
| fmapi_context_length | standard |
| fmapi_input_tokens_per_month | 50,000,000 |
| fmapi_output_tokens_per_month | 10,000,000 |

> Cost = DBU cost only (token-based pricing)

---

#### Example 8: Lakebase (Managed PostgreSQL)
| Column | Value |
|--------|-------|
| workload_name | Operational Database |
| workload_type | `LAKEBASE` |
| lakebase_cu | 4 *(4 CU = 4 DBU/hour)* |
| lakebase_storage_gb | 500 |
| lakebase_ha_enabled | true |
| lakebase_backup_retention_days | 14 |
| runs_per_day | 1 |
| avg_runtime_minutes | 1440 *(24 hours/day, always on)* |
| days_per_month | 30 |

> **Cost Calculation:**
> - DBU per hour = `lakebase_cu` (4 CU = 4 DBU/hour)
> - Hours per month = `runs_per_day × (avg_runtime_minutes / 60) × days_per_month` = 1 × 24 × 30 = 720 hours
> - DBU per month = 4 DBU/hour × 720 hours = 2,880 DBU
> - DBU cost = 2,880 DBU × `sync_pricing_dbu_rates.price_per_dbu` (where `product_type = 'DATABASE_SERVERLESS_COMPUTE'`)
> - Total cost = DBU cost + storage cost + backup cost

---

### 4. `conversation_messages`

**Purpose:** Chat messages between SA and AI Copilot.

| Column | Type | PK | FK | Description |
|--------|------|:--:|:--:|-------------|
| `message_id` | UUID | ✓ | | Unique message identifier |
| `estimate_id` | UUID | | ✓ estimates | Parent estimation |
| `message_role` | VARCHAR(20) | | | user, assistant |
| `message_content` | TEXT | | | Message text |
| `message_sequence` | INT | | | Sequential order |
| `message_type` | VARCHAR(50) | | | initial_prompt, clarifying_question |
| `tokens_used` | INT | | | Token count |
| `model_used` | VARCHAR(50) | | | AI model used |
| `created_at` | TIMESTAMP | | | Message timestamp |

> **Note:** `created_by` removed - for 'user' role, derive from `estimates.owner_user_id`.

**Sample Data:**

| message_id | estimate_id | message_role | message_content | message_sequence |
|------------|-------------|--------------|-----------------|------------------|
| msg-001-... | a1b2c3d4-... | user | "I need to estimate costs for a data platform with 10TB daily ingestion, ETL pipelines, and BI dashboards" | 1 |
| msg-002-... | a1b2c3d4-... | assistant | "I'll help you size this. Let me ask a few clarifying questions: 1) What's your peak concurrency for BI? 2) What's your data retention policy?" | 2 |
| msg-003-... | a1b2c3d4-... | user | "Peak 50 concurrent users, 90 days retention" | 3 |
| msg-004-... | a1b2c3d4-... | assistant | "Based on your requirements, I've created 4 workloads: Daily ETL, Streaming Ingestion, DBSQL Serverless, and ML Feature Eng. Total: $45,230/month" | 4 |

---

### 5. `decision_records`

**Purpose:** AI agent decisions, assumptions, and reasoning.

| Column | Type | PK | FK | Description |
|--------|------|:--:|:--:|-------------|
| `record_id` | UUID | ✓ | | Unique decision identifier |
| `line_item_id` | UUID | | ✓ line_items | Associated line item |
| `record_type` | VARCHAR(50) | | | initial_generation, iteration |
| `user_input` | TEXT | | | User's input/feedback |
| `agent_response` | TEXT | | | AI response |
| `assumptions` | JSON | | | Array of assumptions |
| `calculations` | JSON | | | Calculation details |
| `reasoning` | TEXT | | | AI reasoning |
| `created_at` | TIMESTAMP | | | When decision was made |

> **Note:** `estimate_id` and `created_by` removed - derive via `line_items.estimate_id` → `estimates.owner_user_id`.

**Sample Data:**

| record_id | line_item_id | record_type | reasoning |
|-----------|--------------|-------------|-----------|
| dr-001-... | li-001-... | initial_generation | "Based on 10TB daily ingestion, I sized the cluster with 8x i3.2xlarge workers with Photon for optimal performance" |
| dr-002-... | li-002-... | initial_generation | "For real-time ingestion with 10TB/day, I recommend a streaming cluster running 24/7 with auto-scaling" |
| dr-003-... | li-001-... | iteration | "User requested cost reduction. Reduced workers from 8 to 6 and adjusted runtime. New cost: $10,200/month" |

**Sample `assumptions` JSON:**
```json
[
  {"assumption": "Data is in Parquet format", "impact": "medium", "adjustable": true},
  {"assumption": "Cluster utilization is 70%", "impact": "high", "adjustable": true},
  {"assumption": "Peak hours are 9AM-6PM", "impact": "low", "adjustable": true}
]
```

**Sample `calculations` JSON:**
```json
{
  "dbu_per_hour": 12.0,
  "runtime_hours": 2.5,
  "runs_per_month": 120,
  "total_dbu": 3600,
  "dbu_rate": 0.15,
  "dbu_cost": 540,
  "vm_cost_per_hour": 4.992,
  "vm_cost": 1498,
  "total_cost": 2038
}
```

---

### 6. `templates`

**Purpose:** Metadata for downloadable template files.

| Column | Type | PK | FK | Description |
|--------|------|:--:|:--:|-------------|
| `template_id` | UUID | ✓ | | Unique template identifier |
| `template_name` | VARCHAR(255) | | | Template name |
| `workload_type` | VARCHAR(100) | | | Workload type covered |
| `file_path` | VARCHAR(500) | | | Path in Databricks Volume |
| `file_format` | VARCHAR(10) | | | xlsx, csv |
| `mandatory_fields` | JSON | | | Required field names |
| `optional_fields` | JSON | | | Optional field names |
| `description` | TEXT | | | Template description |
| `version` | INT | | | Template version |
| `is_active` | BOOLEAN | | | Available for download? |
| `created_at` | TIMESTAMP | | | Record creation |
| `updated_at` | TIMESTAMP | | | Last update |

**Sample Data:**

| template_id | template_name | workload_type | file_format | is_active |
|-------------|---------------|---------------|-------------|-----------|
| tpl-001-... | ETL Batch Workload | ETL_BATCH | xlsx | true |
| tpl-002-... | SQL Analytics Warehouse | DBSQL | xlsx | true |
| tpl-003-... | ML Training Pipeline | ML_TRAINING | xlsx | true |
| tpl-004-... | Streaming Ingestion | STREAMING | xlsx | true |
| tpl-005-... | GenAI Application | GENAI | xlsx | true |
| tpl-006-... | Full Platform Estimate | MULTI_WORKLOAD | xlsx | true |

**Sample `mandatory_fields` JSON:**
```json
["workload_name", "cloud", "region", "instance_type", "num_workers", "runtime_hours", "runs_per_month"]
```

**Sample `optional_fields` JSON:**
```json
["photon_enabled", "autoscale_min", "autoscale_max", "spot_percentage", "notes"]
```

---

### 7. `sharing`

**Purpose:** Estimate sharing via links or internal users.

| Column | Type | PK | FK | Description |
|--------|------|:--:|:--:|-------------|
| `share_id` | UUID | ✓ | | Unique sharing identifier |
| `estimate_id` | UUID | | ✓ estimates | Estimation being shared |
| `share_type` | VARCHAR(20) | | | public_link, internal_user |
| `shared_with_user_id` | UUID | | ✓ users | User shared with |
| `share_link` | VARCHAR(255) | | | Unique shareable link (UNIQUE) |
| `permission` | VARCHAR(20) | | | view, edit |
| `expires_at` | TIMESTAMP | | | Link expiration |
| `access_count` | INT | | | Access count (default 0) |
| `last_accessed_at` | TIMESTAMP | | | Last access |
| `created_at` | TIMESTAMP | | | Share creation |

> **Note:** `created_by` removed - the estimate owner is always the one who creates shares (via `estimates.owner_user_id`).

**Sample Data:**

| share_id | estimate_id | share_type | shared_with_user_id | share_link | permission | access_count |
|----------|-------------|------------|---------------------|------------|------------|--------------|
| shr-001-... | a1b2c3d4-... | internal_user | 550e8400-...-003 | NULL | view | 5 |
| shr-002-... | a1b2c3d4-... | internal_user | 550e8400-...-004 | NULL | edit | 12 |
| shr-003-... | e5f6g7h8-... | public_link | NULL | lkmtr.io/abc123 | view | 28 |
| shr-004-... | i9j0k1l2-... | public_link | NULL | lkmtr.io/def456 | view | 3 |

---

### 8. `ref_cloud_tiers`

**Purpose:** Defines which estimate tiers are valid for each cloud provider. Prevents invalid combinations (e.g., "Azure Enterprise" doesn't exist).

| Column | Type | PK | Description |
|--------|------|:--:|-------------|
| `cloud` | VARCHAR(20) | ✓ | Cloud provider: AWS, AZURE, GCP |
| `tier` | VARCHAR(50) | ✓ | Estimate tier: STANDARD, PREMIUM, ENTERPRISE |
| `display_name` | VARCHAR(100) | | Human-readable tier name |
| `description` | TEXT | | Tier description |
| `display_order` | INT | | Sort order in UI dropdown |
| `is_active` | BOOLEAN | | Whether tier is currently available |

**Composite Primary Key:** `(cloud, tier)`

**Constraints:**
- `CHECK (cloud IN ('AWS', 'AZURE', 'GCP'))`
- `CHECK (tier IN ('STANDARD', 'PREMIUM', 'ENTERPRISE', 'FREE_TRIAL', 'DEV_TEST'))`
- Foreign Key: `estimates.cloud + estimates.tier → ref_cloud_tiers(cloud, tier)`

**Sample Data:**

| cloud | tier | display_name | description | is_active |
|-------|------|--------------|-------------|-----------|
| AWS | STANDARD | Standard | Standard production workloads | ✅ |
| AWS | PREMIUM | Premium | High-performance production workloads | ✅ |
| AWS | ENTERPRISE | Enterprise | Enterprise-grade with dedicated support | ✅ |
| AZURE | STANDARD | Standard | Standard production workloads | ✅ |
| AZURE | PREMIUM | Premium | High-performance production workloads | ✅ |
| GCP | STANDARD | Standard | Standard production workloads | ✅ |
| GCP | PREMIUM | Premium | High-performance production workloads | ✅ |
| GCP | ENTERPRISE | Enterprise | Enterprise-grade with dedicated support | ✅ |

> **⚠️ Important:** Only **Azure** does NOT have an ENTERPRISE tier. AWS and GCP both support ENTERPRISE. The composite FK constraint prevents invalid combinations.

**Frontend Usage:**

```sql
-- Example 1: Get valid tiers for selected cloud (AWS)
SELECT tier, display_name, description
FROM ref_cloud_tiers
WHERE cloud = 'AWS' AND is_active = TRUE
ORDER BY display_order;

-- Returns: STANDARD, PREMIUM, ENTERPRISE

-- Example 2: Get valid tiers for Azure
SELECT tier, display_name, description
FROM ref_cloud_tiers
WHERE cloud = 'AZURE' AND is_active = TRUE
ORDER BY display_order;

-- Returns: STANDARD, PREMIUM (NO ENTERPRISE)

-- Example 3: Validate cloud/tier combination before insert
SELECT EXISTS (
    SELECT 1 FROM ref_cloud_tiers 
    WHERE cloud = 'AZURE' AND tier = 'ENTERPRISE'
);

-- Returns: FALSE (invalid combination)
```

**API Endpoint (Suggested):**

```
GET /api/v1/tiers?cloud={cloud}

Response:
{
  "cloud": "AZURE",
  "tiers": [
    { "tier": "STANDARD", "display_name": "Standard", "description": "..." },
    { "tier": "PREMIUM", "display_name": "Premium", "description": "..." }
  ]
}
```

---

### 9. `ref_workload_types`

**Purpose:** Configuration table that drives dynamic form UI. Controls which form sections are shown/hidden based on workload type selection.

| Column | Type | PK | Description |
|--------|------|:--:|-------------|
| `workload_type` | VARCHAR(50) | ✓ | Primary key: JOBS, ALL_PURPOSE, DLT, DBSQL, etc. |
| `display_name` | VARCHAR(100) | | Human-readable name |
| `description` | TEXT | | Description for UI tooltip |
| **Form Section Visibility** |
| `show_compute_config` | BOOLEAN | | Show driver/worker node config (always visible for sizing) |
| `show_serverless_toggle` | BOOLEAN | | Show serverless ON/OFF toggle |
| `show_serverless_performance_mode` | BOOLEAN | | Show serverless mode dropdown (standard/performance) - **JOBS/DLT only** |
| `show_photon_toggle` | BOOLEAN | | Show Photon toggle (disabled when serverless=ON) |
| `show_dlt_config` | BOOLEAN | | Show DLT edition (Core/Pro/Advanced) |
| `show_dbsql_config` | BOOLEAN | | Show warehouse type/size |
| `show_serverless_product` | BOOLEAN | | Show serverless product config (Vector Search, Model Serving) |
| `show_fmapi_config` | BOOLEAN | | Show FMAPI model selection |
| `show_lakebase_config` | BOOLEAN | | Show Lakebase config (CU, storage, HA, backup) |
| `show_vector_search_mode` | BOOLEAN | | Show Vector Search mode dropdown (standard/storage_optimized) |
| `show_vm_pricing` | BOOLEAN | | Show VM pricing tier (hidden when serverless=ON) |
| `show_usage_hours` | BOOLEAN | | Show hours per day/month |
| `show_usage_runs` | BOOLEAN | | Show runs per day, runtime |
| `show_usage_tokens` | BOOLEAN | | Show input/output tokens |
| **SKU Mapping** |
| `sku_product_type_standard` | VARCHAR(100) | | Product type for DBU price lookup (non-Photon) |
| `sku_product_type_photon` | VARCHAR(100) | | Product type for DBU price lookup (Photon) |
| `sku_product_type_serverless` | VARCHAR(100) | | Product type for DBU price lookup (Serverless) |
| `display_order` | INT | | Sort order in UI dropdown |

**Sample Data:**

| workload_type | display_name | show_compute_config | show_serverless_toggle | show_serverless_performance_mode | show_photon_toggle | show_dlt_config | show_dbsql_config | show_lakebase_config | show_vector_search_mode | show_vm_pricing |
|---------------|--------------|:-------------------:|:----------------------:|:--------------------------------:|:------------------:|:---------------:|:-----------------:|:--------------------:|:-----------------------:|:---------------:|
| JOBS | Jobs Compute | ✅ | ✅ | ✅ | ✅ | | | | | ✅ |
| ALL_PURPOSE | All-Purpose Compute | ✅ | ✅ | | ✅ | | | | | ✅ |
| DLT | Delta Live Tables | ✅ | ✅ | ✅ | ✅ | ✅ | | | | ✅ |
| DBSQL | Databricks SQL | | | | | | ✅ | | | |
| VECTOR_SEARCH | Vector Search | | | | | | | | ✅ | |
| MODEL_SERVING | Model Serving | | | | | | | | | |
| FMAPI_DATABRICKS | Foundation Models (Databricks) | | | | | | | | | |
| FMAPI_PROPRIETARY | Foundation Models (Proprietary) | | | | | | | | | |
| LAKEBASE | Lakebase | | | | | | | ✅ | | |

> **Notes:**
> - When `show_lakebase_config = TRUE`, the UI displays: `lakebase_cu` dropdown (1/2/4/8 CU), `lakebase_storage_gb` (number input), `lakebase_ha_enabled` (toggle), `lakebase_backup_retention_days` (number input), plus usage/frequency fields.
> - When `show_vector_search_mode = TRUE`, the UI displays: `vector_search_mode` dropdown (standard/storage_optimized).

**SKU Mapping by Workload Type:**

| workload_type | sku_product_type_standard | sku_product_type_photon | sku_product_type_serverless |
|---------------|---------------------------|-------------------------|----------------------------|
| JOBS | JOBS_COMPUTE | JOBS_COMPUTE_(PHOTON) | JOBS_SERVERLESS_COMPUTE |
| ALL_PURPOSE | ALL_PURPOSE_COMPUTE | ALL_PURPOSE_COMPUTE_(PHOTON) | ALL_PURPOSE_SERVERLESS_COMPUTE |
| DLT | DLT_{edition}_COMPUTE | DLT_{edition}_COMPUTE_(PHOTON) | JOBS_SERVERLESS_COMPUTE |
| DBSQL | SQL_COMPUTE / SQL_PRO_COMPUTE | *(N/A)* | SERVERLESS_SQL_COMPUTE |
| VECTOR_SEARCH | *(N/A)* | *(N/A)* | VECTOR_SEARCH_ENDPOINT |
| MODEL_SERVING | *(N/A)* | *(N/A)* | SERVERLESS_REAL_TIME_INFERENCE |
| FMAPI_DATABRICKS | *(N/A)* | *(N/A)* | SERVERLESS_REAL_TIME_INFERENCE |
| FMAPI_PROPRIETARY | *(N/A)* | *(N/A)* | {PROVIDER}_MODEL_SERVING |
| LAKEBASE | *(N/A)* | *(N/A)* | **DATABASE_SERVERLESS_COMPUTE** |

> **Note for LAKEBASE:** DBU per hour = `lakebase_cu` (1 CU = 1 DBU). Pricing uses `DATABASE_SERVERLESS_COMPUTE` product type from `sync_pricing_dbu_rates`.
> 
> **Note for DLT:** The actual `sku_product_type` depends on `dlt_edition` (CORE/PRO/ADVANCED). Example: `DLT_PRO_COMPUTE_(PHOTON)`.

**Form Behavior When Serverless is Toggled ON:**

| Field | Behavior |
|-------|----------|
| `serverless_enabled` | ✅ ON |
| `photon_enabled` | ✅ **Auto-set to ON** (disabled, cannot toggle off) |
| Driver/Worker config | ✅ Still visible (for sizing estimation) |
| VM Pricing options | ❌ **Hidden** (no VM cost for serverless) |
| Cost calculation | Uses `sku_product_type_serverless` instead of standard/photon |

---

## Table Relationships & Join Keys

### How Pricing Tables Join Together

All pricing tables share common join keys (`cloud`, `region`) allowing seamless lookups:


### Join Key Reference

| From Table | To Table | Join Keys | Purpose |
|------------|----------|-----------|---------|
| `pricing_vm_costs` | `pricing_dbu_rates` | `cloud`, `region` | Get DBU price for same cloud/region |
| `pricing_vm_costs` | `ref_instance_dbu_rates` | `cloud`, `instance_type` | Get DBU rate for instance |
| `ref_instance_dbu_rates` | `ref_dbu_multipliers` | `sku_type` (derived) | Apply Photon multiplier |
| `product_dbsql_rates` | `pricing_dbu_rates` | `cloud`, `sku_product_type` = `product_type` | Get DBU price for warehouse |
| `product_serverless_rates` | `pricing_dbu_rates` | `cloud`, `sku_product_type` = `product_type` | Get DBU price for serverless |
| `product_fmapi_*` | `pricing_dbu_rates` | `cloud`, `sku_product_type` = `product_type` | Get DBU price for FMAPI |
| `ref_dbsql_warehouse_config` | `pricing_vm_costs` | `cloud`, `driver_instance_type`/`worker_instance_type` | Get VM cost for DBSQL |

### How Application Tables Join with Pricing Tables


### Workload Type → Product Type Mapping

The product type for DBU price lookup depends on `workload_type`, `serverless_enabled`, and `photon_enabled`:

| workload_type | serverless_enabled | photon_enabled | product_type | Rate Table |
|---------------|:------------------:|:--------------:|--------------|------------|
| `JOBS` | false | false | `JOBS_COMPUTE` | `sync_ref_instance_dbu_rates` |
| `JOBS` | false | true | `JOBS_COMPUTE_(PHOTON)` | `sync_ref_instance_dbu_rates` |
| `JOBS` | **true** | **true** | `JOBS_SERVERLESS_COMPUTE` | Direct DBU lookup |
| `ALL_PURPOSE` | false | false | `ALL_PURPOSE_COMPUTE` | `sync_ref_instance_dbu_rates` |
| `ALL_PURPOSE` | false | true | `ALL_PURPOSE_COMPUTE_(PHOTON)` | `sync_ref_instance_dbu_rates` |
| `ALL_PURPOSE` | **true** | **true** | `ALL_PURPOSE_SERVERLESS_COMPUTE` | Direct DBU lookup |
| `DLT` | false | false | `DLT_{edition}_COMPUTE` | `sync_ref_instance_dbu_rates` |
| `DLT` | false | true | `DLT_{edition}_COMPUTE_(PHOTON)` | `sync_ref_instance_dbu_rates` |
| `DLT` | **true** | **true** | `JOBS_SERVERLESS_COMPUTE` | Direct DBU lookup |
| `DBSQL` | *(via warehouse_type)* | *(N/A)* | `SQL_COMPUTE` / `SQL_PRO_COMPUTE` / `SERVERLESS_SQL_COMPUTE` | `sync_product_dbsql_rates` |
| `VECTOR_SEARCH` | *(always)* | *(N/A)* | `VECTOR_SEARCH_ENDPOINT` | `sync_product_serverless_rates` |
| `MODEL_SERVING` | *(always)* | *(N/A)* | `SERVERLESS_REAL_TIME_INFERENCE` | `sync_product_serverless_rates` |
| `FMAPI_DATABRICKS` | *(always)* | *(N/A)* | `SERVERLESS_REAL_TIME_INFERENCE` | `sync_product_fmapi_databricks` |
| `FMAPI_PROPRIETARY` | *(always)* | *(N/A)* | `{PROVIDER}_MODEL_SERVING` | `sync_product_fmapi_proprietary` |

> **Key Rules:**
> - When `serverless_enabled = true`, VM costs are **NOT** calculated (only DBU cost).
> - **Serverless Mode Multiplier:** 
>   - `serverless_mode = 'standard'`: DBU calculation uses 1x multiplier
>   - `serverless_mode = 'performance'`: DBU calculation uses **2x multiplier** (double the cost for faster execution)

### Complete Cost Calculation Join Example

```sql
-- Calculate cost for Jobs Compute (Classic with Photon)
-- NOTE: Use v_line_items_with_costs view for production!
-- This example shows the manual calculation for understanding.
WITH estimate_params AS (
    SELECT 
        e.cloud,
        e.region,
        e.tier,
        li.line_item_id,
        li.workload_name,
        li.serverless_enabled,
        li.photon_enabled,
        li.worker_node_type,
        li.num_workers,
        li.runs_per_day,
        li.avg_runtime_minutes,
        li.days_per_month
    FROM estimates e
    JOIN line_items li ON e.estimate_id = li.estimate_id
    WHERE e.estimate_id = :estimate_id
      AND li.workload_type = 'JOBS'
      AND li.serverless_enabled = FALSE  -- Classic only
)
SELECT 
    p.line_item_id,
    p.workload_name,
    
    -- 1. Base DBU calculation
    ir.dbu_rate as instance_dbu_rate,
    ir.dbu_rate * p.num_workers as base_dbu_per_hour,
    
    -- 2. Apply Photon multiplier (only for classic)
    COALESCE(m.multiplier, 1.0) as photon_multiplier,
    ir.dbu_rate * p.num_workers * COALESCE(m.multiplier, 1.0) as dbu_per_hour,
    
    -- 3. Monthly runtime hours
    (p.runs_per_day * p.avg_runtime_minutes / 60.0 * p.days_per_month) as hours_per_month,
    
    -- 4. DBU cost
    dbu.price_per_dbu as dbu_price,
    
    -- 5. VM cost (only for classic, not serverless)
    vm.cost_per_hour as vm_cost_per_hour

FROM estimate_params p

-- Join 1: Get instance DBU rate (for sizing)
JOIN sync_ref_instance_dbu_rates ir 
    ON ir.cloud = p.cloud 
    AND ir.instance_type = p.worker_node_type

-- Join 2: Get Photon multiplier (if enabled)
LEFT JOIN sync_ref_dbu_multipliers m 
    ON m.sku_type = 'JOBS_COMPUTE' 
    AND m.feature = CASE WHEN p.photon_enabled THEN 'photon' ELSE 'standard' END

-- Join 3: Get DBU price (depends on serverless + photon)
JOIN sync_pricing_dbu_rates dbu 
    ON dbu.cloud = p.cloud 
    AND dbu.region = p.region 
    AND dbu.tier = p.tier 
    AND dbu.product_type = CASE 
        WHEN p.serverless_enabled THEN 'JOBS_SERVERLESS_COMPUTE'
        WHEN p.photon_enabled THEN 'JOBS_COMPUTE_(PHOTON)' 
        ELSE 'JOBS_COMPUTE' 
    END

-- Join 4: Get VM cost (ONLY for classic - skip for serverless)
LEFT JOIN sync_pricing_vm_costs vm 
    ON vm.cloud = p.cloud 
    AND vm.region = p.region 
    AND vm.instance_type = p.worker_node_type 
    AND vm.pricing_tier = 'on_demand'
    AND p.serverless_enabled = FALSE;  -- VM cost only for classic
```

### Serverless Cost Calculation (No VM Cost)

```sql
-- Calculate cost for DBSQL Serverless
-- NOTE: Use v_line_items_with_costs view for production!
SELECT 
    e.cloud, e.region, e.tier,
    li.workload_name,
    li.dbsql_warehouse_size,
    li.hours_per_day * li.days_per_month as hours_per_month,
    
    -- Get DBU per hour from product table
    dbsql.dbu_per_hour,
    
    -- Get DBU price
    dbu.price_per_dbu,
    
    -- Calculate cost (serverless = DBU only, no VM)
    dbsql.dbu_per_hour * li.hours_per_day * li.days_per_month as dbu_per_month,
    dbsql.dbu_per_hour * li.hours_per_day * li.days_per_month * dbu.price_per_dbu as total_cost_per_month

FROM estimates e
JOIN line_items li ON e.estimate_id = li.estimate_id
JOIN sync_product_dbsql_rates dbsql 
    ON dbsql.cloud = e.cloud 
    AND dbsql.warehouse_type = 'serverless'
    AND dbsql.warehouse_size = li.dbsql_warehouse_size
JOIN sync_pricing_dbu_rates dbu 
    ON dbu.cloud = e.cloud 
    AND dbu.region = e.region 
    AND dbu.tier = e.tier 
    AND dbu.product_type = dbsql.sku_product_type
WHERE li.workload_type = 'DBSQL';
```

---

## Database Views (Normalized - Calculated On-the-Fly)

**Design Philosophy:** No calculated costs are stored. All costs are computed via views.

### Benefits of Normalized Design:
- ✅ **Easy to write** - Just INSERT/UPDATE input fields
- ✅ **Easy to update** - Change a price, all costs recalculate automatically
- ✅ **No stale data** - Costs always reflect current pricing
- ✅ **Single source of truth** - Pricing tables are the authority

---

### `v_line_items_with_costs` ⭐ Main Cost Calculation View

**Purpose:** Calculate costs for each line item by joining with pricing tables.

**Calculated Fields:**
| Field | Formula |
|-------|---------|
| `hours_per_month` | hours_per_day × days_per_month (or runs × runtime) |
| `dbu_per_hour` | (driver_dbu + workers × worker_dbu) × photon_multiplier |
| `dbu_per_month` | dbu_per_hour × hours_per_month |
| `dbu_cost_per_month` | dbu_per_month × price_per_dbu |
| `vm_cost_per_month` | (driver_vm + workers × worker_vm) × hours |
| `cost_per_month` | dbu_cost + vm_cost |

**Usage:**
```sql
-- Get line items with calculated costs
SELECT 
    workload_name, workload_type,
    dbu_per_hour, dbu_per_month,
    dbu_cost_per_month, vm_cost_per_month,
    cost_per_month
FROM v_line_items_with_costs
WHERE estimate_id = :estimate_id
ORDER BY display_order;
```

---

### `v_estimates_with_totals`

**Purpose:** Get estimates with totals aggregated from line items.

**Usage:**
```sql
-- Dashboard: My estimates with totals
SELECT estimate_id, estimate_name, customer_name, status,
       total_dbu_per_month, total_cost_per_month, line_item_count
FROM v_estimates_with_totals
WHERE owner_user_id = :user_id AND is_deleted = FALSE
ORDER BY created_at DESC;
```

---

### How It Works: Write vs Read

| Operation | Table/View | Fields |
|-----------|------------|--------|
| **INSERT/UPDATE** | `line_items` | Input fields only (node types, workers, hours) |
| **SELECT costs** | `v_line_items_with_costs` | All fields + calculated costs |
| **SELECT totals** | `v_estimates_with_totals` | Estimate + aggregated costs |

**Example: Create a Line Item**
```sql
-- Write: Just insert input fields (no costs to calculate!)
INSERT INTO line_items (
    line_item_id, estimate_id, workload_name, workload_type,
    driver_node_type, worker_node_type, num_workers,
    photon_enabled, runs_per_day, avg_runtime_minutes, days_per_month,
    vm_pricing_tier
) VALUES (
    gen_random_uuid(), :estimate_id, 'Daily ETL', 'JOBS_CLASSIC',
    'i3.xlarge', 'i3.2xlarge', 8,
    true, 4, 45, 30,
    'on_demand'
);

-- Read: Query the view to get costs
SELECT * FROM v_line_items_with_costs 
WHERE line_item_id = :line_item_id;
```

---

## Primary Keys & Indexes

### Synced Tables (Pricing) - `sync_*` prefix

| Table | Primary Key |
|-------|-------------|
| `sync_pricing_dbu_rates` | (cloud, region, tier, product_type, sku_name) |
| `sync_pricing_vm_costs` | (cloud, region, instance_type, pricing_tier, payment_option) |
| `sync_product_dbsql_rates` | (cloud, warehouse_type, warehouse_size) |
| `sync_product_serverless_rates` | (cloud, product, size_or_model) |
| `sync_product_fmapi_databricks` | (model, rate_type) |
| `sync_product_fmapi_proprietary` | (cloud, provider, model, rate_type, endpoint_type, context_length) |
| `sync_ref_instance_dbu_rates` | (cloud, instance_type) |
| `sync_ref_sku_region_map` | (cloud, sku_region) |
| `sync_ref_dbu_multipliers` | (sku_type, feature) |
| `sync_ref_dbsql_warehouse_config` | (cloud, warehouse_type, warehouse_size) |

### Synced Tables (Salesforce) - `sync_salesforce_*` prefix

| Table | Primary Key | Indexes |
|-------|-------------|---------|
| `sync_salesforce_account` | (salesforce_account_id) | salesforce_account_name |
| `sync_salesforce_usecase` | (salesforce_use_case_id) | customer_id |
| `sync_salesforce_opportunity` | (id) | accountid |

### Application Tables

| Table | Primary Key | Additional Indexes |
|-------|-------------|-------------------|
| `users` | user_id | email (UNIQUE), is_active |
| `estimates` | estimate_id | owner_user_id, (owner_user_id, created_at DESC), is_deleted |
| `line_items` | line_item_id | estimate_id, (estimate_id, display_order) |
| `conversation_messages` | message_id | estimate_id, (estimate_id, message_sequence) |
| `decision_records` | record_id | estimate_id, line_item_id |
| `templates` | template_id | workload_type, is_active |
| `sharing` | share_id | estimate_id, shared_with_user_id, share_link (UNIQUE) |

---

## Sample Queries

### 1. Cost Calculation for ETL Classic

```sql
-- Get all components needed for cost calculation
-- NOTE: For production, use v_line_items_with_costs view!
WITH params AS (
    SELECT 
        'AWS' as cloud,
        'us-east-1' as region,
        'PREMIUM' as tier,
        'i3.2xlarge' as worker_type,
        10 as num_workers,
        3.0 as runtime_hours,
        30 as days_per_month,
        TRUE as use_photon
)
SELECT 
    -- DBU calculation
    ir.dbu_rate * p.num_workers as base_dbu_per_hour,
    ir.dbu_rate * p.num_workers * COALESCE(m.multiplier, 1) as dbu_per_hour,
    ir.dbu_rate * p.num_workers * COALESCE(m.multiplier, 1) * p.runtime_hours * p.days_per_month as dbu_per_month,
    
    -- DBU cost
    dbu.price_per_dbu as dbu_price,
    ir.dbu_rate * p.num_workers * COALESCE(m.multiplier, 1) * p.runtime_hours * p.days_per_month * dbu.price_per_dbu as dbu_cost_per_month,
    
    -- VM cost
    vm.cost_per_hour * p.num_workers as vm_cost_per_hour,
    vm.cost_per_hour * p.num_workers * p.runtime_hours * p.days_per_month as vm_cost_per_month
    
FROM params p
JOIN sync_ref_instance_dbu_rates ir ON ir.cloud = p.cloud AND ir.instance_type = p.worker_type
JOIN sync_pricing_vm_costs vm ON vm.cloud = p.cloud AND vm.region = p.region 
    AND vm.instance_type = p.worker_type AND vm.pricing_tier = 'on_demand'
JOIN sync_pricing_dbu_rates dbu ON dbu.cloud = p.cloud AND dbu.region = p.region 
    AND dbu.tier = p.tier 
    AND dbu.product_type = CASE WHEN p.use_photon THEN 'JOBS_COMPUTE_(PHOTON)' ELSE 'JOBS_COMPUTE' END
LEFT JOIN sync_ref_dbu_multipliers m ON m.sku_type = 'JOBS_COMPUTE' 
    AND m.feature = CASE WHEN p.use_photon THEN 'photon' ELSE 'standard' END;
```

### 2. My Estimates Dashboard

```sql
-- Use the view which calculates totals from line items
SELECT 
    estimate_id,
    estimate_name,
    customer_name,
    status,
    total_dbu_per_month,
    total_cost_per_month,
    line_item_count,
    created_at
FROM v_estimates_with_totals
WHERE owner_user_id = :user_id
AND is_deleted = FALSE
ORDER BY created_at DESC
LIMIT 20;
```

### 3. Shared With Me

```sql
SELECT 
    e.estimate_id,
    e.estimate_name,
    e.customer_name,
    u.full_name as owner_name,
    s.permission,
    s.created_at as shared_at
FROM sharing s
JOIN estimates e ON s.estimate_id = e.estimate_id
JOIN users u ON e.owner_user_id = u.user_id
WHERE s.shared_with_user_id = :user_id
AND s.share_type = 'internal_user'
AND e.is_deleted = FALSE
ORDER BY s.created_at DESC;
```

---

## Next Steps

1. **Create Application Tables** in Lakebase (DDL scripts)
2. **Set up FastAPI** to connect to Lakebase
3. **Implement CRUD operations** for estimates and line items
4. **Build cost calculation service** using pricing tables
5. **Integrate AI Copilot** with decision records

---

**End of Document**
