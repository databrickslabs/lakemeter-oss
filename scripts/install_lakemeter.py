#!/usr/bin/env python3
"""
Lakemeter Zero-Click Installer

Provisions a complete Lakemeter environment on Databricks:
  1. Validates prerequisites (CLI, profile, secrets)
  2. Provisions a new Lakebase (PostgreSQL) instance
  3. Creates database, schema, tables, views, constraints
  4. Loads pricing reference data from static JSON files
  5. Configures Service Principal access (OAuth M2M)
  6. Creates Databricks App resources and deploys

Usage:
    python scripts/install_lakemeter.py --profile <cli-profile>

Requirements:
    - Databricks CLI configured with a workspace profile
    - Python 3.10+ with psycopg2, databricks-sdk
    - Service Principal credentials in a Databricks secrets scope
"""
import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
APP_DIR = SCRIPT_DIR.parent
BACKEND_DIR = APP_DIR / "backend"
PRICING_DIR = BACKEND_DIR / "static" / "pricing"
SETUP_DIR = APP_DIR / "etl" / "lakebase_setup" / "setup"

DEFAULT_DB_NAME = "lakemeter_pricing"
DEFAULT_SCHEMA = "lakemeter"
DEFAULT_CU_SIZE = "CU_1"
DEFAULT_NODE_COUNT = 1

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


def prompt_choice(label: str, options: list[str], default: int = 0) -> str:
    """Prompt user to select from a list of options."""
    print(f"  {CYAN}?{NC} {label}")
    for i, opt in enumerate(options):
        marker = ">" if i == default else " "
        print(f"    {marker} [{i+1}] {opt}")
    while True:
        raw = input(f"    Select [1-{len(options)}] (default {default+1}): ").strip()
        if not raw:
            return options[default]
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        print(f"    {RED}Invalid choice{NC}")


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

    # Check Node.js/npm (needed for frontend build during deploy)
    if not shutil.which("node"):
        log_warn("Node.js not found — frontend build will be skipped during deploy")
    elif not shutil.which("npm"):
        log_warn("npm not found — frontend build will be skipped during deploy")
    else:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        log_ok(f"Node.js {result.stdout.strip()}")

    # Check Databricks CLI
    if not shutil.which("databricks"):
        log_err("Databricks CLI not found. Install: pip install databricks-cli")
        sys.exit(1)
    log_ok("Databricks CLI found")

    # Check pricing data directory
    if not PRICING_DIR.exists() or not any(PRICING_DIR.glob("*.json")):
        log_err(f"Pricing data not found at {PRICING_DIR}")
        log_info("Ensure you cloned the full repository including backend/static/pricing/")
        sys.exit(1)
    pricing_count = len(list(PRICING_DIR.glob("*.json")))
    log_ok(f"Pricing data: {pricing_count} JSON files")

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
            "sp_client_id_key": "sp_clientid",
            "sp_secret_key": "sp_secret",
        }

    instance_name = prompt_input("Lakebase instance name", "lakemeter-customer")
    db_name = prompt_input("Database name", DEFAULT_DB_NAME)
    app_name = prompt_input("Databricks App name", "lakemeter")

    cu_options = ["CU_1 (smallest, dev/demo)", "CU_2", "CU_4", "CU_8 (production)"]
    cu_choice = prompt_choice("Compute unit size", cu_options, default=0)
    cu_size = cu_choice.split(" ")[0]

    secrets_scope = prompt_input("Secrets scope name", "lakemeter-secrets")
    sp_client_id_key = prompt_input("SP client ID secret key", "sp_clientid")
    sp_secret_key = prompt_input("SP secret key name", "sp_secret")

    return {
        "instance_name": instance_name,
        "db_name": db_name,
        "app_name": app_name,
        "cu_size": cu_size,
        "secrets_scope": secrets_scope,
        "sp_client_id_key": sp_client_id_key,
        "sp_secret_key": sp_secret_key,
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

    log_info(f"Creating Lakebase instance '{name}' ({cfg['cu_size']}, auto-scaling enabled)...")
    from databricks.sdk.service.database import CreateDatabaseInstanceRequest

    instance = w.database.create_database_instance(
        name=name,
        capacity=cfg["cu_size"],
        stopped=False,
    )
    log_ok(f"Instance created: {instance.name} (uid={instance.uid})")

    # Enable auto-scaling via REST API (not yet in SDK)
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
            },
        )
        if resp.status_code < 300:
            log_ok("Auto-scaling (serverless compute) enabled")
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
    """Execute the table creation, views, constraints, and seed data SQL.

    Extracts SQL from the Databricks notebook .py files and runs them.
    """
    conn = get_owner_connection(ctx, instance_info, cfg)
    conn.autocommit = True
    cur = conn.cursor()

    # --- Application Tables ---
    tables_sql = _extract_sql_from_notebook(SETUP_DIR / "01_Create_Tables.py")
    if tables_sql:
        for stmt in tables_sql:
            try:
                cur.execute(stmt)
            except Exception as e:
                if "already exists" not in str(e):
                    log_warn(f"SQL warning: {str(e)[:100]}")
                conn.rollback() if not conn.autocommit else None
        log_ok("Application tables created (9 tables + seed data)")
    else:
        # Fallback: run inline SQL for core tables
        _create_tables_inline(cur)
        log_ok("Application tables created (inline fallback)")

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


