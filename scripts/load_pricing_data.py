# Databricks notebook source
# MAGIC %md
# MAGIC # Load Pricing Data into Lakebase
# MAGIC Reads pre-flattened CSV files from workspace and bulk-loads into Lakebase sync tables.
# MAGIC Run on serverless compute.

# COMMAND ----------

# MAGIC %pip install psycopg2-binary
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

import csv
import io
import os
import psycopg2
import psycopg2.extras

# Patched by installer before upload
SECRET_SCOPE = "lakemeter-secrets"
PRICING_DIR = "/Workspace/Users/placeholder/lakemeter/pricing_data"

# COMMAND ----------

# Read Lakebase credentials from secrets
host = dbutils.secrets.get(scope=SECRET_SCOPE, key="lakebase-host")
user = dbutils.secrets.get(scope=SECRET_SCOPE, key="lakebase-user")
password = dbutils.secrets.get(scope=SECRET_SCOPE, key="lakebase-password")
database = dbutils.secrets.get(scope=SECRET_SCOPE, key="lakebase-database")

conn = psycopg2.connect(
    host=host, port=5432, database=database,
    user=user, password=password, sslmode="require"
)
conn.autocommit = True
cur = conn.cursor()
print(f"Connected to Lakebase: {database}@{host}")

# COMMAND ----------

# CSV -> table mapping with column definitions
# Each entry: (csv_filename, target_table, columns)
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

# Type casting: columns that need special handling
FLOAT_COLS = {"price_per_dbu", "vcpus", "memory_gb", "dbu_rate", "dbu_per_hour",
              "cost_per_hour", "multiplier"}
BOOL_COLS = {"is_active", "includes_compute", "is_hourly"}


def cast_value(col, val):
    """Cast CSV string value to appropriate Python type."""
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
    """Find the CSV file(s) — handles split files (e.g., vm-costs_part1.csv, vm-costs_part2.csv)."""
    filepath = os.path.join(PRICING_DIR, csv_filename)
    if os.path.exists(filepath):
        return [filepath]
    # Check for split parts: stem_part1.csv, stem_part2.csv, ...
    stem = csv_filename.rsplit(".", 1)[0]
    parts = []
    for i in range(1, 100):
        part_path = os.path.join(PRICING_DIR, f"{stem}_part{i}.csv")
        if os.path.exists(part_path):
            parts.append(part_path)
        else:
            break
    return parts


def load_csv(csv_filename, table, columns):
    """Load a single CSV file (or its split parts) into a Lakebase table."""
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

    # TRUNCATE + bulk INSERT
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

# Populate derived reference tables from main rate tables
print("Populating derived reference tables...")

# ref_model_serving_gpu_types
cur.execute("TRUNCATE TABLE lakemeter.ref_model_serving_gpu_types")
cur.execute("""
    INSERT INTO lakemeter.ref_model_serving_gpu_types (cloud, gpu_type, description, is_active)
    SELECT DISTINCT cloud, size_or_model, '', TRUE
    FROM lakemeter.sync_product_serverless_rates
    WHERE product = 'model_serving' AND LOWER(size_or_model) LIKE '%gpu%'
""")
print(f"  ref_model_serving_gpu_types: {cur.rowcount} rows")

# ref_fmapi_databricks_models
cur.execute("TRUNCATE TABLE lakemeter.ref_fmapi_databricks_models")
cur.execute("""
    INSERT INTO lakemeter.ref_fmapi_databricks_models (model_name, description, is_active)
    SELECT DISTINCT model, '', TRUE
    FROM lakemeter.sync_product_fmapi_databricks
""")
print(f"  ref_fmapi_databricks_models: {cur.rowcount} rows")

# ref_fmapi_proprietary_models
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
print("\nDone.")
