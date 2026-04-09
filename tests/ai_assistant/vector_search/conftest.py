"""Sprint 6 conftest — module-scoped fixtures for VECTOR_SEARCH proposal tests.

Each fixture makes one AI call and is shared across tests in its file.
Five variants: STANDARD, STORAGE_OPTIMIZED, SMALL_RAG, non-VS model, non-VS SQL.
"""
import pytest

from tests.ai_assistant.conftest import send_chat_until_proposal
from tests.ai_assistant.vector_search.prompts import (
    STANDARD_PRIMARY, STANDARD_FOLLOWUP, STANDARD_FINAL,
    STORAGE_OPT_PRIMARY, STORAGE_OPT_FOLLOWUP, STORAGE_OPT_FINAL,
    SMALL_RAG_PRIMARY, SMALL_RAG_FOLLOWUP, SMALL_RAG_FINAL,
    NON_VS_MODEL_PRIMARY, NON_VS_MODEL_FOLLOWUP, NON_VS_MODEL_FINAL,
    NON_VS_SQL_PRIMARY, NON_VS_SQL_FOLLOWUP, NON_VS_SQL_FINAL,
)


@pytest.fixture(scope="module")
def standard_proposal(http_client, test_estimate):
    """Single AI call for Vector Search Standard — shared by standard tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [STANDARD_PRIMARY, STANDARD_FOLLOWUP, STANDARD_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def storage_optimized_proposal(http_client, test_estimate):
    """Single AI call for Vector Search Storage-Optimized — shared by SO tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [STORAGE_OPT_PRIMARY, STORAGE_OPT_FOLLOWUP, STORAGE_OPT_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def small_rag_proposal(http_client, test_estimate):
    """Single AI call for Vector Search Small RAG — shared by small RAG tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [SMALL_RAG_PRIMARY, SMALL_RAG_FOLLOWUP, SMALL_RAG_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def non_vs_model_proposal(http_client, test_estimate):
    """AI call for model serving — should NOT produce VECTOR_SEARCH."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [NON_VS_MODEL_PRIMARY, NON_VS_MODEL_FOLLOWUP, NON_VS_MODEL_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def non_vs_sql_proposal(http_client, test_estimate):
    """AI call for SQL analytics — should NOT produce VECTOR_SEARCH."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [NON_VS_SQL_PRIMARY, NON_VS_SQL_FOLLOWUP, NON_VS_SQL_FINAL],
        test_estimate,
    )
    return proposal