def _extract_sql_from_notebook(notebook_path: Path) -> Optional[list]:
    """Extract executable SQL statements from a Databricks notebook .py file.

    Returns None if the file doesn't exist or can't be parsed.
    """
    if not notebook_path.exists():
        return None

    content = notebook_path.read_text()
    sql_stmts = []
    in_sql_block = False
    current_sql = []

    for line in content.split("\n"):
        # Skip Databricks magic commands, comments, Python code
        stripped = line.strip()
        if stripped.startswith("# MAGIC") or stripped.startswith("# COMMAND"):
            continue
        if stripped.startswith("%run") or stripped.startswith("import "):
            continue

        # Look for SQL in triple-quoted strings or execute() calls
        if 'execute("""' in line or "execute('''" in line:
            in_sql_block = True
            # Extract the part after execute(
            start = line.find('"""') or line.find("'''")
            if start >= 0:
                current_sql.append(line[start + 3 :])
            continue

        if in_sql_block:
            if '""")' in line or "''')" in line:
                end = line.find('"""') or line.find("'''")
                current_sql.append(line[:end])
                sql_stmts.append("\n".join(current_sql))
                current_sql = []
                in_sql_block = False
            else:
                current_sql.append(line)

    return sql_stmts if sql_stmts else None


def _create_tables_inline(cur):
    """Create core tables with inline SQL (fallback when notebooks aren't available)."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS lakemeter.users (
            user_id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            full_name TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS lakemeter.templates (
            template_id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            name TEXT NOT NULL,
            description TEXT,
            cloud TEXT NOT NULL DEFAULT 'AWS',
            region TEXT NOT NULL DEFAULT 'us-east-1',
            tier TEXT NOT NULL DEFAULT 'PREMIUM',
            owner_id TEXT REFERENCES lakemeter.users(user_id),
            is_public BOOLEAN DEFAULT FALSE,
            config JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS lakemeter.ref_cloud_tiers (
            cloud TEXT NOT NULL,
            tier TEXT NOT NULL,
            PRIMARY KEY (cloud, tier)
        );
        CREATE TABLE IF NOT EXISTS lakemeter.estimates (
            estimate_id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            estimate_name TEXT NOT NULL,
            cloud TEXT NOT NULL DEFAULT 'AWS',
            region TEXT NOT NULL DEFAULT 'us-east-1',
            tier TEXT NOT NULL DEFAULT 'PREMIUM',
            owner_id TEXT REFERENCES lakemeter.users(user_id),
            template_id TEXT REFERENCES lakemeter.templates(template_id),
            notes TEXT,
            discount_config JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (cloud, tier) REFERENCES lakemeter.ref_cloud_tiers(cloud, tier)
        );
        CREATE TABLE IF NOT EXISTS lakemeter.ref_workload_types (
            workload_type TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT
        );
        CREATE TABLE IF NOT EXISTS lakemeter.line_items (
            line_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            estimate_id UUID NOT NULL REFERENCES lakemeter.estimates(estimate_id) ON DELETE CASCADE,
            display_order INT,
            workload_name VARCHAR(255) NOT NULL,
            workload_type VARCHAR(50) NOT NULL,
            cloud VARCHAR(20),
            -- Compute config
            serverless_enabled BOOLEAN DEFAULT false,
            serverless_mode VARCHAR(20),
            photon_enabled BOOLEAN DEFAULT false,
            driver_node_type VARCHAR(100),
            worker_node_type VARCHAR(100),
            num_workers INT,
            -- DLT config
            dlt_edition VARCHAR(20),
            -- DBSQL config
            dbsql_warehouse_type VARCHAR(20),
            dbsql_warehouse_size VARCHAR(20),
            dbsql_num_clusters INT DEFAULT 1,
            dbsql_vm_pricing_tier VARCHAR(20),
            dbsql_vm_payment_option VARCHAR(20),
            -- Vector Search config
            vector_search_mode VARCHAR(50),
            vector_capacity_millions DECIMAL(10,2),
            vector_search_storage_gb DECIMAL(10,2) CHECK (vector_search_storage_gb >= 0),
            -- Model Serving config
            model_serving_gpu_type VARCHAR(50),
            -- FMAPI config
            fmapi_provider VARCHAR(50),
            fmapi_model VARCHAR(100),
            fmapi_endpoint_type VARCHAR(20),
            fmapi_context_length VARCHAR(20),
            fmapi_rate_type VARCHAR(20),
            fmapi_quantity BIGINT,
            -- Lakebase config
            lakebase_cu NUMERIC(5,1),
            lakebase_storage_gb INT,
            lakebase_ha_nodes INT DEFAULT 1,
            lakebase_backup_retention_days INT DEFAULT 7,
            lakebase_pitr_gb INT,
            lakebase_snapshot_gb INT,
            -- Usage/frequency
            runs_per_day INT,
            avg_runtime_minutes INT,
            days_per_month INT DEFAULT 30,
            hours_per_month DECIMAL(10,2),
            -- VM pricing
            driver_pricing_tier VARCHAR(20),
            worker_pricing_tier VARCHAR(20),
            driver_payment_option VARCHAR(20),
            worker_payment_option VARCHAR(20),
            -- Extensible config
            workload_config JSON,
            notes TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS lakemeter.conversation_messages (
            message_id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            estimate_id TEXT NOT NULL REFERENCES lakemeter.estimates(estimate_id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS lakemeter.decision_records (
            decision_id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            estimate_id TEXT NOT NULL REFERENCES lakemeter.estimates(estimate_id) ON DELETE CASCADE,
            message_id TEXT REFERENCES lakemeter.conversation_messages(message_id),
            decision_type TEXT NOT NULL,
            summary TEXT,
            details JSONB,
            status TEXT DEFAULT 'proposed',
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS lakemeter.sharing (
            sharing_id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            estimate_id TEXT NOT NULL REFERENCES lakemeter.estimates(estimate_id) ON DELETE CASCADE,
            shared_with_email TEXT NOT NULL,
            permission TEXT NOT NULL DEFAULT 'view',
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # Seed data
    seed_workload_types = [
        ("ALL_PURPOSE", "All-Purpose Compute", "compute", "Interactive notebooks and development"),
        ("JOBS", "Jobs Compute", "compute", "Automated workflows and pipelines"),
        ("DLT", "Delta Live Tables", "compute", "Declarative ETL pipelines"),
        ("SQL_WAREHOUSE", "SQL Warehouse", "sql", "SQL analytics and BI queries"),
        ("MODEL_SERVING", "Model Serving", "ai", "Real-time model inference"),
        ("VECTOR_SEARCH", "Vector Search", "ai", "Vector similarity search"),
        ("FMAPI", "Foundation Model APIs", "ai", "Foundation model inference"),
        ("LAKEBASE", "Lakebase", "database", "Managed PostgreSQL database"),
        ("SERVERLESS_COMPUTE", "Serverless Compute", "compute", "Serverless notebooks and jobs"),
    ]
    for wt in seed_workload_types:
        cur.execute(
            """INSERT INTO lakemeter.ref_workload_types
               (workload_type, display_name, category, description)
               VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING""",
            wt,
        )

    seed_cloud_tiers = [
        ("AWS", "ENTERPRISE"), ("AWS", "PREMIUM"),
        ("AZURE", "ENTERPRISE"), ("AZURE", "PREMIUM"),
        ("GCP", "ENTERPRISE"), ("GCP", "PREMIUM"),
        ("AWS", "STANDARD"), ("AZURE", "STANDARD"),
    ]
    for ct in seed_cloud_tiers:
        cur.execute(
            """INSERT INTO lakemeter.ref_cloud_tiers (cloud, tier)
               VALUES (%s, %s) ON CONFLICT DO NOTHING""",
            ct,
        )

    # Indexes
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_line_items_estimate
        ON lakemeter.line_items(estimate_id);
        CREATE INDEX IF NOT EXISTS idx_line_items_workload_type
        ON lakemeter.line_items(workload_type);
    """)


