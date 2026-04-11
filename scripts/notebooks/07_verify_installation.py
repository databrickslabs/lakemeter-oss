# Databricks notebook source
# MAGIC %md
# MAGIC # Step 7: Verify Installation
# MAGIC Runs smoke tests against the deployed app to confirm everything works.
# MAGIC Tests: health, database, reference data (all clouds), cost calculations, AI assistant, Excel export.

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

# Get app URL
app_info = w.apps.get(app_name)
app_url = app_info.url
if not app_url:
    dbutils.notebook.exit("FAIL: App has no URL — deployment may not be complete")
app_url = app_url.rstrip("/")
print(f"App URL: {app_url}")

# Results tracker
results = []
section_times = {}

def run_test(name, method, url, expected_status=200, json_body=None, check_fn=None, timeout=30):
    """Run a single test and record the result."""
    t0 = time.time()
    try:
        if method == "GET":
            resp = requests.get(url, timeout=timeout)
        elif method == "POST":
            resp = requests.post(url, json=json_body, timeout=timeout)
        elif method == "DELETE":
            resp = requests.delete(url, timeout=timeout)
        else:
            raise ValueError(f"Unknown method: {method}")
        elapsed = time.time() - t0

        if resp.status_code != expected_status:
            results.append({"test": name, "status": "FAIL", "elapsed": f"{elapsed:.1f}s",
                           "detail": f"HTTP {resp.status_code} (expected {expected_status})"})
            return None

        ct = resp.headers.get("content-type", "")
        data = resp.json() if "json" in ct else None

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

def success_with_data(key, min_count=1):
    """Return a check_fn that verifies success=True and data[key] has items."""
    def check(d):
        items = d.get("data", {}).get(key, [])
        ok = d.get("success") and len(items) >= min_count
        return (ok, f"{key}: {len(items)} (need >={min_count})")
    return check

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 1: Health & API Root

t0 = time.time()
print("Test 1: Health & API Root...")

run_test("health_check", "GET", f"{app_url}/health",
         check_fn=lambda d: (d.get("status") == "healthy", f"status={d.get('status')}"))

run_test("api_root", "GET", f"{app_url}/api",
         check_fn=lambda d: ("Lakemeter" in d.get("name", ""), f"name={d.get('name')}"))

section_times["health"] = time.time() - t0
print(f"  Done ({section_times['health']:.1f}s)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 2: Database Connectivity

t0 = time.time()
print("Test 2: Database connectivity...")

run_test("database_debug", "GET", f"{app_url}/api/v1/debug/database",
         check_fn=lambda d: (d.get("database_query_status") == "SUCCESS" or d.get("db_connectable", False),
                            f"DB status: {d.get('database_query_status', d.get('db_connectable', 'unknown'))}"))

section_times["database"] = time.time() - t0
print(f"  Done ({section_times['database']:.1f}s)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 3: Reference Data — All Clouds

t0 = time.time()
print("Test 3: Reference data across all clouds...")

# Cloud/region combos to test
CLOUDS = {
    "AWS": "us-east-1",
    "AZURE": "eastus",
    "GCP": "us-central1",
}

# -- Clouds & regions (global) --
run_test("ref_regions_all", "GET", f"{app_url}/api/v1/reference/regions",
         check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("regions", [])) > 0,
                            f"regions: {len(d.get('data', {}).get('regions', []))}"))

# -- Per-cloud: regions --
for cloud in CLOUDS:
    run_test(f"ref_regions_{cloud.lower()}", "GET",
             f"{app_url}/api/v1/reference/regions?cloud={cloud}",
             check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("regions", [])) > 0,
                                f"regions: {len(d.get('data', {}).get('regions', []))}"))

# -- Per-cloud: tiers --
for cloud in CLOUDS:
    run_test(f"ref_tiers_{cloud.lower()}", "GET",
             f"{app_url}/api/v1/reference/tiers?cloud={cloud}",
             check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("tiers", [])) > 0,
                                f"tiers: {len(d.get('data', {}).get('tiers', []))}"))

