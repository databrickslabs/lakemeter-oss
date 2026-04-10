"""
AI Assistant Accept Button — All 12 Workload Types

Tests that clicking "Confirm & Add" preserves ALL non-default values
the AI proposed, rather than falling back to defaults.

This is a comprehensive regression test for Bug C:
  "Accept button populated workload with DEFAULT values instead of
   the AI-suggested non-default values."

Run:
    pytest tests/ai_assistant/test_accept_all_types.py --timeout=300 -v

Each test sends a prompt with specific non-default parameters, confirms
the proposed workload, and asserts every requested field survived the
confirm round-trip.
"""
import pytest

from tests.ai_assistant.chat_helpers import (
    send_chat_until_proposal,
    confirm_proposal,
    AUTH_HEADERS,
)


# ── helpers ─────────────────────────────────────────────────────────
def _propose_and_confirm(http_client, estimate, prompt_messages, expected):
    """
    Send prompt(s), confirm the proposal, and assert expected fields.

    Args:
        prompt_messages: list of strings (will retry until proposal)
        expected: dict of field_name → expected_value to check in
                  the confirmed workload_config
    Returns:
        The full confirmed workload_config dict for further assertions.
    """
    proposal, last_resp = send_chat_until_proposal(
        http_client, prompt_messages, estimate
    )
    cid = last_resp["_conversation_id"]

    # Confirm
    result = confirm_proposal(http_client, cid, proposal["proposal_id"])
    config = result["workload_config"]

    # Assert every expected field
    for field, want in expected.items():
        got = config.get(field)
        assert got == want, (
            f"Field '{field}': expected {want!r}, got {got!r}.\n"
            f"Full config: {config}"
        )

    return config


# ── 1. JOBS Classic ────────────────────────────────────────────────
def test_jobs_classic_accept(http_client, test_estimate):
    _propose_and_confirm(
        http_client,
        test_estimate,
        [
            "Add a Jobs Classic workload named 'ETL Pipeline Test' with "
            "i3.xlarge driver, i3.2xlarge workers, 5 workers, photon enabled, "
            "8 runs per day, 45 minutes each, 22 days per month."
        ],
        {
            "workload_type": "JOBS",
            "workload_name": "ETL Pipeline Test",
            "driver_node_type": "i3.xlarge",
            "worker_node_type": "i3.2xlarge",
            "num_workers": 5,
            "photon_enabled": True,
            "serverless_enabled": False,
            "runs_per_day": 8,
            "avg_runtime_minutes": 45,
            "days_per_month": 22,
        },
    )


# ── 2. JOBS Serverless ────────────────────────────────────────────
def test_jobs_serverless_accept(http_client, test_estimate):
    _propose_and_confirm(
        http_client,
        test_estimate,
        [
            "Add a Jobs Serverless workload named 'Nightly Data Sync' with "
            "performance mode, 4 runs per day, 30 minutes each, 30 days per month."
        ],
        {
            "workload_type": "JOBS",
            "workload_name": "Nightly Data Sync",
            "serverless_enabled": True,
            "serverless_mode": "performance",
            "runs_per_day": 4,
            "avg_runtime_minutes": 30,
            "days_per_month": 30,
        },
    )


# ── 3. ALL_PURPOSE Classic ────────────────────────────────────────
def test_all_purpose_classic_accept(http_client, test_estimate):
    _propose_and_confirm(
        http_client,
        test_estimate,
        [
            "Add an All-Purpose Classic cluster named 'Dev Notebook Cluster' with "
            "m5.2xlarge driver, r5.xlarge workers, 3 workers, photon enabled, "
            "176 hours per month. Use 1-year reserved pricing for the driver."
        ],
        {
            "workload_type": "ALL_PURPOSE",
            "workload_name": "Dev Notebook Cluster",
            "driver_node_type": "m5.2xlarge",
            "worker_node_type": "r5.xlarge",
            "num_workers": 3,
            "photon_enabled": True,
            "serverless_enabled": False,
            "hours_per_month": 176,
            "driver_pricing_tier": "1yr_reserved",
        },
    )


# ── 4. DLT Classic PRO ────────────────────────────────────────────
def test_dlt_classic_pro_accept(http_client, test_estimate):
    _propose_and_confirm(
        http_client,
        test_estimate,
        [
            "Add a DLT Classic pipeline named 'Streaming Ingest Pipeline' with "
            "PRO edition, m5.xlarge driver, i3.xlarge workers, 4 workers, "
            "photon enabled, 500 hours per month, 30 days per month."
        ],
        {
            "workload_type": "DLT",
            "workload_name": "Streaming Ingest Pipeline",
            "dlt_edition": "PRO",
            "driver_node_type": "m5.xlarge",
            "worker_node_type": "i3.xlarge",
            "num_workers": 4,
            "photon_enabled": True,
            "serverless_enabled": False,
            "hours_per_month": 500,
            "days_per_month": 30,
        },
    )


# ── 5. DBSQL Pro ──────────────────────────────────────────────────
def test_dbsql_pro_accept(http_client, test_estimate):
    _propose_and_confirm(
        http_client,
        test_estimate,
        [
            "Add a DBSQL Pro warehouse named 'BI Analytics Warehouse' with "
            "Large size, 3 clusters, 400 hours per month."
        ],
        {
            "workload_type": "DBSQL",
            "workload_name": "BI Analytics Warehouse",
            "dbsql_warehouse_type": "PRO",
            "dbsql_warehouse_size": "Large",
            "dbsql_num_clusters": 3,
            "hours_per_month": 400,
        },
    )