# ===================================================================
# Step 5: Load Pricing Data
# ===================================================================
def load_pricing_data(ctx: dict, instance_info: dict, cfg: dict):
    """Load pricing reference data from static JSON files into sync tables."""
    import psycopg2.extras

    conn = get_owner_connection(ctx, instance_info, cfg)
    conn.autocommit = True
    cur = conn.cursor()

    now = datetime.utcnow().isoformat()

    # Create sync tables if they don't exist
    _create_sync_tables(cur)

    # Load each pricing file
    loaders = [
        ("dbu-rates.json", _load_dbu_rates),
        ("instance-dbu-rates.json", _load_instance_dbu_rates),
        ("dbu-multipliers.json", _load_dbu_multipliers),
        ("dbsql-rates.json", _load_dbsql_rates),
        ("dbsql-warehouse-config.json", _load_dbsql_warehouse_config),
        ("model-serving-rates.json", _load_model_serving_rates),
        ("vector-search-rates.json", _load_vector_search_rates),
        ("fmapi-databricks-rates.json", _load_fmapi_databricks_rates),
        ("fmapi-proprietary-rates.json", _load_fmapi_proprietary_rates),
    ]

    total_rows = 0
    for filename, loader_fn in loaders:
        filepath = PRICING_DIR / filename
        if not filepath.exists():
            log_warn(f"Pricing file not found: {filename}")
            continue
        with open(filepath) as f:
            data = json.load(f)
        count = loader_fn(cur, data, now)
        total_rows += count
        log_info(f"  {filename}: {count} rows")

    log_ok(f"Loaded {total_rows} pricing rows total")

    cur.close()
    conn.close()


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