# -- Per-cloud+region: instance types --
for cloud, region in CLOUDS.items():
    run_test(f"ref_instances_{cloud.lower()}", "GET",
             f"{app_url}/api/v1/reference/instances/types?cloud={cloud}&region={region}&limit=5",
             check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("instance_types", [])) > 0,
                                f"instances: {len(d.get('data', {}).get('instance_types', []))}"))

# -- Per-cloud: VM costs (spot check one instance per cloud) --
VM_SPOT_CHECKS = {
    "AWS": ("us-east-1", "i3.xlarge"),
    "AZURE": ("eastus", "Standard_DS3_v2"),
    "GCP": ("us-central1", "n1-standard-4"),
}
for cloud, (region, inst) in VM_SPOT_CHECKS.items():
    run_test(f"ref_vm_costs_{cloud.lower()}", "GET",
             f"{app_url}/api/v1/reference/instances/vm-costs?cloud={cloud}&region={region}&instance_type={inst}",
             check_fn=lambda d: (d.get("success"), f"vm cost lookup failed"))

# -- Per-cloud: DBSQL warehouse sizes --
for cloud in CLOUDS:
    run_test(f"ref_dbsql_sizes_{cloud.lower()}", "GET",
             f"{app_url}/api/v1/reference/dbsql/warehouse-sizes?cloud={cloud}",
             check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("warehouse_sizes", [])) > 0,
                                f"warehouse_sizes: {len(d.get('data', {}).get('warehouse_sizes', []))}"))

# -- Per-cloud: DBSQL warehouse VM costs --
for cloud, region in CLOUDS.items():
    run_test(f"ref_dbsql_vm_{cloud.lower()}", "GET",
             f"{app_url}/api/v1/reference/dbsql/warehouse-vm-costs?cloud={cloud}&region={region}&warehouse_type=CLASSIC&warehouse_size=Small",
             check_fn=lambda d: (d.get("success"), f"dbsql vm cost lookup failed"))

# -- Per-cloud: pricing product types --
for cloud, region in CLOUDS.items():
    run_test(f"ref_pricing_types_{cloud.lower()}", "GET",
             f"{app_url}/api/v1/reference/pricing/product-types?cloud={cloud}&region={region}&tier=PREMIUM",
             check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("product_types", [])) > 0,
                                f"product_types: {len(d.get('data', {}).get('product_types', []))}"))

# -- Per-cloud: DBU rates --
for cloud, region in CLOUDS.items():
    run_test(f"ref_dbu_rates_{cloud.lower()}", "GET",
             f"{app_url}/api/v1/reference/pricing/dbu-rates?cloud={cloud}&region={region}&tier=PREMIUM",
             check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("dbu_rates", [])) > 0,
                                f"dbu_rates: {len(d.get('data', {}).get('dbu_rates', []))}"))

# -- Per-cloud: Model Serving GPU types --
for cloud in CLOUDS:
    run_test(f"ref_gpu_types_{cloud.lower()}", "GET",
             f"{app_url}/api/v1/reference/model-serving/gpu-types?cloud={cloud}",
             check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("gpu_types", [])) > 0,
                                f"gpu_types: {len(d.get('data', {}).get('gpu_types', []))}"))

# -- Per-cloud: Vector Search modes --
for cloud in CLOUDS:
    run_test(f"ref_vs_modes_{cloud.lower()}", "GET",
             f"{app_url}/api/v1/reference/vector-search/modes?cloud={cloud}",
             check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("modes", [])) > 0,
                                f"modes: {len(d.get('data', {}).get('modes', []))}"))

# -- Per-cloud: Photon multipliers --
for cloud in CLOUDS:
    run_test(f"ref_photon_{cloud.lower()}", "GET",
             f"{app_url}/api/v1/reference/photon/multipliers?cloud={cloud}",
             check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("multipliers", [])) > 0,
                                f"multipliers: {len(d.get('data', {}).get('multipliers', []))}"))

# -- Global: Lakebase CU sizes --
run_test("ref_lakebase_sizes", "GET", f"{app_url}/api/v1/reference/lakebase/list",
         check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("cu_sizes", d.get("data", {}).get("sizes", []))) > 0,
                            f"lakebase sizes missing"))

# -- Global: DLT editions --
run_test("ref_dlt_editions", "GET", f"{app_url}/api/v1/reference/dlt/editions",
         check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("editions", [])) >= 3,
                            f"editions: {len(d.get('data', {}).get('editions', []))}"))

