"""
Regression tests for bugs found during Sprint 3 DLT testing.

BUG-S3-1: DLT Serverless SKU — now aligned to JOBS_SERVERLESS_COMPUTE (matching frontend)
BUG-S3-2: DLT Classic Photon SKU — now includes _(PHOTON) suffix (matching frontend)
BUG-S3-3: DLT Serverless also respects mode (standard vs performance), unlike ALL_PURPOSE
"""
import os
import sys
import pytest

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

from tests.export.dlt.conftest import make_line_item


class TestBugS3_1_DLTServerlessSKU:
    """BUG-S3-1: DLT Serverless now aligned to JOBS_SERVERLESS_COMPUTE.
    Fixed in Sprint 1 SKU alignment — backend now matches frontend.
    """

    def test_backend_dlt_serverless_sku(self):
        from app.routes.export import _get_sku_type

        item = make_line_item(
            dlt_edition="CORE", serverless_enabled=True,
        )
        sku = _get_sku_type(item, "aws")
        assert sku == "JOBS_SERVERLESS_COMPUTE", \
            f"Backend DLT serverless SKU should be JOBS_SERVERLESS_COMPUTE, got {sku}"

    def test_backend_dlt_serverless_all_editions(self):
        """All editions get the same serverless SKU."""
        from app.routes.export import _get_sku_type

        for edition in ["CORE", "PRO", "ADVANCED"]:
            item = make_line_item(
                dlt_edition=edition, serverless_enabled=True,
            )
            sku = _get_sku_type(item, "aws")
            assert sku == "JOBS_SERVERLESS_COMPUTE", \
                f"DLT {edition} serverless should be JOBS_SERVERLESS_COMPUTE, got {sku}"


class TestBugS3_2_DLTPhotonSKUSuffix:
    """BUG-S3-2: DLT Classic Photon now includes _(PHOTON) suffix.
    Fixed in Sprint 1 SKU alignment — backend now matches frontend.
    """

    @pytest.mark.parametrize("edition", ["CORE", "PRO", "ADVANCED"])
    def test_backend_dlt_photon_has_suffix(self, edition):
        from app.routes.export import _get_sku_type

        item = make_line_item(
            dlt_edition=edition, photon_enabled=True,
            serverless_enabled=False,
        )
        sku = _get_sku_type(item, "aws")
        assert sku == f"DLT_{edition}_COMPUTE_(PHOTON)", \
            f"Backend DLT {edition} photon should be DLT_{edition}_COMPUTE_(PHOTON), got {sku}"


class TestBugS3_3_DLTServerlessModeRespected:
    """BUG-S3-3: DLT Serverless respects mode (standard vs performance),
    UNLIKE ALL_PURPOSE which always forces performance (2x).
    Regression: ensure this distinction is maintained.
    """

    def test_dlt_serverless_standard_is_1x(self):
        from app.routes.export import _calculate_dbu_per_hour

        item = make_line_item(
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            dlt_edition="CORE",
            serverless_enabled=True,
            serverless_mode="standard",
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # base(5.0) * photon(2.9 from JSON) * standard(1) = 14.5
        assert dbu_hr == pytest.approx(14.5)

    def test_dlt_serverless_performance_is_2x(self):
        from app.routes.export import _calculate_dbu_per_hour

        item = make_line_item(
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            dlt_edition="CORE",
            serverless_enabled=True,
            serverless_mode="performance",
        )
        dbu_hr, _ = _calculate_dbu_per_hour(item, "aws")
        # base(5.0) * photon(2.9 from JSON) * perf(2) = 29.0
        assert dbu_hr == pytest.approx(29.0)

    def test_dlt_modes_differ(self):
        """DLT standard != performance (unlike ALL_PURPOSE which always forces 2x)."""
        from app.routes.export import _calculate_dbu_per_hour

        item_std = make_line_item(
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            serverless_enabled=True,
            serverless_mode="standard",
        )
        item_perf = make_line_item(
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            serverless_enabled=True,
            serverless_mode="performance",
        )
        std_dbu, _ = _calculate_dbu_per_hour(item_std, "aws")
        perf_dbu, _ = _calculate_dbu_per_hour(item_perf, "aws")
        assert perf_dbu == pytest.approx(std_dbu * 2), \
            f"DLT: performance({perf_dbu}) should be 2x standard({std_dbu})"

    def test_allpurpose_modes_forced_same(self):
        """Contrast: ALL_PURPOSE always forces 2x regardless of mode."""
        from app.routes.export import _calculate_dbu_per_hour
        from tests.export.all_purpose.conftest import make_line_item as make_ap_item

        item_std = make_ap_item(
            workload_type="ALL_PURPOSE",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            serverless_enabled=True,
            serverless_mode="standard",
        )
        item_perf = make_ap_item(
            workload_type="ALL_PURPOSE",
            driver_node_type="i3.xlarge",
            worker_node_type="i3.xlarge",
            num_workers=4,
            serverless_enabled=True,
            serverless_mode="performance",
        )
        std_dbu, _ = _calculate_dbu_per_hour(item_std, "aws")
        perf_dbu, _ = _calculate_dbu_per_hour(item_perf, "aws")
        assert std_dbu == pytest.approx(perf_dbu), \
            "ALL_PURPOSE: standard and performance should be identical"
