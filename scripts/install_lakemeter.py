#!/usr/bin/env python3
"""
Lakemeter Zero-Click Installer

Provisions a complete Lakemeter environment on Databricks:
  1. Validates prerequisites (CLI, Python packages, CSV pricing data)
  2. Gathers configuration (instance name, database, app name, secrets scope)
  3. Provisions Lakebase instance (reuses if already exists)
  4. Creates database, schema, tables, and auth role
  5. Loads pricing data via serverless notebook
  6. Creates SKU discount mapping and cost calculation views
  7. Configures application (app.yaml, resources, SP access)
  8. Deploys application

Usage:
    python scripts/install_lakemeter.py --profile <cli-profile>

Requirements:
    - Databricks CLI configured with a workspace profile
    - Python 3.10+ with databricks-sdk, psycopg2-binary, requests
"""
import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
APP_DIR = SCRIPT_DIR.parent
BACKEND_DIR = APP_DIR / "backend"
PRICING_DIR = BACKEND_DIR / "static" / "pricing"

DEFAULT_DB_NAME = "lakemeter_pricing"
DEFAULT_SCHEMA = "lakemeter"
DEFAULT_CU_SIZE = "CU_1"  # Start at 1 CU, autoscale to 16 CU
DEFAULT_CLAUDE_ENDPOINT = "databricks-claude-opus-4-6"
DEFAULT_NODE_COUNT = 1

# Secrets required for API pricing mode
# Notebook 01 (DBU prices) needs workspace configs for 3 clouds
# Notebook 03 (AWS VM) needs AWS credentials
# Colors
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
NC = "\033[0m"


def log_step(step: int, total: int, msg: str):
    print(f"\n{YELLOW}[{step}/{total}]{NC} {BOLD}{msg}{NC}")


def log_ok(msg: str):
    print(f"  {GREEN}✓{NC} {msg}")


def log_warn(msg: str):
    print(f"  {YELLOW}⚠{NC} {msg}")


def log_err(msg: str):
    print(f"  {RED}✗{NC} {msg}")


def log_info(msg: str):
    print(f"  {BLUE}→{NC} {msg}")


def prompt_input(label: str, default: str = "") -> str:
    """Prompt user for input with a default value."""
    suffix = f" [{default}]" if default else ""
    value = input(f"  {CYAN}?{NC} {label}{suffix}: ").strip()
    return value if value else default


# ===================================================================
# Step 1: Validate Prerequisites
# ===================================================================
def validate_prerequisites(profile: str) -> dict:
    """Check CLI, SDK, dependencies, and workspace connectivity."""
    import shutil
    import subprocess

    # Check Python version
    if sys.version_info < (3, 10):
        log_err(f"Python 3.10+ required (found {sys.version})")
        sys.exit(1)
    log_ok(f"Python {sys.version_info.major}.{sys.version_info.minor}")

    # Check required Python packages
    missing_pkgs = []
    for pkg, import_name in [("databricks-sdk", "databricks.sdk"),
                              ("psycopg2-binary", "psycopg2"),
                              ("requests", "requests")]:
        try:
            __import__(import_name)
        except ImportError:
            missing_pkgs.append(pkg)
    if missing_pkgs:
        log_err(f"Missing Python packages: {', '.join(missing_pkgs)}")
        log_info(f"Install with: pip install {' '.join(missing_pkgs)}")
        sys.exit(1)
    log_ok("Required Python packages installed")

    # Check Node.js/npm (optional — only needed to rebuild frontend from source)
    if shutil.which("node") and shutil.which("npm"):
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        log_ok(f"Node.js {result.stdout.strip()} (frontend will be rebuilt from source)")
    else:
        log_info("Node.js not found — using pre-built frontend assets from repository")

    # Check Databricks CLI
    if not shutil.which("databricks"):
        log_err("Databricks CLI not found. Install: pip install databricks-cli")
        sys.exit(1)
    log_ok("Databricks CLI found")

    # Check pricing data directory (CSV files)
    if not PRICING_DIR.exists() or not any(PRICING_DIR.glob("*.csv")):
        log_err(f"Pricing CSV files not found at {PRICING_DIR}")
        log_info("Ensure you cloned the full repository including backend/static/pricing/")
        sys.exit(1)
    pricing_count = len(list(PRICING_DIR.glob("*.csv")))
    log_ok(f"Pricing data: {pricing_count} CSV files")

    # Connect to workspace
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.config import Config

    config = Config(profile=profile)
    w = WorkspaceClient(config=config)

    try:
        me = w.current_user.me()
        log_ok(f"Authenticated as {me.user_name}")
    except Exception as e:
        log_err(f"Cannot connect to workspace: {e}")
        sys.exit(1)

    return {"client": w, "host": config.host, "user": me.user_name}


# ===================================================================
# Step 2: Gather Configuration
# ===================================================================
def gather_config(ctx: dict, non_interactive: bool = False) -> dict:
    """Interactive prompts to configure the installation."""
    print(f"\n{BOLD}=== Lakemeter Installation Configuration ==={NC}\n")

    if non_interactive:
        log_info("Non-interactive mode — using all defaults")
        return {
            "instance_name": "lakemeter-customer",
            "db_name": DEFAULT_DB_NAME,
            "app_name": "lakemeter",
            "cu_size": DEFAULT_CU_SIZE,
            "secrets_scope": "lakemeter-secrets",
            "claude_endpoint": DEFAULT_CLAUDE_ENDPOINT,
        }

    instance_name = prompt_input("Lakebase instance name", "lakemeter-customer")
    db_name = prompt_input("Database name", DEFAULT_DB_NAME)
    app_name = prompt_input("Databricks App name", "lakemeter")
    secrets_scope = prompt_input("Secrets scope name", "lakemeter-secrets")

    # Fixed values — not user-configurable
    log_info("Lakebase: autoscaling 1–16 CU with scale-to-zero enabled")
    log_info(f"Claude AI endpoint: {DEFAULT_CLAUDE_ENDPOINT}")

    return {
        "instance_name": instance_name,
        "db_name": db_name,
        "app_name": app_name,
        "cu_size": DEFAULT_CU_SIZE,
        "secrets_scope": secrets_scope,
        "claude_endpoint": DEFAULT_CLAUDE_ENDPOINT,
    }


