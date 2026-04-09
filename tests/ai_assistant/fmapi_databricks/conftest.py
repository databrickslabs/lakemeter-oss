"""Sprint 7 conftest — module-scoped fixtures for FMAPI_DATABRICKS proposal tests.

Each fixture makes one AI call and is shared across tests in its file.
Five variants: Llama input, output tokens, BGE embeddings, non-DB Claude, non-DB GPU.
"""
import pytest

from tests.ai_assistant.conftest import send_chat_until_proposal
from tests.ai_assistant.fmapi_databricks.prompts import (
    LLAMA_INPUT_PRIMARY, LLAMA_INPUT_FOLLOWUP, LLAMA_INPUT_FINAL,
    OUTPUT_TOKEN_PRIMARY, OUTPUT_TOKEN_FOLLOWUP, OUTPUT_TOKEN_FINAL,
    EMBEDDINGS_PRIMARY, EMBEDDINGS_FOLLOWUP, EMBEDDINGS_FINAL,
    NON_DB_CLAUDE_PRIMARY, NON_DB_CLAUDE_FOLLOWUP, NON_DB_CLAUDE_FINAL,
    NON_DB_GPU_PRIMARY, NON_DB_GPU_FOLLOWUP, NON_DB_GPU_FINAL,
)


@pytest.fixture(scope="module")
def llama_input_proposal(http_client, test_estimate):
    """AI call for Llama 4 Maverick input tokens — shared by input tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [LLAMA_INPUT_PRIMARY, LLAMA_INPUT_FOLLOWUP, LLAMA_INPUT_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def output_token_proposal(http_client, test_estimate):
    """AI call for Llama output tokens — shared by output token tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [OUTPUT_TOKEN_PRIMARY, OUTPUT_TOKEN_FOLLOWUP, OUTPUT_TOKEN_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def embeddings_proposal(http_client, test_estimate):
    """AI call for BGE-Large embeddings — shared by embeddings tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [EMBEDDINGS_PRIMARY, EMBEDDINGS_FOLLOWUP, EMBEDDINGS_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def non_db_claude_proposal(http_client, test_estimate):
    """AI call for Claude (proprietary) — should NOT produce FMAPI_DATABRICKS."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [NON_DB_CLAUDE_PRIMARY, NON_DB_CLAUDE_FOLLOWUP, NON_DB_CLAUDE_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def non_db_gpu_proposal(http_client, test_estimate):
    """AI call for GPU model serving — should NOT produce FMAPI_DATABRICKS."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [NON_DB_GPU_PRIMARY, NON_DB_GPU_FOLLOWUP, NON_DB_GPU_FINAL],
        test_estimate,
    )
    return proposal
