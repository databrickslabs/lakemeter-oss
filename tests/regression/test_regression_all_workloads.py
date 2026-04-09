"""Sprint 5: Multi-config regression tests for all 9 workload types.

Verifies that every workload type with multiple configurations produces
valid, non-negative DBU/hr values, correct SKUs, correct serverless
classification, and valid hours — covering classic/photon/serverless
variants. This catches regressions introduced by Sprints 1-4 fixes.
"""
import math
import pytest

from tests.regression.conftest import (
    make_jobs_classic, make_jobs_photon,
    make_jobs_serverless_std, make_jobs_serverless_perf,
    make_ap_classic, make_ap_photon, make_ap_serverless,
    make_dlt_core_classic, make_dlt_pro_serverless, make_dlt_advanced_photon,
    make_dbsql_classic_small, make_dbsql_pro_medium, make_dbsql_serverless_large,
    make_ms_cpu, make_ms_gpu_a10g,
    make_fmapi_db_input, make_fmapi_db_output, make_fmapi_db_batch,
    make_fmapi_db_provisioned,
    make_fmapi_prop_openai_input, make_fmapi_prop_anthropic_output,
    make_fmapi_prop_google_input,
    make_vs_standard, make_vs_storage_opt,
    make_lakebase_small, make_lakebase_large,
    make_all_regression_items,
)
from app.routes.export.calculations import (
    _calculate_dbu_per_hour, _calculate_hours_per_month, _is_serverless_workload,
)
from app.routes.export.pricing import _get_sku_type, _get_dbu_price
from app.routes.export.excel_item_helpers import calc_item_values


# ---------- JOBS ----------
class TestJobsRegression:
    def test_classic_dbu(self):
        dbu, w = _calculate_dbu_per_hour(make_jobs_classic(), 'aws')
        assert dbu == pytest.approx(0.5, abs=0.01)  # driver fallback only

    def test_classic_sku(self):
        assert _get_sku_type(make_jobs_classic(), 'aws') == 'JOBS_COMPUTE'

    def test_classic_not_serverless(self):
        assert _is_serverless_workload(make_jobs_classic()) is False

    def test_photon_dbu(self):
        dbu, _ = _calculate_dbu_per_hour(make_jobs_photon(), 'aws')
        # (0.5 + 0.5*2) * photon_mult(~2.0) = 1.5 * 2.0 = 3.0
        assert dbu > 0

    def test_photon_sku(self):
        assert _get_sku_type(make_jobs_photon(), 'aws') == 'JOBS_COMPUTE_(PHOTON)'

    def test_serverless_std_dbu(self):
        dbu, _ = _calculate_dbu_per_hour(make_jobs_serverless_std(), 'aws')
        # serverless standard: base * photon_mult * 1
        assert dbu > 0

    def test_serverless_perf_dbu(self):
        dbu, _ = _calculate_dbu_per_hour(make_jobs_serverless_perf(), 'aws')
        # serverless perf: base * photon_mult * 2
        assert dbu > 0

    def test_serverless_perf_double_std(self):
        dbu_std, _ = _calculate_dbu_per_hour(make_jobs_serverless_std(), 'aws')
        dbu_perf, _ = _calculate_dbu_per_hour(make_jobs_serverless_perf(), 'aws')
        assert dbu_perf == pytest.approx(dbu_std * 2, abs=0.01)

    def test_serverless_sku(self):
        assert _get_sku_type(make_jobs_serverless_std(), 'aws') == 'JOBS_SERVERLESS_COMPUTE'

    def test_serverless_is_serverless(self):
        assert _is_serverless_workload(make_jobs_serverless_std()) is True


# ---------- ALL_PURPOSE ----------
class TestAllPurposeRegression:
    def test_classic_dbu(self):
        dbu, _ = _calculate_dbu_per_hour(make_ap_classic(), 'aws')
        assert dbu == pytest.approx(1.0, abs=0.01)  # 0.5 + 0.5*1

    def test_classic_sku(self):
        assert _get_sku_type(make_ap_classic(), 'aws') == 'ALL_PURPOSE_COMPUTE'

    def test_photon_dbu(self):
        dbu, _ = _calculate_dbu_per_hour(make_ap_photon(), 'aws')
        assert dbu > 0

    def test_photon_sku(self):
        assert _get_sku_type(make_ap_photon(), 'aws') == 'ALL_PURPOSE_COMPUTE_(PHOTON)'

    def test_serverless_dbu(self):
        dbu, _ = _calculate_dbu_per_hour(make_ap_serverless(), 'aws')
        # AP serverless always uses mode_multiplier=2
        assert dbu > 0

    def test_serverless_sku(self):
        assert _get_sku_type(make_ap_serverless(), 'aws') == 'ALL_PURPOSE_SERVERLESS_COMPUTE'

    def test_serverless_is_serverless(self):
        assert _is_serverless_workload(make_ap_serverless()) is True

    def test_classic_not_serverless(self):
        assert _is_serverless_workload(make_ap_classic()) is False


