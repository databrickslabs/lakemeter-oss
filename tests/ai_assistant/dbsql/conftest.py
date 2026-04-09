"""Sprint 4 conftest — module-scoped fixtures for DBSQL proposal tests.

Each fixture makes one AI call and is shared across tests in its file.
Five variants: SERVERLESS, PRO, CLASSIC, non-DBSQL interactive, non-DBSQL batch ETL.
"""
import pytest

from tests.ai_assistant.conftest import send_chat_until_proposal
from tests.ai_assistant.dbsql.prompts import (
    DBSQL_SERVERLESS_PRIMARY, DBSQL_SERVERLESS_FOLLOWUP, DBSQL_SERVERLESS_FINAL,
    DBSQL_PRO_PRIMARY, DBSQL_PRO_FOLLOWUP, DBSQL_PRO_FINAL,
    DBSQL_CLASSIC_PRIMARY, DBSQL_CLASSIC_FOLLOWUP, DBSQL_CLASSIC_FINAL,
    NON_DBSQL_PRIMARY, NON_DBSQL_FOLLOWUP, NON_DBSQL_FINAL,
    NON_DBSQL_ETL_PRIMARY, NON_DBSQL_ETL_FOLLOWUP, NON_DBSQL_ETL_FINAL,
)


@pytest.fixture(scope="module")
def dbsql_serverless_proposal(http_client, test_estimate):
    """Single AI call for DBSQL Serverless Medium — shared by serverless tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [DBSQL_SERVERLESS_PRIMARY, DBSQL_SERVERLESS_FOLLOWUP, DBSQL_SERVERLESS_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def dbsql_pro_proposal(http_client, test_estimate):
    """Single AI call for DBSQL Pro Large — shared by pro tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [DBSQL_PRO_PRIMARY, DBSQL_PRO_FOLLOWUP, DBSQL_PRO_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def dbsql_classic_proposal(http_client, test_estimate):
    """Single AI call for DBSQL Classic Small — shared by classic tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [DBSQL_CLASSIC_PRIMARY, DBSQL_CLASSIC_FOLLOWUP, DBSQL_CLASSIC_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def non_dbsql_proposal(http_client, test_estimate):
    """AI call for interactive compute — should NOT produce DBSQL."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [NON_DBSQL_PRIMARY, NON_DBSQL_FOLLOWUP, NON_DBSQL_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def non_dbsql_etl_proposal(http_client, test_estimate):
    """AI call for batch ETL — should NOT produce DBSQL."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [NON_DBSQL_ETL_PRIMARY, NON_DBSQL_ETL_FOLLOWUP, NON_DBSQL_ETL_FINAL],
        test_estimate,
    )
    return proposal
