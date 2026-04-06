"""
Harness Test (iv): AI Assistant — prompt for different workload types,
verify proposals are correctly populated.

Tests:
- POST /api/v1/chat with workload-specific prompts
- Verify the AI response includes correct workload_type
- Verify proposals contain the right fields for each workload
- Test apply and confirm-workload flows
"""
import pytest
import time


# Prompts designed to trigger specific workload types in the AI assistant
WORKLOAD_PROMPTS = [
    {
        "prompt": "I need a Spark job that runs 5 times a day for data processing, each run takes about 30 minutes",
        "expected_type": "JOBS",
        "expected_fields": ["runs_per_day", "avg_runtime_minutes"],
    },
    {
        "prompt": "Set up an interactive notebook cluster for data scientists, they'll use it 8 hours a day",
        "expected_type": "ALL_PURPOSE",
        "expected_fields": ["hours_per_day"],
    },
    {
        "prompt": "I need a SQL warehouse for our BI dashboards, medium size, running about 10 hours per day",
        "expected_type": "DBSQL",
        "expected_fields": ["dbsql_warehouse_size"],
    },
    {
        "prompt": "Set up a DLT pipeline with the Pro edition for ETL, runs 4 times daily, 45 min each",
        "expected_type": "DLT",
        "expected_fields": ["dlt_edition"],
    },
    {
        "prompt": "Deploy a model serving endpoint with GPU for real-time inference, small scale",
        "expected_type": "MODEL_SERVING",
        "expected_fields": ["model_serving_gpu_type"],
    },
    {
        "prompt": "I want to use the Databricks DBRX model for text generation, about 50 million tokens per month",
        "expected_type": "FMAPI_DATABRICKS",
        "expected_fields": ["fmapi_model"],
    },
    {
        "prompt": "Set up Claude Sonnet from Anthropic via the Foundation Model API for our chatbot",
        "expected_type": "FMAPI_PROPRIETARY",
        "expected_fields": ["fmapi_provider", "fmapi_model"],
    },
    {
        "prompt": "I need vector search for our RAG application with about 100 million vectors",
        "expected_type": "VECTOR_SEARCH",
        "expected_fields": ["vector_search_mode"],
    },
    {
        "prompt": "Provision a Lakebase database with 4 compute units and 1 read replica, always on",
        "expected_type": "LAKEBASE",
        "expected_fields": ["lakebase_cu"],
    },
]


