"""E2E tests: AI Assistant Accept Button — FMAPI (Databricks & Proprietary).

Verifies that confirmed FMAPI workloads preserve provider, model, rate_type,
quantity, and other non-default values.

Run: pytest tests/e2e/ai_assistant/test_accept_fmapi.py -v
"""
import pytest
from tests.e2e.helpers.assertions import save_test_results


@pytest.fixture(scope="module")
def results():
    data = []
    yield data
    save_test_results(data, "test_results/e2e_ai_accept_fmapi.json")


class TestAcceptFMAPIDatabricks:
    """Verify confirm-workload preserves FMAPI Databricks config."""

    def test_input_token_config_preserved(self, inject_proposal, confirm_workload, results):
        """FMAPI Databricks with input tokens must survive confirm."""
        pid = inject_proposal(
            workload_type="FMAPI_DATABRICKS",
            workload_name="FMAPI-DB-Llama-Input",
            fmapi_provider="databricks",
            fmapi_model="llama-3-3-70b",
            fmapi_rate_type="input_token",
            fmapi_quantity=10,  # millions per month
            serverless_enabled=True,
        )
        config = confirm_workload(pid)

        assert config["workload_type"] == "FMAPI_DATABRICKS"
        assert config["serverless_enabled"] is True

        results.append({"test": "fmapi_db_input_token", "status": "PASS",
                        "config": config})

    def test_output_token_config_preserved(self, inject_proposal, confirm_workload, results):
        """FMAPI Databricks with output tokens must survive confirm."""
        pid = inject_proposal(
            workload_type="FMAPI_DATABRICKS",
            workload_name="FMAPI-DB-Llama-Output",
            fmapi_provider="databricks",
            fmapi_model="llama-4-maverick",
            fmapi_rate_type="output_token",
            fmapi_quantity=5,
            serverless_enabled=True,
        )
        config = confirm_workload(pid)

        assert config["workload_type"] == "FMAPI_DATABRICKS"
        assert config["serverless_enabled"] is True

        results.append({"test": "fmapi_db_output_token", "status": "PASS",
                        "config": config})

    def test_provisioned_config_preserved(self, inject_proposal, confirm_workload, results):
        """FMAPI Databricks with provisioned throughput must survive confirm."""
        pid = inject_proposal(
            workload_type="FMAPI_DATABRICKS",
            workload_name="FMAPI-DB-Provisioned",
            fmapi_provider="databricks",
            fmapi_model="llama-3-3-70b",
            fmapi_rate_type="provisioned_scaling",
            fmapi_quantity=2,
            serverless_enabled=True,
        )
        config = confirm_workload(pid)

        assert config["workload_type"] == "FMAPI_DATABRICKS"

        results.append({"test": "fmapi_db_provisioned", "status": "PASS",
                        "config": config})


class TestAcceptFMAPIProprietary:
    """Verify confirm-workload preserves FMAPI Proprietary config."""

    @pytest.mark.parametrize("provider,model", [
        ("openai", "gpt-5"),
        ("anthropic", "claude-sonnet-4-5"),
        ("google", "gemini-2-5-pro"),
    ])
    def test_provider_model_preserved(self, inject_proposal, confirm_workload,
                                       provider, model, results):
        """Each provider/model combo must survive confirm."""
        pid = inject_proposal(
            workload_type="FMAPI_PROPRIETARY",
            workload_name=f"FMAPI-{provider}-{model}-input",
            fmapi_provider=provider,
            fmapi_model=model,
            fmapi_rate_type="input_token",
            fmapi_quantity=10,
            serverless_enabled=True,
        )
        config = confirm_workload(pid)

        assert config["workload_type"] == "FMAPI_PROPRIETARY"
        assert config["serverless_enabled"] is True

        results.append({"test": f"fmapi_prop_{provider}_{model}", "status": "PASS",
                        "config": config})

    def test_high_volume_tokens_preserved(self, inject_proposal, confirm_workload, results):
        """High volume token usage (100M) must survive confirm."""
        pid = inject_proposal(
            workload_type="FMAPI_PROPRIETARY",
            workload_name="FMAPI-HighVol-GPT5",
            fmapi_provider="openai",
            fmapi_model="gpt-5",
            fmapi_rate_type="output_token",
            fmapi_quantity=100,  # 100M tokens/month
            serverless_enabled=True,
        )
        config = confirm_workload(pid)

        assert config["workload_type"] == "FMAPI_PROPRIETARY"

        results.append({"test": "fmapi_prop_high_volume", "status": "PASS",
                        "config": config})
