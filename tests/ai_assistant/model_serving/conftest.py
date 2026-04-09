"""Sprint 5 conftest — module-scoped fixtures for MODEL_SERVING proposal tests.

Each fixture makes one AI call and is shared across tests in its file.
Five variants: GPU_MEDIUM, CPU, GPU_SMALL, non-serving interactive, non-serving ETL.
"""
import pytest

from tests.ai_assistant.conftest import send_chat_until_proposal
from tests.ai_assistant.model_serving.prompts import (
    GPU_MEDIUM_PRIMARY, GPU_MEDIUM_FOLLOWUP, GPU_MEDIUM_FINAL,
    CPU_PRIMARY, CPU_FOLLOWUP, CPU_FINAL,
    GPU_SMALL_PRIMARY, GPU_SMALL_FOLLOWUP, GPU_SMALL_FINAL,
    NON_SERVING_INTERACTIVE_PRIMARY, NON_SERVING_INTERACTIVE_FOLLOWUP,
    NON_SERVING_INTERACTIVE_FINAL,
    NON_SERVING_ETL_PRIMARY, NON_SERVING_ETL_FOLLOWUP,
    NON_SERVING_ETL_FINAL,
)


@pytest.fixture(scope="module")
def gpu_medium_proposal(http_client, test_estimate):
    """Single AI call for Model Serving GPU Medium — shared by gpu_medium tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [GPU_MEDIUM_PRIMARY, GPU_MEDIUM_FOLLOWUP, GPU_MEDIUM_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def cpu_proposal(http_client, test_estimate):
    """Single AI call for Model Serving CPU — shared by cpu tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [CPU_PRIMARY, CPU_FOLLOWUP, CPU_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def gpu_small_proposal(http_client, test_estimate):
    """Single AI call for Model Serving GPU Small — shared by gpu_small tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [GPU_SMALL_PRIMARY, GPU_SMALL_FOLLOWUP, GPU_SMALL_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def non_serving_interactive_proposal(http_client, test_estimate):
    """AI call for interactive compute — should NOT produce MODEL_SERVING."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [NON_SERVING_INTERACTIVE_PRIMARY, NON_SERVING_INTERACTIVE_FOLLOWUP,
         NON_SERVING_INTERACTIVE_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def non_serving_etl_proposal(http_client, test_estimate):
    """AI call for batch ETL — should NOT produce MODEL_SERVING."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [NON_SERVING_ETL_PRIMARY, NON_SERVING_ETL_FOLLOWUP,
         NON_SERVING_ETL_FINAL],
        test_estimate,
    )
    return proposal
