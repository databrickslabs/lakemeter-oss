# Databricks notebook source
# MAGIC %md
# MAGIC # Step 1: Provision Lakebase Autoscaling
# MAGIC Creates or reuses a direct project with its production branch and endpoint.
# MAGIC Outputs resource names and host via task values for downstream notebooks.

# COMMAND ----------

import time
_start = time.time()

dbutils.widgets.text("project_id", "lakemeter-customer")
project_id = dbutils.widgets.get("project_id")
print(f"Project ID: {project_id}")

# COMMAND ----------

import os
import sys
from pathlib import Path
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

notebook_context = (
    dbutils.notebook.entry_point.getDbutils().notebook().getContext()
)
notebook_path = notebook_context.notebookPath().get()
if not notebook_path.startswith("/Workspace"):
    notebook_path = f"/Workspace{notebook_path}"
bundle_root = Path(os.path.dirname(os.path.dirname(notebook_path)))
sys.path.insert(0, str(bundle_root))

from lakebase_autoscaling import ensure_autoscaling_project

resources, created = ensure_autoscaling_project(
    w,
    project_id,
    display_name=f"Lakemeter — {project_id}",
    min_cu=1.0,
    max_cu=16.0,
    suspend_after_seconds=300,
)

for key, value in resources.as_dict().items():
    if value is not None:
        dbutils.jobs.taskValues.set(key=key, value=value)

action = "Created" if created else "Reused"
elapsed = time.time() - _start
print(f"{action} {resources.project_name}")
print(f"Production branch: {resources.branch_name}")
print(f"Primary endpoint: {resources.endpoint_name}")
print(f"Host: {resources.host}")
dbutils.notebook.exit(
    f"{action} direct Autoscaling project in {elapsed:.1f}s"
)
