# Databricks notebook source
# MAGIC %md
# MAGIC # Step 7: Verify Installation
# MAGIC Runs smoke tests against the deployed app to confirm everything works.
# MAGIC Tests: health, database, reference data, and cost calculations.

# COMMAND ----------

import time
_start = time.time()

dbutils.widgets.text("app_name", "lakemeter")
dbutils.widgets.text("instance_name", "lakemeter-customer")
dbutils.widgets.text("db_name", "lakemeter_pricing")

app_name = dbutils.widgets.get("app_name")
instance_name = dbutils.widgets.get("instance_name")
db_name = dbutils.widgets.get("db_name")

print(f"App: {app_name}")
print(f"Instance: {instance_name}")
print(f"Database: {db_name}")

# COMMAND ----------

import json
import requests
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
host = w.config.host.rstrip("/")
headers = w.config.authenticate()

# Get app URL
app_info = w.apps.get(app_name)
app_url = app_info.url
if not app_url:
    dbutils.notebook.exit("FAIL: App has no URL — deployment may not be complete")
app_url = app_url.rstrip("/")
print(f"App URL: {app_url}")

# Results tracker
results = []

def run_test(name, method, url, expected_status=200, json_body=None, check_fn=None, timeout=30):
    """Run a single test and record the result."""
    t0 = time.time()
    try:
        if method == "GET":
            resp = requests.get(url, timeout=timeout)
        else:
            resp = requests.post(url, json=json_body, timeout=timeout)
        elapsed = time.time() - t0

        if resp.status_code != expected_status:
            results.append({"test": name, "status": "FAIL", "elapsed": f"{elapsed:.1f}s",
                           "detail": f"HTTP {resp.status_code} (expected {expected_status})"})
            return None

        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else None

        if check_fn and data:
            ok, detail = check_fn(data)
            if not ok:
                results.append({"test": name, "status": "FAIL", "elapsed": f"{elapsed:.1f}s", "detail": detail})
                return data

        results.append({"test": name, "status": "PASS", "elapsed": f"{elapsed:.1f}s"})
        return data
    except Exception as e:
        elapsed = time.time() - t0
        results.append({"test": name, "status": "FAIL", "elapsed": f"{elapsed:.1f}s", "detail": str(e)[:200]})
        return None

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 1: Health & API Root

t0 = time.time()
print("Test 1: Health & API Root...")

run_test("health_check", "GET", f"{app_url}/health",
         check_fn=lambda d: (d.get("status") == "healthy", f"status={d.get('status')}"))

run_test("api_root", "GET", f"{app_url}/api",
         check_fn=lambda d: ("Lakemeter" in d.get("name", ""), f"name={d.get('name')}"))

print(f"  Done ({time.time() - t0:.1f}s)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 2: Database Connectivity

t0 = time.time()
print("Test 2: Database connectivity...")

run_test("database_debug", "GET", f"{app_url}/api/v1/debug/database",
         check_fn=lambda d: (d.get("database_query_status") == "SUCCESS" or d.get("db_connectable", False),
                            f"DB status: {d.get('database_query_status', d.get('db_connectable', 'unknown'))}"))

print(f"  Done ({time.time() - t0:.1f}s)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 3: Reference Data (clouds, regions, instances, warehouses)

t0 = time.time()
print("Test 3: Reference data endpoints...")

# Clouds & regions
run_test("clouds_regions", "GET", f"{app_url}/api/v1/reference/clouds-and-regions",
         check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("clouds", [])) >= 3,
                            f"clouds count: {len(d.get('data', {}).get('clouds', []))}"))

# Instance types for AWS
run_test("instance_types_aws", "GET", f"{app_url}/api/v1/reference/instance-types?cloud=AWS",
         check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("instance_types", [])) > 0,
                            f"instance count: {len(d.get('data', {}).get('instance_types', []))}"))

# DBSQL warehouse sizes
run_test("dbsql_warehouse_sizes", "GET", f"{app_url}/api/v1/reference/dbsql/warehouse-sizes?cloud=AWS",
         check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("warehouse_sizes", [])) > 0,
                            f"warehouse sizes: {len(d.get('data', {}).get('warehouse_sizes', []))}"))

# SKU types
run_test("sku_types", "GET", f"{app_url}/api/v1/reference/sku-types",
         check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("sku_types", [])) > 0,
                            f"sku count: {len(d.get('data', {}).get('sku_types', []))}"))