# -- Global: Serverless modes --
run_test("ref_serverless_modes", "GET", f"{app_url}/api/v1/reference/serverless/modes",
         check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("modes", [])) >= 2,
                            f"modes: {len(d.get('data', {}).get('modes', []))}"))

# -- Global: VM pricing options --
run_test("ref_vm_pricing_opts", "GET", f"{app_url}/api/v1/reference/instances/vm-pricing-options",
         check_fn=lambda d: (d.get("success"), "vm pricing options failed"))

# -- Global: SKU types --
run_test("ref_sku_types", "GET", f"{app_url}/api/v1/reference/sku-types",
         check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("sku_types", [])) > 0,
                            f"sku_types: {len(d.get('data', {}).get('sku_types', []))}"))

# -- FMAPI: Databricks models --
run_test("ref_fmapi_db_models", "GET", f"{app_url}/api/v1/reference/fmapi/databricks-models/list",
         check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("models", [])) > 0,
                            f"models: {len(d.get('data', {}).get('models', []))}"))

# -- FMAPI: Proprietary models (each provider) --
for provider in ["openai", "anthropic", "google"]:
    run_test(f"ref_fmapi_{provider}", "GET",
             f"{app_url}/api/v1/reference/fmapi/proprietary-models/list?provider={provider}",
             check_fn=lambda d: (d.get("success") and len(d.get("data", {}).get("models", [])) > 0,
                                f"models: {len(d.get('data', {}).get('models', []))}"))

# -- FMAPI: Form configs --
run_test("ref_fmapi_db_config", "GET", f"{app_url}/api/v1/reference/fmapi-databricks",
         check_fn=lambda d: (d.get("success"), "fmapi databricks config failed"))

run_test("ref_fmapi_prop_config", "GET", f"{app_url}/api/v1/reference/fmapi-proprietary",
         check_fn=lambda d: (d.get("success"), "fmapi proprietary config failed"))

section_times["reference"] = time.time() - t0
print(f"  Done ({section_times['reference']:.1f}s) — tested across AWS, Azure, GCP")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 4: Cost Calculations

t0 = time.time()
print("Test 4: Cost calculations...")

def cost_check(d):
    cost = d.get("data", {}).get("total_cost", {}).get("cost_per_month", 0)
    return (d.get("success") and cost > 0, f"cost={cost}")

# Jobs Classic
run_test("calc_jobs_classic", "POST", f"{app_url}/api/v1/calculate/jobs-classic", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "driver_node_type": "i3.xlarge", "worker_node_type": "i3.xlarge", "num_workers": 2,
    "photon_enabled": False, "hours_per_month": 100,
    "driver_pricing_tier": "on_demand", "worker_pricing_tier": "on_demand",
}, check_fn=cost_check)

# Jobs Serverless
run_test("calc_jobs_serverless", "POST", f"{app_url}/api/v1/calculate/jobs-serverless", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "driver_node_type": "i3.xlarge", "worker_node_type": "i3.xlarge", "num_workers": 2,
    "hours_per_month": 100,
}, check_fn=cost_check)

# DBSQL Classic
run_test("calc_dbsql_classic", "POST", f"{app_url}/api/v1/calculate/dbsql-classic", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "warehouse_size": "Small", "num_clusters": 1, "hours_per_month": 100,
}, check_fn=cost_check)

# DBSQL Pro
run_test("calc_dbsql_pro", "POST", f"{app_url}/api/v1/calculate/dbsql-pro", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "warehouse_size": "Small", "num_clusters": 1, "hours_per_month": 100,
}, check_fn=cost_check)

# DBSQL Serverless
run_test("calc_dbsql_serverless", "POST", f"{app_url}/api/v1/calculate/dbsql-serverless", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "warehouse_size": "Small", "hours_per_month": 100,
}, check_fn=cost_check)

# All-Purpose Classic
run_test("calc_ap_classic", "POST", f"{app_url}/api/v1/calculate/all-purpose-classic", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "driver_node_type": "i3.xlarge", "worker_node_type": "i3.xlarge", "num_workers": 2,
    "photon_enabled": False, "hours_per_month": 100,
    "driver_pricing_tier": "on_demand", "worker_pricing_tier": "on_demand",
}, check_fn=cost_check)

