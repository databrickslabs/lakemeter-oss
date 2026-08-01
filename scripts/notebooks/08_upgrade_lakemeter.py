# Databricks notebook source
"""Run a planned Lakemeter status, upgrade, or rollback operation."""

# COMMAND ----------

dbutils.widgets.dropdown(
    "command",
    "plan",
    ["status", "plan", "doctor", "apply", "rollback"],
)
dbutils.widgets.text("app_name", "lakemeter")

command = dbutils.widgets.get("command")
app_name = dbutils.widgets.get("app_name")

# COMMAND ----------

import json
import os
import sys
from pathlib import Path

from databricks.sdk import WorkspaceClient

notebook_context = (
    dbutils.notebook.entry_point.getDbutils().notebook().getContext()
)
notebook_path = notebook_context.notebookPath().get()
if not notebook_path.startswith("/Workspace"):
    notebook_path = f"/Workspace{notebook_path}"

bundle_root = Path(os.path.dirname(os.path.dirname(notebook_path)))
sys.path.insert(0, str(bundle_root))

from upgrader.runner import run_command

# COMMAND ----------

print(f"Lakemeter upgrade command: {command}")
print(f"App: {app_name}")
print(f"Payload: {bundle_root / 'upgrade_payload'}")

result = run_command(
    workspace_client=WorkspaceClient(),
    command=command,
    app_name=app_name,
    payload_root=bundle_root / "upgrade_payload",
)

rendered = json.dumps(result, indent=2, sort_keys=True)
print(rendered)
dbutils.notebook.exit(rendered)

