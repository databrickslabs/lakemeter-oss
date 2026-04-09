"""Chat helper utilities for AI assistant end-to-end tests.

Shared functions for sending messages, extracting proposals,
confirming/rejecting workloads, and fetching conversation state.
"""
import time
import uuid
from typing import Optional

AUTH_EMAIL = "test-harness@databricks.com"
AUTH_HEADERS = {"X-Forwarded-Email": AUTH_EMAIL}


def send_chat_message(
    http_client,
    message: str,
    estimate: dict,
    conversation_id: Optional[str] = None,
    workloads_context: Optional[list] = None,
    max_retries: int = 2,
) -> dict:
    """Send a non-streaming chat message and return the parsed response.

    Retries on 500 errors (rate-limit, transient Claude failures) with a
    30-second backoff between attempts.
    """
    cid = conversation_id or str(uuid.uuid4())
    payload = {
        "message": message,
        "conversation_id": cid,
        "estimate_context": {
            "estimate_id": estimate["estimate_id"],
            "estimate_name": estimate["estimate_name"],
            "cloud": estimate.get("cloud", "AWS"),
            "region": estimate.get("region", "us-east-1"),
            "tier": estimate.get("tier", "PREMIUM"),
        },
        "workloads_context": workloads_context or [],
        "mode": "estimate",
        "stream": False,
    }
    last_err = ""
    for attempt in range(1 + max_retries):
        resp = http_client.post(
            "/api/v1/chat", json=payload, headers=AUTH_HEADERS
        )
        if resp.status_code == 200:
            data = resp.json()
            data["_conversation_id"] = data.get("conversation_id", cid)
            return data
        last_err = resp.text[:300]
        if attempt < max_retries:
            time.sleep(30)  # back off for rate limits
    assert False, (
        f"Chat call failed after {1 + max_retries} attempts "
        f"({resp.status_code}): {last_err}"
    )


def extract_proposal(response: dict) -> Optional[dict]:
    """Extract proposed_workload from a chat response."""
    pw = response.get("proposed_workload")
    if pw:
        return pw
    for tr in response.get("tool_results") or []:
        if (
            tr.get("tool") == "propose_workload"
            and tr.get("result", {}).get("success")
        ):
            return tr["result"].get("workload")
    return None


def send_chat_until_proposal(
    http_client,
    messages: list[str],
    estimate: dict,
    conversation_id: Optional[str] = None,
) -> tuple[dict, dict]:
    """Send messages sequentially until we get a proposed_workload.

    Returns (proposal_dict, last_response_dict).
    Raises AssertionError if no proposal after all messages.
    """
    cid = conversation_id or str(uuid.uuid4())
    last_resp: dict = {}
    for msg in messages:
        last_resp = send_chat_message(
            http_client, msg, estimate, conversation_id=cid
        )
        proposal = extract_proposal(last_resp)
        if proposal:
            return proposal, last_resp
    raise AssertionError(
        f"No proposal after {len(messages)} messages. "
        f"Last response: {last_resp.get('content', '')[:300]}"
    )


def confirm_proposal(http_client, conversation_id: str, proposal_id: str) -> dict:
    """Confirm a proposed workload."""
    resp = http_client.post(
        f"/api/v1/chat/{conversation_id}/confirm-workload",
        json={"proposal_id": proposal_id, "confirmed": True},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200, f"Confirm failed: {resp.text[:200]}"
    return resp.json()


def reject_proposal(http_client, conversation_id: str, proposal_id: str) -> dict:
    """Reject a proposed workload."""
    resp = http_client.post(
        f"/api/v1/chat/{conversation_id}/confirm-workload",
        json={"proposal_id": proposal_id, "confirmed": False},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200, f"Reject failed: {resp.text[:200]}"
    return resp.json()


def get_conversation_state(http_client, conversation_id: str) -> dict:
    """Get conversation state (pending proposals, confirmed workloads)."""
    resp = http_client.get(
        f"/api/v1/chat/{conversation_id}/state",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200, f"State fetch failed: {resp.text[:200]}"
    return resp.json()