print(f"  Done ({time.time() - t0:.1f}s)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 4: Cost Calculations

t0 = time.time()
print("Test 4: Cost calculations...")

# Jobs Classic
run_test("calc_jobs_classic", "POST", f"{app_url}/api/v1/calculate/jobs-classic", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "driver_node_type": "i3.xlarge", "worker_node_type": "i3.xlarge", "num_workers": 2,
    "photon_enabled": False, "hours_per_month": 100,
    "driver_pricing_tier": "on_demand", "worker_pricing_tier": "on_demand",
}, check_fn=lambda d: (d.get("success") and d["data"]["total_cost"]["cost_per_month"] > 0,
                       f"cost={d.get('data', {}).get('total_cost', {}).get('cost_per_month', 0)}"))

# Jobs Serverless
run_test("calc_jobs_serverless", "POST", f"{app_url}/api/v1/calculate/jobs-serverless", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "driver_node_type": "i3.xlarge", "worker_node_type": "i3.xlarge", "num_workers": 2,
    "hours_per_month": 100,
}, check_fn=lambda d: (d.get("success") and d["data"]["total_cost"]["cost_per_month"] > 0,
                       f"cost={d.get('data', {}).get('total_cost', {}).get('cost_per_month', 0)}"))

# DBSQL Classic
run_test("calc_dbsql_classic", "POST", f"{app_url}/api/v1/calculate/dbsql-classic", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "warehouse_size": "Small", "num_clusters": 1, "hours_per_month": 100,
}, check_fn=lambda d: (d.get("success") and d["data"]["total_cost"]["cost_per_month"] > 0,
                       f"cost={d.get('data', {}).get('total_cost', {}).get('cost_per_month', 0)}"))

# DBSQL Serverless
run_test("calc_dbsql_serverless", "POST", f"{app_url}/api/v1/calculate/dbsql-serverless", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "warehouse_size": "Small", "hours_per_month": 100,
}, check_fn=lambda d: (d.get("success") and d["data"]["total_cost"]["cost_per_month"] > 0,
                       f"cost={d.get('data', {}).get('total_cost', {}).get('cost_per_month', 0)}"))

# All-Purpose Classic
run_test("calc_allpurpose_classic", "POST", f"{app_url}/api/v1/calculate/all-purpose-classic", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "driver_node_type": "i3.xlarge", "worker_node_type": "i3.xlarge", "num_workers": 2,
    "photon_enabled": False, "hours_per_month": 100,
    "driver_pricing_tier": "on_demand", "worker_pricing_tier": "on_demand",
}, check_fn=lambda d: (d.get("success") and d["data"]["total_cost"]["cost_per_month"] > 0,
                       f"cost={d.get('data', {}).get('total_cost', {}).get('cost_per_month', 0)}"))

# All-Purpose Serverless
run_test("calc_allpurpose_serverless", "POST", f"{app_url}/api/v1/calculate/all-purpose-serverless", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "driver_node_type": "i3.xlarge", "worker_node_type": "i3.xlarge", "num_workers": 2,
    "hours_per_month": 100,
}, check_fn=lambda d: (d.get("success") and d["data"]["total_cost"]["cost_per_month"] > 0,
                       f"cost={d.get('data', {}).get('total_cost', {}).get('cost_per_month', 0)}"))

# DLT Classic
run_test("calc_dlt_classic", "POST", f"{app_url}/api/v1/calculate/dlt-classic", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "dlt_edition": "CORE", "photon_enabled": False,
    "driver_node_type": "i3.xlarge", "worker_node_type": "i3.xlarge", "num_workers": 2,
    "hours_per_month": 100,
    "driver_pricing_tier": "on_demand", "worker_pricing_tier": "on_demand",
}, check_fn=lambda d: (d.get("success") and d["data"]["total_cost"]["cost_per_month"] > 0,
                       f"cost={d.get('data', {}).get('total_cost', {}).get('cost_per_month', 0)}"))

# DLT Serverless
run_test("calc_dlt_serverless", "POST", f"{app_url}/api/v1/calculate/dlt-serverless", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "driver_node_type": "i3.xlarge", "worker_node_type": "i3.xlarge", "num_workers": 2,
    "hours_per_month": 100,
}, check_fn=lambda d: (d.get("success") and d["data"]["total_cost"]["cost_per_month"] > 0,
                       f"cost={d.get('data', {}).get('total_cost', {}).get('cost_per_month', 0)}"))

# Model Serving
run_test("calc_model_serving", "POST", f"{app_url}/api/v1/calculate/model-serving", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "gpu_type": "GPU_SMALL", "num_gpus": 1, "hours_per_month": 100,
    "provisioned_throughput": False,
}, check_fn=lambda d: (d.get("success") and d["data"]["total_cost"]["cost_per_month"] > 0,
                       f"cost={d.get('data', {}).get('total_cost', {}).get('cost_per_month', 0)}"))