# ── 6. DBSQL Serverless ───────────────────────────────────────────
def test_dbsql_serverless_accept(http_client, test_estimate):
    _propose_and_confirm(
        http_client,
        test_estimate,
        [
            "Add a DBSQL Serverless warehouse named 'Real-time Dashboard' with "
            "Medium size, 2 clusters, 600 hours per month."
        ],
        {
            "workload_type": "DBSQL",
            "workload_name": "Real-time Dashboard",
            "dbsql_warehouse_type": "SERVERLESS",
            "dbsql_warehouse_size": "Medium",
            "dbsql_num_clusters": 2,
            "hours_per_month": 600,
        },
    )


# ── 7. MODEL_SERVING ──────────────────────────────────────────────
def test_model_serving_accept(http_client, test_estimate):
    _propose_and_confirm(
        http_client,
        test_estimate,
        [
            "Add a Model Serving endpoint named 'Fraud Detection Model' with "
            "gpu_small type, scale to zero disabled, 730 hours per month."
        ],
        {
            "workload_type": "MODEL_SERVING",
            "workload_name": "Fraud Detection Model",
            "hours_per_month": 730,
        },
    )


# ── 8. VECTOR_SEARCH ──────────────────────────────────────────────
def test_vector_search_accept(http_client, test_estimate):
    _propose_and_confirm(
        http_client,
        test_estimate,
        [
            "Add a Vector Search endpoint named 'Document Search Index' with "
            "STORAGE_OPTIMIZED type, 50 million vectors, 100 GB storage."
        ],
        {
            "workload_type": "VECTOR_SEARCH",
            "workload_name": "Document Search Index",
            "vector_capacity_millions": 50,
            "vector_search_storage_gb": 100,
        },
    )


# ── 9. FMAPI_DATABRICKS ───────────────────────────────────────────
def test_fmapi_databricks_accept(http_client, test_estimate):
    _propose_and_confirm(
        http_client,
        test_estimate,
        [
            "Add a Foundation Model API Databricks workload named 'Llama Chat Input' "
            "using llama-3-3-70b model from Meta, input_token rate type, "
            "100 million tokens per month, regional endpoint."
        ],
        {
            "workload_type": "FMAPI_DATABRICKS",
            "workload_name": "Llama Chat Input",
            "fmapi_model": "llama-3-3-70b",
            "fmapi_provider": "meta",
            "fmapi_rate_type": "input_token",
            "fmapi_quantity": 100,
            "fmapi_endpoint_type": "regional",
        },
    )


# ── 10. FMAPI_PROPRIETARY ─────────────────────────────────────────
def test_fmapi_proprietary_accept(http_client, test_estimate):
    _propose_and_confirm(
        http_client,
        test_estimate,
        [
            "Add a Foundation Model API Proprietary workload named 'Claude Output Tokens' "
            "using claude-sonnet-4-5 model from Anthropic, output_token rate type, "
            "25 million tokens per month, global endpoint, long context length."
        ],
        {
            "workload_type": "FMAPI_PROPRIETARY",
            "workload_name": "Claude Output Tokens",
            "fmapi_model": "claude-sonnet-4-5",
            "fmapi_provider": "anthropic",
            "fmapi_rate_type": "output_token",
            "fmapi_quantity": 25,
            "fmapi_endpoint_type": "global",
            "fmapi_context_length": "long",
        },
    )


# ── 11. LAKEBASE ──────────────────────────────────────────────────
def test_lakebase_accept(http_client, test_estimate):
    _propose_and_confirm(
        http_client,
        test_estimate,
        [
            "Add a Lakebase database named 'Product Catalog DB' with "
            "10000 reads per second, 5000 bulk writes per second, "
            "500 incremental writes per second, 1KB average row size, "
            "HA enabled, 2 read replicas, 500 GB storage, "
            "200 GB PITR, 100 GB snapshot storage."
        ],
        {
            "workload_type": "LAKEBASE",
            "workload_name": "Product Catalog DB",
            "lakebase_storage_gb": 500,
            "lakebase_pitr_gb": 200,
            "lakebase_snapshot_gb": 100,
        },
    )


# ── 12. DATABRICKS_APPS ───────────────────────────────────────────
def test_databricks_apps_accept(http_client, test_estimate):
    _propose_and_confirm(
        http_client,
        test_estimate,
        [
            "Add a Databricks Apps workload named 'Internal Dashboard App' "
            "with large size, 500 hours per month."
        ],
        {
            "workload_type": "DATABRICKS_APPS",
            "workload_name": "Internal Dashboard App",
            "databricks_apps_size": "large",
            "hours_per_month": 500,
        },
    )


# ── 13. AI_PARSE ──────────────────────────────────────────────────
def test_ai_parse_accept(http_client, test_estimate):
    _propose_and_confirm(
        http_client,
        test_estimate,
        [
            "Add an AI Parse workload named 'Contract Scanner' with "
            "pages billing mode, high complexity, 200 thousand pages per month."
        ],
        {
            "workload_type": "AI_PARSE",
            "workload_name": "Contract Scanner",
            "ai_parse_mode": "pages",
            "ai_parse_complexity": "high",
            "ai_parse_pages_thousands": 200,
        },
    )


# ── 14. SHUTTERSTOCK_IMAGEAI ──────────────────────────────────────
def test_shutterstock_imageai_accept(http_client, test_estimate):
    _propose_and_confirm(
        http_client,
        test_estimate,
        [
            "Add a Shutterstock ImageAI workload named 'Marketing Image Gen' "
            "generating 5000 images per month."
        ],
        {
            "workload_type": "SHUTTERSTOCK_IMAGEAI",
            "workload_name": "Marketing Image Gen",
            "shutterstock_images": 5000,
        },
    )