def _batch_insert(cur, table: str, columns: list, rows: list):
    """Batch insert rows using execute_values for performance."""
    if not rows:
        return 0
    import psycopg2.extras

    cols = ", ".join(columns)
    tmpl = "(" + ", ".join(["%s"] * len(columns)) + ")"
    sql = f"INSERT INTO lakemeter.{table} ({cols}) VALUES %s"

    # Truncate first (full refresh)
    cur.execute(f"TRUNCATE TABLE lakemeter.{table}")
    psycopg2.extras.execute_values(cur, sql, rows, template=tmpl, page_size=500)
    return len(rows)


def _load_dbu_rates(cur, data: dict, now: str) -> int:
    rows = []
    for key, rate in data.items():
        parts = key.split(":")
        if len(parts) >= 3:
            cloud, region, tier = parts[0], parts[1], parts[2]
        else:
            continue
        if isinstance(rate, dict):
            for sku_name, val in rate.items():
                # val can be a float (rate) or a dict with metadata
                if isinstance(val, dict):
                    price = val.get("price_per_dbu", 0)
                    product_type = val.get("product_type", "")
                    sku_region = val.get("sku_region", "")
                    usage_unit = val.get("usage_unit", "DBU")
                    currency = val.get("currency_code", "USD")
                    pricing_type = val.get("pricing_type", "")
                else:
                    price = float(val) if val else 0
                    product_type = ""
                    sku_region = ""
                    usage_unit = "DBU"
                    currency = "USD"
                    pricing_type = ""
                rows.append((
                    sku_name, cloud.upper(), tier, product_type,
                    sku_region, region, usage_unit,
                    price, currency, pricing_type, now,
                ))
    return _batch_insert(cur, "sync_pricing_dbu_rates",
        ["sku_name", "cloud", "tier", "product_type", "sku_region", "region",
         "usage_unit", "price_per_dbu", "currency_code", "pricing_type", "fetched_at"],
        rows)


