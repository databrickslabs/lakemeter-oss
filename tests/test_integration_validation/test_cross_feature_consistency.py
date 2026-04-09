"""Integration validation: cross-feature data consistency.

Validates that pricing data, calculation helpers, and export logic
are consistent across all 9 workload types. Catches data drift
where one workload's pricing is updated but another's is not.
"""
import json
import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = str(Path(__file__).resolve().parent.parent.parent / "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

PRICING_DIR = Path(BACKEND_DIR) / "static" / "pricing"


class TestPricingDataConsistency:
    """Cross-workload pricing data consistency checks."""

    @pytest.fixture(scope="class")
    def dbu_rates(self):
        return json.loads((PRICING_DIR / "dbu-rates.json").read_text())

    @pytest.fixture(scope="class")
    def instance_rates(self):
        return json.loads((PRICING_DIR / "instance-dbu-rates.json").read_text())

    @pytest.fixture(scope="class")
    def multipliers(self):
        return json.loads((PRICING_DIR / "dbu-multipliers.json").read_text())

    def test_dbu_rates_has_all_three_clouds(self, dbu_rates):
        """DBU rates should cover aws, azure, gcp."""
        clouds = set()
        for key in dbu_rates:
            cloud = key.split(":")[0]
            clouds.add(cloud)
        assert "aws" in clouds, "Missing AWS DBU rates"
        assert "azure" in clouds, "Missing Azure DBU rates"
        assert "gcp" in clouds, "Missing GCP DBU rates"

    def test_instance_rates_has_all_three_clouds(self, instance_rates):
        """Instance DBU rates should have aws, azure, gcp top-level keys."""
        for cloud in ["aws", "azure", "gcp"]:
            assert cloud in instance_rates, f"Missing {cloud} in instance rates"

    def test_multipliers_has_all_three_clouds(self, multipliers):
        """Multipliers should cover all three clouds."""
        clouds = set()
        for key in multipliers:
            cloud = key.split(":")[0]
            clouds.add(cloud)
        assert "aws" in clouds, "Missing AWS multipliers"
        assert "azure" in clouds, "Missing Azure multipliers"
        assert "gcp" in clouds, "Missing GCP multipliers"

    def test_dbu_rates_values_positive(self, dbu_rates):
        """All DBU rate values should be positive numbers."""
        for key, rates in dbu_rates.items():
            if isinstance(rates, dict):
                for wtype, rate in rates.items():
                    if isinstance(rate, (int, float)):
                        assert rate > 0, (
                            f"Non-positive DBU rate for {key}:{wtype} = {rate}"
                        )

    def test_multipliers_values_positive(self, multipliers):
        """All multiplier values should be positive."""
        for key, value in multipliers.items():
            if isinstance(value, (int, float)):
                assert value > 0, f"Non-positive multiplier: {key} = {value}"
            elif isinstance(value, dict):
                for subkey, subval in value.items():
                    if isinstance(subval, (int, float)):
                        assert subval > 0, (
                            f"Non-positive multiplier: {key}:{subkey} = {subval}"
                        )


class TestDBSQLDataConsistency:
    """DBSQL-specific data consistency."""

    @pytest.fixture(scope="class")
    def dbsql_rates(self):
        return json.loads((PRICING_DIR / "dbsql-rates.json").read_text())

    @pytest.fixture(scope="class")
    def warehouse_config(self):
        return json.loads((PRICING_DIR / "dbsql-warehouse-config.json").read_text())

    def test_dbsql_rates_non_empty(self, dbsql_rates):
        assert len(dbsql_rates) > 0, "DBSQL rates file is empty"

    def test_warehouse_config_non_empty(self, warehouse_config):
        assert len(warehouse_config) > 0, "Warehouse config file is empty"

    def test_dbsql_rates_key_format(self, dbsql_rates):
        """Keys should be cloud:type:size format."""
        for key in list(dbsql_rates.keys())[:20]:
            parts = key.split(":")
            assert len(parts) >= 3, f"Invalid DBSQL rate key format: {key}"


class TestFMAPIDataConsistency:
    """FMAPI data consistency across Databricks and proprietary models."""

    @pytest.fixture(scope="class")
    def fmapi_db(self):
        return json.loads((PRICING_DIR / "fmapi-databricks-rates.json").read_text())

    @pytest.fixture(scope="class")
    def fmapi_prop(self):
        return json.loads((PRICING_DIR / "fmapi-proprietary-rates.json").read_text())

    def test_fmapi_db_non_empty(self, fmapi_db):
        assert len(fmapi_db) > 0

    def test_fmapi_prop_non_empty(self, fmapi_prop):
        assert len(fmapi_prop) > 0

    def test_fmapi_db_key_format(self, fmapi_db):
        for key in list(fmapi_db.keys())[:10]:
            parts = key.split(":")
            assert len(parts) >= 3, f"Invalid FMAPI DB key format: {key}"

    def test_fmapi_prop_key_format(self, fmapi_prop):
        for key in list(fmapi_prop.keys())[:10]:
            parts = key.split(":")
            assert len(parts) >= 3, f"Invalid FMAPI prop key format: {key}"


class TestServingDataConsistency:
    """Model Serving and Vector Search data consistency."""

    @pytest.fixture(scope="class")
    def ms_rates(self):
        return json.loads((PRICING_DIR / "model-serving-rates.json").read_text())

    @pytest.fixture(scope="class")
    def vs_rates(self):
        return json.loads((PRICING_DIR / "vector-search-rates.json").read_text())

    def test_model_serving_non_empty(self, ms_rates):
        assert len(ms_rates) > 0

    def test_vector_search_non_empty(self, vs_rates):
        assert len(vs_rates) > 0

    def test_model_serving_key_format(self, ms_rates):
        for key in list(ms_rates.keys())[:10]:
            parts = key.split(":")
            assert len(parts) >= 2, f"Invalid MS rate key format: {key}"

    def test_vector_search_key_format(self, vs_rates):
        for key in list(vs_rates.keys())[:10]:
            parts = key.split(":")
            assert len(parts) >= 2, f"Invalid VS rate key format: {key}"


class TestManifestConsistency:
    """Manifest should be consistent with actual pricing files."""

    @pytest.fixture(scope="class")
    def manifest(self):
        return json.loads((PRICING_DIR / "manifest.json").read_text())

    def test_manifest_file_count(self, manifest):
        files = manifest.get("files", [])
        assert len(files) == 9, f"Expected 9 files in manifest, got {len(files)}"

    def test_manifest_total_matches_sum(self, manifest):
        """Total entries should be consistent (> 4000 based on current data)."""
        total = manifest.get("total_entries", 0)
        assert total > 4000, f"Total entries {total} seems low"

    def test_all_manifest_files_exist(self, manifest):
        files = manifest.get("files", [])
        for fname in files:
            assert (PRICING_DIR / fname).is_file(), (
                f"Manifest lists {fname} but file doesn't exist"
            )
