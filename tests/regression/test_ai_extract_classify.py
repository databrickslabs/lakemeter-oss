"""Regression tests for the AI Extract and AI Classify workload types.

Covers the acceptance criteria of the feature request:
  - calculation endpoints price presets and custom rates against the
    SERVERLESS_REAL_TIME_INFERENCE SKU
  - every SKU resolver (Python and SQL) maps both types
  - line-item fields persist, clone, and round-trip without alias mapping
  - Excel export DBU quantities match the calculation API
  - exported DBUs/Mo cells are written as values, so a full recalculation
    (Google Sheets, LibreOffice, Ctrl+Alt+F9) cannot collapse them to zero
"""
import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.routes.calculate import ai_extract_calc, ai_classify_calc
from app.routes.calculate.ai_extract_calc import (
    EXTRACT_DOCUMENT_RATES, calculate_ai_extract_cost,
)
from app.routes.calculate.ai_classify_calc import (
    CLASSIFY_DOCUMENT_RATES, calculate_ai_classify_cost,
)
from app.routes.calculate.helpers import get_sku_type as get_calculation_sku_type
from app.routes.calculate.schemas import (
    AIExtractCalculationRequest, AIClassifyCalculationRequest,
)
from app.routes.export.excel_builder import build_estimate_excel
from app.routes.export.excel_item_helpers import calc_item_values
from app.routes.export.pricing import _get_sku_type as get_export_sku_type
from app.routes.estimates import _copy_line_item
from app.models.line_item import LineItem
from app.schemas.line_item import LineItemCreate
from app.services.lakebase_queries import get_sku_type as get_service_sku_type

RTI_PRICE = 0.07  # AWS us-east-1 PREMIUM reference rate for the SRTI SKU


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _PricingDb:
    def __init__(self):
        self.product_types = []

    def execute(self, statement, params):
        self.product_types.append(params["pt"])
        return _Result(SimpleNamespace(price_per_dbu=RTI_PRICE))


@pytest.fixture(autouse=True)
def _patch_validation(monkeypatch):
    for module in (ai_extract_calc, ai_classify_calc):
        monkeypatch.setattr(module, "validate_cloud", lambda *a, **k: None)
        monkeypatch.setattr(module, "validate_region", lambda *a, **k: None)
        monkeypatch.setattr(module, "validate_tier", lambda *a, **k: None)


def _extract_request(**kwargs):
    base = dict(cloud="AWS", region="us-east-1", tier="PREMIUM")
    base.update(kwargs)
    return AIExtractCalculationRequest(**base)


def _classify_request(**kwargs):
    base = dict(cloud="AWS", region="us-east-1", tier="PREMIUM")
    base.update(kwargs)
    return AIClassifyCalculationRequest(**base)


