# Databricks notebook source
# MAGIC %md
# MAGIC # Step 5b: Grant App Service Principal Lakebase Access
# MAGIC Grants the app's SP a Lakebase role and SQL permissions.
# MAGIC Depends on: 01_provision_lakebase + 02_create_database + 05a_create_app

# COMMAND ----------

import time
_start = time.time()

dbutils.widgets.text("project_id", "lakemeter-customer")
dbutils.widgets.text("db_name", "lakemeter_pricing")
dbutils.widgets.text("app_name", "lakemeter")
dbutils.widgets.text("secrets_scope", "lakemeter-secrets")
dbutils.widgets.text("claude_endpoint", "databricks-claude-opus-4-6")

project_id = dbutils.widgets.get("project_id")
db_name = dbutils.widgets.get("db_name")
app_name = dbutils.widgets.get("app_name")
secrets_scope = dbutils.widgets.get("secrets_scope")
claude_endpoint = dbutils.widgets.get("claude_endpoint")

print(f"Project: {project_id}")
print(f"Database: {db_name}")
print(f"App: {app_name}")

# COMMAND ----------

import psycopg2
import requests
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.postgres import (
    Role,
    RoleAuthMethod,
    RoleIdentityType,
    RoleRoleSpec,
)

w = WorkspaceClient()
branch_name = dbutils.jobs.taskValues.get(
    taskKey="provision_lakebase",
    key="branch_name",
)
endpoint_name = dbutils.jobs.taskValues.get(
    taskKey="provision_lakebase",
    key="endpoint_name",
)
instance_host = dbutils.jobs.taskValues.get(
    taskKey="provision_lakebase",
    key="host",
)

# COMMAND ----------

# 1. Configure app resources after all database secrets exist.
t0 = time.time()
print("Step 1: Configuring app resources...")
resources = []
for name, secret_key, description in [
    ("lm-lakebase-project", "lakebase-project", "Lakebase project"),
    ("lm-lakebase-branch", "lakebase-branch", "Production branch"),
    ("lm-lakebase-endpoint", "lakebase-endpoint", "Primary endpoint"),
    ("lm-db-host", "lakebase-host", "Database host"),
    ("lm-db-user", "lakebase-user", "Database user"),
    ("lm-db-name", "lakebase-database", "Database name"),
]:
    resources.append(
        {
            "name": name,
            "description": description,
            "secret": {
                "scope": secrets_scope,
                "key": secret_key,
                "permission": "READ",
            },
        }
    )
resources.append(
    {
        "name": "lm-claude-endpoint",
        "description": "Claude model endpoint for AI Assistant",
        "serving_endpoint": {
            "name": claude_endpoint,
            "permission": "CAN_QUERY",
        },
    }
)
response = requests.patch(
    f"{w.config.host.rstrip('/')}/api/2.0/apps/{app_name}",
    headers=w.config.authenticate(),
    json={"resources": resources},
)
if response.status_code >= 300:
    raise RuntimeError(
        f"Failed to configure app resources: {response.status_code} "
        f"{response.text[:300]}"
    )
print(f"  App resources configured ({time.time() - t0:.1f}s)")

# COMMAND ----------

# 2. Get the app's Service Principal
t0 = time.time()
print("Step 2: Getting app service principal...")

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

# 3. Create Lakebase role for the app's SP
t0 = time.time()
print("Step 3: Creating Lakebase role for app SP...")

existing_roles = list(w.postgres.list_roles(parent=branch_name))
sp_role = next(
    (
        role
        for role in existing_roles
        if getattr(
            getattr(role, "spec", None) or getattr(role, "status", None),
            "postgres_role",
            None,
        )
        == app_sp_id
    ),
    None,
)

if not sp_role:
    role_id = f"{app_name.lower().replace('_', '-')}-app"
    w.postgres.create_role(
        parent=branch_name,
        role_id=role_id,
        role=Role(
            spec=RoleRoleSpec(
                auth_method=RoleAuthMethod.LAKEBASE_OAUTH_V1,
                identity_type=RoleIdentityType.SERVICE_PRINCIPAL,
                postgres_role=app_sp_id,
            )
        ),
    ).wait()
    print(f"  App SP Lakebase role created ({time.time() - t0:.1f}s)")
else:
    print(f"  App SP already has Lakebase role ({time.time() - t0:.1f}s)")

# COMMAND ----------

# 4. Grant SQL-level permissions
t0 = time.time()
print("Step 4: Granting SQL permissions to app SP...")

try:
    cred = w.postgres.generate_database_credential(endpoint=endpoint_name)
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
    cur.execute(
        f'ALTER DEFAULT PRIVILEGES IN SCHEMA lakemeter '
        f'GRANT ALL PRIVILEGES ON TABLES TO "{app_sp_id}"'
    )
    cur.execute(
        f'ALTER DEFAULT PRIVILEGES IN SCHEMA lakemeter '
        f'GRANT EXECUTE ON FUNCTIONS TO "{app_sp_id}"'
    )
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
