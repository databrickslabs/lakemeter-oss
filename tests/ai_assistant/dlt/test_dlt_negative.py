"""Tests: Non-DLT prompt must NOT produce a DLT workload (negative discrimination)."""
import pytest


class TestDltNegativeDiscrimination:
    """Non-DLT prompt (interactive compute) must NOT produce a DLT workload."""

    def test_non_dlt_prompt_does_not_produce_dlt(self, non_dlt_proposal):
        wt = non_dlt_proposal.get("workload_type", "")
        assert wt != "DLT", (
            f"Interactive compute prompt should NOT produce DLT, got {wt}"
        )

    def test_non_dlt_prompt_produces_all_purpose(self, non_dlt_proposal):
        wt = non_dlt_proposal.get("workload_type", "")
        assert wt == "ALL_PURPOSE", (
            f"Interactive compute prompt should produce ALL_PURPOSE, got {wt}"
        )
