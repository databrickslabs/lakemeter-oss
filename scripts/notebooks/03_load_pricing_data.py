# Databricks notebook source
# MAGIC %md
# MAGIC # Step 3: Load Pricing Data into Lakebase
# MAGIC Creates sync tables, reads CSV files from DABs bundle path, and bulk-loads into Lakebase.
# MAGIC Runs on serverless compute (environment v5 — psycopg2 pre-installed).

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

import csv
import io
import os
import psycopg2
import psycopg2.extras
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# COMMAND ----------

# Get Lakebase connection via owner credentials (OAuth)
instance = w.database.get_database_instance(instance_name)
instance_host = instance.read_write_dns
import uuid
cred = w.database.generate_database_credential(request_id=str(uuid.uuid4()), instance_names=[instance_name])
owner_user = w.current_user.me().user_name

conn = psycopg2.connect(
    host=instance_host,
    port=5432,
    database=db_name,
    user=owner_user,
    password=cred.token,
    sslmode="require",
)
conn.autocommit = True
cur = conn.cursor()
print(f"Connected to Lakebase: {db_name}@{instance_host}")

# COMMAND ----------

# Create sync tables
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
print("Sync tables ready")

# COMMAND ----------

# Resolve the DABs bundle files path for pricing_data/
# DABs syncs to: /Workspace/Users/{user}/.bundle/{bundle}/{target}/files/
# This notebook runs from .../files/notebooks/03_load_pricing_data
nb_context = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
nb_path = nb_context.notebookPath().get()
# notebookPath returns /Users/... but filesystem needs /Workspace/Users/...
if not nb_path.startswith("/Workspace"):
    nb_path = "/Workspace" + nb_path
# Go up from notebooks/ to files/, then into pricing_data/
bundle_files_dir = os.path.dirname(os.path.dirname(nb_path))
pricing_dir = os.path.join(bundle_files_dir, "pricing_data")

# Verify CSVs exist
csv_count = len([f for f in os.listdir(pricing_dir) if f.endswith(".csv")]) if os.path.isdir(pricing_dir) else 0
print(f"Pricing data directory: {pricing_dir}")
print(f"CSV files found: {csv_count}")
assert csv_count > 0, f"No CSV files found in {pricing_dir}"

# COMMAND ----------

# CSV -> table mapping
LOAD_MAP = [
    ("dbu-rates.csv", "sync_pricing_dbu_rates", [
        "sku_name", "cloud", "tier", "product_type", "sku_region", "region",
        "usage_unit", "price_per_dbu", "currency_code", "pricing_type", "fetched_at"
    ]),
    ("instance-dbu-rates.csv", "sync_ref_instance_dbu_rates", [
        "cloud", "instance_type", "vcpus", "memory_gb", "dbu_rate",
        "instance_family", "is_active", "source"
    ]),
    ("dbu-multipliers.csv", "sync_ref_dbu_multipliers", [
        "cloud", "sku_type", "feature", "multiplier", "category"
    ]),
    ("dbsql-rates.csv", "sync_product_dbsql_rates", [
        "cloud", "warehouse_type", "warehouse_size", "sku_product_type",
        "dbu_per_hour", "includes_compute"
    ]),
    ("dbsql-warehouse-config.csv", "sync_ref_dbsql_warehouse_config", [
        "cloud", "warehouse_size", "worker_count", "driver_instance_type",
        "worker_instance_type", "warehouse_type"
    ]),
    ("serverless-rates.csv", "sync_product_serverless_rates", [
        "cloud", "product", "size_or_model", "rate_type", "dbu_rate",
        "input_divisor", "is_hourly", "sku_product_type", "description"
    ]),
    ("fmapi-databricks-rates.csv", "sync_product_fmapi_databricks", [
        "cloud", "model", "rate_type", "dbu_rate", "input_divisor",
        "is_hourly", "sku_product_type"
    ]),
    ("fmapi-proprietary-rates.csv", "sync_product_fmapi_proprietary", [
        "provider", "model", "endpoint_type", "context_length", "rate_type",
        "dbu_rate", "input_divisor", "is_hourly", "sku_product_type", "cloud"
    ]),
    ("vm-costs.csv", "sync_pricing_vm_costs", [
        "cloud", "region", "instance_type", "pricing_tier", "payment_option",
        "cost_per_hour", "currency", "source", "fetched_at"
    ]),
    ("sku-region-map.csv", "sync_ref_sku_region_map", [
        "cloud", "sku_region", "region_code"
    ]),
]

