"""Sprint 8 conftest — module-scoped fixtures for FMAPI_PROPRIETARY proposal tests.

Each fixture makes one AI call and is shared across tests in its file.
Three positive: Claude (Anthropic), GPT (OpenAI), Gemini (Google).
Two negative: Llama (FMAPI_DATABRICKS), GPU serving (MODEL_SERVING).
"""
import pytest

from tests.ai_assistant.conftest import send_chat_until_proposal
from tests.ai_assistant.fmapi_proprietary.prompts import (
    CLAUDE_INPUT_PRIMARY, CLAUDE_INPUT_FOLLOWUP, CLAUDE_INPUT_FINAL,
    GPT_INPUT_PRIMARY, GPT_INPUT_FOLLOWUP, GPT_INPUT_FINAL,
    GEMINI_INPUT_PRIMARY, GEMINI_INPUT_FOLLOWUP, GEMINI_INPUT_FINAL,
    NON_PROP_LLAMA_PRIMARY, NON_PROP_LLAMA_FOLLOWUP, NON_PROP_LLAMA_FINAL,
    NON_PROP_GPU_PRIMARY, NON_PROP_GPU_FOLLOWUP, NON_PROP_GPU_FINAL,
)


@pytest.fixture(scope="module")
def claude_input_proposal(http_client, test_estimate):
    """AI call for Claude Sonnet 4.5 input tokens — shared by Claude tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [CLAUDE_INPUT_PRIMARY, CLAUDE_INPUT_FOLLOWUP, CLAUDE_INPUT_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def gpt_input_proposal(http_client, test_estimate):
    """AI call for GPT-5 mini input tokens — shared by OpenAI tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [GPT_INPUT_PRIMARY, GPT_INPUT_FOLLOWUP, GPT_INPUT_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def gemini_input_proposal(http_client, test_estimate):
    """AI call for Gemini 2.5 Flash input tokens — shared by Google tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [GEMINI_INPUT_PRIMARY, GEMINI_INPUT_FOLLOWUP, GEMINI_INPUT_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def non_prop_llama_proposal(http_client, test_estimate):
    """AI call for Llama (open model) — should NOT produce FMAPI_PROPRIETARY."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [NON_PROP_LLAMA_PRIMARY, NON_PROP_LLAMA_FOLLOWUP, NON_PROP_LLAMA_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def non_prop_gpu_proposal(http_client, test_estimate):
    """AI call for GPU model serving — should NOT produce FMAPI_PROPRIETARY."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [NON_PROP_GPU_PRIMARY, NON_PROP_GPU_FOLLOWUP, NON_PROP_GPU_FINAL],
        test_estimate,
    )
    return proposal
