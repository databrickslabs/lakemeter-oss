"""Sprint 10: Cross-workload consistency checks — all 9 types together."""
from tests.export.cross_workload.conftest import make_all_nine_items
from app.routes.export.calculations import (
    _calculate_dbu_per_hour, _calculate_hours_per_month, _is_serverless_workload,
)
from app.routes.export.pricing import _get_sku_type


class TestAllNineItemsCalc:
    """AC-14: Cross-workload consistency checks."""

    def test_all_items_produce_valid_dbu(self):
        """Every item returns a numeric, non-negative DBU/hr."""
        for item in make_all_nine_items():
            dbu, warnings = _calculate_dbu_per_hour(item, 'aws')
            assert isinstance(dbu, (int, float)), \
                f"{item.workload_type} returned non-numeric"
            assert dbu >= 0, \
                f"{item.workload_type} returned negative DBU"

    def test_all_items_produce_valid_sku(self):
        """Every item maps to a non-empty SKU string."""
        for item in make_all_nine_items():
            sku = _get_sku_type(item, 'aws')
            assert isinstance(sku, str) and len(sku) > 0, \
                f"{item.workload_type} returned invalid SKU"

    def test_all_items_produce_valid_hours(self):
        """Every non-FMAPI item returns positive hours."""
        for item in make_all_nine_items():
            hours = _calculate_hours_per_month(item)
            if item.workload_type not in ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY'):
                assert hours > 0, f"{item.workload_type} returned 0 hours"

    def test_serverless_classification(self):
        """All 9 items in combined set are correctly classified."""
        expected_serverless = {
            "JOBS": True,
            "ALL_PURPOSE": False,
            "DLT": True,
            "DBSQL": True,
            "MODEL_SERVING": True,
            "FMAPI_DATABRICKS": True,
            "FMAPI_PROPRIETARY": True,
            "VECTOR_SEARCH": True,
            "LAKEBASE": True,
        }
        for item in make_all_nine_items():
            result = _is_serverless_workload(item)
            expected = expected_serverless[item.workload_type]
            assert result == expected, \
                f"{item.workload_type}: expected serverless={expected}, got {result}"