def _load_instance_dbu_rates(cur, data: dict, now: str) -> int:
    rows = []
    for key, val in data.items():
        if isinstance(val, dict) and "dbu_rate" not in val:
            # Nested format: {cloud: {instance_type: {dbu_rate, vcpus, ...}}}
            cloud = key
            for instance_type, info in val.items():
                if isinstance(info, dict):
                    rows.append((
                        cloud.upper(), instance_type,
                        info.get("vcpus", 0), info.get("memory_gb", 0),
                        info.get("dbu_rate", 0), info.get("family", info.get("instance_family", "")),
                        True, "pricing_bundle",
                    ))
        else:
            # Flat format: {cloud:instance_type: {dbu_rate, vcpus, ...}}
            parts = key.split(":")
            if len(parts) >= 2:
                cloud, instance_type = parts[0], parts[1]
            else:
                continue
            info = val if isinstance(val, dict) else {}
            rows.append((
                cloud.upper(), instance_type,
                info.get("vcpus", 0), info.get("memory_gb", 0),
                info.get("dbu_rate", 0), info.get("family", info.get("instance_family", "")),
                True, "pricing_bundle",
            ))
    return _batch_insert(cur, "sync_ref_instance_dbu_rates",
        ["cloud", "instance_type", "vcpus", "memory_gb", "dbu_rate", "instance_family",
         "is_active", "source"],
        rows)


def _load_dbu_multipliers(cur, data: dict, now: str) -> int:
    rows = []
    for key, info in data.items():
        parts = key.split(":")
        if len(parts) >= 3:
            cloud, sku_type, feature = parts[0], parts[1], parts[2]
        else:
            continue
        rows.append((
            cloud.upper(), sku_type, feature,
            info.get("multiplier", 1.0), info.get("category", ""),
        ))
    return _batch_insert(cur, "sync_ref_dbu_multipliers",
        ["cloud", "sku_type", "feature", "multiplier", "category"],
        rows)


def _load_dbsql_rates(cur, data: dict, now: str) -> int:
    rows = []
    for key, info in data.items():
        parts = key.split(":")
        if len(parts) >= 3:
            cloud, wh_type, wh_size = parts[0], parts[1], parts[2]
        else:
            continue
        rows.append((
            cloud.upper(), wh_type, wh_size,
            info.get("sku_product_type", ""),
            info.get("dbu_per_hour", 0),
            info.get("includes_compute", False),
        ))
    return _batch_insert(cur, "sync_product_dbsql_rates",
        ["cloud", "warehouse_type", "warehouse_size", "sku_product_type",
         "dbu_per_hour", "includes_compute"],
        rows)


def _load_dbsql_warehouse_config(cur, data: dict, now: str) -> int:
    rows = []
    for key, info in data.items():
        parts = key.split(":")
        if len(parts) >= 3:
            cloud, wh_size, wh_type = parts[0], parts[1], parts[2] if len(parts) > 2 else ""
        else:
            continue
        rows.append((
            cloud.upper(), wh_size, str(info.get("worker_count", "")),
            info.get("driver_instance_type", ""),
            info.get("worker_instance_type", ""),
            wh_type,
        ))
    return _batch_insert(cur, "sync_ref_dbsql_warehouse_config",
        ["cloud", "warehouse_size", "worker_count", "driver_instance_type",
         "worker_instance_type", "warehouse_type"],
        rows)


def _load_model_serving_rates(cur, data: dict, now: str) -> int:
    # Model serving data populates both serverless rates and ref tables
    rows_serverless = []
    rows_gpu = []
    seen_gpu = set()

    for key, info in data.items():
        parts = key.split(":")
        if len(parts) >= 2:
            cloud = parts[0].upper()
            model_or_type = parts[1]
        else:
            continue

        if isinstance(info, dict):
            rows_serverless.append((
                cloud, "model_serving", model_or_type,
                info.get("rate_type", ""), info.get("dbu_rate", 0),
                info.get("input_divisor", ""), info.get("is_hourly", False),
                info.get("sku_product_type", ""), info.get("description", ""),
            ))
            gpu_key = (cloud, model_or_type)
            if gpu_key not in seen_gpu and "gpu" in model_or_type.lower():
                rows_gpu.append((cloud, model_or_type, "", True))
                seen_gpu.add(gpu_key)

    count = _batch_insert(cur, "sync_product_serverless_rates",
        ["cloud", "product", "size_or_model", "rate_type", "dbu_rate",
         "input_divisor", "is_hourly", "sku_product_type", "description"],
        rows_serverless)

    if rows_gpu:
        import psycopg2.extras
        cur.execute("TRUNCATE TABLE lakemeter.ref_model_serving_gpu_types")
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO lakemeter.ref_model_serving_gpu_types (cloud, gpu_type, description, is_active) VALUES %s",
            rows_gpu, page_size=100,
        )
        count += len(rows_gpu)

    return count


