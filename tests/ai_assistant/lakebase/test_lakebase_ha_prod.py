"""Tests: AI proposes LAKEBASE with HA enabled for production database."""
import pytest


class TestLakebaseHaProd:
    """AI proposes a LAKEBASE HA production workload (AC-1 to AC-10)."""

    def test_workload_type_is_lakebase(self, ha_prod_proposal):
        wt = ha_prod_proposal["workload_type"]
        assert wt == "LAKEBASE", f"Expected LAKEBASE, got {wt}"

    def test_ha_enabled(self, ha_prod_proposal):
        """HA should be enabled via ha_enabled flag, read replicas, or ha_nodes."""
        ha_flag = ha_prod_proposal.get("lakebase_ha_enabled")
        replicas = ha_prod_proposal.get("lakebase_num_read_replicas", 0)
        ha_nodes = ha_prod_proposal.get("lakebase_ha_nodes", 1)
        ha_detected = (
            ha_flag is True
            or (replicas is not None and replicas > 0)
            or (ha_nodes is not None and ha_nodes > 1)
        )
        assert ha_detected, (
            f"HA should be enabled for production. "
            f"ha_enabled={ha_flag}, num_read_replicas={replicas}, "
            f"ha_nodes={ha_nodes}"
        )

    def test_storage_gb_populated(self, ha_prod_proposal):
        storage = ha_prod_proposal.get("lakebase_storage_gb")
        assert storage is not None and storage > 0, (
            f"lakebase_storage_gb should be > 0, got {storage}"
        )

    def test_storage_gb_in_range(self, ha_prod_proposal):
        """Requested 500GB — should be in a reasonable range."""
        storage = ha_prod_proposal.get("lakebase_storage_gb", 0)
        assert 50 <= storage <= 5000, (
            f"lakebase_storage_gb should be roughly 500 (range 50-5000), "
            f"got {storage}"
        )

    def test_cu_populated(self, ha_prod_proposal):
        cu = ha_prod_proposal.get("lakebase_cu")
        assert cu is not None and cu >= 1, (
            f"lakebase_cu should be >= 1 for production, got {cu}"
        )

    def test_cu_in_range(self, ha_prod_proposal):
        """Requested 4 CU — should be in a reasonable range."""
        cu = ha_prod_proposal.get("lakebase_cu", 0)
        assert 1 <= cu <= 32, (
            f"lakebase_cu should be roughly 4 (range 1-32), got {cu}"
        )

    def test_workload_name_non_empty(self, ha_prod_proposal):
        name = ha_prod_proposal.get("workload_name", "")
        assert name and len(name) >= 3, (
            f"workload_name too short or missing: '{name}'"
        )

    def test_reason_populated(self, ha_prod_proposal):
        reason = ha_prod_proposal.get("reason", "")
        assert reason and len(reason) >= 10, (
            f"reason too short or missing: '{reason}'"
        )

    def test_notes_populated(self, ha_prod_proposal):
        notes = ha_prod_proposal.get("notes", "")
        assert notes and len(notes) >= 1, (
            f"notes should be populated: '{notes}'"
        )

    def test_proposal_id_present(self, ha_prod_proposal):
        pid = ha_prod_proposal.get("proposal_id", "")
        assert pid, "proposal_id must be present for confirm/reject flow"
