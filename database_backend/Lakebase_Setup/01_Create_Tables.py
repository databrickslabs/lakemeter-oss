# Databricks notebook source
# MAGIC %md
# MAGIC # Lakemeter - Create Application Tables
# MAGIC 
# MAGIC **Purpose:** Creates all application tables for the Lakemeter cost estimation app
# MAGIC 
# MAGIC **Connects to:** Lakebase (PostgreSQL)
# MAGIC 
# MAGIC **Tables Created:**
# MAGIC - users
# MAGIC - templates  
# MAGIC - estimates
# MAGIC - line_items
# MAGIC - ref_workload_types (with seed data)
# MAGIC - ref_cloud_tiers (with seed data)
# MAGIC - conversation_messages
# MAGIC - decision_records
# MAGIC - sharing
# MAGIC 
# MAGIC **Constraints Added:**
# MAGIC - Cloud/Tier validation (~32 constraints)
# MAGIC - Business logic constraints (8)
# MAGIC - Enum value constraints (15)
# MAGIC - Triggers for auto-sync
# MAGIC 
# MAGIC **Run Order:**
# MAGIC 1. Run this notebook FIRST
# MAGIC 2. Run Pricing_Sync notebooks
# MAGIC 3. Run 04_Add_Sync_Constraints (region + instance validation)
# MAGIC 4. Run 02_Create_Views (cost calculation views)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Install Dependencies & Connect to Lakebase

# COMMAND ----------

# Install required packages
%pip install psycopg2-binary --quiet
dbutils.library.restartPython()

# COMMAND ----------

import psycopg2
from datetime import datetime

# Lakebase connection details
LAKEBASE_HOST = "instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com"
LAKEBASE_PORT = 5432
LAKEBASE_DATABASE = "lakemeter_pricing"
LAKEBASE_USER = "lakemeter_sync_role"
LAKEBASE_PASSWORD = "***REMOVED_DATABASE_CREDENTIAL***"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Helper Functions

# COMMAND ----------

def get_connection():
    """Create PostgreSQL connection"""
    return psycopg2.connect(
        host=LAKEBASE_HOST,
        port=LAKEBASE_PORT,
        database=LAKEBASE_DATABASE,
        user=LAKEBASE_USER,
        password=LAKEBASE_PASSWORD,
        sslmode='require'
    )