# All-Purpose Serverless
run_test("calc_ap_serverless", "POST", f"{app_url}/api/v1/calculate/all-purpose-serverless", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "driver_node_type": "i3.xlarge", "worker_node_type": "i3.xlarge", "num_workers": 2,
    "hours_per_month": 100,
}, check_fn=cost_check)

# DLT Classic — all 3 editions
for edition in ["CORE", "PRO", "ADVANCED"]:
    run_test(f"calc_dlt_{edition.lower()}", "POST", f"{app_url}/api/v1/calculate/dlt-classic", json_body={
        "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
        "dlt_edition": edition, "photon_enabled": False,
        "driver_node_type": "i3.xlarge", "worker_node_type": "i3.xlarge", "num_workers": 2,
        "hours_per_month": 100,
        "driver_pricing_tier": "on_demand", "worker_pricing_tier": "on_demand",
    }, check_fn=cost_check)

# DLT Serverless
run_test("calc_dlt_serverless", "POST", f"{app_url}/api/v1/calculate/dlt-serverless", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "driver_node_type": "i3.xlarge", "worker_node_type": "i3.xlarge", "num_workers": 2,
    "hours_per_month": 100,
}, check_fn=cost_check)

# Model Serving
run_test("calc_model_serving", "POST", f"{app_url}/api/v1/calculate/model-serving", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "gpu_type": "GPU_SMALL", "num_gpus": 1, "hours_per_month": 100,
    "provisioned_throughput": False,
}, check_fn=cost_check)

# Vector Search
run_test("calc_vector_search", "POST", f"{app_url}/api/v1/calculate/vector-search", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "endpoint_type": "starter", "hours_per_month": 730,
}, check_fn=cost_check)

# FMAPI Databricks
run_test("calc_fmapi_databricks", "POST", f"{app_url}/api/v1/calculate/fmapi", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "provider_type": "databricks", "model_category": "general_purpose",
    "model_name": "llama-4-maverick",
    "input_tokens_per_month": 1000000, "output_tokens_per_month": 500000,
}, check_fn=cost_check)

# FMAPI Proprietary (Anthropic)
run_test("calc_fmapi_anthropic", "POST", f"{app_url}/api/v1/calculate/fmapi", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "provider_type": "proprietary", "model_category": "general_purpose",
    "provider": "anthropic", "model_name": "claude-sonnet-4",
    "input_tokens_per_month": 1000000, "output_tokens_per_month": 500000,
}, check_fn=cost_check)

# Lakebase
run_test("calc_lakebase", "POST", f"{app_url}/api/v1/calculate/lakebase", json_body={
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
    "cu_size": "CU_1", "hours_per_month": 730,
}, check_fn=cost_check)

# Cross-cloud: Jobs Classic on Azure + GCP
run_test("calc_jobs_azure", "POST", f"{app_url}/api/v1/calculate/jobs-classic", json_body={
    "cloud": "AZURE", "region": "eastus", "tier": "PREMIUM",
    "driver_node_type": "Standard_DS3_v2", "worker_node_type": "Standard_DS3_v2", "num_workers": 2,
    "photon_enabled": False, "hours_per_month": 100,
    "driver_pricing_tier": "on_demand", "worker_pricing_tier": "on_demand",
}, check_fn=cost_check)

run_test("calc_jobs_gcp", "POST", f"{app_url}/api/v1/calculate/jobs-classic", json_body={
    "cloud": "GCP", "region": "us-central1", "tier": "PREMIUM",
    "driver_node_type": "n1-standard-4", "worker_node_type": "n1-standard-4", "num_workers": 2,
    "photon_enabled": False, "hours_per_month": 100,
    "driver_pricing_tier": "on_demand", "worker_pricing_tier": "on_demand",
}, check_fn=cost_check)