# Vector Search
run_test("calc_vector_search", "POST", f"{app_url}/api/v1/calculate/vector-search", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "endpoint_type": "starter", "hours_per_month": 730,
}, check_fn=lambda d: (d.get("success") and d["data"]["total_cost"]["cost_per_month"] > 0,
                       f"cost={d.get('data', {}).get('total_cost', {}).get('cost_per_month', 0)}"))

# FMAPI
run_test("calc_fmapi", "POST", f"{app_url}/api/v1/calculate/fmapi", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "provider_type": "databricks", "model_category": "general_purpose",
    "model_name": "llama-4-maverick",
    "input_tokens_per_month": 1000000, "output_tokens_per_month": 500000,
}, check_fn=lambda d: (d.get("success") and d["data"]["total_cost"]["cost_per_month"] > 0,
                       f"cost={d.get('data', {}).get('total_cost', {}).get('cost_per_month', 0)}"))

# Lakebase
run_test("calc_lakebase", "POST", f"{app_url}/api/v1/calculate/lakebase", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "cu_size": "CU_1", "hours_per_month": 730,
}, check_fn=lambda d: (d.get("success") and d["data"]["total_cost"]["cost_per_month"] > 0,
                       f"cost={d.get('data', {}).get('total_cost', {}).get('cost_per_month', 0)}"))

print(f"  Done ({time.time() - t0:.1f}s)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 5: Estimate CRUD + Excel Export

t0 = time.time()
print("Test 5: Estimate CRUD + Excel export...")

# Create estimate
est_data = run_test("create_estimate", "POST", f"{app_url}/api/v1/estimates/", json_body={
    "name": f"Installer Verification Test",
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
}, check_fn=lambda d: (d.get("success") and d.get("data", {}).get("id") is not None,
                       f"no estimate id"))

if est_data and est_data.get("success"):
    est_id = est_data["data"]["id"]

    # Add a line item
    run_test("add_line_item", "POST", f"{app_url}/api/v1/line-items/", json_body={
        "estimate_id": est_id,
        "workload_type": "jobs_classic",
        "name": "Test Workload",
        "configuration": {
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
            "driver_node_type": "i3.xlarge", "worker_node_type": "i3.xlarge",
            "num_workers": 2, "photon_enabled": False,
            "hours_per_month": 100,
            "driver_pricing_tier": "on_demand", "worker_pricing_tier": "on_demand",
        },
    }, check_fn=lambda d: (d.get("success"), f"add line item failed"))

    # Export Excel
    try:
        t_export = time.time()
        resp = requests.get(f"{app_url}/api/v1/export/estimate/{est_id}/excel", timeout=30)
        export_elapsed = time.time() - t_export
        if resp.status_code == 200 and len(resp.content) > 1000:
            results.append({"test": "excel_export", "status": "PASS", "elapsed": f"{export_elapsed:.1f}s",
                           "detail": f"{len(resp.content)} bytes"})
        else:
            results.append({"test": "excel_export", "status": "FAIL", "elapsed": f"{export_elapsed:.1f}s",
                           "detail": f"HTTP {resp.status_code}, size={len(resp.content)}"})
    except Exception as e:
        results.append({"test": "excel_export", "status": "FAIL", "elapsed": "0s", "detail": str(e)[:200]})

    # Delete estimate (cleanup)
    try:
        requests.delete(f"{app_url}/api/v1/estimates/{est_id}", timeout=10)
    except Exception:
        pass

print(f"  Done ({time.time() - t0:.1f}s)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Results Summary

elapsed = time.time() - _start
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
total = len(results)

print(f"\n{'='*60}")
print(f"VERIFICATION RESULTS ({elapsed:.1f}s)")
print(f"{'='*60}")
print(f"  Passed: {passed}/{total}")
print(f"  Failed: {failed}/{total}")
print(f"{'='*60}")

for r in results:
    icon = "PASS" if r["status"] == "PASS" else "FAIL"
    detail = f" — {r['detail']}" if r.get("detail") else ""
    print(f"  [{icon}] {r['test']:<30} {r['elapsed']:>6}{detail}")

print(f"{'='*60}")

# Set task values for CLI progress display
dbutils.jobs.taskValues.set(key="tests_passed", value=passed)
dbutils.jobs.taskValues.set(key="tests_failed", value=failed)
dbutils.jobs.taskValues.set(key="tests_total", value=total)

if failed > 0:
    failed_tests = [r["test"] for r in results if r["status"] == "FAIL"]
    dbutils.notebook.exit(f"FAIL: {failed}/{total} tests failed ({', '.join(failed_tests)}) ({elapsed:.1f}s)")
else:
    dbutils.notebook.exit(f"PASS: All {total} tests passed ({elapsed:.1f}s)")
