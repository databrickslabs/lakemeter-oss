"""Regression coverage for consistent VM calculation presentation."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CALCULATOR = ROOT / "frontend" / "src" / "pages" / "Calculator.tsx"
WORKLOAD_FORM = ROOT / "frontend" / "src" / "components" / "WorkloadForm.tsx"
API_CLIENT = ROOT / "frontend" / "src" / "api" / "client.ts"


def test_shared_vm_equation_labels_driver_workers_rates_and_total():
    source = CALCULATOR.read_text()
    component = source[
        source.index("const VMCalculationLine"):
        source.index("const WorkloadCostDisplay")
    ]

    for required_text in (
        ">Driver<",
        "workerCount",
        "driverRate.toFixed(4)",
        "workerRate.toFixed(4)",
        "formatCurrency(total)",
    ):
        assert required_text in component


def test_all_table_and_card_vm_paths_use_shared_equation():
    source = CALCULATOR.read_text()

    # DBSQL and generic compute each render once in table view and once in card view.
    assert source.count("<VMCalculationLine\n") == 4
    assert source.count("if (wType === 'DBSQL')") >= 2
    assert "case 'JOBS':" in source
    assert "case 'ALL_PURPOSE':" in source
    assert "case 'DLT':" in source


def test_old_unlabelled_vm_equations_cannot_return():
    source = CALCULATOR.read_text()

    assert 'title={driverNode}>${driverVMCost' not in source
    assert 'title={workerNode}>${workerVMCost' not in source


def test_dlt_edition_is_shown_in_both_calculation_views():
    source = CALCULATOR.read_text()

    assert source.count("({effectiveItem.dlt_edition || 'CORE'} edition)") == 2


def test_sdp_dropdown_handles_legacy_cached_and_api_shapes():
    form_source = WORKLOAD_FORM.read_text()
    client_source = API_CLIENT.read_text()

    assert "hasValidDltEditions" in form_source
    for edition in ("CORE", "PRO", "ADVANCED"):
        assert f"id: '{edition}'" in form_source
    assert "typeof edition === 'string'" in client_source
    assert "edition.id || edition.edition" in client_source
