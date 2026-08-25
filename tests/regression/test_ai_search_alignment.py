from pathlib import Path

import pytest

from app.routes.calculate.schemas import VectorSearchCalculationRequest
from app.routes.calculate.vector_search_calc import (
    AI_SEARCH_RERANKER_DBU_PER_THOUSAND_REQUESTS,
    calculate_ai_search_addons,
)
from app.routes.export.helpers import _get_workload_display_name
from app.routes.workload_types import DEFAULT_WORKLOAD_TYPES, get_workload_type
from app.schemas.line_item import (
    AI_SEARCH_CONFIG_FIELDS,
    map_ai_parse_api_fields,
    validate_ai_search_workload_config,
)
from tests.export.vector_search.conftest import make_line_item
from tests.export.vector_search.excel_helpers import generate_xlsx


ROOT = Path(__file__).resolve().parents[2]


def test_ai_search_addons_use_30_gb_free_tier_and_reranker_rate():
    usage = calculate_ai_search_addons(
        units_used=3,
        storage_gb=100,
        reranker_enabled=True,
        reranker_requests_thousands=12.5,
    )

    assert usage["storage"] == {
        "total_gb": 100,
        "free_gb": 30,
        "billable_gb": 70,
        "price_per_gb": 0.023,
        "cost_per_month": pytest.approx(1.61),
    }
    assert usage["reranker"]["dbu_per_month"] == pytest.approx(
        12.5 * AI_SEARCH_RERANKER_DBU_PER_THOUSAND_REQUESTS
    )


def test_calculation_request_accepts_legacy_and_frontend_capacity_names():
    common = {
        "cloud": "aws",
        "region": "ap-southeast-1",
        "tier": "PREMIUM",
        "mode": "standard",
    }
    legacy = VectorSearchCalculationRequest(
        **common,
        num_vectors_millions=2,
    )
    frontend = VectorSearchCalculationRequest(
        **common,
        vector_capacity_millions=3,
        reranker_enabled=True,
        reranker_requests_thousands=4,
    )

    assert legacy.num_vectors_millions == 2
    assert frontend.num_vectors_millions == 3
    assert frontend.reranker_requests_thousands == 4


def test_reranker_fields_fold_into_workload_config_without_schema_columns():
    public_fields = {
        "workload_type",
        "ai_search_reranker_enabled",
        "ai_search_reranker_requests_thousands",
    }
    mapped = map_ai_parse_api_fields(
        {
            "workload_type": "VECTOR_SEARCH",
            "ai_search_reranker_enabled": True,
            "ai_search_reranker_requests_thousands": 25,
        },
        public_fields,
    )

    assert mapped["workload_config"] == {
        "ai_search_reranker_enabled": True,
        "ai_search_reranker_requests_thousands": 25,
    }
    for field in AI_SEARCH_CONFIG_FIELDS:
        assert field not in mapped


def test_reranker_validation_rejects_invalid_usage():
    validate_ai_search_workload_config(
        "VECTOR_SEARCH",
        {
            "ai_search_reranker_enabled": True,
            "ai_search_reranker_requests_thousands": 0,
        },
    )
    with pytest.raises(ValueError, match="greater than or equal to 0"):
        validate_ai_search_workload_config(
            "VECTOR_SEARCH",
            {
                "ai_search_reranker_enabled": True,
                "ai_search_reranker_requests_thousands": -1,
            },
        )


def test_workload_registry_and_export_use_ai_search_name_and_srti_sku():
    workload = next(
        item
        for item in DEFAULT_WORKLOAD_TYPES
        if item["workload_type"] == "VECTOR_SEARCH"
    )
    assert workload["display_name"] == "AI Search"
    assert workload["sku_product_type_serverless"] == (
        "SERVERLESS_REAL_TIME_INFERENCE"
    )
    assert _get_workload_display_name("VECTOR_SEARCH") == "AI Search"


def test_single_workload_lookup_uses_curated_ai_search_name():
    workload = get_workload_type("vector_search", db=None)

    assert workload.workload_type == "VECTOR_SEARCH"
    assert workload.display_name == "AI Search"


def test_user_facing_sources_do_not_use_legacy_product_name():
    legacy_name = "vector" + " search"
    roots = (
        ROOT / "backend/app",
        ROOT / "frontend/src",
        ROOT / "docs-site",
    )

    matches = []
    for root in roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in {
                ".py",
                ".ts",
                ".tsx",
                ".md",
            }:
                continue
            if legacy_name in path.read_text(encoding="utf-8").lower():
                matches.append(str(path.relative_to(ROOT)))

    assert matches == []


def test_frontend_invalidates_and_normalizes_cached_ai_search_metadata():
    store_source = (
        ROOT / "frontend/src/store/useStore.ts"
    ).read_text(encoding="utf-8")
    form_source = (
        ROOT / "frontend/src/components/WorkloadForm.tsx"
    ).read_text(encoding="utf-8")

    assert "const CACHE_VERSION = 'v12'" in store_source
    assert "function canonicalizeWorkloadType" in store_source
    assert "display_name: 'AI Search'" in store_source
    assert (
        "wt.workload_type === 'VECTOR_SEARCH' ? 'AI Search' : wt.display_name"
        in form_source
    )


def test_excel_writes_separate_dbu_month_reranker_and_30_gb_storage():
    item = make_line_item(
        workload_name="Search",
        vector_capacity_millions=2,
        vector_search_storage_gb=40,
        workload_config={
            "ai_search_reranker_enabled": True,
            "ai_search_reranker_requests_thousands": 5,
        },
    )
    sheet = generate_xlsx([item]).active

    reranker_row = next(
        row
        for row in range(1, sheet.max_row + 1)
        if sheet.cell(row, 2).value == "Search – AI Search Reranker"
    )
    assert sheet.cell(reranker_row, 3).value == "AI Search (Reranker)"
    assert sheet.cell(reranker_row, 6).value == (
        "SERVERLESS_REAL_TIME_INFERENCE"
    )
    assert sheet.cell(reranker_row, 5).value == (
        "5K requests × 28.571 DBU/1K = 142.855 DBU/mo"
    )
    for column in (12, 13, 14, 15, 16):
        assert sheet.cell(reranker_row, column).value == "N/A"
    assert sheet.cell(reranker_row, 17).value == pytest.approx(142.855)
    assert sheet.cell(reranker_row, 17).number_format == "#,##0.00"
    assert sheet.cell(reranker_row, 21).value == (
        f"=Q{reranker_row}*R{reranker_row}"
    )

    storage_row = next(
        row
        for row in range(1, sheet.max_row + 1)
        if sheet.cell(row, 6).value == "DATABRICKS_STORAGE"
    )
    assert sheet.cell(storage_row, 3).value == "AI Search (Storage)"
    assert "free: 30 GB" in sheet.cell(storage_row, 5).value


def test_data_update_is_idempotent_and_has_no_schema_migration():
    source = (
        ROOT
        / "scripts/upgrades/data_updates/023_ai_search_alignment.sql"
    ).read_text(encoding="utf-8")
    assert "'AI Search'" in source
    assert "ON CONFLICT (workload_type) DO UPDATE" in source
    assert "ALTER TABLE" not in source.upper()
