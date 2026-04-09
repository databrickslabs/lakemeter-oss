---
sidebar_position: 3
---

# Database

Lakemeter uses **Lakebase** (Databricks' managed PostgreSQL) as its transactional database. This page covers the schema design and data management.

![Database guide documentation page](/img/guides/admin-database-guide.png)
*The Database guide — schema overview and application table definitions.*

![Database schema details](/img/guides/admin-database-schema.png)
*Column definitions, relationships, and data types for the core tables.*

## Schema Overview

All tables live in the `lakemeter` schema within the `lakemeter_pricing` database.

### Application Tables

#### estimates

Stores cost estimates created by users.

| Column | Type | Description |
|--------|------|-------------|
| `estimate_id` | UUID | Primary key |
| `estimate_name` | VARCHAR(500) | User-provided name |
| `owner_user_id` | UUID | FK to `users` table |
| `customer_name` | VARCHAR(255) | Optional customer name |
| `cloud` | VARCHAR(50) | Cloud provider (AWS, AZURE, GCP) |
| `region` | VARCHAR(50) | Deployment region |
| `tier` | VARCHAR(20) | Pricing tier (PREMIUM, ENTERPRISE) |
| `status` | VARCHAR(20) | `draft` or `approved` |
| `version` | INTEGER | Increments on each save |
| `template_id` | UUID | Optional FK to `templates` table |
| `original_prompt` | TEXT | AI prompt if generated via chat |
| `discount_config` | JSONB | Discount configuration |
| `is_deleted` | BOOLEAN | Soft delete flag |
| `created_at` | TIMESTAMP | Creation time |
| `updated_at` | TIMESTAMP | Last update time |
| `updated_by` | UUID | FK to `users` — last editor |

#### line_items

Stores individual workloads within an estimate. This is a wide table with columns for all 9 workload types — only the relevant columns are populated for each type.

| Column | Type | Description |
|--------|------|-------------|
| `line_item_id` | UUID | Primary key |
| `estimate_id` | UUID | FK to `estimates` (CASCADE delete) |
| `display_order` | INTEGER | Sort position in the UI |
| `workload_name` | VARCHAR(255) | User-provided name |
| `workload_type` | VARCHAR(50) | FK to `ref_workload_types` |
| `cloud` | VARCHAR(50) | Cloud provider |
| **Serverless** | | |
| `serverless_enabled` | BOOLEAN | Serverless mode flag |
| `serverless_mode` | VARCHAR(20) | `standard` or `performance` |
| **Classic Compute** | | |
| `photon_enabled` | BOOLEAN | Photon acceleration flag |
| `driver_node_type` | VARCHAR(100) | Driver VM instance type |
| `worker_node_type` | VARCHAR(100) | Worker VM instance type |
| `num_workers` | INTEGER | Worker count |
| **DLT** | | |
| `dlt_edition` | VARCHAR(20) | `core`, `pro`, or `advanced` |
| **DBSQL** | | |
| `dbsql_warehouse_type` | VARCHAR(20) | `classic`, `pro`, or `serverless` |
| `dbsql_warehouse_size` | VARCHAR(20) | `2x-small` through `4x-large` |
| `dbsql_num_clusters` | INTEGER | Number of clusters |
| `dbsql_vm_pricing_tier` | VARCHAR(20) | `on-demand`, `1yr`, `3yr` |
| `dbsql_vm_payment_option` | VARCHAR(20) | `no-upfront`, `partial-upfront`, `all-upfront` |
| **Vector Search** | | |
| `vector_search_mode` | VARCHAR(20) | `standard` or `storage_optimized` |
| `vector_capacity_millions` | INTEGER | Vector capacity in millions |
| `vector_search_storage_gb` | INTEGER | Storage in GB |
| **Model Serving** | | |
| `model_serving_gpu_type` | VARCHAR(50) | GPU type (e.g., `gpu_medium_a10g_1x`) |
| **FMAPI** | | |
| `fmapi_provider` | VARCHAR(50) | `anthropic`, `openai`, `google` |
| `fmapi_model` | VARCHAR(100) | Model name |
| `fmapi_endpoint_type` | VARCHAR(20) | `global` or `in_geo` |
| `fmapi_context_length` | VARCHAR(20) | `all`, `short`, `long` |
| `fmapi_rate_type` | VARCHAR(20) | `input_token`, `output_token`, `cache_read`, `cache_write` |
| `fmapi_quantity` | NUMERIC(18,2) | Quantity in millions |
| **Lakebase** | | |
| `lakebase_cu` | INTEGER | Compute units |
| `lakebase_storage_gb` | INTEGER | Storage in GB |
| `lakebase_ha_nodes` | INTEGER | HA replica nodes |
| `lakebase_backup_retention_days` | INTEGER | Backup retention |
| **Usage** | | |
| `runs_per_day` | INTEGER | Daily job runs |
| `avg_runtime_minutes` | INTEGER | Average runtime per run |
| `days_per_month` | INTEGER | Active days (default: 22) |
| `hours_per_month` | INTEGER | Monthly usage hours |
| **Pricing** | | |
| `driver_pricing_tier` | VARCHAR(20) | `on-demand`, `1yr`, `3yr` |
| `worker_pricing_tier` | VARCHAR(20) | `spot`, `on-demand`, `1yr`, `3yr` |
| `driver_payment_option` | VARCHAR(20) | Payment option for driver |
| `worker_payment_option` | VARCHAR(20) | Payment option for workers |
| **Other** | | |
| `workload_config` | JSON | Flexible config for additional fields |
| `notes` | TEXT | User notes |
| `created_at` | TIMESTAMP | Creation time |
| `updated_at` | TIMESTAMP | Last update time |

#### users

Stores user accounts (auto-created on first login via SSO).

| Column | Type | Description |
|--------|------|-------------|
| `user_id` | UUID | Primary key |
| `email` | VARCHAR(255) | Unique email address (indexed) |
| `full_name` | VARCHAR(255) | Display name |
| `role` | VARCHAR(50) | User role |
| `is_active` | BOOLEAN | Account active flag |
| `last_login_at` | TIMESTAMP | Most recent login time |
| `created_at` | TIMESTAMP | First login time |
| `updated_at` | TIMESTAMP | Last update time |

#### templates

Stores workload templates for quick estimate creation.

| Column | Type | Description |
|--------|------|-------------|
| `template_id` | UUID | Primary key |
| `template_name` | VARCHAR(255) | Template name |
| `workload_type` | VARCHAR(100) | Associated workload type |
| `file_path` | VARCHAR(500) | Template file path |
| `file_format` | VARCHAR(10) | File format |
| `mandatory_fields` | JSON | Required fields definition |
| `optional_fields` | JSON | Optional fields definition |
| `description` | TEXT | Template description |
| `version` | INTEGER | Template version |
| `is_active` | BOOLEAN | Active flag |
| `created_at` | TIMESTAMP | Creation time |
| `updated_at` | TIMESTAMP | Last update time |

#### sharing

Stores estimate sharing configuration (user-based and link-based).

| Column | Type | Description |
|--------|------|-------------|
| `share_id` | UUID | Primary key |
| `estimate_id` | UUID | FK to `estimates` (CASCADE delete) |
| `share_type` | VARCHAR(20) | `user` or `link` |
| `shared_with_user_id` | UUID | FK to `users` (for user sharing) |
| `share_link` | VARCHAR(255) | Unique share link (for link sharing) |
| `permission` | VARCHAR(20) | `view` or `edit` |
| `expires_at` | TIMESTAMP | Link expiry time |
| `access_count` | INTEGER | Number of accesses |
| `last_accessed_at` | TIMESTAMP | Last access time |
| `created_at` | TIMESTAMP | Creation time |

#### conversation_messages

Stores AI chat conversation history.

| Column | Type | Description |
|--------|------|-------------|
| `message_id` | UUID | Primary key |
| `estimate_id` | UUID | FK to `estimates` (CASCADE delete) |
| `message_role` | VARCHAR(20) | `user`, `assistant`, or `system` |
| `message_content` | TEXT | Message text |
| `message_sequence` | INTEGER | Order within conversation |
| `message_type` | VARCHAR(50) | Message type classifier |
| `tokens_used` | INTEGER | Token count for this message |
| `model_used` | VARCHAR(50) | AI model used |
| `created_at` | TIMESTAMP | Creation time |

#### decision_records

Stores AI decision audit trail — records the reasoning behind AI-generated workloads.

| Column | Type | Description |
|--------|------|-------------|
| `record_id` | UUID | Primary key |
| `line_item_id` | UUID | FK to `line_items` (CASCADE delete) |
| `record_type` | VARCHAR(50) | Decision type |
| `user_input` | TEXT | Original user request |
| `agent_response` | TEXT | AI agent's response |
| `assumptions` | JSON | Assumptions made by the AI |
| `calculations` | JSON | Calculation details |
| `reasoning` | TEXT | Explanation of the decision |
| `created_at` | TIMESTAMP | Creation time |

### Reference Tables

#### ref_workload_types

Defines the 9 supported workload types and their UI configuration.

| Column | Type | Description |
|--------|------|-------------|
| `workload_type` | VARCHAR(50) | Primary key (JOBS, SQL_WAREHOUSE, etc.) |
| `display_name` | VARCHAR(100) | Human-readable name |
| `description` | TEXT | Description |
| `show_compute_config` | BOOLEAN | Show compute config in UI |
| `show_serverless_toggle` | BOOLEAN | Show serverless option |
| `show_serverless_performance_mode` | BOOLEAN | Show performance mode |
| `show_photon_toggle` | BOOLEAN | Show Photon option |
| `show_dlt_config` | BOOLEAN | Show DLT edition selector |
| `show_dbsql_config` | BOOLEAN | Show DBSQL config fields |
| `show_fmapi_config` | BOOLEAN | Show FMAPI config fields |
| `show_lakebase_config` | BOOLEAN | Show Lakebase config fields |
| `show_vector_search_mode` | BOOLEAN | Show vector search mode |
| `show_vm_pricing` | BOOLEAN | Show VM pricing options |
| `show_usage_hours` | BOOLEAN | Show hours input |
| `show_usage_runs` | BOOLEAN | Show runs-per-day input |
| `show_usage_tokens` | BOOLEAN | Show token quantity input |
| `sku_product_type_standard` | VARCHAR(100) | Standard SKU product type |
| `sku_product_type_photon` | VARCHAR(100) | Photon SKU product type |
| `sku_product_type_serverless` | VARCHAR(100) | Serverless SKU product type |
| `display_order` | INTEGER | Sort order in UI |

#### ref_cloud_tiers

Valid cloud provider and pricing tier combinations.

| Column | Type |
|--------|------|
| `cloud` | VARCHAR (PK) |
| `tier` | VARCHAR (PK) |

Seeded values: AWS/AZURE/GCP with PREMIUM/ENTERPRISE tiers, plus AWS/AZURE with STANDARD tier.

### Pricing Sync Tables

These tables store pricing data loaded from `backend/static/pricing/` JSON files by the installer:

| Table | Content |
|-------|---------|
| `sync_pricing_dbu_rates` | DBU rates by SKU, cloud, region, tier |
| `sync_pricing_vm_costs` | VM instance costs by cloud, region, pricing tier |
| `sync_product_dbsql_rates` | DBSQL warehouse DBU rates by type and size |
| `sync_product_fmapi_databricks` | FMAPI Databricks-hosted model rates |
| `sync_product_fmapi_proprietary` | FMAPI proprietary model rates |
| `sync_product_serverless_rates` | Serverless product rates |
| `sync_ref_dbsql_warehouse_config` | DBSQL warehouse driver/worker configurations |
| `sync_ref_dbu_multipliers` | Feature multipliers (Photon, serverless) |
| `sync_ref_instance_dbu_rates` | Instance-level DBU rates with vCPU/memory |
| `sync_ref_sku_region_map` | SKU region to region code mapping |
| `ref_fmapi_databricks_models` | Available FMAPI Databricks models |
| `ref_fmapi_proprietary_models` | Available FMAPI proprietary models |
| `ref_model_serving_gpu_types` | Available Model Serving GPU types |

## Database Access

### From the Application

The FastAPI backend uses SQLAlchemy with OAuth token-based authentication. The token manager (`backend/app/auth/token_manager.py`) handles SP credential exchange and token refresh automatically. The database engine is configured with connection pooling (5 connections, 10 overflow, 15-minute recycle) and proactive token refresh every 30 minutes.

No manual connection handling is needed — the `get_db()` dependency provides a session per request and handles token refresh on auth failures.

### From Notebooks

```python
# Using Databricks SDK credential generation
from databricks.sdk import WorkspaceClient
import psycopg2

w = WorkspaceClient()
cred = w.database.generate_database_credential(
    request_id="your-request-id",
    instance_names=["your-instance-name"]
)

conn = psycopg2.connect(
    host="instance-xxx.database.cloud.databricks.com",
    port=5432,
    database="lakemeter_pricing",
    user="your-email@company.com",
    password=cred.token,
    sslmode="require"
)
```

## Backups

Lakebase provides built-in backup and recovery. No additional backup configuration is required for the application database. Consult your Databricks workspace administrator for backup policies.

## Indexes

The following indexes are created by the installer:

| Index | Table | Column(s) |
|-------|-------|-----------|
| `idx_line_items_estimate` | `line_items` | `estimate_id` |
| `idx_line_items_workload_type` | `line_items` | `workload_type` |
| (unique) | `users` | `email` |