def execute_sql(sql_statement, description="SQL", show_error=True):
    """Execute SQL statement and return success/failure"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql_statement)
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ {description}")
        return True
    except Exception as e:
        error_msg = str(e)
        if show_error:
            # Check if it's a "doesn't exist" error (harmless)
            if "does not exist" in error_msg:
                print(f"⚪ {description} (doesn't exist - OK)")
                return True  # Treat as success
            else:
                # Real error (like ownership issue)
                print(f"❌ {description}")
                print(f"   Error: {error_msg}")
                return False
        else:
            # Silent mode
            print(f"⚪ {description}")
            return False

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Test Connection

# COMMAND ----------

try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    cur.close()
    conn.close()
    print("✅ Connected to Lakebase!")
    print(f"   PostgreSQL version: {version[:50]}...")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Drop Existing Objects

# COMMAND ----------

print("=" * 80)
print("🗑️  DROPPING EXISTING OBJECTS (if they exist)")
print("=" * 80)
print("\nThis ensures a clean slate by removing any existing objects.")
print("Drop order: Triggers → Functions → Views → Tables")
print("=" * 80)

# Drop in correct dependency order
drop_statements = [
    # 1. Drop triggers first (depend on functions and tables)
    ("DROP TRIGGER IF EXISTS trg_sync_line_item_cloud ON lakemeter.line_items CASCADE", "Drop trigger: trg_sync_line_item_cloud"),
    ("DROP TRIGGER IF EXISTS trg_sync_estimate_cloud ON lakemeter.estimates CASCADE", "Drop trigger: trg_sync_estimate_cloud"),
    
    # 2. Drop functions (triggers depend on these)
    ("DROP FUNCTION IF EXISTS lakemeter.sync_line_item_cloud() CASCADE", "Drop function: sync_line_item_cloud()"),
    ("DROP FUNCTION IF EXISTS lakemeter.sync_estimate_cloud_to_line_items() CASCADE", "Drop function: sync_estimate_cloud_to_line_items()"),
    
    # 3. Drop views (depend on tables)
    ("DROP VIEW IF EXISTS lakemeter.v_estimates_with_totals CASCADE", "Drop view: v_estimates_with_totals"),
    ("DROP VIEW IF EXISTS lakemeter.v_line_items_with_costs CASCADE", "Drop view: v_line_items_with_costs"),
    
    # 4. Drop tables (in reverse dependency order)
    ("DROP TABLE IF EXISTS lakemeter.decision_records CASCADE", "Drop table: decision_records"),
    ("DROP TABLE IF EXISTS lakemeter.conversation_messages CASCADE", "Drop table: conversation_messages"),
    ("DROP TABLE IF EXISTS lakemeter.sharing CASCADE", "Drop table: sharing"),
    ("DROP TABLE IF EXISTS lakemeter.line_items CASCADE", "Drop table: line_items"),
    ("DROP TABLE IF EXISTS lakemeter.estimates CASCADE", "Drop table: estimates"),
    ("DROP TABLE IF EXISTS lakemeter.templates CASCADE", "Drop table: templates"),
    ("DROP TABLE IF EXISTS lakemeter.users CASCADE", "Drop table: users"),
    ("DROP TABLE IF EXISTS lakemeter.ref_cloud_tiers CASCADE", "Drop table: ref_cloud_tiers"),
    ("DROP TABLE IF EXISTS lakemeter.ref_workload_types CASCADE", "Drop table: ref_workload_types"),
]

print("\n📋 Dropping objects...")
success_count = 0
failed_objects = []

for sql, desc in drop_statements:
    # Show errors so we can see what's failing
    result = execute_sql(sql, desc, show_error=True)
    if result:
        success_count += 1
    else:
        failed_objects.append(desc)

print(f"\n📊 Cleanup summary: {success_count}/{len(drop_statements)} objects dropped")

if failed_objects:
    print(f"\n⚠️  WARNING: {len(failed_objects)} objects could not be dropped:")
    for obj in failed_objects:
        print(f"   ❌ {obj}")
    print("\n💡 This usually means objects are owned by another user.")
    print("\n🔧 SOLUTION: Run this SQL in Lakebase SQL Editor to diagnose and fix:")
    print("=" * 70)
    print("""
-- 1. Check who owns the functions
SELECT 
    p.proname as function_name,
    pg_get_userbyid(p.proowner) as owner,
    'DROP FUNCTION lakemeter.' || p.proname || '() CASCADE;' as drop_command
FROM pg_proc p 
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'lakemeter' AND p.proname LIKE 'sync_%';

-- 2. Copy and run the DROP commands from above output
--    (or run this if you own them):
DROP FUNCTION IF EXISTS lakemeter.sync_line_item_cloud() CASCADE;
DROP FUNCTION IF EXISTS lakemeter.sync_estimate_cloud_to_line_items() CASCADE;

