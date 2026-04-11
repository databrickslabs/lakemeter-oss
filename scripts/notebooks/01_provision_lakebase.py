# Databricks notebook source
# MAGIC %md
# MAGIC # Step 1: Provision Lakebase Instance
# MAGIC Creates or reuses a Lakebase (managed PostgreSQL) instance.
# MAGIC Outputs instance host/uid via task values for downstream notebooks.

# COMMAND ----------

import time as _time
_start = _time.time()

dbutils.widgets.text("instance_name", "lakemeter-customer")
instance_name = dbutils.widgets.get("instance_name")
print(f"Instance name: {instance_name}")

# COMMAND ----------

import time
import requests
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.database import DatabaseInstance

w = WorkspaceClient()
host = w.config.host.rstrip("/")

# COMMAND ----------

# Check if instance already exists
try:
    existing = w.database.get_database_instance(instance_name)
    print(f"Instance '{instance_name}' already exists (state={existing.state})")

    # Ensure pg_native_login is enabled
    if not existing.effective_enable_pg_native_login:
        try:
            w.database.update_database_instance(
                name=instance_name,
                database_instance=DatabaseInstance(name=instance_name, enable_pg_native_login=True),
                update_mask="enable_pg_native_login",
            )
            print("pg_native_login enabled on existing instance")
        except Exception as e:
            print(f"Warning: Could not enable pg_native_login: {e}")

    instance_host = existing.read_write_dns
    instance_uid = existing.uid

    # Set task values for downstream notebooks
    dbutils.jobs.taskValues.set(key="instance_host", value=instance_host)
    dbutils.jobs.taskValues.set(key="instance_uid", value=instance_uid)
    dbutils.jobs.taskValues.set(key="instance_name", value=existing.name)
    print(f"Instance AVAILABLE at {instance_host}")
    dbutils.notebook.exit(f"Reused existing instance: {instance_host} ({_time.time() - _start:.1f}s)")

except Exception:
    print(f"Instance '{instance_name}' not found — creating new one")

# COMMAND ----------

# Create new instance
print(f"Creating Lakebase instance '{instance_name}' (autoscaling 1-16 CU, scale-to-zero)...")
waiter = w.database.create_database_instance(
    database_instance=DatabaseInstance(
        name=instance_name,
        capacity="CU_1",
        stopped=False,
    ),
)
instance = waiter.response
print(f"Instance created: {instance.name} (uid={instance.uid})")

# COMMAND ----------

# Enable auto-scaling with scale-to-zero via REST API
try:
    headers = w.config.authenticate()
    resp = requests.patch(
        f"{host}/api/2.0/database/instances/{instance_name}",
        headers=headers,
        json={
            "name": instance_name,
            "enable_serverless_compute": True,
            "min_capacity": "CU_1",
            "max_capacity": "CU_16",
            "scale_to_zero": True,
        },
    )
    if resp.status_code < 300:
        print("Auto-scaling enabled (1-16 CU, scale-to-zero)")
    else:
        print(f"Warning: Could not enable auto-scaling: {resp.status_code} {resp.text[:200]}")
except Exception as e:
    print(f"Warning: Could not enable auto-scaling: {e}")

# Enable pg_native_login for password-based auth fallback
try:
    w.database.update_database_instance(
        name=instance_name,
        database_instance=DatabaseInstance(name=instance_name, enable_pg_native_login=True),
        update_mask="enable_pg_native_login",
    )
    print("pg_native_login enabled (password auth fallback)")
except Exception as e:
    print(f"Warning: Could not enable pg_native_login: {e}")

# COMMAND ----------

# Wait for AVAILABLE
print("Waiting for instance to become AVAILABLE...")
for i in range(120):  # 10 minutes max
    inst = w.database.get_database_instance(instance_name)
    state = str(inst.state)
    if "AVAILABLE" in state:
        print(f"Instance is AVAILABLE at {inst.read_write_dns}")
        dbutils.jobs.taskValues.set(key="instance_host", value=inst.read_write_dns)
        dbutils.jobs.taskValues.set(key="instance_uid", value=inst.uid)
        dbutils.jobs.taskValues.set(key="instance_name", value=inst.name)
        dbutils.notebook.exit(f"Created new instance: {inst.read_write_dns} ({_time.time() - _start:.1f}s)")
    if "FAILED" in state or "DELETED" in state:
        raise RuntimeError(f"Instance entered {state} state")
    if i % 10 == 0:
        print(f"  State: {state} (waiting...)")
    time.sleep(5)

raise RuntimeError("Timeout waiting for instance to become AVAILABLE (10 minutes)")
