# Databricks notebook source
# MAGIC %md
# MAGIC # Step 2: Create Database, Schema, Tables, and Auth Role
# MAGIC Creates the application database, schema, all tables with seed data,
# MAGIC and a password-authenticated role for fallback connectivity.

# COMMAND ----------

dbutils.widgets.text("instance_name", "lakemeter-customer")
dbutils.widgets.text("db_name", "lakemeter_pricing")
dbutils.widgets.text("secrets_scope", "lakemeter-secrets")

instance_name = dbutils.widgets.get("instance_name")
db_name = dbutils.widgets.get("db_name")
secrets_scope = dbutils.widgets.get("secrets_scope")

print(f"Instance: {instance_name}")
print(f"Database: {db_name}")
print(f"Secrets scope: {secrets_scope}")

# COMMAND ----------

import uuid
import secrets as py_secrets
import psycopg2
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Get instance info from upstream task
instance_host = dbutils.jobs.taskValues.get(taskKey="provision_lakebase", key="instance_host")
print(f"Instance host: {instance_host}")

SCHEMA = "lakemeter"

def get_owner_connection(database="postgres"):
    """Get a psycopg2 connection as the instance owner."""
    cred = w.database.generate_database_credential(
        request_id=str(uuid.uuid4()),
        instance_names=[instance_name],
    )
    return psycopg2.connect(
        host=instance_host,
        port=5432,
        database=database,
        user=w.current_user.me().user_name,
        password=cred.token,
        sslmode="require",
    )

# COMMAND ----------

# Create database if not exists
conn = get_owner_connection("postgres")
conn.autocommit = True
cur = conn.cursor()

cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
if not cur.fetchone():
    print(f"Creating database '{db_name}'...")
    cur.execute(f'CREATE DATABASE {db_name}')
    print(f"Database '{db_name}' created")
else:
    print(f"Database '{db_name}' already exists")

cur.close()
conn.close()

# Create schema
conn = get_owner_connection(db_name)
conn.autocommit = True
cur = conn.cursor()
cur.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
print(f"Schema '{SCHEMA}' ready")
cur.close()
conn.close()

# COMMAND ----------

# Create application tables
conn = get_owner_connection(db_name)
conn.autocommit = True
cur = conn.cursor()