-- 3. Then re-run this notebook
""")
    print("=" * 70)
    print("\n🛑 STOPPING: Cannot proceed with failed drops.")
    print("   Fix ownership issues above, then re-run this notebook.")
    raise Exception("Ownership errors detected. Fix in SQL Editor first.")
else:
    print("\n✅ All objects dropped successfully!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Create Application Tables

# COMMAND ----------

print("=" * 80)
print("📋 CREATING APPLICATION TABLES")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5.1 Users Table

# COMMAND ----------

create_users_sql = """
CREATE TABLE lakemeter.users (
    user_id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

execute_sql(create_users_sql, "Created users table")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5.2 Templates Table

# COMMAND ----------

create_templates_sql = """
CREATE TABLE lakemeter.templates (
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
"""

execute_sql(create_templates_sql, "Created templates table")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5.3 Estimates Table

# COMMAND ----------

create_estimates_sql = """
CREATE TABLE lakemeter.estimates (
    estimate_id UUID PRIMARY KEY,
    estimate_name VARCHAR(500),
    owner_user_id UUID REFERENCES lakemeter.users(user_id),
    customer_sfdc_id VARCHAR(18),
    customer_name VARCHAR(255),
    uco_opportunity_id VARCHAR(18),
    cloud VARCHAR(20),
    region VARCHAR(50),
    tier VARCHAR(20),
    status VARCHAR(20) DEFAULT 'draft',
    version INT DEFAULT 1,
    template_id UUID REFERENCES lakemeter.templates(template_id),
    original_prompt TEXT,
    is_deleted BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by UUID REFERENCES lakemeter.users(user_id)
);
"""

execute_sql(create_estimates_sql, "Created estimates table")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5.4 Line Items Table (with cloud column for validation)

# COMMAND ----------

create_line_items_sql = """
CREATE TABLE lakemeter.line_items (
    line_item_id UUID PRIMARY KEY,
    estimate_id UUID REFERENCES lakemeter.estimates(estimate_id),
    display_order INT,
    
    -- Workload identity
    workload_name VARCHAR(255),
    workload_type VARCHAR(50) NOT NULL,
    cloud VARCHAR(20),  -- Auto-synced from estimates.cloud (for instance type validation)
    
    -- Compute config
    serverless_enabled BOOLEAN DEFAULT false,
    serverless_mode VARCHAR(20),
    photon_enabled BOOLEAN DEFAULT false,
    driver_node_type VARCHAR(100),
    worker_node_type VARCHAR(100),
    num_workers INT,
    autoscale_enabled BOOLEAN DEFAULT false,
    autoscale_min_workers INT,
    autoscale_max_workers INT,
    
    -- DLT config
    dlt_edition VARCHAR(20),
    dlt_pipeline_mode VARCHAR(20),
    
    -- DBSQL config
    dbsql_warehouse_type VARCHAR(20),
    dbsql_warehouse_size VARCHAR(20),
    dbsql_num_clusters INT DEFAULT 1,
    
    -- Serverless products
    serverless_product VARCHAR(50),
    serverless_size VARCHAR(50),
    vector_search_mode VARCHAR(50),
    
    -- FMAPI config
    fmapi_provider VARCHAR(50),
    fmapi_model VARCHAR(100),
    fmapi_endpoint_type VARCHAR(20),
    fmapi_context_length VARCHAR(20),
    fmapi_input_tokens_per_month BIGINT,
    fmapi_output_tokens_per_month BIGINT,
    
    -- Lakebase config
    lakebase_cu INT,
    lakebase_storage_gb INT,
    lakebase_ha_enabled BOOLEAN DEFAULT false,
    lakebase_backup_retention_days INT DEFAULT 7,
    
    -- Usage/frequency
    runs_per_day INT,
    avg_runtime_minutes INT,
    days_per_month INT DEFAULT 30,
    
    -- VM pricing (separate for driver/worker)
    driver_pricing_tier VARCHAR(20),
    worker_pricing_tier VARCHAR(20),
    vm_pricing_tier VARCHAR(20) DEFAULT 'on_demand',
    vm_payment_option VARCHAR(20),
    spot_percentage INT,
    
    -- Extensible config
    workload_config JSON,
    
    -- Metadata
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

execute_sql(create_line_items_sql, "Created line_items table")

# COMMAND ----------

# Add indexes
execute_sql("CREATE INDEX idx_line_items_estimate ON lakemeter.line_items(estimate_id);", "Created index: idx_line_items_estimate")
execute_sql("CREATE INDEX idx_line_items_workload_type ON lakemeter.line_items(workload_type);", "Created index: idx_line_items_workload_type")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5.5 Reference Tables

# COMMAND ----------

# MAGIC %md
# MAGIC #### 5.5.1 ref_workload_types

# COMMAND ----------

create_ref_workload_types_sql = """
CREATE TABLE lakemeter.ref_workload_types (
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
);
"""

execute_sql(create_ref_workload_types_sql, "Created ref_workload_types table")

# COMMAND ----------

# Populate ref_workload_types with seed data
print("\n📝 Populating ref_workload_types...")

workload_type_inserts = [
    """INSERT INTO lakemeter.ref_workload_types VALUES
    ('JOBS', 'Jobs Compute', 'Scheduled batch jobs (Classic or Serverless)', 
     true, true, true, true, false, false, false, false, false, false, true, false, true, false,
     'JOBS_COMPUTE', 'JOBS_COMPUTE_(PHOTON)', 'JOBS_SERVERLESS_COMPUTE', 1)
    ON CONFLICT (workload_type) DO NOTHING""",
    
    """INSERT INTO lakemeter.ref_workload_types VALUES
    ('ALL_PURPOSE', 'All-Purpose Compute', 'Interactive clusters for notebooks (Classic or Serverless)', 
     true, true, false, true, false, false, false, false, false, false, true, true, false, false,
     'ALL_PURPOSE_COMPUTE', 'ALL_PURPOSE_COMPUTE_(PHOTON)', 'ALL_PURPOSE_SERVERLESS_COMPUTE', 2)
    ON CONFLICT (workload_type) DO NOTHING""",
    
    """INSERT INTO lakemeter.ref_workload_types VALUES
    ('DLT', 'Delta Live Tables', 'Declarative ETL pipelines (Classic or Serverless)',
     true, true, true, true, true, false, false, false, false, false, true, true, false, false,
     'DLT_CORE_COMPUTE', 'DLT_CORE_COMPUTE_(PHOTON)', 'DELTA_LIVE_TABLES_SERVERLESS', 3)
    ON CONFLICT (workload_type) DO NOTHING""",
    
    """INSERT INTO lakemeter.ref_workload_types VALUES
    ('DBSQL', 'Databricks SQL', 'SQL analytics warehouse (Classic/Pro/Serverless)',
     false, false, false, false, false, true, false, false, false, false, false, true, false, false,
     'SQL_COMPUTE', 'SQL_PRO_COMPUTE', 'SERVERLESS_SQL_COMPUTE', 4)
    ON CONFLICT (workload_type) DO NOTHING""",
    
    """INSERT INTO lakemeter.ref_workload_types VALUES
    ('VECTOR_SEARCH', 'Vector Search', 'Vector search endpoints for RAG',
     false, false, false, false, false, false, true, false, false, true, false, true, false, false,
     NULL, NULL, 'VECTOR_SEARCH_ENDPOINT', 5)
    ON CONFLICT (workload_type) DO NOTHING""",
    
    """INSERT INTO lakemeter.ref_workload_types VALUES
    ('MODEL_SERVING', 'Model Serving', 'Real-time model inference endpoints',
     false, false, false, false, false, false, true, false, false, false, false, true, false, false,
     NULL, NULL, 'SERVERLESS_REAL_TIME_INFERENCE', 6)
    ON CONFLICT (workload_type) DO NOTHING""",
    
    """INSERT INTO lakemeter.ref_workload_types VALUES
    ('FMAPI_DATABRICKS', 'Foundation Models (Databricks)', 'Databricks-hosted LLMs (Llama, DBRX)',
     false, false, false, false, false, false, false, true, false, false, false, false, false, true,
     NULL, NULL, 'SERVERLESS_REAL_TIME_INFERENCE', 7)
    ON CONFLICT (workload_type) DO NOTHING""",
    
    """INSERT INTO lakemeter.ref_workload_types VALUES
    ('FMAPI_PROPRIETARY', 'Foundation Models (Proprietary)', 'OpenAI, Anthropic, Google models served by Databricks',
     false, false, false, false, false, false, false, true, false, false, false, false, false, true,
     NULL, NULL, NULL, 8)
    ON CONFLICT (workload_type) DO NOTHING""",
    
    """INSERT INTO lakemeter.ref_workload_types VALUES
    ('LAKEBASE', 'Lakebase', 'Managed PostgreSQL database for operational workloads',
     false, false, false, false, false, false, false, false, true, false, false, true, true, false,
     NULL, NULL, 'DATABASE_SERVERLESS_COMPUTE', 9)
    ON CONFLICT (workload_type) DO NOTHING""",
]

for i, sql in enumerate(workload_type_inserts, 1):
    execute_sql(sql, f"  {i}/9 workload types")

print("✅ All workload types populated")

# COMMAND ----------

# MAGIC %md
# MAGIC #### 5.5.2 ref_cloud_tiers

# COMMAND ----------

create_ref_cloud_tiers_sql = """
CREATE TABLE lakemeter.ref_cloud_tiers (
    cloud VARCHAR(20) NOT NULL,
    tier VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    display_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    PRIMARY KEY (cloud, tier),
    CHECK (cloud IN ('AWS', 'AZURE', 'GCP')),
    CHECK (tier IN ('STANDARD', 'PREMIUM', 'ENTERPRISE', 'FREE_TRIAL', 'DEV_TEST'))
);
"""

execute_sql(create_ref_cloud_tiers_sql, "Created ref_cloud_tiers table")

# COMMAND ----------

# Populate ref_cloud_tiers with seed data
print("\n📝 Populating ref_cloud_tiers...")

cloud_tier_inserts = [
    # AWS: All 3 tiers
    """INSERT INTO lakemeter.ref_cloud_tiers VALUES
    ('AWS', 'STANDARD', 'Standard', 'Standard production workloads', 1, true)
    ON CONFLICT (cloud, tier) DO NOTHING""",
    
    """INSERT INTO lakemeter.ref_cloud_tiers VALUES
    ('AWS', 'PREMIUM', 'Premium', 'High-performance production workloads', 2, true)
    ON CONFLICT (cloud, tier) DO NOTHING""",
    
    """INSERT INTO lakemeter.ref_cloud_tiers VALUES
    ('AWS', 'ENTERPRISE', 'Enterprise', 'Enterprise-grade workloads with dedicated support', 3, true)
    ON CONFLICT (cloud, tier) DO NOTHING""",
    
    # Azure: Only STANDARD and PREMIUM (NO ENTERPRISE)
    """INSERT INTO lakemeter.ref_cloud_tiers VALUES
    ('AZURE', 'STANDARD', 'Standard', 'Standard production workloads', 1, true)
    ON CONFLICT (cloud, tier) DO NOTHING""",
    
    """INSERT INTO lakemeter.ref_cloud_tiers VALUES
    ('AZURE', 'PREMIUM', 'Premium', 'High-performance production workloads', 2, true)
    ON CONFLICT (cloud, tier) DO NOTHING""",
    
    # GCP: All 3 tiers (including ENTERPRISE)
    """INSERT INTO lakemeter.ref_cloud_tiers VALUES
    ('GCP', 'STANDARD', 'Standard', 'Standard production workloads', 1, true)
    ON CONFLICT (cloud, tier) DO NOTHING""",
    
    """INSERT INTO lakemeter.ref_cloud_tiers VALUES
    ('GCP', 'PREMIUM', 'Premium', 'High-performance production workloads', 2, true)
    ON CONFLICT (cloud, tier) DO NOTHING""",
    
    """INSERT INTO lakemeter.ref_cloud_tiers VALUES
    ('GCP', 'ENTERPRISE', 'Enterprise', 'Enterprise-grade workloads with dedicated support', 3, true)
    ON CONFLICT (cloud, tier) DO NOTHING""",
]

for i, sql in enumerate(cloud_tier_inserts, 1):
    cloud_tier = sql.split("'")[1::2][:2]  # Extract cloud and tier from SQL
    execute_sql(sql, f"  {i}/8 cloud/tier combinations")

print("✅ All cloud/tier combinations populated")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5.6 Other Application Tables

# COMMAND ----------

create_conversation_messages_sql = """
CREATE TABLE lakemeter.conversation_messages (
    message_id UUID PRIMARY KEY,
    estimate_id UUID REFERENCES lakemeter.estimates(estimate_id),
    message_role VARCHAR(20),
    message_content TEXT,
    message_sequence INT,
    message_type VARCHAR(50),
    tokens_used INT,
    model_used VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

execute_sql(create_conversation_messages_sql, "Created conversation_messages table")

# COMMAND ----------

create_decision_records_sql = """
CREATE TABLE lakemeter.decision_records (
    record_id UUID PRIMARY KEY,
    line_item_id UUID REFERENCES lakemeter.line_items(line_item_id),
    record_type VARCHAR(50),
    user_input TEXT,
    agent_response TEXT,
    assumptions JSON,
    calculations JSON,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

execute_sql(create_decision_records_sql, "Created decision_records table")

# COMMAND ----------

create_sharing_sql = """
CREATE TABLE lakemeter.sharing (
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
);
"""

execute_sql(create_sharing_sql, "Created sharing table")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Add Foreign Key Constraints

# COMMAND ----------

print("\n" + "=" * 80)
print("🔗 ADDING FOREIGN KEY CONSTRAINTS")
print("=" * 80)

# Cloud/Tier FK
execute_sql("""
ALTER TABLE lakemeter.estimates 
ADD CONSTRAINT fk_estimates_cloud_tier 
FOREIGN KEY (cloud, tier) REFERENCES lakemeter.ref_cloud_tiers(cloud, tier);
""", "FK: estimates(cloud, tier) → ref_cloud_tiers")

# Workload Type FK
execute_sql("""
ALTER TABLE lakemeter.line_items 
ADD CONSTRAINT fk_line_items_workload_type 
FOREIGN KEY (workload_type) REFERENCES lakemeter.ref_workload_types(workload_type);
""", "FK: line_items(workload_type) → ref_workload_types")

print("\n✅ All FK constraints added")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Add Triggers for Auto-Sync

# COMMAND ----------

print("\n" + "=" * 80)
print("🔄 ADDING TRIGGERS FOR AUTO-SYNC")
print("=" * 80)

# COMMAND ----------

# Trigger 1: Sync line_items.cloud from estimates.cloud
create_sync_function_sql = """
CREATE OR REPLACE FUNCTION lakemeter.sync_line_item_cloud()
RETURNS TRIGGER AS $$
BEGIN
    -- On INSERT: Copy cloud from parent estimate
    IF (TG_OP = 'INSERT') THEN
        SELECT cloud INTO NEW.cloud
        FROM lakemeter.estimates
        WHERE estimate_id = NEW.estimate_id;
    END IF;
    
    -- On UPDATE of estimate_id: Resync cloud
    IF (TG_OP = 'UPDATE' AND OLD.estimate_id IS DISTINCT FROM NEW.estimate_id) THEN
        SELECT cloud INTO NEW.cloud
        FROM lakemeter.estimates
        WHERE estimate_id = NEW.estimate_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

execute_sql(create_sync_function_sql, "Created function: sync_line_item_cloud()")

# COMMAND ----------

create_trigger_line_item_sql = """
CREATE TRIGGER trg_sync_line_item_cloud
BEFORE INSERT OR UPDATE ON lakemeter.line_items
FOR EACH ROW
EXECUTE FUNCTION lakemeter.sync_line_item_cloud();
"""

execute_sql(create_trigger_line_item_sql, "Created trigger: trg_sync_line_item_cloud")

# COMMAND ----------

# Trigger 2: Update line_items when estimates.cloud changes
create_estimate_sync_function_sql = """
CREATE OR REPLACE FUNCTION lakemeter.sync_estimate_cloud_to_line_items()
RETURNS TRIGGER AS $$
BEGIN
    -- On UPDATE of cloud: Update all child line_items
    IF (TG_OP = 'UPDATE' AND OLD.cloud IS DISTINCT FROM NEW.cloud) THEN
        UPDATE lakemeter.line_items
        SET cloud = NEW.cloud
        WHERE estimate_id = NEW.estimate_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

execute_sql(create_estimate_sync_function_sql, "Created function: sync_estimate_cloud_to_line_items()")

# COMMAND ----------

create_trigger_estimate_sql = """
CREATE TRIGGER trg_sync_estimate_cloud
AFTER UPDATE ON lakemeter.estimates
FOR EACH ROW
EXECUTE FUNCTION lakemeter.sync_estimate_cloud_to_line_items();
"""

execute_sql(create_trigger_estimate_sql, "Created trigger: trg_sync_estimate_cloud")

print("\n✅ All triggers created")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Add Business Logic Constraints

# COMMAND ----------

print("\n" + "=" * 80)
print("⚙️  ADDING BUSINESS LOGIC CONSTRAINTS")
print("=" * 80)

business_logic_constraints = [
    ("chk_serverless_requires_photon", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_serverless_requires_photon 
    CHECK (serverless_enabled = FALSE OR photon_enabled = TRUE)
    """, "Serverless requires Photon"),
    
    ("chk_num_workers_range", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_num_workers_range 
    CHECK (num_workers IS NULL OR (num_workers >= 0 AND num_workers <= 1000))
    """, "Workers: 0-1000"),
    
    ("chk_autoscale_min_max", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_autoscale_min_max 
    CHECK (autoscale_enabled = FALSE OR (autoscale_min_workers IS NOT NULL AND autoscale_max_workers IS NOT NULL AND autoscale_min_workers <= autoscale_max_workers))
    """, "Autoscale min ≤ max"),
    
    ("chk_dbsql_num_clusters_range", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_dbsql_num_clusters_range 
    CHECK (dbsql_num_clusters IS NULL OR (dbsql_num_clusters >= 1 AND dbsql_num_clusters <= 100))
    """, "DBSQL clusters: 1-100"),
    
    ("chk_days_per_month_range", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_days_per_month_range 
    CHECK (days_per_month IS NULL OR (days_per_month >= 1 AND days_per_month <= 31))
    """, "Days per month: 1-31"),
    
    ("chk_positive_usage", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_positive_usage 
    CHECK ((runs_per_day IS NULL OR runs_per_day > 0) AND (avg_runtime_minutes IS NULL OR avg_runtime_minutes > 0))
    """, "Usage values > 0"),
    
    ("chk_lakebase_storage_range", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_lakebase_storage_range 
    CHECK (lakebase_storage_gb IS NULL OR (lakebase_storage_gb >= 100 AND lakebase_storage_gb <= 10000))
    """, "Lakebase storage: 100-10000 GB"),
    
    ("chk_lakebase_backup_range", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_lakebase_backup_range 
    CHECK (lakebase_backup_retention_days >= 1 AND lakebase_backup_retention_days <= 35)
    """, "Lakebase backup: 1-35 days"),
]

for i, (name, sql, desc) in enumerate(business_logic_constraints, 1):
    execute_sql(sql, f"  {i}/8 {desc}")

print("\n✅ All business logic constraints added")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Add Enum Value Constraints

# COMMAND ----------

print("\n" + "=" * 80)
print("📋 ADDING ENUM VALUE CONSTRAINTS")
print("=" * 80)

enum_constraints = [
    # Estimates table
    ("chk_estimates_cloud", """
    ALTER TABLE lakemeter.estimates 
    ADD CONSTRAINT chk_estimates_cloud 
    CHECK (cloud IN ('AWS', 'AZURE', 'GCP'))
    """, "estimates.cloud"),
    
    ("chk_estimates_status", """
    ALTER TABLE lakemeter.estimates 
    ADD CONSTRAINT chk_estimates_status 
    CHECK (status IN ('draft', 'submitted', 'approved', 'rejected', 'archived'))
    """, "estimates.status"),
    
    # Line items table
    ("chk_serverless_mode", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_serverless_mode 
    CHECK (serverless_mode IS NULL OR serverless_mode IN ('standard', 'performance'))
    """, "line_items.serverless_mode"),
    
    ("chk_dlt_edition", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_dlt_edition 
    CHECK (dlt_edition IS NULL OR dlt_edition IN ('CORE', 'PRO', 'ADVANCED'))
    """, "line_items.dlt_edition"),
    
    ("chk_dlt_pipeline_mode", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_dlt_pipeline_mode 
    CHECK (dlt_pipeline_mode IS NULL OR dlt_pipeline_mode IN ('TRIGGERED', 'CONTINUOUS'))
    """, "line_items.dlt_pipeline_mode"),
    
    ("chk_dbsql_warehouse_type", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_dbsql_warehouse_type 
    CHECK (dbsql_warehouse_type IS NULL OR dbsql_warehouse_type IN ('CLASSIC', 'PRO', 'SERVERLESS'))
    """, "line_items.dbsql_warehouse_type"),
    
    ("chk_dbsql_warehouse_size", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_dbsql_warehouse_size 
    CHECK (dbsql_warehouse_size IS NULL OR dbsql_warehouse_size IN ('2X-Small', 'X-Small', 'Small', 'Medium', 'Large', 'X-Large', '2X-Large', '3X-Large', '4X-Large'))
    """, "line_items.dbsql_warehouse_size"),
    
    ("chk_vector_search_mode", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_vector_search_mode 
    CHECK (vector_search_mode IS NULL OR vector_search_mode IN ('standard', 'storage_optimized'))
    """, "line_items.vector_search_mode"),
    
    ("chk_driver_pricing_tier", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_driver_pricing_tier 
    CHECK (driver_pricing_tier IS NULL OR driver_pricing_tier IN ('on_demand', 'reserved_1y', 'reserved_3y'))
    """, "line_items.driver_pricing_tier"),
    
    ("chk_worker_pricing_tier", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_worker_pricing_tier 
    CHECK (worker_pricing_tier IS NULL OR worker_pricing_tier IN ('on_demand', 'spot', 'reserved_1y', 'reserved_3y'))
    """, "line_items.worker_pricing_tier"),
    
    ("chk_vm_pricing_tier", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_vm_pricing_tier 
    CHECK (vm_pricing_tier IS NULL OR vm_pricing_tier IN ('on_demand', 'spot', 'reserved_1y', 'reserved_3y'))
    """, "line_items.vm_pricing_tier"),
    
    ("chk_vm_payment_option", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_vm_payment_option 
    CHECK (vm_payment_option IS NULL OR vm_payment_option IN ('on_demand', 'spot', 'no_upfront', 'partial_upfront', 'all_upfront', 'NA'))
    """, "line_items.vm_payment_option"),
    
    ("chk_lakebase_cu", """
    ALTER TABLE lakemeter.line_items 
    ADD CONSTRAINT chk_lakebase_cu 
    CHECK (lakebase_cu IS NULL OR lakebase_cu IN (1, 2, 4, 8))
    """, "line_items.lakebase_cu"),
]

for i, (name, sql, desc) in enumerate(enum_constraints, 1):
    execute_sql(sql, f"  {i}/13 {desc}")

print("\n✅ All enum constraints added")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Verification

# COMMAND ----------

print("\n" + "=" * 80)
print("✅ VERIFICATION: Tables & Constraints")
print("=" * 80)

conn = get_connection()
cur = conn.cursor()

# Check tables
cur.execute("""
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'lakemeter' 
AND table_type = 'BASE TABLE'
ORDER BY table_name;
""")

tables = cur.fetchall()
print(f"\n📋 Tables created: {len(tables)}")
for table in tables:
    print(f"   ✅ {table[0]}")

# Check constraints
cur.execute("""
SELECT contype, COUNT(*) as count
FROM pg_constraint c
JOIN pg_class t ON c.conrelid = t.oid
JOIN pg_namespace n ON t.relnamespace = n.oid
WHERE n.nspname = 'lakemeter'
GROUP BY contype
ORDER BY contype;
""")

constraints = cur.fetchall()
print(f"\n🔒 Constraints added:")
constraint_types = {'p': 'PRIMARY KEY', 'f': 'FOREIGN KEY', 'u': 'UNIQUE', 'c': 'CHECK'}
for ctype, count in constraints:
    print(f"   {constraint_types.get(ctype, ctype)}: {count}")

# Check triggers
cur.execute("""
SELECT trigger_name 
FROM information_schema.triggers 
WHERE trigger_schema = 'lakemeter'
ORDER BY trigger_name;
""")

triggers = cur.fetchall()
print(f"\n🔄 Triggers created: {len(triggers)}")
for trigger in triggers:
    print(f"   ✅ {trigger[0]}")

cur.close()
conn.close()

print("\n" + "=" * 80)
print("🎉 APPLICATION TABLES CREATED SUCCESSFULLY!")
print("=" * 80)
print("\n📋 Next Steps:")
print("   1. Run Pricing_Sync notebooks to create sync_* tables")
print("   2. Run 04_Add_Sync_Constraints to add region + instance validation")
print("   3. Run 02_Create_Views to create cost calculation views")
print("=" * 80)