def _load_vector_search_rates(cur, data: dict, now: str) -> int:
    rows = []
    for key, info in data.items():
        parts = key.split(":")
        if len(parts) >= 2:
            cloud, ep_type = parts[0].upper(), parts[1]
        else:
            continue
        if isinstance(info, dict):
            rows.append((
                cloud, "vector_search", ep_type,
                info.get("rate_type", ""), info.get("dbu_rate", 0),
                info.get("input_divisor", ""), info.get("is_hourly", True),
                info.get("sku_product_type", ""), info.get("description", ""),
            ))
    # Append to serverless_rates (don't truncate — model serving already loaded)
    if rows:
        import psycopg2.extras
        psycopg2.extras.execute_values(
            cur,
            """INSERT INTO lakemeter.sync_product_serverless_rates
               (cloud, product, size_or_model, rate_type, dbu_rate,
                input_divisor, is_hourly, sku_product_type, description) VALUES %s""",
            rows, page_size=100,
        )
    return len(rows)


def _load_fmapi_databricks_rates(cur, data: dict, now: str) -> int:
    rows = []
    seen_models = set()
    for key, rate in data.items():
        parts = key.split(":")
        if len(parts) >= 3:
            cloud, model, rate_type = parts[0].upper(), parts[1], parts[2]
        else:
            continue
        if isinstance(rate, (int, float)):
            rows.append((cloud, model, rate_type, rate, "", False, ""))
        elif isinstance(rate, dict):
            rows.append((
                cloud, model, rate_type, rate.get("dbu_rate", 0),
                rate.get("input_divisor", ""), rate.get("is_hourly", False),
                rate.get("sku_product_type", ""),
            ))
        seen_models.add(model)

    count = _batch_insert(cur, "sync_product_fmapi_databricks",
        ["cloud", "model", "rate_type", "dbu_rate", "input_divisor",
         "is_hourly", "sku_product_type"],
        rows)

    # Populate ref table
    if seen_models:
        import psycopg2.extras
        cur.execute("TRUNCATE TABLE lakemeter.ref_fmapi_databricks_models")
        model_rows = [(m, "", True) for m in seen_models]
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO lakemeter.ref_fmapi_databricks_models (model_name, description, is_active) VALUES %s",
            model_rows, page_size=100,
        )
        count += len(model_rows)

    return count


def _load_fmapi_proprietary_rates(cur, data: dict, now: str) -> int:
    rows = []
    seen_models = set()

    for key, rate in data.items():
        parts = key.split(":")
        if len(parts) >= 3:
            cloud_or_provider = parts[0]
            model = parts[1]
            rate_type = parts[2]
        else:
            continue

        if isinstance(rate, dict):
            rows.append((
                rate.get("provider", cloud_or_provider), model,
                rate.get("endpoint_type", ""), rate.get("context_length", ""),
                rate_type, rate.get("dbu_rate", 0),
                rate.get("input_divisor", ""), rate.get("is_hourly", False),
                rate.get("sku_product_type", ""),
                rate.get("cloud", cloud_or_provider.upper()),
            ))
            seen_models.add((rate.get("provider", cloud_or_provider), model))
        elif isinstance(rate, (int, float)):
            rows.append((
                cloud_or_provider, model, "", "", rate_type, rate,
                "", False, "", cloud_or_provider.upper(),
            ))
            seen_models.add((cloud_or_provider, model))

    count = _batch_insert(cur, "sync_product_fmapi_proprietary",
        ["provider", "model", "endpoint_type", "context_length", "rate_type",
         "dbu_rate", "input_divisor", "is_hourly", "sku_product_type", "cloud"],
        rows)

    if seen_models:
        import psycopg2.extras
        cur.execute("TRUNCATE TABLE lakemeter.ref_fmapi_proprietary_models")
        model_rows = [(p, m, "", True) for p, m in seen_models]
        psycopg2.extras.execute_values(
            cur,
            """INSERT INTO lakemeter.ref_fmapi_proprietary_models
               (provider, model_name, description, is_active) VALUES %s""",
            model_rows, page_size=100,
        )
        count += len(model_rows)

    return count


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

    views_sql = _extract_sql_from_notebook(SETUP_DIR / "02_Create_Views.py")
    if views_sql:
        for stmt in views_sql:
            try:
                cur.execute(stmt)
            except Exception as e:
                log_warn(f"View creation warning: {str(e)[:100]}")
        log_ok("Cost calculation views created")
    else:
        log_warn("Could not extract views SQL — run 02_Create_Views.py manually")

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
    # Build frontend from source (Node.js 22 + npm available in Databricks Apps runtime)
    cd frontend && npm ci --silent && npm run build && cd .. &&
    # Start FastAPI backend
    cd backend && ../.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port ${{DATABRICKS_APP_PORT:-8000}}