# ---------- DLT ----------
class TestDltRegression:
    def test_core_classic_dbu(self):
        dbu, _ = _calculate_dbu_per_hour(make_dlt_core_classic(), 'aws')
        assert dbu == pytest.approx(0.5, abs=0.01)  # no photon, no workers

    def test_core_classic_sku(self):
        assert _get_sku_type(make_dlt_core_classic(), 'aws') == 'DLT_CORE_COMPUTE'

    def test_pro_serverless_dbu(self):
        dbu, _ = _calculate_dbu_per_hour(make_dlt_pro_serverless(), 'aws')
        assert dbu > 0

    def test_pro_serverless_sku(self):
        assert _get_sku_type(make_dlt_pro_serverless(), 'aws') == 'JOBS_SERVERLESS_COMPUTE'

    def test_advanced_photon_dbu(self):
        dbu, _ = _calculate_dbu_per_hour(make_dlt_advanced_photon(), 'aws')
        assert dbu > 0

    def test_advanced_photon_sku(self):
        assert _get_sku_type(make_dlt_advanced_photon(), 'aws') == 'DLT_ADVANCED_COMPUTE_(PHOTON)'

    def test_core_not_serverless(self):
        assert _is_serverless_workload(make_dlt_core_classic()) is False

    def test_pro_sl_is_serverless(self):
        assert _is_serverless_workload(make_dlt_pro_serverless()) is True


# ---------- DBSQL ----------
class TestDbsqlRegression:
    def test_classic_small_dbu(self):
        dbu, _ = _calculate_dbu_per_hour(make_dbsql_classic_small(), 'aws')
        assert dbu == pytest.approx(12, abs=0.01)

    def test_classic_sku(self):
        assert _get_sku_type(make_dbsql_classic_small(), 'aws') == 'SQL_COMPUTE'

    def test_pro_medium_dbu(self):
        dbu, _ = _calculate_dbu_per_hour(make_dbsql_pro_medium(), 'aws')
        assert dbu == pytest.approx(24, abs=0.01)

    def test_pro_sku(self):
        assert _get_sku_type(make_dbsql_pro_medium(), 'aws') == 'SQL_PRO_COMPUTE'

    def test_serverless_large_dbu(self):
        dbu, _ = _calculate_dbu_per_hour(make_dbsql_serverless_large(), 'aws')
        assert dbu == pytest.approx(40, abs=0.01)

    def test_serverless_sku(self):
        assert _get_sku_type(make_dbsql_serverless_large(), 'aws') == 'SERVERLESS_SQL_COMPUTE'

    def test_classic_not_serverless(self):
        assert _is_serverless_workload(make_dbsql_classic_small()) is False

    def test_serverless_is_serverless(self):
        assert _is_serverless_workload(make_dbsql_serverless_large()) is True


# ---------- MODEL_SERVING ----------
class TestModelServingRegression:
    def test_cpu_dbu(self):
        dbu, _ = _calculate_dbu_per_hour(make_ms_cpu(), 'aws')
        assert dbu >= 0

    def test_gpu_a10g_dbu(self):
        dbu, _ = _calculate_dbu_per_hour(make_ms_gpu_a10g(), 'aws')
        assert dbu == pytest.approx(20.0, abs=0.01)

    def test_sku(self):
        assert _get_sku_type(make_ms_cpu(), 'aws') == 'SERVERLESS_REAL_TIME_INFERENCE'

    def test_always_serverless(self):
        assert _is_serverless_workload(make_ms_cpu()) is True
        assert _is_serverless_workload(make_ms_gpu_a10g()) is True


# ---------- FMAPI_DATABRICKS ----------
class TestFmapiDbRegression:
    def test_input_token_calc(self):
        item = make_fmapi_db_input()
        h, tq, dpm, total, tt = calc_item_values(item, True, False, 0, 'aws', [])
        assert tq == 100
        assert total == pytest.approx(tq * dpm, abs=0.01)
        assert tt == 'Input'

    def test_output_token_calc(self):
        item = make_fmapi_db_output()
        h, tq, dpm, total, tt = calc_item_values(item, True, False, 0, 'aws', [])
        assert tq == 50
        assert tt == 'Output'

    def test_batch_inference_is_token_based(self):
        item = make_fmapi_db_batch()
        # batch_inference uses token-based billing
        h, tq, dpm, total, tt = calc_item_values(item, True, False, 0, 'aws', [])
        assert tq == 200
        assert tt == 'Batch'

    def test_provisioned_is_hourly(self):
        item = make_fmapi_db_provisioned()
        h, tq, dpm, total, tt = calc_item_values(item, False, True, 0, 'aws', [])
        assert h == 100  # fmapi_quantity as hours
        assert total > 0

    def test_dbu_per_hour_is_zero(self):
        dbu, _ = _calculate_dbu_per_hour(make_fmapi_db_input(), 'aws')
        assert dbu == 0