# Type casting
FLOAT_COLS = {"price_per_dbu", "vcpus", "memory_gb", "dbu_rate", "dbu_per_hour",
              "cost_per_hour", "multiplier"}
BOOL_COLS = {"is_active", "includes_compute", "is_hourly"}


def cast_value(col, val):
    if val == "" or val is None:
        if col in FLOAT_COLS:
            return 0.0
        if col in BOOL_COLS:
            return False
        return ""
    if col in FLOAT_COLS:
        return float(val)
    if col in BOOL_COLS:
        return val.lower() in ("true", "1", "yes")
    return val


def find_csv_files(csv_filename):
    filepath = os.path.join(pricing_dir, csv_filename)
    if os.path.exists(filepath):
        return [filepath]
    # Check for split parts (e.g., vm-costs_part1.csv)
    stem = csv_filename.rsplit(".", 1)[0]
    parts = []
    for i in range(1, 100):
        part_path = os.path.join(pricing_dir, f"{stem}_part{i}.csv")
        if os.path.exists(part_path):
            parts.append(part_path)
        else:
            break
    return parts


def load_csv(csv_filename, table, columns):
    filepaths = find_csv_files(csv_filename)
    if not filepaths:
        print(f"  SKIP {csv_filename} (not found)")
        return 0
    rows = []
    for fp in filepaths:
        with open(fp, "r") as f:
            reader = csv.DictReader(f)
            rows.extend(
                tuple(cast_value(col, row.get(col, "")) for col in columns)
                for row in reader
            )
    if not rows:
        print(f"  SKIP {csv_filename} (empty)")
        return 0
    cur.execute(f"TRUNCATE TABLE lakemeter.{table}")
    cols_str = ", ".join(columns)
    tmpl = "(" + ", ".join(["%s"] * len(columns)) + ")"
    sql = f"INSERT INTO lakemeter.{table} ({cols_str}) VALUES %s"
    psycopg2.extras.execute_values(cur, sql, rows, template=tmpl, page_size=2000)
    parts_note = f" ({len(filepaths)} parts)" if len(filepaths) > 1 else ""
    print(f"  {csv_filename} -> {table}: {len(rows)} rows{parts_note}")
    return len(rows)

# COMMAND ----------

# Load all CSV files
print("Loading pricing data into Lakebase...")
total = 0
for csv_file, table, cols in LOAD_MAP:
    total += load_csv(csv_file, table, cols)

print(f"\nLoaded {total} rows across {len(LOAD_MAP)} tables")

# COMMAND ----------

# Populate derived reference tables
print("Populating derived reference tables...")

cur.execute("TRUNCATE TABLE lakemeter.ref_model_serving_gpu_types")
cur.execute("""
    INSERT INTO lakemeter.ref_model_serving_gpu_types (cloud, gpu_type, description, is_active)
    SELECT DISTINCT cloud, size_or_model, '', TRUE
    FROM lakemeter.sync_product_serverless_rates
    WHERE product = 'model_serving' AND LOWER(size_or_model) LIKE '%gpu%'
""")
print(f"  ref_model_serving_gpu_types: {cur.rowcount} rows")

cur.execute("TRUNCATE TABLE lakemeter.ref_fmapi_databricks_models")
cur.execute("""
    INSERT INTO lakemeter.ref_fmapi_databricks_models (model_name, description, is_active)
    SELECT DISTINCT model, '', TRUE
    FROM lakemeter.sync_product_fmapi_databricks
""")
print(f"  ref_fmapi_databricks_models: {cur.rowcount} rows")

cur.execute("TRUNCATE TABLE lakemeter.ref_fmapi_proprietary_models")
cur.execute("""
    INSERT INTO lakemeter.ref_fmapi_proprietary_models (provider, model_name, description, is_active)
    SELECT DISTINCT provider, model, '', TRUE
    FROM lakemeter.sync_product_fmapi_proprietary
""")
print(f"  ref_fmapi_proprietary_models: {cur.rowcount} rows")

# COMMAND ----------

# Verify row counts
print("\n=== Verification ===")
tables = [t for _, t, _ in LOAD_MAP] + [
    "ref_model_serving_gpu_types",
    "ref_fmapi_databricks_models",
    "ref_fmapi_proprietary_models",
]
for table in tables:
    cur.execute(f"SELECT COUNT(*) FROM lakemeter.{table}")
    count = cur.fetchone()[0]
    print(f"  {table}: {count}")

cur.close()
conn.close()
print("\nPricing data load complete.")
