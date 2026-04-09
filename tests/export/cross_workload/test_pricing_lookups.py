"""Sprint 10: Pricing lookup validation — standard configs resolve without fallback."""
from tests.export.cross_workload.conftest import (
    make_jobs_serverless, make_all_purpose_classic_photon,
    make_dbsql_serverless_medium, make_model_serving_gpu,
    make_vector_search_standard, make_lakebase,
    make_dlt_pro_serverless, make_fmapi_databricks, make_fmapi_proprietary,
)
from app.routes.export.calculations import _calculate_dbu_per_hour


class TestPricingLookups:
    """Verify standard configs resolve without fallback warnings."""

    def test_jobs_no_warnings(self):
        item = make_jobs_serverless()
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert len(warnings) == 0, f"Jobs had warnings: {warnings}"

    def test_dbsql_no_warnings(self):
        item = make_dbsql_serverless_medium()
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert len(warnings) == 0, f"DBSQL had warnings: {warnings}"

    def test_lakebase_no_warnings(self):
        item = make_lakebase()
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert len(warnings) == 0, f"Lakebase had warnings: {warnings}"

    def test_model_serving_no_warnings(self):
        item = make_model_serving_gpu()
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert len(warnings) == 0, f"Model Serving had warnings: {warnings}"

    def test_all_purpose_no_warnings(self):
        item = make_all_purpose_classic_photon()
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert len(warnings) == 0, f"All-Purpose had warnings: {warnings}"

    def test_vector_search_no_warnings(self):
        """Vector Search DBU calc itself has no warnings (rate lookup is separate)."""
        item = make_vector_search_standard()
        _, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert len(warnings) == 0, f"Vector Search had warnings: {warnings}"


class TestFallbackPricingExpected:
    """Document which workload types use fallback DBU rates.

    DLT SERVERLESS and VECTOR_SEARCH_ENDPOINT SKUs are not yet in the
    pricing JSON, so the Excel builder applies fallback rates and generates
    warning notes. These tests verify the expected behavior is stable.
    """

    def test_dlt_no_calc_warnings(self):
        """DLT DBU/hr calculation itself succeeds without warnings."""
        item = make_dlt_pro_serverless()
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu > 0, "DLT should return positive DBU/hr"
        assert len(warnings) == 0, f"DLT calc warnings: {warnings}"

    def test_fmapi_databricks_zero_dbu(self):
        """FMAPI Databricks is token-based: 0 DBU/hr, no warnings."""
        item = make_fmapi_databricks()
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 0, "FMAPI DB should return 0 DBU/hr (token-based)"
        assert len(warnings) == 0, f"FMAPI DB warnings: {warnings}"

    def test_fmapi_proprietary_zero_dbu(self):
        """FMAPI Proprietary is token-based: 0 DBU/hr, no warnings."""
        item = make_fmapi_proprietary()
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu == 0, "FMAPI Prop should return 0 DBU/hr (token-based)"
        assert len(warnings) == 0, f"FMAPI Prop warnings: {warnings}"


class TestMultiCloudPricing:
    """Verify pricing lookups work across all 3 clouds."""

    def test_jobs_all_clouds_no_warnings(self):
        item = make_jobs_serverless()
        for cloud in ('aws', 'azure', 'gcp'):
            _, warnings = _calculate_dbu_per_hour(item, cloud)
            assert len(warnings) == 0, f"Jobs {cloud}: {warnings}"

    def test_dbsql_all_clouds_no_warnings(self):
        item = make_dbsql_serverless_medium()
        for cloud in ('aws', 'azure', 'gcp'):
            _, warnings = _calculate_dbu_per_hour(item, cloud)
            assert len(warnings) == 0, f"DBSQL {cloud}: {warnings}"

    def test_model_serving_aws_nonzero(self):
        """gpu_medium_a10g_1x is AWS-specific; verify it resolves on AWS."""
        item = make_model_serving_gpu()
        dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
        assert dbu > 0, f"Model Serving aws: 0 DBU/hr"
        assert len(warnings) == 0
