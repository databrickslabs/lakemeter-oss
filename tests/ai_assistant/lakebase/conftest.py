"""Sprint 9 conftest — module-scoped fixtures for LAKEBASE proposal tests.

Each fixture makes one AI call and is shared across tests in its file.
Two positive: HA production (4 CU, 500GB, HA), small dev/test (0.5 CU, 10GB).
Two negative: ETL pipeline (JOBS), SQL analytics (DBSQL).
"""
import pytest

from tests.ai_assistant.conftest import send_chat_until_proposal
from tests.ai_assistant.lakebase.prompts import (
    HA_PROD_PRIMARY, HA_PROD_FOLLOWUP, HA_PROD_FINAL,
    SMALL_DEV_PRIMARY, SMALL_DEV_FOLLOWUP, SMALL_DEV_FINAL,
    NON_LB_ETL_PRIMARY, NON_LB_ETL_FOLLOWUP, NON_LB_ETL_FINAL,
    NON_LB_SQL_PRIMARY, NON_LB_SQL_FOLLOWUP, NON_LB_SQL_FINAL,
)


@pytest.fixture(scope="module")
def ha_prod_proposal(http_client, test_estimate):
    """AI call for HA production Lakebase — shared by HA prod tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [HA_PROD_PRIMARY, HA_PROD_FOLLOWUP, HA_PROD_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def small_dev_proposal(http_client, test_estimate):
    """AI call for small dev/test Lakebase — shared by small dev tests."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [SMALL_DEV_PRIMARY, SMALL_DEV_FOLLOWUP, SMALL_DEV_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def non_lb_etl_proposal(http_client, test_estimate):
    """AI call for ETL pipeline — should NOT produce LAKEBASE."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [NON_LB_ETL_PRIMARY, NON_LB_ETL_FOLLOWUP, NON_LB_ETL_FINAL],
        test_estimate,
    )
    return proposal


@pytest.fixture(scope="module")
def non_lb_sql_proposal(http_client, test_estimate):
    """AI call for SQL analytics — should NOT produce LAKEBASE."""
    proposal, resp = send_chat_until_proposal(
        http_client,
        [NON_LB_SQL_PRIMARY, NON_LB_SQL_FOLLOWUP, NON_LB_SQL_FINAL],
        test_estimate,
    )
    return proposal