# ===================================================================
# Step 3: Provision Lakebase Instance
# ===================================================================
def provision_lakebase(ctx: dict, cfg: dict) -> dict:
    """Create a new Lakebase instance and wait for it to be AVAILABLE."""
    w = ctx["client"]
    name = cfg["instance_name"]

    # Check if instance already exists
    try:
        existing = w.database.get_database_instance(name)
        log_warn(f"Instance '{name}' already exists (state={existing.state})")

        # Ensure pg_native_login is enabled (password auth fallback)
        if not existing.effective_enable_pg_native_login:
            try:
                from databricks.sdk.service.database import DatabaseInstance
                w.database.update_database_instance(
                    name=name,
                    database_instance=DatabaseInstance(name=name, enable_pg_native_login=True),
                    update_mask="enable_pg_native_login",
                )
                log_ok("pg_native_login enabled on existing instance")
            except Exception as e:
                log_warn(f"Could not enable pg_native_login: {e}")

        return {
            "host": existing.read_write_dns,
            "uid": existing.uid,
            "name": existing.name,
        }
    except Exception:
        pass

    log_info(f"Creating Lakebase instance '{name}' (autoscaling 1–16 CU, scale-to-zero)...")
    from databricks.sdk.service.database import DatabaseInstance
    waiter = w.database.create_database_instance(
        database_instance=DatabaseInstance(
            name=name,
            capacity=cfg["cu_size"],
            stopped=False,
        ),
    )
    instance = waiter.response
    log_ok(f"Instance created: {instance.name} (uid={instance.uid})")

    # Enable auto-scaling with scale-to-zero via REST API
    try:
        import requests
        headers = w.config.authenticate()
        host = ctx["host"].rstrip("/")
        resp = requests.patch(
            f"{host}/api/2.0/database/instances/{name}",
            headers=headers,
            json={
                "name": name,
                "enable_serverless_compute": True,
                "min_capacity": "CU_1",
                "max_capacity": "CU_16",
                "scale_to_zero": True,
            },
        )
        if resp.status_code < 300:
            log_ok("Auto-scaling enabled (0.5–16 CU, scale-to-zero)")
        else:
            log_warn(f"Could not enable auto-scaling: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        log_warn(f"Could not enable auto-scaling: {e}")

    # Enable pg_native_login for password-based auth fallback
    # This ensures the app can connect even without SP OAuth credentials
    try:
        from databricks.sdk.service.database import DatabaseInstance
        w.database.update_database_instance(
            name=name,
            database_instance=DatabaseInstance(name=name, enable_pg_native_login=True),
            update_mask="enable_pg_native_login",
        )
        log_ok("pg_native_login enabled (password auth fallback)")
    except Exception as e:
        log_warn(f"Could not enable pg_native_login: {e}")

    # Wait for AVAILABLE
    log_info("Waiting for instance to become AVAILABLE...")
    for i in range(120):  # 10 minutes max
        inst = w.database.get_database_instance(name)
        state = str(inst.state)
        if "AVAILABLE" in state:
            log_ok(f"Instance is AVAILABLE at {inst.read_write_dns}")
            return {
                "host": inst.read_write_dns,
                "uid": inst.uid,
                "name": inst.name,
            }
        if "FAILED" in state or "DELETED" in state:
            log_err(f"Instance entered {state} state")
            sys.exit(1)
        if i % 10 == 0:
            log_info(f"  State: {state} (waiting...)")
        time.sleep(5)

    log_err("Timeout waiting for instance to become AVAILABLE")
    sys.exit(1)


# ===================================================================
# Step 4: Create Database, Schema, Tables
# ===================================================================
def get_owner_connection(ctx: dict, instance_info: dict, cfg: dict):
    """Get a psycopg2 connection as the instance owner."""
    import psycopg2

    w = ctx["client"]
    cred = w.database.generate_database_credential(
        request_id=str(uuid.uuid4()),
        instance_names=[instance_info["name"]],
    )
    return psycopg2.connect(
        host=instance_info["host"],
        port=5432,
        database=cfg["db_name"],
        user=ctx["user"],
        password=cred.token,
        sslmode="require",
    )


def create_database_and_schema(ctx: dict, instance_info: dict, cfg: dict):
    """Create the database and lakemeter schema."""
    import psycopg2

    w = ctx["client"]
    cred = w.database.generate_database_credential(
        request_id=str(uuid.uuid4()),
        instance_names=[instance_info["name"]],
    )

    # Connect to default 'postgres' DB first to create our database
    conn = psycopg2.connect(
        host=instance_info["host"],
        port=5432,
        database="postgres",
        user=ctx["user"],
        password=cred.token,
        sslmode="require",
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Check if database exists
    cur.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s", (cfg["db_name"],)
    )
    if not cur.fetchone():
        log_info(f"Creating database '{cfg['db_name']}'...")
        cur.execute(f'CREATE DATABASE {cfg["db_name"]}')
        log_ok(f"Database '{cfg['db_name']}' created")
    else:
        log_ok(f"Database '{cfg['db_name']}' already exists")

    cur.close()
    conn.close()

    # Now connect to the target database and create schema
    conn = get_owner_connection(ctx, instance_info, cfg)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {DEFAULT_SCHEMA}")
    log_ok(f"Schema '{DEFAULT_SCHEMA}' ready")

    cur.close()
    conn.close()


def create_password_auth_role(ctx: dict, instance_info: dict, cfg: dict):
    """Create a password-authenticated role as fallback when SP OAuth isn't configured.

    This prevents the app from failing to connect after deployment when the
    app's service principal doesn't have Lakebase access or SP credentials
    aren't stored in the secrets scope.
    """
    import secrets as py_secrets

    w = ctx["client"]
    scope = cfg["secrets_scope"]
    role_name = "lakemeter_sync_role"

    # Ensure secrets scope exists (needed for storing DB credentials)
    try:
        w.secrets.list_secrets(scope=scope)
    except Exception:
        try:
            w.secrets.create_scope(scope=scope)
            log_ok(f"Secrets scope '{scope}' created")
        except Exception as e:
            if "already exists" not in str(e).lower():
                log_err(f"Cannot create secrets scope: {e}")
                sys.exit(1)

    conn = get_owner_connection(ctx, instance_info, cfg)
    conn.autocommit = True
    cur = conn.cursor()

    # Check if role exists
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role_name,))
    exists = cur.fetchone()

    # Generate a secure password
    password = py_secrets.token_urlsafe(32)

    if not exists:
        log_info(f"Creating password-auth role '{role_name}'...")
        cur.execute(f"CREATE ROLE {role_name} LOGIN PASSWORD %s", (password,))
        log_ok(f"Role '{role_name}' created")
    else:
        # Reset password to ensure it matches what we store in secrets
        cur.execute(f"ALTER ROLE {role_name} PASSWORD %s", (password,))
        log_ok(f"Role '{role_name}' password reset")

    # Grant permissions
    cur.execute(f"GRANT CONNECT ON DATABASE {cfg['db_name']} TO {role_name}")
    cur.execute(f"GRANT USAGE ON SCHEMA {DEFAULT_SCHEMA} TO {role_name}")
    cur.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {DEFAULT_SCHEMA} TO {role_name}")
    cur.execute(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {DEFAULT_SCHEMA} TO {role_name}")
    cur.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA {DEFAULT_SCHEMA} "
        f"GRANT ALL PRIVILEGES ON TABLES TO {role_name}"
    )
    log_ok(f"Permissions granted to '{role_name}'")

    cur.close()
    conn.close()

    # Store credentials in secrets scope (used by password auth fallback in database.py)
    w.secrets.put_secret(scope=scope, key="lakebase-user", string_value=role_name)
    w.secrets.put_secret(scope=scope, key="lakebase-password", string_value=password)
    w.secrets.put_secret(scope=scope, key="lakebase-host", string_value=instance_info["host"])
    w.secrets.put_secret(scope=scope, key="lakebase-database", string_value=cfg["db_name"])
    log_ok("Password-auth credentials stored in secrets scope")


