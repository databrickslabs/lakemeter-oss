"""Sprint 11 conftest — module-scoped fixtures for ML pipeline tests.

ML pipeline conversations require multiple AI calls within the same
conversation_id. Each fixture builds a full conversation collecting
proposals across turns for VECTOR_SEARCH, FMAPI_PROPRIETARY, MODEL_SERVING.
"""
import uuid

import pytest

from tests.ai_assistant.chat_helpers import (
    send_chat_until_proposal,
    confirm_proposal,
)
from tests.ai_assistant.ml_pipeline.prompts import (
    RAG_PRIMARY, RAG_VS_FOLLOWUP, RAG_VS_FINAL,
    RAG_FMAPI_PRIMARY, RAG_FMAPI_FOLLOWUP, RAG_FMAPI_FINAL,
    RAG_MS_PRIMARY, RAG_MS_FOLLOWUP, RAG_MS_FINAL,
    TWO_WL_PRIMARY, TWO_WL_VS_FOLLOWUP, TWO_WL_VS_FINAL,
    TWO_WL_FMAPI_PRIMARY, TWO_WL_FMAPI_FOLLOWUP, TWO_WL_FMAPI_FINAL,
    NEG_MS_ONLY_PRIMARY, NEG_MS_ONLY_FOLLOWUP, NEG_MS_ONLY_FINAL,
)


def _collect_ml_pipeline_proposals(http_client, test_estimate):
    """Run a 3-workload ML pipeline conversation.

    VECTOR_SEARCH -> FMAPI_PROPRIETARY -> MODEL_SERVING.
    Returns dict with conversation_id, proposals, confirmations.
    """
    cid = str(uuid.uuid4())
    proposals = []
    confirmations = []

    # --- Workload 1: VECTOR_SEARCH ---
    vs_proposal, _ = send_chat_until_proposal(
        http_client,
        [RAG_PRIMARY, RAG_VS_FOLLOWUP, RAG_VS_FINAL],
        test_estimate,
        conversation_id=cid,
    )
    proposals.append(vs_proposal)
    vs_confirm = confirm_proposal(
        http_client, cid, vs_proposal["proposal_id"]
    )
    confirmations.append(vs_confirm)

    # --- Workload 2: FMAPI_PROPRIETARY ---
    fmapi_proposal, _ = send_chat_until_proposal(
        http_client,
        [RAG_FMAPI_PRIMARY, RAG_FMAPI_FOLLOWUP, RAG_FMAPI_FINAL],
        test_estimate,
        conversation_id=cid,
    )
    proposals.append(fmapi_proposal)
    fmapi_confirm = confirm_proposal(
        http_client, cid, fmapi_proposal["proposal_id"]
    )
    confirmations.append(fmapi_confirm)

    # --- Workload 3: MODEL_SERVING ---
    ms_proposal, _ = send_chat_until_proposal(
        http_client,
        [RAG_MS_PRIMARY, RAG_MS_FOLLOWUP, RAG_MS_FINAL],
        test_estimate,
        conversation_id=cid,
    )
    proposals.append(ms_proposal)
    ms_confirm = confirm_proposal(
        http_client, cid, ms_proposal["proposal_id"]
    )
    confirmations.append(ms_confirm)

    return {
        "conversation_id": cid,
        "proposals": proposals,
        "confirmations": confirmations,
    }


def _collect_two_ml_proposals(http_client, test_estimate):
    """Run a 2-workload conversation: VECTOR_SEARCH -> FMAPI_PROPRIETARY.

    Returns dict with conversation_id, proposals, confirmations.
    """
    cid = str(uuid.uuid4())
    proposals = []
    confirmations = []

    # --- Workload 1: VECTOR_SEARCH ---
    vs_proposal, _ = send_chat_until_proposal(
        http_client,
        [TWO_WL_PRIMARY, TWO_WL_VS_FOLLOWUP, TWO_WL_VS_FINAL],
        test_estimate,
        conversation_id=cid,
    )
    proposals.append(vs_proposal)
    vs_confirm = confirm_proposal(
        http_client, cid, vs_proposal["proposal_id"]
    )
    confirmations.append(vs_confirm)

    # --- Workload 2: FMAPI_PROPRIETARY ---
    fmapi_proposal, _ = send_chat_until_proposal(
        http_client,
        [
            TWO_WL_FMAPI_PRIMARY,
            TWO_WL_FMAPI_FOLLOWUP,
            TWO_WL_FMAPI_FINAL,
        ],
        test_estimate,
        conversation_id=cid,
    )
    proposals.append(fmapi_proposal)
    fmapi_confirm = confirm_proposal(
        http_client, cid, fmapi_proposal["proposal_id"]
    )
    confirmations.append(fmapi_confirm)

    return {
        "conversation_id": cid,
        "proposals": proposals,
        "confirmations": confirmations,
    }


@pytest.fixture(scope="module")
def ml_pipeline_session(http_client, test_estimate):
    """Full 3-workload ML pipeline: VS + FMAPI_PROP + MODEL_SERVING."""
    return _collect_ml_pipeline_proposals(http_client, test_estimate)


@pytest.fixture(scope="module")
def two_ml_session(http_client, test_estimate):
    """2-workload ML session: VECTOR_SEARCH + FMAPI_PROPRIETARY."""
    return _collect_two_ml_proposals(http_client, test_estimate)


@pytest.fixture(scope="module")
def negative_ms_only_proposal(http_client, test_estimate):
    """Single-workload: model serving only — should not produce VS/FMAPI."""
    proposal, _ = send_chat_until_proposal(
        http_client,
        [NEG_MS_ONLY_PRIMARY, NEG_MS_ONLY_FOLLOWUP, NEG_MS_ONLY_FINAL],
        test_estimate,
    )
    return proposal
