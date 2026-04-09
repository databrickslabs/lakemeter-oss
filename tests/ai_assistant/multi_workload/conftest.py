"""Sprint 10 conftest — module-scoped fixtures for multi-workload tests.

Multi-workload conversations require multiple AI calls within the same
conversation_id. Each fixture builds a full conversation collecting
proposals across turns.
"""
import uuid

import pytest

from tests.ai_assistant.chat_helpers import (
    send_chat_until_proposal,
    confirm_proposal,
    extract_proposal,
    send_chat_message,
)
from tests.ai_assistant.multi_workload.prompts import (
    PLATFORM_PRIMARY, PLATFORM_FOLLOWUP, PLATFORM_FINAL,
    PLATFORM_NEXT_INTERACTIVE_PRIMARY, PLATFORM_NEXT_INTERACTIVE_FOLLOWUP,
    PLATFORM_NEXT_INTERACTIVE_FINAL,
    PLATFORM_NEXT_DBSQL_PRIMARY, PLATFORM_NEXT_DBSQL_FOLLOWUP,
    PLATFORM_NEXT_DBSQL_FINAL,
    TWO_WL_PRIMARY, TWO_WL_JOBS_FOLLOWUP, TWO_WL_JOBS_FINAL,
    TWO_WL_DBSQL_PRIMARY, TWO_WL_DBSQL_FOLLOWUP, TWO_WL_DBSQL_FINAL,
    NEG_DS_ONLY_PRIMARY, NEG_DS_ONLY_FOLLOWUP, NEG_DS_ONLY_FINAL,
)


def _collect_three_proposals(http_client, test_estimate):
    """Run a 3-workload conversation: JOBS → ALL_PURPOSE → DBSQL.

    Returns dict with keys: conversation_id, proposals (list of 3 dicts),
    confirmations (list of 3 confirm-response dicts).
    """
    cid = str(uuid.uuid4())
    proposals = []
    confirmations = []

    # --- Workload 1: JOBS ---
    jobs_proposal, _ = send_chat_until_proposal(
        http_client,
        [PLATFORM_PRIMARY, PLATFORM_FOLLOWUP, PLATFORM_FINAL],
        test_estimate,
        conversation_id=cid,
    )
    proposals.append(jobs_proposal)
    jobs_confirm = confirm_proposal(
        http_client, cid, jobs_proposal["proposal_id"]
    )
    confirmations.append(jobs_confirm)

    # --- Workload 2: ALL_PURPOSE ---
    ap_proposal, _ = send_chat_until_proposal(
        http_client,
        [
            PLATFORM_NEXT_INTERACTIVE_PRIMARY,
            PLATFORM_NEXT_INTERACTIVE_FOLLOWUP,
            PLATFORM_NEXT_INTERACTIVE_FINAL,
        ],
        test_estimate,
        conversation_id=cid,
    )
    proposals.append(ap_proposal)
    ap_confirm = confirm_proposal(
        http_client, cid, ap_proposal["proposal_id"]
    )
    confirmations.append(ap_confirm)

    # --- Workload 3: DBSQL ---
    dbsql_proposal, _ = send_chat_until_proposal(
        http_client,
        [
            PLATFORM_NEXT_DBSQL_PRIMARY,
            PLATFORM_NEXT_DBSQL_FOLLOWUP,
            PLATFORM_NEXT_DBSQL_FINAL,
        ],
        test_estimate,
        conversation_id=cid,
    )
    proposals.append(dbsql_proposal)
    dbsql_confirm = confirm_proposal(
        http_client, cid, dbsql_proposal["proposal_id"]
    )
    confirmations.append(dbsql_confirm)

    return {
        "conversation_id": cid,
        "proposals": proposals,
        "confirmations": confirmations,
    }


def _collect_two_proposals(http_client, test_estimate):
    """Run a 2-workload conversation: JOBS → DBSQL.

    Returns dict with keys: conversation_id, proposals, confirmations.
    """
    cid = str(uuid.uuid4())
    proposals = []
    confirmations = []

    # --- Workload 1: JOBS ---
    jobs_proposal, _ = send_chat_until_proposal(
        http_client,
        [TWO_WL_PRIMARY, TWO_WL_JOBS_FOLLOWUP, TWO_WL_JOBS_FINAL],
        test_estimate,
        conversation_id=cid,
    )
    proposals.append(jobs_proposal)
    jobs_confirm = confirm_proposal(
        http_client, cid, jobs_proposal["proposal_id"]
    )
    confirmations.append(jobs_confirm)

    # --- Workload 2: DBSQL ---
    dbsql_proposal, _ = send_chat_until_proposal(
        http_client,
        [TWO_WL_DBSQL_PRIMARY, TWO_WL_DBSQL_FOLLOWUP, TWO_WL_DBSQL_FINAL],
        test_estimate,
        conversation_id=cid,
    )
    proposals.append(dbsql_proposal)
    dbsql_confirm = confirm_proposal(
        http_client, cid, dbsql_proposal["proposal_id"]
    )
    confirmations.append(dbsql_confirm)

    return {
        "conversation_id": cid,
        "proposals": proposals,
        "confirmations": confirmations,
    }


@pytest.fixture(scope="module")
def three_workload_session(http_client, test_estimate):
    """Full 3-workload conversation: JOBS + ALL_PURPOSE + DBSQL.

    Expensive fixture (3+ AI calls). Shared across all tests in
    test_multi_three_workloads.py.
    """
    return _collect_three_proposals(http_client, test_estimate)


@pytest.fixture(scope="module")
def two_workload_session(http_client, test_estimate):
    """2-workload conversation: JOBS + DBSQL.

    Shared across all tests in test_multi_two_workloads.py.
    """
    return _collect_two_proposals(http_client, test_estimate)


@pytest.fixture(scope="module")
def negative_ds_only_proposal(http_client, test_estimate):
    """Single-workload: data science only — should produce ALL_PURPOSE."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [NEG_DS_ONLY_PRIMARY, NEG_DS_ONLY_FOLLOWUP, NEG_DS_ONLY_FINAL],
        test_estimate,
    )
    return proposal