# ---------- FMAPI_PROPRIETARY ----------
class TestFmapiPropRegression:
    def test_openai_input(self):
        item = make_fmapi_prop_openai_input()
        h, tq, dpm, total, tt = calc_item_values(item, True, False, 0, 'aws', [])
        assert tq == 80
        assert total == pytest.approx(tq * dpm, abs=0.01)

    def test_anthropic_output(self):
        item = make_fmapi_prop_anthropic_output()
        h, tq, dpm, total, tt = calc_item_values(item, True, False, 0, 'aws', [])
        assert tq == 50
        assert tt == 'Output'

    def test_google_input(self):
        item = make_fmapi_prop_google_input()
        h, tq, dpm, total, tt = calc_item_values(item, True, False, 0, 'aws', [])
        assert tq == 120

    def test_openai_sku(self):
        assert _get_sku_type(make_fmapi_prop_openai_input(), 'aws') == 'OPENAI_MODEL_SERVING'

    def test_anthropic_sku(self):
        assert _get_sku_type(make_fmapi_prop_anthropic_output(), 'aws') == 'ANTHROPIC_MODEL_SERVING'

    def test_google_sku(self):
        assert _get_sku_type(make_fmapi_prop_google_input(), 'aws') == 'GEMINI_MODEL_SERVING'


# ---------- VECTOR_SEARCH ----------
class TestVectorSearchRegression:
    def test_standard_dbu(self):
        dbu, _ = _calculate_dbu_per_hour(make_vs_standard(), 'aws')
        # ceil(5M / 2M) = 3 units * 4.0 = 12.0
        assert dbu == pytest.approx(12.0, abs=0.01)

    def test_storage_opt_dbu(self):
        dbu, _ = _calculate_dbu_per_hour(make_vs_storage_opt(), 'aws')
        # ceil(10M / 64M) = 1 unit * 18.29 = 18.29
        assert dbu == pytest.approx(18.29, abs=0.01)

    def test_sku(self):
        assert _get_sku_type(make_vs_standard(), 'aws') == 'SERVERLESS_REAL_TIME_INFERENCE'

    def test_always_serverless(self):
        assert _is_serverless_workload(make_vs_standard()) is True


# ---------- LAKEBASE ----------
class TestLakebaseRegression:
    def test_small_dbu(self):
        dbu, _ = _calculate_dbu_per_hour(make_lakebase_small(), 'aws')
        assert dbu == pytest.approx(2.0, abs=0.01)  # 2 CU * 1 node

    def test_large_dbu(self):
        dbu, _ = _calculate_dbu_per_hour(make_lakebase_large(), 'aws')
        assert dbu == pytest.approx(24.0, abs=0.01)  # 8 CU * 3 nodes

    def test_sku(self):
        assert _get_sku_type(make_lakebase_small(), 'aws') == 'DATABASE_SERVERLESS_COMPUTE'

    def test_always_serverless(self):
        assert _is_serverless_workload(make_lakebase_small()) is True


# ---------- CROSS-WORKLOAD ----------
class TestAllWorkloadsValid:
    """Every item in the full regression set produces valid calculations."""

    def test_all_valid_dbu(self):
        for item in make_all_regression_items():
            dbu, _ = _calculate_dbu_per_hour(item, 'aws')
            assert isinstance(dbu, (int, float)) and dbu >= 0, \
                f"{item.workload_name}: invalid DBU {dbu}"

    def test_all_valid_sku(self):
        for item in make_all_regression_items():
            sku = _get_sku_type(item, 'aws')
            assert isinstance(sku, str) and len(sku) > 0, \
                f"{item.workload_name}: invalid SKU"

    def test_all_valid_hours(self):
        for item in make_all_regression_items():
            hours = _calculate_hours_per_month(item)
            wt = item.workload_type
            # FMAPI items (both token-based and provisioned) use fmapi_quantity,
            # not hours_per_month — so _calculate_hours_per_month returns 0
            is_fmapi = wt in ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY')
            if not is_fmapi:
                assert hours > 0, f"{item.workload_name}: 0 hours"

    def test_all_sku_have_dbu_price(self):
        """Every SKU resolves to a non-zero $/DBU price."""
        for item in make_all_regression_items():
            sku = _get_sku_type(item, 'aws')
            price, _ = _get_dbu_price('aws', 'us-east-1', 'PREMIUM', sku)
            assert price > 0, f"{item.workload_name} SKU={sku}: price is 0"


class TestCrossCloudRegression:
    """All workload types produce valid results for all 3 clouds."""

    @pytest.mark.parametrize("cloud", ["aws", "azure", "gcp"])
    def test_all_items_valid_dbu(self, cloud):
        for item in make_all_regression_items():
            dbu, _ = _calculate_dbu_per_hour(item, cloud)
            assert isinstance(dbu, (int, float)) and dbu >= 0, \
                f"{cloud}/{item.workload_name}: invalid DBU"

    @pytest.mark.parametrize("cloud", ["aws", "azure", "gcp"])
    def test_all_items_valid_sku(self, cloud):
        for item in make_all_regression_items():
            sku = _get_sku_type(item, cloud)
            assert isinstance(sku, str) and len(sku) > 0