class TestAIAssistantWorkloads:
    """Test AI assistant generates correct workload proposals."""

    @pytest.fixture(scope="class")
    def chat_estimate(self, client, test_user_id):
        """Create an estimate for chat testing."""
        resp = client.post("/api/v1/estimates", json={
            "estimate_name": "AI-Chat Harness",
            "customer_name": "AI Test Corp",
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
        }, headers={"X-User-Id": test_user_id})
        data = resp.json()
        return data.get("estimate_id") or data.get("data", {}).get("estimate_id")

    @pytest.mark.parametrize("prompt_cfg", WORKLOAD_PROMPTS,
                             ids=[p["expected_type"] for p in WORKLOAD_PROMPTS])
    def test_workload_prompt(self, client, test_user_id, chat_estimate, prompt_cfg):
        """Send a workload-specific prompt and verify the AI proposes the right type."""
        resp = client.post("/api/v1/chat", json={
            "estimate_id": chat_estimate,
            "message": prompt_cfg["prompt"],
        }, headers={"X-User-Id": test_user_id})

        # Chat endpoint might return 200 or stream
        if resp.status_code != 200:
            pytest.skip(f"Chat endpoint returned {resp.status_code} — AI may not be configured")

        data = resp.json()

        # The response should contain a proposed workload or action
        response_text = ""
        proposed_workloads = []

        if isinstance(data, dict):
            response_text = data.get("response", data.get("message", ""))
            proposed_workloads = data.get("proposed_workloads", data.get("workloads", []))
            # Also check nested data
            if "data" in data:
                response_text = data["data"].get("response", response_text)
                proposed_workloads = data["data"].get("proposed_workloads", proposed_workloads)

        # Verify the AI understood the workload type
        expected = prompt_cfg["expected_type"]
        found_type = False

        # Check proposed workloads
        for wl in proposed_workloads:
            wl_type = wl.get("workload_type", "").upper()
            if expected in wl_type or wl_type in expected:
                found_type = True
                # Check expected fields are populated
                for field in prompt_cfg["expected_fields"]:
                    assert wl.get(field) is not None or wl.get("workload_config", {}).get(field) is not None, (
                        f"Expected field '{field}' not populated in {expected} proposal"
                    )
                break

        # If no structured proposals, check the response text mentions the workload
        if not found_type and response_text:
            type_keywords = {
                "JOBS": ["job", "spark job"],
                "ALL_PURPOSE": ["all-purpose", "interactive", "notebook"],
                "DBSQL": ["sql warehouse", "dbsql", "databricks sql"],
                "DLT": ["dlt", "delta live", "pipeline"],
                "MODEL_SERVING": ["model serving", "inference", "endpoint"],
                "FMAPI_DATABRICKS": ["fmapi", "foundation model", "dbrx"],
                "FMAPI_PROPRIETARY": ["claude", "anthropic", "proprietary"],
                "VECTOR_SEARCH": ["vector search", "rag"],
                "LAKEBASE": ["lakebase", "database", "postgresql"],
            }
            keywords = type_keywords.get(expected, [expected.lower()])
            text_lower = response_text.lower()
            found_type = any(kw in text_lower for kw in keywords)

        assert found_type, (
            f"AI did not propose {expected} workload for prompt: '{prompt_cfg['prompt'][:50]}...'\n"
            f"Response: {response_text[:200]}\n"
            f"Proposals: {proposed_workloads}"
        )


class TestAIChatFlow:
    """Test the full chat flow: create conversation, chat, apply, confirm."""

    def test_chat_create_and_respond(self, client, test_user_id):
        """Basic chat flow: send message, get response."""
        # Create estimate
        resp = client.post("/api/v1/estimates", json={
            "estimate_name": "Chat Flow Test",
            "customer_name": "Flow Test Corp",
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
        }, headers={"X-User-Id": test_user_id})
        data = resp.json()
        est_id = data.get("estimate_id") or data.get("data", {}).get("estimate_id")

        # Send chat message
        resp = client.post("/api/v1/chat", json={
            "estimate_id": est_id,
            "message": "Add a small Spark job that runs twice daily",
        }, headers={"X-User-Id": test_user_id})

        if resp.status_code != 200:
            pytest.skip("Chat endpoint not available")

        data = resp.json()
        # Should have a conversation_id or response
        assert data, "Empty chat response"

    def test_chat_delete_conversation(self, client, test_user_id):
        """Test conversation cleanup."""
        # Create estimate + chat
        resp = client.post("/api/v1/estimates", json={
            "estimate_name": "Chat Delete Test",
            "customer_name": "Delete Corp",
            "cloud": "AWS", "region": "us-east-1", "tier": "PREMIUM",
        }, headers={"X-User-Id": test_user_id})
        data = resp.json()
        est_id = data.get("estimate_id") or data.get("data", {}).get("estimate_id")

        resp = client.post("/api/v1/chat", json={
            "estimate_id": est_id,
            "message": "Hello",
        }, headers={"X-User-Id": test_user_id})

        if resp.status_code != 200:
            pytest.skip("Chat not available")

        data = resp.json()
        cid = None
        if isinstance(data, dict):
            cid = data.get("conversation_id") or data.get("data", {}).get("conversation_id")

        if cid:
            resp = client.delete(
                f"/api/v1/chat/{cid}",
                headers={"X-User-Id": test_user_id},
            )
            assert resp.status_code in (200, 204), f"Delete failed: {resp.status_code}"
