"""Sprint 3 conftest — module-scoped fixtures for DLT/SDP proposal tests.

Each fixture makes one AI call and is shared across tests in this package.
Four variants: PRO serverless, CORE classic, ADVANCED serverless, non-DLT negative.
"""
import pytest

from tests.ai_assistant.conftest import send_chat_until_proposal
from tests.ai_assistant.dlt.prompts import (
    DLT_PRO_PRIMARY, DLT_PRO_FOLLOWUP, DLT_PRO_FINAL,
    DLT_CORE_PRIMARY, DLT_CORE_FOLLOWUP, DLT_CORE_FINAL,
    DLT_ADVANCED_PRIMARY, DLT_ADVANCED_FOLLOWUP, DLT_ADVANCED_FINAL,
    NON_DLT_PRIMARY, NON_DLT_FOLLOWUP, NON_DLT_FINAL,
)


@pytest.fixture(scope="module")
def dlt_pro_proposal(http_client, test_estimate):
    """Single AI call for DLT Pro serverless — shared by basic tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [DLT_PRO_PRIMARY, DLT_PRO_FOLLOWUP, DLT_PRO_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def dlt_core_proposal(http_client, test_estimate):
    """Single AI call for DLT Core classic."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [DLT_CORE_PRIMARY, DLT_CORE_FOLLOWUP, DLT_CORE_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def dlt_advanced_proposal(http_client, test_estimate):
    """Single AI call for DLT Advanced serverless."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [DLT_ADVANCED_PRIMARY, DLT_ADVANCED_FOLLOWUP, DLT_ADVANCED_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def non_dlt_proposal(http_client, test_estimate):
    """AI call for an interactive compute request — should NOT be DLT."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [NON_DLT_PRIMARY, NON_DLT_FOLLOWUP, NON_DLT_FINAL],
        test_estimate,
    )
    return proposal