env:
  # App environment
  - name: "ENVIRONMENT"
    value: "production"
  - name: "CORS_ORIGINS"
    value: ""

  # Note: DATABRICKS_HOST is auto-populated by Databricks Apps platform.
  # Do NOT set it manually — the platform injects the correct workspace URL.

  # Secrets scope containing SP credentials
  - name: "DATABRICKS_SECRETS_SCOPE"
    valueFrom: "{cfg['secrets_scope']}-scope"
  - name: "SP_CLIENT_ID_KEY"
    value: "{cfg['sp_client_id_key']}"
  - name: "SP_SECRET_KEY"
    value: "{cfg['sp_secret_key']}"

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
        "secrets-scope-name": scope,
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
        f"{scope}-scope": ("secrets-scope-name", "Secrets scope name"),
        f"{app_name}-lakebase-instance": ("lakebase-instance-name", "Lakebase instance name"),
        f"{app_name}-db-host": ("lakebase-host", "Database host"),
        f"{app_name}-db-user": ("lakebase-user", "Database user"),
        f"{app_name}-db-name": ("lakebase-database", "Database name"),
    }

    # 3. Configure app resources via REST API
    import requests
    resources = []
    for name, (secret_key, desc) in resource_map.items():
        resources.append({
            "name": name,
            "description": desc,
            "secret": {"scope": scope, "key": secret_key, "permission": "READ"},
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
# Step 10: Deploy App
# ===================================================================
def deploy_app(ctx: dict, cfg: dict):
    """Build frontend and deploy to Databricks Apps via workspace sync.

    Only syncs the files needed for the app to run:
    - backend/ (FastAPI app, routes, services, static assets)
    - frontend/ (React source — built at startup via app.yaml command)
    - scripts/ (installer)
    - app.yaml, requirements.txt

    Excludes tests/, etl/, docs-site/, harness/, .venv/, .git/, node_modules/.
    """
    import subprocess

    deploy_script = APP_DIR / "deploy.sh"
    if deploy_script.exists():
        log_info("Running deploy.sh --workspace-deploy ...")
        profile = ctx.get("profile", "")
        result = subprocess.run(
            ["bash", str(deploy_script), "--workspace-deploy"],
            cwd=str(APP_DIR),
            env={
                **os.environ,
                "DATABRICKS_HOST": ctx["host"].replace("https://", ""),
                "LAKEMETER_APP_NAME": cfg["app_name"],
                "DATABRICKS_PROFILE": profile,
            },
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            log_ok("App deployed successfully")
            if result.stdout:
                # Show last few lines of deploy output
                for line in result.stdout.strip().split('\n')[-5:]:
                    log_info(line)
        else:
            log_warn(f"Deploy script exited with code {result.returncode}")
            if result.stderr:
                log_info(result.stderr[:500])
            if result.stdout:
                log_info(result.stdout[-500:])
    else:
        log_warn("deploy.sh not found — deploy manually")
        log_info(f"  cd {APP_DIR} && bash deploy.sh --workspace-deploy")


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
        "--skip-deploy", action="store_true", help="Skip frontend build and app deployment"
    )
    parser.add_argument(
        "--skip-provision", action="store_true",
        help="Skip Lakebase provisioning (use existing instance)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate config and show plan without making changes",
    )
    parser.add_argument(
        "--non-interactive", action="store_true",
        help="Use all defaults, no prompts (for CI/CD pipelines)",
    )
    args = parser.parse_args()

    TOTAL_STEPS = 10

    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{BOLD}  Lakemeter Installer — Zero-Click Deployment{NC}")
    print(f"{BOLD}{'='*60}{NC}")

    # Step 1: Validate
    log_step(1, TOTAL_STEPS, "Validating prerequisites")
    ctx = validate_prerequisites(args.profile)

    # Step 2: Gather config
    log_step(2, TOTAL_STEPS, "Gathering configuration")
    cfg = gather_config(ctx, non_interactive=args.non_interactive)

    if args.dry_run:
        print(f"\n{BOLD}=== DRY RUN — No changes will be made ==={NC}")
        print(f"  Instance:  {CYAN}{cfg['instance_name']}{NC}")
        print(f"  Database:  {CYAN}{cfg['db_name']}{NC}")
        print(f"  App:       {CYAN}{cfg['app_name']}{NC}")
        print(f"  CU Size:   {CYAN}{cfg['cu_size']}{NC}")
        print(f"  Scope:     {CYAN}{cfg['secrets_scope']}{NC}")
        print(f"\n{GREEN}Dry run complete. Remove --dry-run to execute.{NC}")
        return

    # Step 3: Provision Lakebase
    log_step(3, TOTAL_STEPS, "Provisioning Lakebase instance")
    if args.skip_provision:
        log_info("Skipping provisioning (--skip-provision)")
        w = ctx["client"]
        inst = w.database.get_database_instance(cfg["instance_name"])
        instance_info = {"host": inst.read_write_dns, "uid": inst.uid, "name": inst.name}
    else:
        instance_info = provision_lakebase(ctx, cfg)

    # Step 4: Create database & schema & tables
    log_step(4, TOTAL_STEPS, "Creating database, schema, and tables")
    create_database_and_schema(ctx, instance_info, cfg)
    create_password_auth_role(ctx, instance_info, cfg)
    run_setup_sql(ctx, instance_info, cfg)

    # Step 5: Load pricing data
    log_step(5, TOTAL_STEPS, "Loading pricing reference data")
    load_pricing_data(ctx, instance_info, cfg)

    # Step 6: SKU discount mapping
    log_step(6, TOTAL_STEPS, "Creating SKU discount mapping")
    create_sku_discount_mapping(ctx, instance_info, cfg)

    # Step 7: Configure SP access
    log_step(7, TOTAL_STEPS, "Configuring Service Principal access")
    configure_sp_access(ctx, instance_info, cfg)

    # Step 8: Create views
    log_step(8, TOTAL_STEPS, "Creating cost calculation views")
    create_views(ctx, instance_info, cfg)

    # Step 9: Generate app.yaml + configure app resources
    log_step(9, TOTAL_STEPS, "Generating app configuration & resources")
    generate_app_config(ctx, instance_info, cfg)

    log_info("Configuring Databricks App resources (so valueFrom references resolve)...")
    configure_app_resources(ctx, instance_info, cfg)

    # Grant app SP access to Lakebase (so OAuth auth works)
    log_info("Granting app service principal Lakebase access...")
    w = ctx["client"]
    try:
        app_info = w.apps.get(cfg["app_name"])
        app_sp_id = app_info.service_principal_client_id
        if app_sp_id:
            import requests
            host = ctx["host"].rstrip("/")
            headers = w.config.authenticate()
            roles_url = f"{host}/api/2.0/database/instances/{instance_info['name']}/roles"

            # Check if role exists
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
            log_ok("App SP SQL permissions granted (tables, sequences, functions)")
    except Exception as e:
        log_warn(f"Could not configure app SP Lakebase access: {e}")
        log_info("App will use password-auth fallback (lakemeter_sync_role)")

    # Step 10: Deploy
    if not args.skip_deploy:
        log_step(10, TOTAL_STEPS, "Deploying application")
        deploy_app(ctx, cfg)
    else:
        log_step(10, TOTAL_STEPS, "Deploying application")
        log_info("Skipping deployment (--skip-deploy)")

    # Summary
    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{GREEN}{BOLD}  Installation Complete!{NC}")
    print(f"{BOLD}{'='*60}{NC}")
    print(f"\n  Instance:  {CYAN}{instance_info['name']}{NC}")
    print(f"  Database:  {CYAN}{cfg['db_name']}{NC}")
    print(f"  DB Host:   {CYAN}{instance_info['host']}{NC}")
    print(f"  App Name:  {CYAN}{cfg['app_name']}{NC}")
    print(f"\n  Next steps:")
    print(f"  1. Verify the app is running:")
    print(f"     databricks apps get {cfg['app_name']} --profile {args.profile}")
    print(f"  2. Run permission tests:")
    print(f"     pytest tests/test_lakebase_permissions.py -v")
    print()


if __name__ == "__main__":
    main()
