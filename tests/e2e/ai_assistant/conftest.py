"""Fixtures for AI assistant confirm-workload tests.

These tests verify that when the AI proposes a workload with specific
non-default configuration values, the confirm-workload endpoint returns
those EXACT values — not defaults.

The tests bypass the LLM call entirely by injecting proposals directly
into the in-memory agent state, then exercising the confirm endpoint.
"""
import uuid
import pytest

# Re-use the parent conftest's http_client and e2e_client fixtures
# (they're defined in tests/e2e/conftest.py and auto-discovered by pytest)


@pytest.fixture
def conversation_id():
    """Generate a unique conversation ID per test."""
    return f"e2e-ai-test-{uuid.uuid4()}"


@pytest.fixture
def inject_proposal(http_client, conversation_id):
    """Factory fixture: inject a proposal directly into the agent's in-memory state.

    Returns a function that:
      1. Creates an EstimateAgent for `conversation_id` (with a dummy token)
      2. Calls _propose_workload() with the given kwargs
      3. Returns the proposal_id

    This skips the LLM entirely — we're testing the confirm pipeline, not the AI.
    """
    from app.routes.chat import _conversation_agents
    from app.services.ai_agent import EstimateAgent

    def _inject(workload_type: str, workload_name: str, cloud: str = "aws",
                region: str = "us-east-1", tier: str = "PREMIUM", **kwargs):
        # Create agent if not exists
        if conversation_id not in _conversation_agents:
            agent = EstimateAgent.__new__(EstimateAgent)
            agent.proposed_workloads = []
            agent.current_workloads = []
            agent.current_estimate = {
                "cloud": cloud, "region": region, "tier": tier,
                "estimate_id": "test-estimate",
            }
            agent.conversation_history = []
            _conversation_agents[conversation_id] = agent

        agent = _conversation_agents[conversation_id]

        # Build proposal directly (same as _propose_workload but without defaults)
        proposal_id = str(uuid.uuid4())
        proposal = {
            "proposal_id": proposal_id,
            "workload_type": workload_type,
            "workload_name": workload_name,
            "cloud": cloud,
            "reason": "E2E test proposal",
            "status": "pending_confirmation",
            **kwargs,
        }
        agent.proposed_workloads.append(proposal)
        return proposal_id

    yield _inject

    # Cleanup: remove the agent
    from app.routes.chat import _conversation_agents as agents
    agents.pop(conversation_id, None)


@pytest.fixture
def confirm_workload(http_client, conversation_id):
    """Call the confirm-workload endpoint and return the response JSON."""
    from tests.e2e.helpers.api_client import AUTH_HEADERS

    def _confirm(proposal_id: str):
        resp = http_client.post(
            f"/api/v1/chat/{conversation_id}/confirm-workload",
            json={"proposal_id": proposal_id, "confirmed": True},
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200, f"Confirm failed: {resp.text}"
        data = resp.json()
        assert data["success"] is True
        assert data["action"] == "confirmed"
        return data["workload_config"]

    return _confirm