def run_setup_sql(ctx: dict, instance_info: dict, cfg: dict):
    """Execute the table creation, views, constraints, and seed data SQL."""
    conn = get_owner_connection(ctx, instance_info, cfg)
    conn.autocommit = True
    cur = conn.cursor()

    # --- Application Tables (inline SQL — self-contained, no notebook parsing) ---
    _create_tables_inline(cur)
    log_ok("Application tables created (9 tables + seed data)")

    # --- Discount config column ---
    cur.execute("""
        ALTER TABLE lakemeter.estimates
        ADD COLUMN IF NOT EXISTS discount_config JSONB
    """)
    log_ok("discount_config column added")

    # --- Migrate line_items to current schema ---
    # Add any columns that may be missing from older installations
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
            cur.execute(f"ALTER TABLE lakemeter.line_items ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
        except Exception:
            pass  # Column may already exist with different type
    log_ok("line_items schema migration complete")

    # --- Lakebase CU sizes ---
    cur.execute("ALTER TABLE lakemeter.line_items DROP CONSTRAINT IF EXISTS chk_lakebase_cu")
    cur.execute("ALTER TABLE lakemeter.line_items ALTER COLUMN lakebase_cu TYPE NUMERIC(5,1)")
    valid_cus = ",".join(str(v) for v in [0.5] + list(range(1, 113)))
    cur.execute(f"""
        ALTER TABLE lakemeter.line_items
        ADD CONSTRAINT chk_lakebase_cu CHECK (lakebase_cu IN ({valid_cus}))
    """)
    log_ok("Lakebase CU size constraint updated")

    # --- Case normalization triggers ---
    # DB-level triggers that auto-normalize enum fields to canonical case
    try:
        cur.execute("""
            CREATE OR REPLACE FUNCTION lakemeter.normalize_estimates_case()
            RETURNS TRIGGER AS $$
            BEGIN
                IF NEW.cloud IS NOT NULL THEN NEW.cloud = UPPER(NEW.cloud); END IF;
                IF NEW.tier IS NOT NULL THEN NEW.tier = UPPER(NEW.tier); END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        cur.execute("""
            CREATE OR REPLACE FUNCTION lakemeter.normalize_line_items_case()
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
        cur.execute("DROP TRIGGER IF EXISTS trg_normalize_estimates_case ON lakemeter.estimates")
        cur.execute("""
            CREATE TRIGGER trg_normalize_estimates_case
            BEFORE INSERT OR UPDATE ON lakemeter.estimates
            FOR EACH ROW EXECUTE FUNCTION lakemeter.normalize_estimates_case()
        """)
        cur.execute("DROP TRIGGER IF EXISTS trg_normalize_line_items_case ON lakemeter.line_items")
        cur.execute("""
            CREATE TRIGGER trg_normalize_line_items_case
            BEFORE INSERT OR UPDATE ON lakemeter.line_items
            FOR EACH ROW EXECUTE FUNCTION lakemeter.normalize_line_items_case()
        """)
        log_ok("Case normalization triggers created")
    except Exception as e:
        log_warn(f"Case normalization triggers: {str(e)[:100]}")

    # --- Migrate sync_ref_instance_dbu_rates to include is_active and source ---
    for col_name, col_type in [("is_active", "BOOLEAN DEFAULT TRUE"), ("source", "TEXT")]:
        try:
            cur.execute(f"ALTER TABLE lakemeter.sync_ref_instance_dbu_rates ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
        except Exception:
            pass
    log_ok("sync_ref_instance_dbu_rates schema migration complete")

    cur.close()
    conn.close()



def _create_tables_inline(cur):
    """Create all application tables with correct UUID types matching production schema."""
    # Execute each statement individually so one failure doesn't cascade
    table_stmts = [
        # Schema
        "CREATE SCHEMA IF NOT EXISTS lakemeter",

        # Users
        """CREATE TABLE IF NOT EXISTS lakemeter.users (
            user_id UUID PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            full_name VARCHAR(255),
            role VARCHAR(50),
            is_active BOOLEAN DEFAULT true,
            last_login_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",

        # Templates
        """CREATE TABLE IF NOT EXISTS lakemeter.templates (
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

        # Reference: cloud tiers
        """CREATE TABLE IF NOT EXISTS lakemeter.ref_cloud_tiers (
            cloud VARCHAR(20) NOT NULL,
            tier VARCHAR(50) NOT NULL,
            display_name VARCHAR(100),
            description TEXT,
            display_order INT DEFAULT 0,
            is_active BOOLEAN DEFAULT true,
            PRIMARY KEY (cloud, tier)
        )""",

        # Reference: workload types
        """CREATE TABLE IF NOT EXISTS lakemeter.ref_workload_types (
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

        # Estimates
        """CREATE TABLE IF NOT EXISTS lakemeter.estimates (
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
        )""",

        # Line items
        """CREATE TABLE IF NOT EXISTS lakemeter.line_items (
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

        # Conversation messages
        """CREATE TABLE IF NOT EXISTS lakemeter.conversation_messages (
            message_id UUID PRIMARY KEY,
            estimate_id UUID REFERENCES lakemeter.estimates(estimate_id),
            message_role VARCHAR(20),
            message_content TEXT,
            message_sequence INT,
            message_type VARCHAR(50),
            tokens_used INT,
            model_used VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",

        # Decision records
        """CREATE TABLE IF NOT EXISTS lakemeter.decision_records (
            record_id UUID PRIMARY KEY,
            line_item_id UUID REFERENCES lakemeter.line_items(line_item_id),
            record_type VARCHAR(50),
            user_input TEXT,
            agent_response TEXT,
            assumptions JSON,
            calculations JSON,
            reasoning TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",

        # Sharing
        """CREATE TABLE IF NOT EXISTS lakemeter.sharing (
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
        )""",

        # Indexes
        "CREATE INDEX IF NOT EXISTS idx_line_items_estimate ON lakemeter.line_items(estimate_id)",
        "CREATE INDEX IF NOT EXISTS idx_line_items_workload_type ON lakemeter.line_items(workload_type)",
    ]

    for stmt in table_stmts:
        try:
            cur.execute(stmt)
        except Exception as e:
            if "already exists" not in str(e):
                log_warn(f"Table DDL: {str(e)[:120]}")

    # Seed workload types (matching production notebook)
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
            """INSERT INTO lakemeter.ref_workload_types
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

    # Seed cloud tiers (matching production notebook)
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
            """INSERT INTO lakemeter.ref_cloud_tiers
               (cloud, tier, display_name, description, display_order, is_active)
               VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (cloud, tier) DO NOTHING""",
            ct,
        )


# ===================================================================
# Step 5: Load Pricing Data
# ===================================================================
def load_pricing_data(ctx: dict, instance_info: dict, cfg: dict):
    """Upload CSV pricing data + loader notebook to workspace, run on serverless."""
    import base64
    from databricks.sdk.service.workspace import ImportFormat, Language

    w = ctx["client"]
    user = ctx["user"]
    secrets_scope = cfg["secrets_scope"]

    # Ensure sync tables exist (DDL still runs locally — small operation)
    conn = get_owner_connection(ctx, instance_info, cfg)
    conn.autocommit = True
    cur = conn.cursor()
    _create_sync_tables(cur)
    cur.close()
    conn.close()

    # 1. Upload CSV files to workspace
    pricing_workspace_dir = f"/Workspace/Users/{user}/lakemeter/pricing_data"
    try:
        w.workspace.mkdirs(pricing_workspace_dir)
    except Exception:
        pass  # directory may already exist

    csv_files = sorted(PRICING_DIR.glob("*.csv"))
    if not csv_files:
        raise RuntimeError(
            f"No CSV pricing files found in {PRICING_DIR}. "
            "Run 'python scripts/convert_pricing_to_csv.py' first."
        )

    MAX_IMPORT_SIZE = 9 * 1024 * 1024  # 9MB (workspace limit is 10MB)
    for csv_file in csv_files:
        file_bytes = csv_file.read_bytes()
        if len(file_bytes) <= MAX_IMPORT_SIZE:
            w.workspace.import_(
                path=f"{pricing_workspace_dir}/{csv_file.name}",
                content=base64.b64encode(file_bytes).decode("ascii"),
                format=ImportFormat.AUTO,
                overwrite=True,
            )
            log_info(f"  Uploaded {csv_file.name}")
        else:
            # Split large CSV into parts that fit under the import limit
            text = file_bytes.decode("utf-8")
            lines = text.split("\n")
            header = lines[0]
            data_lines = [l for l in lines[1:] if l.strip()]
            part_num = 0
            chunk = [header]
            chunk_size = len(header.encode("utf-8"))
            for line in data_lines:
                line_size = len(line.encode("utf-8")) + 1  # +1 for newline
                if chunk_size + line_size > MAX_IMPORT_SIZE and len(chunk) > 1:
                    part_num += 1
                    part_content = "\n".join(chunk) + "\n"
                    stem = csv_file.stem
                    part_name = f"{stem}_part{part_num}.csv"
                    w.workspace.import_(
                        path=f"{pricing_workspace_dir}/{part_name}",
                        content=base64.b64encode(part_content.encode("utf-8")).decode("ascii"),
                        format=ImportFormat.AUTO,
                        overwrite=True,
                    )
                    log_info(f"  Uploaded {part_name} ({len(chunk)-1} rows)")
                    chunk = [header]
                    chunk_size = len(header.encode("utf-8"))
                chunk.append(line)
                chunk_size += line_size
            if len(chunk) > 1:
                part_num += 1
                part_content = "\n".join(chunk) + "\n"
                stem = csv_file.stem
                part_name = f"{stem}_part{part_num}.csv"
                w.workspace.import_(
                    path=f"{pricing_workspace_dir}/{part_name}",
                    content=base64.b64encode(part_content.encode("utf-8")).decode("ascii"),
                    format=ImportFormat.AUTO,
                    overwrite=True,
                )
                log_info(f"  Uploaded {part_name} ({len(chunk)-1} rows)")
            log_info(f"  Uploaded {csv_file.name} in {part_num} parts")

    log_ok(f"Uploaded {len(csv_files)} CSV files to {pricing_workspace_dir}")

    # 2. Upload loader notebook (patch SECRET_SCOPE and PRICING_DIR)
    nb_path = SCRIPT_DIR / "load_pricing_data.py"
    nb_content = nb_path.read_text(encoding="utf-8")

    if secrets_scope != "lakemeter-secrets":
        nb_content = nb_content.replace(
            'SECRET_SCOPE = "lakemeter-secrets"',
            f'SECRET_SCOPE = "{secrets_scope}"',
        )
    nb_content = nb_content.replace(
        'PRICING_DIR = "/Workspace/Users/placeholder/lakemeter/pricing_data"',
        f'PRICING_DIR = "{pricing_workspace_dir}"',
    )

    notebook_workspace_path = f"{pricing_workspace_dir}/load_pricing_data"
    w.workspace.import_(
        path=notebook_workspace_path,
        content=base64.b64encode(nb_content.encode("utf-8")).decode("ascii"),
        format=ImportFormat.SOURCE,
        language=Language.PYTHON,
        overwrite=True,
    )
    log_ok(f"Uploaded loader notebook to {notebook_workspace_path}")

    # 3. Run as one-shot serverless job
    from databricks.sdk.service.jobs import NotebookTask, SubmitTask

    log_info("Running pricing data load on serverless...")
    run = w.jobs.submit(
        run_name="lakemeter-load-pricing-data",
        tasks=[SubmitTask(
            task_key="load_pricing",
            notebook_task=NotebookTask(
                notebook_path=notebook_workspace_path,
            ),
        )],
    )

    # 4. Poll until complete
    run_id = run.response.run_id if hasattr(run, 'response') else run.run_id
    while True:
        status = w.jobs.get_run(run_id)
        state = status.state.life_cycle_state.value
        if state in ("TERMINATED", "SKIPPED", "INTERNAL_ERROR"):
            break
        log_info(f"  Job state: {state}...")
        time.sleep(5)

    result_state = status.state.result_state
    if result_state is None or result_state.value != "SUCCESS":
        error_msg = getattr(status.state, 'state_message', 'Unknown error')
        raise RuntimeError(
            f"Pricing data load failed: {result_state} — {error_msg}\n"
            f"Check run at: {w.config.host}/#job/{run_id}"
        )

    log_ok("Pricing data loaded via serverless notebook")


def _create_sync_tables(cur):
    """Create sync_* tables for pricing data."""
    cur.execute("""
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
    """)


# ===================================================================
# Step 6: SKU Discount Mapping & Cross-Service Eligibility
# ===================================================================
def create_sku_discount_mapping(ctx: dict, instance_info: dict, cfg: dict):
    """Create the sku_discount_mapping table with seed data."""
    conn = get_owner_connection(ctx, instance_info, cfg)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS lakemeter.sku_discount_mapping (
            sku TEXT PRIMARY KEY,
            sku_display_name TEXT,
            discount_category TEXT NOT NULL
                CHECK (discount_category IN ('dbu', 'storage', 'support', 'network', 'excluded')),
            cross_service_eligible BOOLEAN NOT NULL DEFAULT TRUE,
            notes TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_sku_discount_category
            ON lakemeter.sku_discount_mapping(discount_category);
    """)

    # We'll read the existing mapping from the database if already populated,
    # otherwise the 04_Create_SKU_Discount_Mapping notebook handles this.
    cur.execute("SELECT COUNT(*) FROM lakemeter.sku_discount_mapping")
    if cur.fetchone()[0] == 0:
        log_info("Populating SKU discount mapping from DBU rates...")
        # Auto-populate from sync_pricing_dbu_rates
        cur.execute("""
            INSERT INTO lakemeter.sku_discount_mapping (sku, sku_display_name, discount_category)
            SELECT DISTINCT sku_name, sku_name, 'dbu'
            FROM lakemeter.sync_pricing_dbu_rates
            WHERE sku_name IS NOT NULL AND sku_name != ''
            ON CONFLICT DO NOTHING
        """)
        log_ok("SKU discount mapping populated")
    else:
        log_ok("SKU discount mapping already populated")

    # Mark non-cross-service-eligible SKUs
    non_eligible = [
        "Model Serving%", "Model Training%", "%Proprietary%",
    ]
    for pattern in non_eligible:
        cur.execute(
            "UPDATE lakemeter.sku_discount_mapping SET cross_service_eligible = FALSE WHERE sku LIKE %s",
            (pattern,)
        )

    cur.close()
    conn.close()


# ===================================================================
# Step 7: Configure Service Principal Access
# ===================================================================
def configure_sp_access(ctx: dict, instance_info: dict, cfg: dict):
    """Create the SP role on Lakebase with proper identity_type and permissions."""
    import requests

    w = ctx["client"]
    host = ctx["host"]

    # Ensure secrets scope exists (auto-create if missing)
    scope = cfg["secrets_scope"]
    try:
        w.secrets.list_secrets(scope=scope)
        log_ok(f"Secrets scope '{scope}' exists")
    except Exception:
        log_info(f"Secrets scope '{scope}' not found — creating...")
        try:
            w.secrets.create_scope(scope=scope)
            log_ok(f"Secrets scope '{scope}' created")
        except Exception as e2:
            if "already exists" not in str(e2).lower():
                log_err(f"Cannot create secrets scope: {e2}")
                sys.exit(1)

    # Get SP client ID from secrets (prompt if missing)
    try:
        sp_client_id = w.dbutils.secrets.get(
            scope=scope, key=cfg["sp_client_id_key"]
        )
    except Exception:
        log_warn(f"SP client ID not found in {scope}:{cfg['sp_client_id_key']}")
        sp_client_id = prompt_input("Enter Service Principal Client ID", "").strip()
        if not sp_client_id:
            log_err("SP client ID is required")
            sys.exit(1)
        w.secrets.put_secret(scope=scope, key=cfg["sp_client_id_key"],
                             string_value=sp_client_id)
        log_ok(f"SP client ID stored in {scope}:{cfg['sp_client_id_key']}")

        # Also prompt for SP secret since it's likely missing too
        sp_secret_val = prompt_input("Enter Service Principal Secret", "").strip()
        if sp_secret_val:
            w.secrets.put_secret(scope=scope, key=cfg["sp_secret_key"],
                                 string_value=sp_secret_val)
            log_ok(f"SP secret stored in {scope}:{cfg['sp_secret_key']}")

    log_info(f"Service Principal ID: {sp_client_id}")

    # Step A: Grant CAN_MANAGE at workspace level
    headers = w.config.authenticate()
    url = f"{host}/api/2.0/permissions/database-instances/{instance_info['name']}"
    payload = {
        "access_control_list": [
            {
                "service_principal_name": sp_client_id,
                "all_permissions": [{"permission_level": "CAN_MANAGE"}],
            }
        ]
    }
    resp = requests.patch(url, headers=headers, json=payload)
    if resp.status_code < 300:
        log_ok("Workspace CAN_MANAGE permission granted")
    else:
        log_warn(f"Permission grant returned {resp.status_code}: {resp.text[:200]}")

    # Step B: Create the SP role via the Lakebase Roles API
    # CRITICAL: Must use identity_type=SERVICE_PRINCIPAL, not CREATE ROLE in PG
    roles_url = f"{host}/api/2.0/database/instances/{instance_info['name']}/roles"

    # Check if role already exists with correct identity_type
    resp = requests.get(roles_url, headers=headers)
    if resp.status_code == 200:
        existing_roles = resp.json().get("database_instance_roles", [])
        sp_role = next((r for r in existing_roles if r["name"] == sp_client_id), None)

        if sp_role and sp_role.get("identity_type") == "SERVICE_PRINCIPAL":
            log_ok("SP role already exists with correct identity_type")
        else:
            if sp_role:
                # Delete the incorrect role first (PG_ONLY → SERVICE_PRINCIPAL)
                del_url = f"{roles_url}/{sp_client_id}"
                requests.delete(del_url, headers=headers)
                log_info("Removed existing PG_ONLY role")

            # Create with correct identity_type
            create_payload = {
                "name": sp_client_id,
                "identity_type": "SERVICE_PRINCIPAL",
                "membership_role": "DATABRICKS_SUPERUSER",
            }
            resp = requests.post(roles_url, headers=headers, json=create_payload)
            if resp.status_code == 200:
                log_ok("SP role created (identity_type=SERVICE_PRINCIPAL)")
            else:
                log_err(f"Failed to create SP role: {resp.status_code} {resp.text[:200]}")
                sys.exit(1)

    # Step C: Grant schema-level permissions via SQL
    conn = get_owner_connection(ctx, instance_info, cfg)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute(f'GRANT CONNECT ON DATABASE {cfg["db_name"]} TO "{sp_client_id}"')
    log_ok("Database-level permissions granted")

    cur.execute(f'GRANT USAGE ON SCHEMA {DEFAULT_SCHEMA} TO "{sp_client_id}"')
    cur.execute(
        f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {DEFAULT_SCHEMA} TO "{sp_client_id}"'
    )
    cur.execute(
        f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {DEFAULT_SCHEMA} TO "{sp_client_id}"'
    )
    cur.execute(
        f'GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {DEFAULT_SCHEMA} TO "{sp_client_id}"'
    )
    cur.execute(
        f'ALTER DEFAULT PRIVILEGES IN SCHEMA {DEFAULT_SCHEMA} '
        f'GRANT ALL PRIVILEGES ON TABLES TO "{sp_client_id}"'
    )
    cur.execute(
        f'ALTER DEFAULT PRIVILEGES IN SCHEMA {DEFAULT_SCHEMA} '
        f'GRANT EXECUTE ON FUNCTIONS TO "{sp_client_id}"'
    )
    log_ok("Schema-level permissions granted (tables, sequences, functions)")

    # Step D: Verify SP can connect
    log_info("Verifying SP connectivity...")
    try:
        sp_secret = w.dbutils.secrets.get(
            scope=cfg["secrets_scope"], key=cfg["sp_secret_key"]
        )
        from databricks.sdk.core import Config as SdkConfig

        sp_config = SdkConfig(
            host=host,
            client_id=sp_client_id,
            client_secret=sp_secret,
            auth_type="oauth-m2m",
        )
        sp_client = WorkspaceClient(config=sp_config)
        sp_cred = sp_client.database.generate_database_credential(
            request_id=str(uuid.uuid4()),
            instance_names=[instance_info["name"]],
        )

        import psycopg2

        sp_conn = psycopg2.connect(
            host=instance_info["host"],
            port=5432,
            database=cfg["db_name"],
            user=sp_client_id,
            password=sp_cred.token,
            sslmode="require",
        )
        sp_cur = sp_conn.cursor()
        sp_cur.execute("SELECT 1")
        assert sp_cur.fetchone()[0] == 1
        sp_cur.close()
        sp_conn.close()
        log_ok("SP connectivity verified — OAuth M2M auth works")
    except Exception as e:
        log_err(f"SP verification failed: {e}")
        log_warn("The app may not be able to connect. Check SP credentials.")

    cur.close()
    conn.close()

    from databricks.sdk import WorkspaceClient


# ===================================================================
# Step 8: Create Views
# ===================================================================
def create_views(ctx: dict, instance_info: dict, cfg: dict):
    """Create cost calculation views."""
    conn = get_owner_connection(ctx, instance_info, cfg)
    conn.autocommit = True
    cur = conn.cursor()

    # Views are optional — the API layer calculates costs on the fly.
    # If you need the summary views (v_line_items_with_costs, v_estimates_with_totals),
    # run etl/lakebase_setup/setup/02_Create_Views.py in the Databricks workspace.
    log_ok("Views step skipped (API calculates costs directly)")

    cur.close()
    conn.close()


# ===================================================================
# Step 9: Generate app.yaml with correct resource references
# ===================================================================
def generate_app_config(ctx: dict, instance_info: dict, cfg: dict):
    """Write out the app.yaml with valueFrom references."""
    app_yaml = APP_DIR / "app.yaml"

    content = f"""# Databricks App Configuration — generated by install_lakemeter.py
# Instance: {instance_info['name']} | Generated: {datetime.now().isoformat()[:19]}

command:
  - "/bin/bash"
  - "-c"
  - |
    # Start FastAPI backend (frontend is pre-built into backend/static/)
    cd backend && ../.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port ${{DATABRICKS_APP_PORT:-8000}}

env:
  # App environment
  - name: "ENVIRONMENT"
    value: "production"
  - name: "CORS_ORIGINS"
    value: ""

  # Note: DATABRICKS_HOST, DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET are
  # auto-injected by the Databricks Apps platform. The app's built-in SP
  # handles all authentication (Lakebase OAuth, model serving, etc.).

  # Lakebase database configuration
  - name: "LAKEBASE_INSTANCE_NAME"
    valueFrom: "{cfg['app_name']}-lakebase-instance"
  - name: "DB_HOST"
    valueFrom: "{cfg['app_name']}-db-host"
  - name: "DB_USER"
    valueFrom: "{cfg['app_name']}-db-user"
  - name: "DB_NAME"
    valueFrom: "{cfg['app_name']}-db-name"
  - name: "DB_PORT"
    value: "5432"
  - name: "DB_SSLMODE"
    value: "require"

  # AI Assistant (Claude) model serving endpoint
  - name: "CLAUDE_MODEL_ENDPOINT"
    valueFrom: "{cfg['app_name']}-claude-endpoint"
"""
    app_yaml.write_text(content)
    log_ok(f"app.yaml written to {app_yaml}")


# ===================================================================
# Step 9b: Configure Databricks App Resources
# ===================================================================
def configure_app_resources(ctx: dict, instance_info: dict, cfg: dict):
    """Create workspace secrets and configure app resources for valueFrom references.

    Databricks Apps app.yaml uses 'valueFrom' to read env vars from app-level
    resources. Each resource maps to a workspace secret (scope:key). This step
    ensures the secrets exist and the app resources are configured so the app
    can read its configuration at startup.
    """
    w = ctx["client"]
    scope = cfg["secrets_scope"]
    app_name = cfg["app_name"]

    # 1. Create workspace secrets for config values (idempotent — overwrites if exists)
    config_secrets = {
        "lakebase-instance-name": instance_info["name"],
    }
    # lakebase-host, lakebase-user, lakebase-database should already exist from earlier steps
    for key, value in config_secrets.items():
        try:
            w.secrets.put_secret(scope=scope, key=key, string_value=value)
            log_info(f"Secret {scope}:{key} set")
        except Exception as e:
            log_warn(f"Could not set secret {key}: {e}")

    # 2. Define resource mappings: valueFrom name -> scope:key
    resource_map = {
        f"{app_name}-lakebase-instance": ("lakebase-instance-name", "Lakebase instance name"),
        f"{app_name}-db-host": ("lakebase-host", "Database host"),
        f"{app_name}-db-user": ("lakebase-user", "Database user"),
        f"{app_name}-db-name": ("lakebase-database", "Database name"),
    }

    # 3. Create app if it doesn't exist
    import requests
    user = ctx["user"]
    try:
        w.apps.get(app_name)
    except Exception:
        log_info(f"Creating Databricks App '{app_name}'...")
        try:
            from databricks.sdk.service.apps import App
            app_obj = App(
                name=app_name,
                description="Lakemeter — Databricks cost estimation tool",
                default_source_code_path=f"/Workspace/Users/{user}/apps/{app_name}",
            )
            w.apps.create_and_wait(app_obj)
            log_ok(f"App '{app_name}' created")
        except Exception as e:
            log_warn(f"Could not create app: {str(e)[:200]}")
            log_info("Create the app manually via Databricks UI, then re-run the installer")

    # 4. Configure app resources via REST API
    resources = []
    for name, (secret_key, desc) in resource_map.items():
        resources.append({
            "name": name,
            "description": desc,
            "secret": {"scope": scope, "key": secret_key, "permission": "READ"},
        })

    # 4. Add serving endpoint resource for AI Assistant (Claude)
    claude_endpoint = cfg.get("claude_endpoint", "databricks-claude-opus-4-6")
    resources.append({
        "name": f"{app_name}-claude-endpoint",
        "description": "Claude model endpoint for AI Assistant",
        "serving_endpoint": {"name": claude_endpoint, "permission": "CAN_QUERY"},
    })

    host = ctx["host"].rstrip("/")
    headers = w.config.authenticate()
    resp = requests.patch(
        f"{host}/api/2.0/apps/{app_name}",
        headers=headers,
        json={"resources": resources},
    )
    if resp.status_code == 200:
        log_ok(f"App resources configured ({len(resources)} resources)")
    else:
        log_warn(f"Failed to configure app resources: {resp.status_code} {resp.text[:200]}")
        log_info("You may need to set resources manually in the Databricks Apps UI → Environment tab")


# ===================================================================
# Step 11b: Grant App SP Lakebase Access
# ===================================================================
def grant_app_sp_lakebase_access(ctx: dict, instance_info: dict, cfg: dict):
    """Grant the Databricks App's built-in Service Principal access to Lakebase.

    Databricks Apps auto-creates an SP for each app. This SP needs:
    1. A Lakebase role with identity_type=SERVICE_PRINCIPAL
    2. SQL-level permissions on the lakemeter schema
    """
    import requests

    w = ctx["client"]
    log_info("Granting app service principal Lakebase access...")
    try:
        app_info = w.apps.get(cfg["app_name"])
        app_sp_id = app_info.service_principal_client_id
        if not app_sp_id:
            log_warn("App has no service principal — Lakebase OAuth will not work")
            return

        host = ctx["host"].rstrip("/")
        headers = w.config.authenticate()
        roles_url = f"{host}/api/2.0/database/instances/{instance_info['name']}/roles"

        # Check if role exists with correct identity_type
        resp = requests.get(roles_url, headers=headers)
        existing_roles = resp.json().get("database_instance_roles", []) if resp.status_code == 200 else []
        sp_role = next((r for r in existing_roles if r["name"] == app_sp_id), None)

        if not sp_role or sp_role.get("identity_type") != "SERVICE_PRINCIPAL":
            if sp_role:
                requests.delete(f"{roles_url}/{app_sp_id}", headers=headers)
            resp = requests.post(roles_url, headers=headers, json={
                "name": app_sp_id,
                "identity_type": "SERVICE_PRINCIPAL",
                "membership_role": "DATABRICKS_SUPERUSER",
            })
            if resp.status_code == 200:
                log_ok(f"App SP Lakebase role created ({app_sp_id[:12]}...)")
            else:
                log_warn(f"Could not create app SP role: {resp.status_code}")
        else:
            log_ok("App SP already has Lakebase role")

        # Grant SQL-level permissions
        conn = get_owner_connection(ctx, instance_info, cfg)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(f'GRANT CONNECT ON DATABASE {cfg["db_name"]} TO "{app_sp_id}"')
        cur.execute(f'GRANT USAGE ON SCHEMA {DEFAULT_SCHEMA} TO "{app_sp_id}"')
        cur.execute(f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {DEFAULT_SCHEMA} TO "{app_sp_id}"')
        cur.execute(f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {DEFAULT_SCHEMA} TO "{app_sp_id}"')
        cur.execute(f'GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {DEFAULT_SCHEMA} TO "{app_sp_id}"')
        cur.close()
        conn.close()
        log_ok("App SP SQL permissions granted")
    except Exception as e:
        log_warn(f"Could not configure app SP Lakebase access: {e}")
        log_info("App will use password-auth fallback (lakemeter_sync_role)")


# ===================================================================
# Step 12: Deploy App
# ===================================================================
def deploy_app(ctx: dict, cfg: dict):
    """Sync essential files to workspace and deploy via SDK.

    Only uploads what the app needs at runtime:
    - backend/app/ (FastAPI)
    - backend/static/ (built frontend assets — excludes vm-costs.csv)
    - backend/scripts/ (startup helpers)
    - frontend/ (source — built at startup via app.yaml command)
    - app.yaml, requirements.txt
    """
    import base64
    import shutil
    import subprocess
    from databricks.sdk.service.workspace import ImportFormat, Language

    w = ctx["client"]
    user = ctx["user"]
    app_name = cfg["app_name"]
    ws_path = f"/Workspace/Users/{user}/apps/{app_name}"

    # 1. Build frontend from source if Node.js is available, otherwise use pre-built assets
    frontend_dir = APP_DIR / "frontend"
    static_dir = APP_DIR / "backend" / "static"
    if shutil.which("npm") and frontend_dir.exists() and (frontend_dir / "package.json").exists():
        log_info("Building frontend from source...")
        result = subprocess.run(
            ["npm", "ci", "--silent"],
            cwd=str(frontend_dir),
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            log_warn(f"npm ci failed: {result.stderr[:200]}")
        else:
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=str(frontend_dir),
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                log_ok("Frontend built from source")
            else:
                log_warn(f"npm build failed: {result.stderr[:200]}")
    else:
        log_info("Using pre-built frontend assets from repository")

    # Verify pre-built static assets exist (either from npm build or committed in repo)
    if not (static_dir / "index.html").exists():
        log_err("No frontend assets found at backend/static/index.html")
        log_info("Either install Node.js to build from source, or ensure the repo was cloned completely")
        return

    # 2. Sync essential files to workspace
    MAX_FILE_SIZE = 9 * 1024 * 1024  # workspace import limit ~10MB
    uploaded = 0

    created_dirs = set()

    def ensure_ws_dir(ws_dir_path: str):
        """Create workspace directory if not already created."""
        if ws_dir_path in created_dirs:
            return
        try:
            w.workspace.mkdirs(ws_dir_path)
        except Exception:
            pass
        created_dirs.add(ws_dir_path)

    def upload_dir(local_dir: Path, ws_dir: str, exclude_patterns=None):
        """Recursively upload a directory to workspace."""
        nonlocal uploaded
        if not local_dir.exists():
            return
        exclude_patterns = exclude_patterns or []
        ensure_ws_dir(ws_dir)
        for item in sorted(local_dir.rglob("*")):
            if item.is_dir():
                continue
            rel = item.relative_to(local_dir)
            # Skip excluded patterns
            skip = False
            for pat in exclude_patterns:
                if pat in str(rel):
                    skip = True
                    break
            if skip:
                continue
            # Skip files that are too large
            if item.stat().st_size > MAX_FILE_SIZE:
                log_info(f"  Skipping {rel} ({item.stat().st_size // 1024 // 1024}MB > limit)")
                continue
            # Skip __pycache__, .pyc
            if "__pycache__" in str(rel) or str(rel).endswith(".pyc"):
                continue
            # Ensure parent directory exists in workspace
            rel_parent = str(rel.parent)
            if rel_parent != ".":
                ensure_ws_dir(f"{ws_dir}/{rel_parent}")
            file_bytes = item.read_bytes()
            target = f"{ws_dir}/{rel}"
            try:
                w.workspace.import_(
                    path=target,
                    content=base64.b64encode(file_bytes).decode("ascii"),
                    format=ImportFormat.AUTO,
                    overwrite=True,
                )
                uploaded += 1
            except Exception as e:
                log_warn(f"  Upload failed for {rel}: {str(e)[:100]}")

    def upload_file(local_file: Path, ws_file: str):
        """Upload a single file to workspace."""
        nonlocal uploaded
        if not local_file.exists():
            return
        file_bytes = local_file.read_bytes()
        try:
            w.workspace.import_(
                path=ws_file,
                content=base64.b64encode(file_bytes).decode("ascii"),
                format=ImportFormat.AUTO,
                overwrite=True,
            )
            uploaded += 1
        except Exception as e:
            log_warn(f"  Upload failed for {local_file.name}: {str(e)[:100]}")

    # Backend app code (FastAPI source)
    upload_dir(APP_DIR / "backend" / "app", f"{ws_path}/backend/app")
    # Backend static: pre-built frontend (JS/CSS/HTML) + JSON pricing bundle
    # Exclude CSVs (pricing data is in Lakebase) and build-time-only files
    upload_dir(APP_DIR / "backend" / "static", f"{ws_path}/backend/static",
               exclude_patterns=[".csv", "manifest.json"])
    # NOTE: backend/scripts/ excluded — only contains build-time tools, not needed at runtime
    # NOTE: frontend/ excluded — app.yaml runs pre-built static assets from backend/static/,
    #        does NOT build frontend from source at startup

    # Top-level config
    upload_file(APP_DIR / "app.yaml", f"{ws_path}/app.yaml")
    upload_file(APP_DIR / "requirements.txt", f"{ws_path}/requirements.txt")

    log_ok(f"Uploaded {uploaded} files to {ws_path}")

    # 3. Deploy
    profile = ctx.get("profile", "")
    profile_flag = f"--profile {profile}" if profile else ""
    result = subprocess.run(
        f"databricks apps deploy {app_name} {profile_flag} --source-code-path \"{ws_path}\"",
        shell=True,
        capture_output=True, text=True, timeout=600,
    )
    if result.returncode == 0:
        log_ok("App deployment started")
        # Wait for deployment
        log_info("Waiting for deployment to complete...")
        import time
        for _ in range(60):  # 10 min max
            time.sleep(10)
            try:
                app_info = w.apps.get(app_name)
                ad = getattr(app_info, "active_deployment", None)
                pd = getattr(app_info, "pending_deployment", None)
                deploy = pd or ad
                if deploy:
                    state = deploy.status.state.value if hasattr(deploy.status.state, "value") else str(deploy.status.state)
                    log_info(f"  Deploy state: {state}")
                    if state == "SUCCEEDED":
                        log_ok(f"App deployed and running at {app_info.url}")
                        return
                    if state == "FAILED":
                        log_warn(f"Deploy failed: {deploy.status.message}")
                        return
            except Exception:
                pass
        log_warn("Timed out waiting for deployment")
    else:
        log_warn(f"Deploy command failed: {result.stderr[:300]}")


# ===================================================================
# Main
# ===================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Lakemeter Zero-Click Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--profile", required=True, help="Databricks CLI profile name"
    )
    parser.add_argument(
        "--non-interactive", action="store_true",
        help="Use all defaults, no prompts (for CI/CD pipelines)",
    )
    args = parser.parse_args()

    TOTAL_STEPS = 8

    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{BOLD}  Lakemeter Installer — Zero-Click Deployment{NC}")
    print(f"{BOLD}{'='*60}{NC}")

    # Step 1: Validate prerequisites
    log_step(1, TOTAL_STEPS, "Validating prerequisites")
    ctx = validate_prerequisites(args.profile)

    # Step 2: Gather configuration
    log_step(2, TOTAL_STEPS, "Gathering configuration")
    cfg = gather_config(ctx, non_interactive=args.non_interactive)

    # Step 3: Provision Lakebase (reuses if already exists)
    log_step(3, TOTAL_STEPS, "Provisioning Lakebase instance")
    instance_info = provision_lakebase(ctx, cfg)

    # Step 4: Create database, schema, tables, and auth role
    log_step(4, TOTAL_STEPS, "Creating database, schema, and tables")
    create_database_and_schema(ctx, instance_info, cfg)
    create_password_auth_role(ctx, instance_info, cfg)
    run_setup_sql(ctx, instance_info, cfg)

    # Step 5: Load pricing data (serverless notebook)
    log_step(5, TOTAL_STEPS, "Loading pricing reference data")
    load_pricing_data(ctx, instance_info, cfg)

    # Step 6: Create SKU discount mapping and cost calculation views
    log_step(6, TOTAL_STEPS, "Creating SKU mapping and views")
    create_sku_discount_mapping(ctx, instance_info, cfg)
    create_views(ctx, instance_info, cfg)

    # Step 7: Configure application (app.yaml, resources, SP access)
    log_step(7, TOTAL_STEPS, "Configuring application")
    generate_app_config(ctx, instance_info, cfg)
    configure_app_resources(ctx, instance_info, cfg)
    grant_app_sp_lakebase_access(ctx, instance_info, cfg)

    # Step 8: Deploy application
    log_step(8, TOTAL_STEPS, "Deploying application")
    deploy_app(ctx, cfg)

    # Summary
    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{GREEN}{BOLD}  Installation Complete!{NC}")
    print(f"{BOLD}{'='*60}{NC}")
    print(f"\n  Instance:  {CYAN}{instance_info['name']}{NC}")
    print(f"  Database:  {CYAN}{cfg['db_name']}{NC}")
    print(f"  DB Host:   {CYAN}{instance_info['host']}{NC}")
    print(f"  App Name:  {CYAN}{cfg['app_name']}{NC}")
    print(f"\n  Verify the app is running:")
    print(f"  databricks apps get {cfg['app_name']} --profile {args.profile}")
    print()


if __name__ == "__main__":
    main()