table_stmts = [
    f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}",

    f"""CREATE TABLE IF NOT EXISTS {SCHEMA}.users (
        user_id UUID PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        full_name VARCHAR(255),
        role VARCHAR(50),
        is_active BOOLEAN DEFAULT true,
        last_login_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",

    f"""CREATE TABLE IF NOT EXISTS {SCHEMA}.templates (
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
    )""",

    f"""CREATE TABLE IF NOT EXISTS {SCHEMA}.ref_cloud_tiers (
        cloud VARCHAR(20) NOT NULL,
        tier VARCHAR(50) NOT NULL,
        display_name VARCHAR(100),
        description TEXT,
        display_order INT DEFAULT 0,
        is_active BOOLEAN DEFAULT true,
        PRIMARY KEY (cloud, tier)
    )""",

    f"""CREATE TABLE IF NOT EXISTS {SCHEMA}.ref_workload_types (
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
    )""",

    f"""CREATE TABLE IF NOT EXISTS {SCHEMA}.estimates (
        estimate_id UUID PRIMARY KEY,
        estimate_name VARCHAR(500),
        owner_user_id UUID REFERENCES {SCHEMA}.users(user_id),
        sfdc_account_id VARCHAR(255),
        customer_name VARCHAR(255),
        uco_id VARCHAR(255),
        opportunity_id VARCHAR(255),
        cloud VARCHAR(20),
        region VARCHAR(50),
        tier VARCHAR(20),
        status VARCHAR(20) DEFAULT 'draft',
        version INT DEFAULT 1,
        template_id UUID REFERENCES {SCHEMA}.templates(template_id),
        original_prompt TEXT,
        display_order INT DEFAULT 0,
        is_deleted BOOLEAN DEFAULT false,
        discount_config JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_by UUID REFERENCES {SCHEMA}.users(user_id)
    )""",

    f"""CREATE TABLE IF NOT EXISTS {SCHEMA}.line_items (
        line_item_id UUID PRIMARY KEY,
        estimate_id UUID REFERENCES {SCHEMA}.estimates(estimate_id),
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
        fmapi_provider VARCHAR(50),
        fmapi_model VARCHAR(100),
        fmapi_endpoint_type VARCHAR(20),
        fmapi_context_length VARCHAR(20),
        fmapi_rate_type VARCHAR(20),
        fmapi_quantity BIGINT,
        lakebase_cu NUMERIC(5,1),
        lakebase_storage_gb INT,
        lakebase_ha_nodes INT DEFAULT 1,
        lakebase_backup_retention_days INT DEFAULT 7,
        lakebase_pitr_gb INT,
        lakebase_snapshot_gb INT,
        databricks_apps_size VARCHAR(20),
        clean_room_collaborators INTEGER,
        ai_parse_mode VARCHAR(20),
        ai_parse_complexity VARCHAR(20),
        ai_parse_pages_thousands NUMERIC(12,2),
        shutterstock_images INTEGER,
        lakeflow_connect_pipeline_mode VARCHAR(20),
        lakeflow_connect_gateway_enabled BOOLEAN,
        lakeflow_connect_gateway_instance VARCHAR(100),
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",

    f"""CREATE TABLE IF NOT EXISTS {SCHEMA}.conversation_messages (
        message_id UUID PRIMARY KEY,
        estimate_id UUID REFERENCES {SCHEMA}.estimates(estimate_id),
        message_role VARCHAR(20),
        message_content TEXT,
        message_sequence INT,
        message_type VARCHAR(50),
        tokens_used INT,
        model_used VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",

    f"""CREATE TABLE IF NOT EXISTS {SCHEMA}.decision_records (
        record_id UUID PRIMARY KEY,
        line_item_id UUID REFERENCES {SCHEMA}.line_items(line_item_id),
        record_type VARCHAR(50),
        user_input TEXT,
        agent_response TEXT,
        assumptions JSON,
        calculations JSON,
        reasoning TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",

    f"""CREATE TABLE IF NOT EXISTS {SCHEMA}.sharing (
        share_id UUID PRIMARY KEY,
        estimate_id UUID REFERENCES {SCHEMA}.estimates(estimate_id),
        share_type VARCHAR(20),
        shared_with_user_id UUID REFERENCES {SCHEMA}.users(user_id),
        share_link VARCHAR(255) UNIQUE,
        permission VARCHAR(20),
        expires_at TIMESTAMP,
        access_count INT DEFAULT 0,
        last_accessed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",

    f"CREATE INDEX IF NOT EXISTS idx_line_items_estimate ON {SCHEMA}.line_items(estimate_id)",
    f"CREATE INDEX IF NOT EXISTS idx_line_items_workload_type ON {SCHEMA}.line_items(workload_type)",
]

for stmt in table_stmts:
    try:
        cur.execute(stmt)
    except Exception as e:
        if "already exists" not in str(e):
            print(f"Warning: {str(e)[:120]}")

print("Application tables created")

# COMMAND ----------

# Seed workload types
workload_seeds = [
    ("JOBS", "Jobs Compute", "Scheduled batch jobs (Classic or Serverless)",
     True, True, True, True, False, False, False, False, False, False, True, False, True, False,
     "JOBS_COMPUTE", "JOBS_COMPUTE_(PHOTON)", "JOBS_SERVERLESS_COMPUTE", 1),
    ("ALL_PURPOSE", "All-Purpose Compute", "Interactive clusters for notebooks (Classic or Serverless)",
     True, True, False, True, False, False, False, False, False, False, True, True, False, False,
     "ALL_PURPOSE_COMPUTE", "ALL_PURPOSE_COMPUTE_(PHOTON)", "ALL_PURPOSE_SERVERLESS_COMPUTE", 2),
    ("DLT", "Delta Live Tables", "Declarative ETL pipelines (Classic or Serverless)",
     True, True, True, True, True, False, False, False, False, False, True, True, False, False,
     "DLT_CORE_COMPUTE", "DLT_CORE_COMPUTE_(PHOTON)", "JOBS_SERVERLESS_COMPUTE", 3),
    ("DBSQL", "Databricks SQL", "SQL analytics warehouse (Classic/Pro/Serverless)",
     False, False, False, False, False, True, False, False, False, False, False, True, False, False,
     "SQL_COMPUTE", "SQL_PRO_COMPUTE", "SERVERLESS_SQL_COMPUTE", 4),
    ("VECTOR_SEARCH", "Vector Search", "Vector search endpoints for RAG",
     False, False, False, False, False, False, True, False, False, True, False, True, False, False,
     None, None, "VECTOR_SEARCH_ENDPOINT", 5),
    ("MODEL_SERVING", "Model Serving", "Real-time model inference endpoints",
     False, False, False, False, False, False, True, False, False, False, False, True, False, False,
     None, None, "SERVERLESS_REAL_TIME_INFERENCE", 6),
    ("FMAPI_DATABRICKS", "Foundation Models (Databricks)", "Databricks-hosted LLMs (Llama, DBRX)",
     False, False, False, False, False, False, False, True, False, False, False, False, False, True,
     None, None, "SERVERLESS_REAL_TIME_INFERENCE", 7),
    ("FMAPI_PROPRIETARY", "Foundation Models (Proprietary)", "OpenAI, Anthropic, Google models served by Databricks",
     False, False, False, False, False, False, False, True, False, False, False, False, False, True,
     None, None, None, 8),
    ("LAKEBASE", "Lakebase", "Managed PostgreSQL database for operational workloads",
     False, False, False, False, False, False, False, False, True, False, False, True, True, False,
     None, None, "DATABASE_SERVERLESS_COMPUTE", 9),
]

for wt in workload_seeds:
    cur.execute(
        f"""INSERT INTO {SCHEMA}.ref_workload_types
           (workload_type, display_name, description,
            show_compute_config, show_serverless_toggle, show_serverless_performance_mode,
            show_photon_toggle, show_dlt_config, show_dbsql_config,
            show_serverless_product, show_fmapi_config, show_lakebase_config,
            show_vector_search_mode, show_vm_pricing, show_usage_hours,
            show_usage_runs, show_usage_tokens,
            sku_product_type_standard, sku_product_type_photon, sku_product_type_serverless,
            display_order)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT (workload_type) DO NOTHING""",
        wt,
    )

# Seed cloud tiers
cloud_tier_seeds = [
    ("AWS", "STANDARD", "Standard", "Standard production workloads", 1, True),
    ("AWS", "PREMIUM", "Premium", "High-performance production workloads", 2, True),
    ("AWS", "ENTERPRISE", "Enterprise", "Enterprise-grade workloads", 3, True),
    ("AZURE", "STANDARD", "Standard", "Standard production workloads", 1, True),
    ("AZURE", "PREMIUM", "Premium", "High-performance production workloads", 2, True),
    ("GCP", "STANDARD", "Standard", "Standard production workloads", 1, True),
    ("GCP", "PREMIUM", "Premium", "High-performance production workloads", 2, True),
    ("GCP", "ENTERPRISE", "Enterprise", "Enterprise-grade workloads", 3, True),
]

for ct in cloud_tier_seeds:
    cur.execute(
        f"""INSERT INTO {SCHEMA}.ref_cloud_tiers
           (cloud, tier, display_name, description, display_order, is_active)
           VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (cloud, tier) DO NOTHING""",
        ct,
    )

print("Seed data loaded (9 workload types, 8 cloud tiers)")

# COMMAND ----------

# Schema migrations (ensure all columns exist for older installations)
migration_columns = [
    ("display_order", "INT"),
    ("serverless_enabled", "BOOLEAN DEFAULT false"),
    ("serverless_mode", "VARCHAR(20)"),
    ("photon_enabled", "BOOLEAN DEFAULT false"),
    ("driver_node_type", "VARCHAR(100)"),
    ("worker_node_type", "VARCHAR(100)"),
    ("num_workers", "INT"),
    ("dlt_edition", "VARCHAR(20)"),
    ("dbsql_warehouse_type", "VARCHAR(20)"),
    ("dbsql_warehouse_size", "VARCHAR(20)"),
    ("dbsql_num_clusters", "INT DEFAULT 1"),
    ("dbsql_vm_pricing_tier", "VARCHAR(20)"),
    ("dbsql_vm_payment_option", "VARCHAR(20)"),
    ("vector_search_mode", "VARCHAR(50)"),
    ("vector_capacity_millions", "DECIMAL(10,2)"),
    ("vector_search_storage_gb", "DECIMAL(10,2)"),
    ("model_serving_gpu_type", "VARCHAR(50)"),
    ("fmapi_provider", "VARCHAR(50)"),
    ("fmapi_model", "VARCHAR(100)"),
    ("fmapi_endpoint_type", "VARCHAR(20)"),
    ("fmapi_context_length", "VARCHAR(20)"),
    ("fmapi_rate_type", "VARCHAR(20)"),
    ("fmapi_quantity", "BIGINT"),
    ("lakebase_cu", "NUMERIC(5,1)"),
    ("databricks_apps_size", "VARCHAR(20)"),
    ("clean_room_collaborators", "INTEGER"),
    ("ai_parse_mode", "VARCHAR(20)"),
    ("ai_parse_complexity", "VARCHAR(20)"),
    ("ai_parse_pages_thousands", "NUMERIC(12,2)"),
    ("shutterstock_images", "INTEGER"),
    ("lakeflow_connect_pipeline_mode", "VARCHAR(20)"),
    ("lakeflow_connect_gateway_enabled", "BOOLEAN"),
    ("lakeflow_connect_gateway_instance", "VARCHAR(100)"),
    ("lakebase_storage_gb", "INT"),
    ("lakebase_ha_nodes", "INT DEFAULT 1"),
    ("lakebase_backup_retention_days", "INT DEFAULT 7"),
    ("lakebase_pitr_gb", "INT"),
    ("lakebase_snapshot_gb", "INT"),
    ("runs_per_day", "INT"),
    ("avg_runtime_minutes", "INT"),
    ("days_per_month", "INT DEFAULT 30"),
    ("hours_per_month", "DECIMAL(10,2)"),
    ("driver_pricing_tier", "VARCHAR(20)"),
    ("worker_pricing_tier", "VARCHAR(20)"),
    ("driver_payment_option", "VARCHAR(20)"),
    ("worker_payment_option", "VARCHAR(20)"),
    ("workload_config", "JSON"),
]

for col_name, col_type in migration_columns:
    try:
        cur.execute(f"ALTER TABLE {SCHEMA}.line_items ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
    except Exception:
        pass

# discount_config on estimates
cur.execute(f"ALTER TABLE {SCHEMA}.estimates ADD COLUMN IF NOT EXISTS discount_config JSONB")

# Lakebase CU constraint
cur.execute(f"ALTER TABLE {SCHEMA}.line_items DROP CONSTRAINT IF EXISTS chk_lakebase_cu")
cur.execute(f"ALTER TABLE {SCHEMA}.line_items ALTER COLUMN lakebase_cu TYPE NUMERIC(5,1)")
valid_cus = ",".join(str(v) for v in [0.5] + list(range(1, 113)))
cur.execute(f"ALTER TABLE {SCHEMA}.line_items ADD CONSTRAINT chk_lakebase_cu CHECK (lakebase_cu IN ({valid_cus}))")

print("Schema migrations complete")

# COMMAND ----------

# Case normalization triggers
try:
    cur.execute(f"""
        CREATE OR REPLACE FUNCTION {SCHEMA}.normalize_estimates_case()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.cloud IS NOT NULL THEN NEW.cloud = UPPER(NEW.cloud); END IF;
            IF NEW.tier IS NOT NULL THEN NEW.tier = UPPER(NEW.tier); END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    cur.execute(f"""
        CREATE OR REPLACE FUNCTION {SCHEMA}.normalize_line_items_case()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.cloud IS NOT NULL THEN NEW.cloud = UPPER(NEW.cloud); END IF;
            IF NEW.workload_type IS NOT NULL THEN NEW.workload_type = UPPER(NEW.workload_type); END IF;
            IF NEW.dbsql_warehouse_type IS NOT NULL THEN NEW.dbsql_warehouse_type = UPPER(NEW.dbsql_warehouse_type); END IF;
            IF NEW.dlt_edition IS NOT NULL THEN NEW.dlt_edition = UPPER(NEW.dlt_edition); END IF;
            IF NEW.serverless_mode IS NOT NULL THEN NEW.serverless_mode = LOWER(NEW.serverless_mode); END IF;
            IF NEW.vector_search_mode IS NOT NULL THEN NEW.vector_search_mode = LOWER(NEW.vector_search_mode); END IF;
            IF NEW.fmapi_provider IS NOT NULL THEN NEW.fmapi_provider = LOWER(NEW.fmapi_provider); END IF;
            IF NEW.fmapi_rate_type IS NOT NULL THEN NEW.fmapi_rate_type = LOWER(NEW.fmapi_rate_type); END IF;
            IF NEW.fmapi_endpoint_type IS NOT NULL THEN NEW.fmapi_endpoint_type = LOWER(NEW.fmapi_endpoint_type); END IF;
            IF NEW.fmapi_context_length IS NOT NULL THEN NEW.fmapi_context_length = LOWER(NEW.fmapi_context_length); END IF;
            IF NEW.model_serving_gpu_type IS NOT NULL THEN NEW.model_serving_gpu_type = LOWER(NEW.model_serving_gpu_type); END IF;
            IF NEW.driver_pricing_tier IS NOT NULL THEN NEW.driver_pricing_tier = LOWER(NEW.driver_pricing_tier); END IF;
            IF NEW.worker_pricing_tier IS NOT NULL THEN NEW.worker_pricing_tier = LOWER(NEW.worker_pricing_tier); END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    cur.execute(f"DROP TRIGGER IF EXISTS trg_normalize_estimates_case ON {SCHEMA}.estimates")
    cur.execute(f"""
        CREATE TRIGGER trg_normalize_estimates_case
        BEFORE INSERT OR UPDATE ON {SCHEMA}.estimates
        FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.normalize_estimates_case()
    """)
    cur.execute(f"DROP TRIGGER IF EXISTS trg_normalize_line_items_case ON {SCHEMA}.line_items")
    cur.execute(f"""
        CREATE TRIGGER trg_normalize_line_items_case
        BEFORE INSERT OR UPDATE ON {SCHEMA}.line_items
        FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.normalize_line_items_case()
    """)
    print("Case normalization triggers created")
except Exception as e:
    print(f"Warning: triggers: {str(e)[:100]}")

# COMMAND ----------

# Create password-auth role (fallback when SP OAuth isn't configured)
role_name = "lakemeter_sync_role"

cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role_name,))
exists = cur.fetchone()

password = py_secrets.token_urlsafe(32)

if not exists:
    print(f"Creating password-auth role '{role_name}'...")
    cur.execute(f"CREATE ROLE {role_name} LOGIN PASSWORD %s", (password,))
    print(f"Role '{role_name}' created")
else:
    cur.execute(f"ALTER ROLE {role_name} PASSWORD %s", (password,))
    print(f"Role '{role_name}' password reset")

cur.execute(f"GRANT CONNECT ON DATABASE {db_name} TO {role_name}")
cur.execute(f"GRANT USAGE ON SCHEMA {SCHEMA} TO {role_name}")
cur.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {SCHEMA} TO {role_name}")
cur.execute(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {SCHEMA} TO {role_name}")
cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA} GRANT ALL PRIVILEGES ON TABLES TO {role_name}")
print(f"Permissions granted to '{role_name}'")

cur.close()
conn.close()

# COMMAND ----------

# Store credentials in secrets scope

# Ensure scope exists
try:
    w.secrets.list_secrets(scope=secrets_scope)
except Exception:
    try:
        w.secrets.create_scope(scope=secrets_scope)
        print(f"Secrets scope '{secrets_scope}' created")
    except Exception as e:
        if "already exists" not in str(e).lower():
            raise

w.secrets.put_secret(scope=secrets_scope, key="lakebase-user", string_value=role_name)
w.secrets.put_secret(scope=secrets_scope, key="lakebase-password", string_value=password)
w.secrets.put_secret(scope=secrets_scope, key="lakebase-host", string_value=instance_host)
w.secrets.put_secret(scope=secrets_scope, key="lakebase-database", string_value=db_name)
print("Credentials stored in secrets scope")

dbutils.notebook.exit("Database, schema, tables, and auth role created successfully")
