# Databricks notebook source
# MAGIC %md
# MAGIC # Step 2b: Deploy Stored Functions
# MAGIC Reads function definition files from the DABs bundle, extracts SQL CREATE OR REPLACE
# MAGIC FUNCTION statements, and deploys them to the Lakebase database.

# COMMAND ----------

dbutils.widgets.text("instance_name", "lakemeter-customer")
dbutils.widgets.text("db_name", "lakemeter_pricing")

instance_name = dbutils.widgets.get("instance_name")
db_name = dbutils.widgets.get("db_name")

print(f"Instance: {instance_name}")
print(f"Database: {db_name}")

# COMMAND ----------

import os
import re
import uuid
import psycopg2
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Get Lakebase connection
instance = w.database.get_database_instance(instance_name)
instance_host = instance.read_write_dns
cred = w.database.generate_database_credential(
    request_id=str(uuid.uuid4()), instance_names=[instance_name]
)
owner_user = w.current_user.me().user_name

conn = psycopg2.connect(
    host=instance_host, port=5432, database=db_name,
    user=owner_user, password=cred.token, sslmode="require",
)
conn.autocommit = True
cur = conn.cursor()
print(f"Connected to {db_name}@{instance_host}")

# COMMAND ----------

# Resolve the DABs bundle path to the functions directory
nb_context = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
nb_path = nb_context.notebookPath().get()
if not nb_path.startswith("/Workspace"):
    nb_path = "/Workspace" + nb_path
bundle_files_dir = os.path.dirname(os.path.dirname(nb_path))
functions_dir = os.path.join(bundle_files_dir, "functions")

print(f"Functions directory: {functions_dir}")
assert os.path.isdir(functions_dir), f"Functions directory not found: {functions_dir}"

# Ordered list of function files
FUNCTION_FILES = [
    "01_Utility_Functions.py",
    "02_DBU_Calculators_Classic.py",
    "03_DBU_Calculators_Serverless.py",
    "04_DBU_Calculators_DBSQL.py",
    "05_DBU_Calculators_Vector_Model.py",
    "06_DBU_Calculators_FMAPI.py",
    "08_VM_Cost_Calculators.py",
    "09_Main_Orchestrator.py",
]

found = [f for f in FUNCTION_FILES if os.path.exists(os.path.join(functions_dir, f))]
print(f"Function files found: {len(found)}/{len(FUNCTION_FILES)}")
assert len(found) == len(FUNCTION_FILES), f"Missing function files: {set(FUNCTION_FILES) - set(found)}"

# COMMAND ----------

def extract_sql_functions(file_path):
    """Extract CREATE OR REPLACE FUNCTION and DO $$ blocks from a notebook file."""
    with open(file_path, "r") as f:
        content = f.read()

    sql_statements = []

    # Match triple-quoted strings assigned to known variable names
    triple_quote_pattern = re.compile(
        r'(?:create_function_sql|drop_sql|create_vm_function_sql|create_orchestrator_sql)\s*=\s*"""(.*?)"""',
        re.DOTALL
    )
    matches = triple_quote_pattern.findall(content)

    for match in matches:
        stripped = match.strip()
        if stripped and ("CREATE OR REPLACE FUNCTION" in stripped.upper() or "DO $$" in stripped):
            sql_statements.append(stripped)

    return sql_statements

# COMMAND ----------

# Deploy all functions in order
print("Deploying stored functions...")
total_deployed = 0
total_errors = 0

for filename in FUNCTION_FILES:
    filepath = os.path.join(functions_dir, filename)
    sql_statements = extract_sql_functions(filepath)

    if not sql_statements:
        print(f"  SKIP {filename} (no SQL found)")
        continue

    for i, sql in enumerate(sql_statements):
        func_match = re.search(
            r'(?:CREATE OR REPLACE FUNCTION|DO)\s+(?:lakemeter\.)?(\w+)?',
            sql, re.IGNORECASE
        )
        func_name = func_match.group(1) if func_match and func_match.group(1) else f"statement_{i+1}"

        try:
            cur.execute(sql)
            print(f"  OK: {func_name} ({filename})")
            total_deployed += 1
        except Exception as e:
            print(f"  FAIL: {func_name} ({filename}): {str(e)[:150]}")
            total_errors += 1

# Deploy the lakebase DBU function (not in any file)
lakebase_dbu_sql = """
CREATE OR REPLACE FUNCTION lakemeter.calculate_lakebase_dbu(
    p_lakebase_cu INT DEFAULT 0,
    p_lakebase_ha_nodes INT DEFAULT 1
)
RETURNS DECIMAL(18,4)
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    RETURN (COALESCE(p_lakebase_cu, 0) * COALESCE(p_lakebase_ha_nodes, 1))::DECIMAL(18,4);
END;
$$;
"""
try:
    cur.execute(lakebase_dbu_sql)
    print("  OK: calculate_lakebase_dbu (inline)")
    total_deployed += 1
except Exception as e:
    print(f"  FAIL: calculate_lakebase_dbu: {e}")
    total_errors += 1

print(f"\nDeployed {total_deployed} functions, {total_errors} errors")

# COMMAND ----------

# Verification
print("=== Verification ===")

# List all functions
cur.execute("""
    SELECT p.proname
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'lakemeter'
      AND (p.proname LIKE 'calculate_%' OR p.proname LIKE 'get_%')
    ORDER BY p.proname
""")
functions = [r[0] for r in cur.fetchall()]
print(f"Functions in lakemeter schema: {len(functions)}")
for f in functions:
    print(f"  - {f}")

# Quick smoke test
try:
    cur.execute("SELECT lakemeter.calculate_hours_per_month('JOBS', 5, 30, 22, NULL, NULL)")
    result = cur.fetchone()[0]
    print(f"\nSmoke test: calculate_hours_per_month('JOBS', 5, 30, 22, NULL, NULL) = {result}")
except Exception as e:
    print(f"\nSmoke test failed: {e}")

try:
    cur.execute("SELECT lakemeter.calculate_lakebase_dbu(4, 2)")
    result = cur.fetchone()[0]
    print(f"Smoke test: calculate_lakebase_dbu(4, 2) = {result}")
except Exception as e:
    print(f"Smoke test failed: {e}")

cur.close()
conn.close()

print(f"\nStored functions deployment complete ({total_deployed} deployed, {total_errors} errors)")
if total_errors > 0:
    dbutils.notebook.exit(f"Deployed with {total_errors} errors")
else:
    dbutils.notebook.exit(f"All {total_deployed} functions deployed successfully")
