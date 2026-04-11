# Databricks notebook source
# MAGIC %md
# MAGIC # Step 5b: Grant App Service Principal Lakebase Access
# MAGIC Grants the app's SP a Lakebase role and SQL permissions.
# MAGIC Depends on: 01_provision_lakebase + 02_create_database + 05a_create_app

# COMMAND ----------

import time
_start = time.time()

dbutils.widgets.text("instance_name", "lakemeter-customer")
dbutils.widgets.text("db_name", "lakemeter_pricing")
dbutils.widgets.text("app_name", "lakemeter")

instance_name = dbutils.widgets.get("instance_name")
db_name = dbutils.widgets.get("db_name")
app_name = dbutils.widgets.get("app_name")

print(f"Instance: {instance_name}")
print(f"Database: {db_name}")
print(f"App: {app_name}")

# COMMAND ----------

import uuid
import requests
import psycopg2
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
host = w.config.host.rstrip("/")
headers = w.config.authenticate()

# COMMAND ----------

# 1. Get the app's Service Principal
t0 = time.time()
print("Step 1: Getting app service principal...")

try:
    app_info = w.apps.get(app_name)
    app_sp_id = app_info.service_principal_client_id
    if not app_sp_id:
        print("  Warning: App has no service principal — Lakebase OAuth will not work")
        print("  App will use password-auth fallback (lakemeter_sync_role)")
        dbutils.notebook.exit("No SP — password auth fallback")
    print(f"  App SP: {app_sp_id[:16]}... ({time.time() - t0:.1f}s)")
except Exception as e:
    print(f"  Error getting app info: {e}")
    dbutils.notebook.exit(f"Error: {str(e)[:200]}")

# COMMAND ----------

# 2. Create Lakebase role for the app's SP
t0 = time.time()
print("Step 2: Creating Lakebase role for app SP...")

roles_url = f"{host}/api/2.0/database/instances/{instance_name}/roles"
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
        print(f"  App SP Lakebase role created ({time.time() - t0:.1f}s)")
    else:
        print(f"  Warning: Could not create app SP role: {resp.status_code} {resp.text[:200]}")
else:
    print(f"  App SP already has Lakebase role ({time.time() - t0:.1f}s)")

# COMMAND ----------

# 3. Grant SQL-level permissions
t0 = time.time()
print("Step 3: Granting SQL permissions to app SP...")

try:
    instance = w.database.get_database_instance(instance_name)
    instance_host = instance.read_write_dns
    cred = w.database.generate_database_credential(request_id=str(uuid.uuid4()), instance_names=[instance_name])
    owner_user = w.current_user.me().user_name

    conn = psycopg2.connect(
        host=instance_host, port=5432, database=db_name,
        user=owner_user, password=cred.token, sslmode="require",
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f'GRANT CONNECT ON DATABASE {db_name} TO "{app_sp_id}"')
    cur.execute(f'GRANT USAGE ON SCHEMA lakemeter TO "{app_sp_id}"')
    cur.execute(f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA lakemeter TO "{app_sp_id}"')
    cur.execute(f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA lakemeter TO "{app_sp_id}"')
    cur.execute(f'GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA lakemeter TO "{app_sp_id}"')
    cur.close()
    conn.close()
    print(f"  SQL permissions granted ({time.time() - t0:.1f}s)")
except Exception as e:
    print(f"  Warning: Could not grant SQL permissions: {e}")
    print("  App will use password-auth fallback (lakemeter_sync_role)")

# COMMAND ----------

elapsed = time.time() - _start
print(f"\nApp SP access configuration complete ({elapsed:.1f}s)")
dbutils.notebook.exit(f"App SP access granted ({elapsed:.1f}s)")