class TestCalculation:
    @pytest.mark.parametrize(
        ("document_type", "num_inputs", "expected_dbu"),
        [("invoice", 100_000, 4_500.0), ("financial_report", 10_000, 675.0)],
    )
    def test_extract_presets(self, document_type, num_inputs, expected_dbu):
        response = calculate_ai_extract_cost(
            _extract_request(document_type=document_type, num_inputs=num_inputs),
            db=_PricingDb(),
        )
        data = response["data"]
        assert data["sku_type"] == "SERVERLESS_REAL_TIME_INFERENCE"
        assert data["dbu_calculation"]["dbu_per_month"] == expected_dbu
        assert data["total_cost"]["cost_per_month"] == pytest.approx(
            expected_dbu * RTI_PRICE)
        assert any("ai_parse_document" in note for note in data["notes"])

    @pytest.mark.parametrize(
        ("document_type", "num_docs", "expected_dbu"),
        [("short_text", 500_000, 2_250.0), ("contract", 20_000, 1_000.0)],
    )
    def test_classify_presets(self, document_type, num_docs, expected_dbu):
        response = calculate_ai_classify_cost(
            _classify_request(document_type=document_type, num_docs=num_docs),
            db=_PricingDb(),
        )
        data = response["data"]
        assert data["sku_type"] == "SERVERLESS_REAL_TIME_INFERENCE"
        assert data["dbu_calculation"]["dbu_per_month"] == expected_dbu
        assert data["total_cost"]["cost_per_month"] == pytest.approx(
            expected_dbu * RTI_PRICE)
        assert any("ai_parse_document" in note for note in data["notes"])

    def test_extract_custom_rate(self):
        response = calculate_ai_extract_cost(
            _extract_request(document_type="custom", num_inputs=5_000,
                             dbus_per_thousand=80),
            db=_PricingDb(),
        )
        assert response["data"]["dbu_calculation"]["dbu_per_month"] == 400.0

    def test_classify_custom_rate(self):
        response = calculate_ai_classify_cost(
            _classify_request(document_type="custom", num_docs=5_000,
                              dbus_per_thousand=8),
            db=_PricingDb(),
        )
        assert response["data"]["dbu_calculation"]["dbu_per_month"] == 40.0

    def test_extract_rejects_unknown_document_type(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            calculate_ai_extract_cost(
                _extract_request(document_type="novel"), db=_PricingDb())
        assert exc_info.value.status_code == 400

    def test_custom_requires_rate(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            calculate_ai_classify_cost(
                _classify_request(document_type="custom", num_docs=1_000),
                db=_PricingDb())
        assert exc_info.value.status_code == 400


class TestSkuResolution:
    @pytest.mark.parametrize("workload_type", ["AI_EXTRACT", "AI_CLASSIFY"])
    def test_python_resolvers(self, workload_type):
        assert get_calculation_sku_type(workload_type, False, False) == \
            "SERVERLESS_REAL_TIME_INFERENCE"
        assert get_service_sku_type(workload_type, False, False) == \
            "SERVERLESS_REAL_TIME_INFERENCE"
        item = SimpleNamespace(workload_type=workload_type)
        assert get_export_sku_type(item, "aws") == "SERVERLESS_REAL_TIME_INFERENCE"

    @pytest.mark.parametrize("relative_path", [
        "scripts/functions/01_Utility_Functions.py",
        "etl/lakebase_setup/functions/01_Utility_Functions.py",
    ])
    def test_sql_resolvers(self, relative_path):
        repository_root = Path(__file__).resolve().parents[2]
        source = (repository_root / relative_path).read_text(encoding="utf-8")
        for workload_type in ("AI_EXTRACT", "AI_CLASSIFY"):
            assert f"WHEN '{workload_type}' THEN" in source, (
                f"{relative_path} is missing the {workload_type} mapping")


class TestPersistenceAndClone:
    FIELDS = {
        "ai_extract_document_type": "financial_report",
        "ai_extract_num_inputs": 10_000,
        "ai_extract_dbus_per_thousand": 80,
        "ai_classify_document_type": "contract",
        "ai_classify_num_docs": 20_000,
        "ai_classify_dbus_per_thousand": 8,
    }

    def test_line_item_create_accepts_fields(self):
        from uuid import uuid4
        item = LineItemCreate.model_validate({
            "estimate_id": uuid4(),
            "workload_name": "extraction",
            "workload_type": "AI_EXTRACT",
            **self.FIELDS,
        })
        dumped = item.model_dump()
        for key, value in self.FIELDS.items():
            assert dumped[key] == value
        # field names match ORM columns exactly, so no alias mapping is needed
        for key in self.FIELDS:
            assert hasattr(LineItem, key)

    def test_clone_copies_all_workload_fields(self):
        from uuid import uuid4
        original = LineItem(
            estimate_id=uuid4(), workload_name="extraction",
            workload_type="AI_EXTRACT", **self.FIELDS)
        new_estimate_id = uuid4()
        copy = _copy_line_item(original, new_estimate_id)
        assert copy.estimate_id == new_estimate_id
        for key, value in self.FIELDS.items():
            assert getattr(copy, key) == value
        assert copy.line_item_id != original.line_item_id or copy.line_item_id is None


def _export_item(**kwargs):
    base = dict(
        workload_name="w", workload_type="AI_EXTRACT", serverless_enabled=True,
        photon_enabled=False, driver_node_type=None, worker_node_type=None,
        num_workers=None, hours_per_month=None, runs_per_day=None,
        avg_runtime_minutes=None, days_per_month=None, hours_per_day=None,
        driver_pricing_tier=None, worker_pricing_tier=None,
        driver_payment_option=None, worker_payment_option=None,
        dlt_edition=None, dbsql_warehouse_type=None, dbsql_warehouse_size=None,
        dbsql_num_clusters=None, dbsql_serverless_size=None,
        dbsql_vm_pricing_tier=None, dbsql_vm_payment_option=None,
        notes=None, serverless_mode=None,
        ai_parse_calculation_method=None, ai_parse_complexity=None,
        ai_parse_num_pages=None, ai_parse_dbus=None, ai_parse_hours_per_month=None,
        ai_extract_document_type=None, ai_extract_num_inputs=None,
        ai_extract_dbus_per_thousand=None,
        ai_classify_document_type=None, ai_classify_num_docs=None,
        ai_classify_dbus_per_thousand=None,
        shutterstock_imageai_num_images=None,
        lakebase_cu=None, lakebase_ha_nodes=None, lakebase_storage_gb=None,
        lakebase_pitr_gb=None, lakebase_snapshot_gb=None,
        vector_search_storage_gb=None, vector_search_units=None,
        model_serving_concurrency=None, model_serving_gpu_type=None,
        fmapi_model=None, fmapi_provider=None, fmapi_input_tokens_millions=None,
        fmapi_output_tokens_millions=None, fmapi_provisioned_throughput=None,
        databricks_apps_size=None, databricks_apps_num_apps=None,
        databricks_support_tier=None,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


class TestExportParity:
    def test_calc_item_values_match_api(self):
        extract_item = _export_item(
            workload_type="AI_EXTRACT",
            ai_extract_document_type="invoice", ai_extract_num_inputs=100_000)
        _, _, _, total_dbus, _ = calc_item_values(
            extract_item, False, False, 0, "aws", [])
        assert total_dbus == 4_500.0

        classify_item = _export_item(
            workload_type="AI_CLASSIFY",
            ai_classify_document_type="contract", ai_classify_num_docs=20_000)
        _, _, _, total_dbus, _ = calc_item_values(
            classify_item, False, False, 0, "aws", [])
        assert total_dbus == 1_000.0

    def test_custom_rate_export(self):
        item = _export_item(
            workload_type="AI_EXTRACT", ai_extract_document_type="custom",
            ai_extract_num_inputs=5_000, ai_extract_dbus_per_thousand=80)
        _, _, _, total_dbus, _ = calc_item_values(item, False, False, 0, "aws", [])
        assert total_dbus == 400.0


class TestRecalculationSafeExport:
    def test_dbu_cells_are_values_not_formulas(self):
        import openpyxl

        estimate = SimpleNamespace(
            estimate_name="AI Functions", cloud="AWS", region="us-east-1",
            tier="PREMIUM", estimate_id="e1", status="draft")
        items = [
            _export_item(workload_name="extract",
                         workload_type="AI_EXTRACT",
                         ai_extract_document_type="invoice",
                         ai_extract_num_inputs=100_000),
            _export_item(workload_name="classify",
                         workload_type="AI_CLASSIFY",
                         ai_classify_document_type="short_text",
                         ai_classify_num_docs=500_000),
        ]
        output = build_estimate_excel(estimate, items, "AWS", "us-east-1",
                                      "PREMIUM", db=None)
        payload = io.BytesIO(output.getvalue())
        formulas = openpyxl.load_workbook(payload).active
        payload.seek(0)
        cached = openpyxl.load_workbook(payload, data_only=True).active

        expected = {"extract": 4_500.0, "classify": 2_250.0}
        seen = {}
        for row in range(1, formulas.max_row + 1):
            name = cached.cell(row=row, column=2).value
            if name in expected:
                dbu_cell = formulas.cell(row=row, column=17)
                assert not (isinstance(dbu_cell.value, str)
                            and dbu_cell.value.startswith("=")), (
                    f"{name}: DBUs/Mo must be a value, found formula "
                    f"{dbu_cell.value!r}")
                seen[name] = float(dbu_cell.value)
        assert seen == expected
