# Databricks notebook source
"""Verify that a source installation serves authenticated database APIs."""

import time

import requests
from databricks.sdk import WorkspaceClient


dbutils.widgets.text("app_name", "lakemeter")
dbutils.widgets.text("project_id", "lakemeter-customer")
dbutils.widgets.text("db_name", "lakemeter_pricing")

app_name = dbutils.widgets.get("app_name")
project_id = dbutils.widgets.get("project_id")
db_name = dbutils.widgets.get("db_name")

print(f"App: {app_name}")
print(f"Project: {project_id}")
print(f"Database: {db_name}")

w = WorkspaceClient()
app_info = w.apps.get(app_name)
if not app_info.url:
    raise RuntimeError("App has no URL; deployment is incomplete")

app_url = app_info.url.rstrip("/")

# A notebook's internal token targets the workspace APIs. Databricks Apps
# require an OAuth token whose audience is the app's OAuth client ID.
notebook_token = (
    dbutils.notebook.entry_point.getDbutils()
    .notebook()
    .getContext()
    .apiToken()
    .get()
)
token_response = requests.post(
    f"{w.config.host.rstrip('/')}/oidc/v1/token",
    data={
        "grant_type": (
            "urn:ietf:params:oauth:grant-type:token-exchange"
        ),
        "subject_token": notebook_token,
        "subject_token_type": (
            "urn:databricks:params:oauth:token-type:personal-access-token"
        ),
        "requested_token_type": (
            "urn:ietf:params:oauth:token-type:access_token"
        ),
        "scope": "all-apis",
        "audience": app_info.oauth2_app_client_id,
    },
    timeout=30,
)
token_response.raise_for_status()

session = requests.Session()
session.headers.update(
    {"Authorization": f"Bearer {token_response.json()['access_token']}"}
)
results = []


def check(
    name,
    method,
    path,
    *,
    json_body=None,
    validate=None,
    attempts=1,
    timeout=30,
):
    """Call one app endpoint and fail the verification on bad responses."""
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            response = session.request(
                method,
                f"{app_url}{path}",
                json=json_body,
                timeout=timeout,
            )
            if response.status_code != 200:
                last_error = (
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )
            else:
                content_type = response.headers.get("content-type", "")
                if "application/json" not in content_type:
                    last_error = f"Unexpected content type: {content_type}"
                else:
                    data = response.json()
                    ok, detail = validate(data) if validate else (True, "")
                    if ok:
                        results.append((name, "PASS", detail))
                        print(f"[PASS] {name}: {detail}")
                        return data
                    last_error = detail
        except Exception as error:
            last_error = str(error)

        if attempt < attempts:
            print(
                f"[WAIT] {name} attempt {attempt}/{attempts}: "
                f"{last_error}"
            )
            time.sleep(5)

    results.append((name, "FAIL", last_error))
    print(f"[FAIL] {name}: {last_error}")
    return None


check(
    "api_root",
    "GET",
    "/api",
    validate=lambda data: (
        "Lakemeter" in data.get("name", ""),
        f"name={data.get('name')}",
    ),
    attempts=12,
)

expected_minimums = {"AWS": 17, "AZURE": 38, "GCP": 15}
for cloud, minimum in expected_minimums.items():
    check(
        f"regions_{cloud.lower()}",
        "GET",
        f"/api/v1/regions?cloud={cloud}",
        validate=lambda data, cloud=cloud, minimum=minimum: (
            data.get("success") is True
            and len(data.get("data", {}).get("regions", [])) >= minimum,
            (
                f"{cloud} regions="
                f"{len(data.get('data', {}).get('regions', []))}"
            ),
        ),
        attempts=12,
    )

check(
    "aws_dbu_rates",
    "GET",
    "/api/v1/pricing/dbu-rates"
    "?cloud=AWS&region=us-east-1&tier=PREMIUM",
    validate=lambda data: (
        data.get("success") is True
        and len(data.get("data", {}).get("dbu_rates", [])) > 0,
        f"dbu_rates={len(data.get('data', {}).get('dbu_rates', []))}",
    ),
)

check(
    "jobs_classic_calculation",
    "POST",
    "/api/v1/calculate/jobs-classic",
    json_body={
        "cloud": "AWS",
        "region": "us-east-1",
        "tier": "PREMIUM",
        "driver_node_type": "i3.xlarge",
        "worker_node_type": "i3.xlarge",
        "num_workers": 2,
        "photon_enabled": False,
        "hours_per_month": 100,
        "driver_pricing_tier": "on_demand",
        "worker_pricing_tier": "on_demand",
    },
    validate=lambda data: (
        data.get("success") is True
        and data.get("data", {})
        .get("total_cost", {})
        .get("cost_per_month", 0)
        > 0,
        (
            "cost_per_month="
            f"{data.get('data', {}).get('total_cost', {}).get('cost_per_month')}"
        ),
    ),
)

failed = [name for name, status, _detail in results if status == "FAIL"]
dbutils.jobs.taskValues.set(key="tests_passed", value=len(results) - len(failed))
dbutils.jobs.taskValues.set(key="tests_failed", value=len(failed))
dbutils.jobs.taskValues.set(key="tests_total", value=len(results))

if failed:
    raise RuntimeError(
        f"{len(failed)}/{len(results)} installation checks failed: "
        + ", ".join(failed)
    )

print(f"All {len(results)} authenticated installation checks passed")