section_times["calculations"] = time.time() - t0
print(f"  Done ({section_times['calculations']:.1f}s)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 5: AI Assistant

t0 = time.time()
print("Test 5: AI Assistant...")

# Test non-streaming chat endpoint with a simple query
run_test("ai_chat_response", "POST", f"{app_url}/api/v1/chat", json_body={
    "message": "What workload types does Lakemeter support?",
    "mode": "estimate",
    "stream": False,
}, timeout=60, check_fn=lambda d: (
    d.get("content") is not None and len(d.get("content", "")) > 10,
    f"content length: {len(d.get('content', ''))}"
))

# Test chat with workload proposal — ask for a specific non-default config
chat_data = run_test("ai_propose_workload", "POST", f"{app_url}/api/v1/chat", json_body={
    "message": "Add a Jobs Classic workload on AWS us-east-1 Premium with i3.2xlarge driver, i3.4xlarge workers, 5 workers, photon enabled, 8 runs per day, 30 minutes each",
    "mode": "estimate",
    "stream": False,
    "estimate_context": {"cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM"},
}, timeout=90, check_fn=lambda d: (
    d.get("content") is not None and len(d.get("content", "")) > 10,
    f"content length: {len(d.get('content', ''))}"
))

# If we got a conversation_id and proposed_workload, test confirm-workload
if chat_data and chat_data.get("conversation_id") and chat_data.get("proposed_workload"):
    conv_id = chat_data["conversation_id"]
    proposal = chat_data["proposed_workload"]
    proposal_id = proposal.get("proposal_id", proposal.get("id", ""))

    if proposal_id:
        run_test("ai_confirm_workload", "POST",
                 f"{app_url}/api/v1/chat/{conv_id}/confirm-workload",
                 json_body={"proposal_id": proposal_id, "confirmed": True},
                 check_fn=lambda d: (d.get("success", True), "confirm failed"))

    # Get conversation state
    run_test("ai_conv_state", "GET", f"{app_url}/api/v1/chat/{conv_id}/state",
             check_fn=lambda d: (True, ""))

    # Cleanup conversation
    run_test("ai_conv_cleanup", "DELETE", f"{app_url}/api/v1/chat/{conv_id}", expected_status=200)

section_times["ai_assistant"] = time.time() - t0
print(f"  Done ({section_times['ai_assistant']:.1f}s)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 6: Estimate CRUD + Excel Export

t0 = time.time()
print("Test 6: Estimate CRUD + Excel export...")

# Create estimate
est_data = run_test("create_estimate", "POST", f"{app_url}/api/v1/estimates/", json_body={
    "name": "Installer Verification Test",
    "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
}, check_fn=lambda d: (d.get("success") and d.get("data", {}).get("id") is not None,
                       "no estimate id"))

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
    }, check_fn=lambda d: (d.get("success"), "add line item failed"))

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

section_times["crud_export"] = time.time() - t0
print(f"  Done ({section_times['crud_export']:.1f}s)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Results Summary

elapsed = time.time() - _start
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
total = len(results)

print(f"\n{'='*70}")
print(f"VERIFICATION RESULTS")
print(f"{'='*70}")
print(f"  Total: {total} tests | Passed: {passed} | Failed: {failed} | Time: {elapsed:.1f}s")
print(f"{'='*70}")

# Section timing
print(f"\n  Section Timing:")
for section, secs in section_times.items():
    print(f"    {section:<20} {secs:.1f}s")
print(f"    {'TOTAL':<20} {elapsed:.1f}s")

# Per-test results
print(f"\n  Test Results:")
for r in results:
    icon = "PASS" if r["status"] == "PASS" else "FAIL"
    detail = f" — {r['detail']}" if r.get("detail") else ""
    print(f"    [{icon}] {r['test']:<35} {r['elapsed']:>6}{detail}")

print(f"\n{'='*70}")

# Set task values for CLI progress display
dbutils.jobs.taskValues.set(key="tests_passed", value=passed)
dbutils.jobs.taskValues.set(key="tests_failed", value=failed)
dbutils.jobs.taskValues.set(key="tests_total", value=total)

if failed > 0:
    failed_tests = [r["test"] for r in results if r["status"] == "FAIL"]
    dbutils.notebook.exit(f"FAIL: {failed}/{total} tests failed ({', '.join(failed_tests[:5])}) ({elapsed:.1f}s)")
else:
    dbutils.notebook.exit(f"PASS: All {total} tests passed ({elapsed:.1f}s)")
