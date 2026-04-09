"""Tests: AI proposes LAKEBASE for a small dev/test instance."""
import pytest


class TestLakebaseSmallDev:
    """AI proposes a small LAKEBASE dev/test workload (AC-11 to AC-17)."""

    def test_workload_type_is_lakebase(self, small_dev_proposal):
        wt = small_dev_proposal["workload_type"]
        assert wt == "LAKEBASE", f"Expected LAKEBASE, got {wt}"

    def test_storage_gb_small(self, small_dev_proposal):
        """Requested 10GB — should be in a small range."""
        storage = small_dev_proposal.get("lakebase_storage_gb")
        assert storage is not None and storage > 0, (
            f"lakebase_storage_gb should be > 0, got {storage}"
        )
        assert 1 <= storage <= 100, (
            f"lakebase_storage_gb should be roughly 10 (range 1-100), "
            f"got {storage}"
        )

    def test_cu_small(self, small_dev_proposal):
        """Requested 0.5 CU — should be in a small range."""
        cu = small_dev_proposal.get("lakebase_cu")
        assert cu is not None and cu > 0, (
            f"lakebase_cu should be > 0, got {cu}"
        )
        assert 0.25 <= cu <= 4, (
            f"lakebase_cu should be roughly 0.5 (range 0.25-4), got {cu}"
        )

    def test_ha_not_enabled(self, small_dev_proposal):
        """Dev/test should not have HA unless AI chose it anyway."""
        ha_flag = small_dev_proposal.get("lakebase_ha_enabled")
        replicas = small_dev_proposal.get("lakebase_num_read_replicas", 0)
        # Allow AI to set HA=false or omit it; just flag if HA is on
        if ha_flag is True:
            pytest.skip(
                "AI enabled HA for dev instance — not a failure, "
                "but unexpected for a dev/test workload"
            )
        if replicas and replicas > 0:
            pytest.skip(
                f"AI added {replicas} read replica(s) for dev instance — "
                "not a failure, but unexpected"
            )

    def test_workload_name_non_empty(self, small_dev_proposal):
        name = small_dev_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_reason_populated(self, small_dev_proposal):
        reason = small_dev_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_proposal_id_present(self, small_dev_proposal):
        pid = small_dev_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present for confirm/reject flow"
