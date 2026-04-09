"""Tests for pricing reference data files.

Validates:
- All 9 pricing JSON files exist and are valid
- manifest.json is accurate
- Key formats match expected patterns (cloud:region:tier, cloud:instance, etc.)
- Data has non-zero values where expected
"""
import json
import os

import pytest

PRICING_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "backend", "static", "pricing"
)

EXPECTED_FILES = [
    "dbu-rates.json",
    "instance-dbu-rates.json",
    "dbu-multipliers.json",
    "dbsql-rates.json",
    "dbsql-warehouse-config.json",
    "model-serving-rates.json",
    "vector-search-rates.json",
    "fmapi-databricks-rates.json",
    "fmapi-proprietary-rates.json",
]


@pytest.fixture(scope="module")
def manifest():
    path = os.path.join(PRICING_DIR, "manifest.json")
    with open(path) as f:
        return json.load(f)


def _load_pricing(filename):
    path = os.path.join(PRICING_DIR, filename)
    with open(path) as f:
        return json.load(f)


class TestPricingFilesExist:
    def test_pricing_directory_exists(self):
        assert os.path.isdir(PRICING_DIR)

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_pricing_file_exists(self, filename):
        path = os.path.join(PRICING_DIR, filename)
        assert os.path.isfile(path), f"Missing pricing file: {filename}"

    def test_manifest_exists(self):
        path = os.path.join(PRICING_DIR, "manifest.json")
        assert os.path.isfile(path)


class TestManifest:
    def test_manifest_lists_all_files(self, manifest):
        listed = set(manifest.get("files", []))
        for expected in EXPECTED_FILES:
            assert expected in listed, f"manifest.json missing: {expected}"

    def test_manifest_total_entries_positive(self, manifest):
        assert manifest.get("total_entries", 0) > 0

    def test_manifest_has_timestamp(self, manifest):
        assert "generated_at" in manifest


class TestPricingFileContent:
    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_file_is_valid_json(self, filename):
        path = os.path.join(PRICING_DIR, filename)
        with open(path) as f:
            data = json.load(f)
        assert isinstance(data, dict), f"{filename} root should be a dict"

    @pytest.mark.parametrize("filename", EXPECTED_FILES)
    def test_file_has_entries(self, filename):
        data = _load_pricing(filename)
        assert len(data) > 0, f"{filename} is empty"


class TestDBURatesFormat:
    """Validate dbu-rates.json key format: cloud:region:tier."""

    @pytest.fixture(scope="class")
    def dbu_rates(self):
        return _load_pricing("dbu-rates.json")

    def test_keys_have_three_parts(self, dbu_rates):
        for key in list(dbu_rates.keys())[:20]:
            parts = key.split(":")
            assert len(parts) >= 3, f"DBU rate key should be cloud:region:tier, got: {key}"

    def test_cloud_values_valid(self, dbu_rates):
        valid_clouds = {"aws", "azure", "gcp"}
        for key in dbu_rates:
            cloud = key.split(":")[0].lower()
            assert cloud in valid_clouds, f"Unknown cloud in key: {key}"

    def test_values_are_dicts_with_skus(self, dbu_rates):
        for key, val in list(dbu_rates.items())[:5]:
            assert isinstance(val, dict), f"DBU rate value should be dict for {key}"
            for sku_name, price in val.items():
                assert isinstance(price, (int, float, dict)), \
                    f"SKU price should be numeric or dict: {sku_name}"


class TestInstanceDBURatesFormat:
    """Validate instance-dbu-rates.json: top-level keys are clouds, values are instance dicts."""

    @pytest.fixture(scope="class")
    def instance_rates(self):
        return _load_pricing("instance-dbu-rates.json")

    def test_top_level_keys_are_clouds(self, instance_rates):
        valid_clouds = {"aws", "azure", "gcp"}
        for key in instance_rates:
            assert key.lower() in valid_clouds, f"Top-level key should be cloud, got: {key}"

    def test_entries_have_dbu_rate(self, instance_rates):
        for cloud, instances in instance_rates.items():
            for inst_type, info in list(instances.items())[:5]:
                assert "dbu_rate" in info, f"Missing dbu_rate in {cloud}/{inst_type}"
                assert info["dbu_rate"] > 0, f"dbu_rate should be > 0 for {cloud}/{inst_type}"

    def test_entries_have_vcpus(self, instance_rates):
        for cloud, instances in instance_rates.items():
            for inst_type, info in list(instances.items())[:5]:
                assert "vcpus" in info, f"Missing vcpus in {cloud}/{inst_type}"


class TestDBSQLRatesFormat:
    """Validate dbsql-rates.json key format: cloud:warehouse_type:size."""

    @pytest.fixture(scope="class")
    def dbsql_rates(self):
        return _load_pricing("dbsql-rates.json")

    def test_keys_have_three_parts(self, dbsql_rates):
        for key in list(dbsql_rates.keys())[:10]:
            parts = key.split(":")
            assert len(parts) >= 3, f"DBSQL key should be cloud:type:size, got: {key}"

    def test_entries_have_dbu_per_hour(self, dbsql_rates):
        for key, info in list(dbsql_rates.items())[:10]:
            assert "dbu_per_hour" in info, f"Missing dbu_per_hour in {key}"
            assert info["dbu_per_hour"] > 0, f"dbu_per_hour should be > 0 for {key}"


class TestMultiplierFormat:
    """Validate dbu-multipliers.json key format: cloud:sku_type:feature."""

    @pytest.fixture(scope="class")
    def multipliers(self):
        return _load_pricing("dbu-multipliers.json")

    def test_keys_have_three_parts(self, multipliers):
        for key in list(multipliers.keys())[:10]:
            parts = key.split(":")
            assert len(parts) >= 3, f"Multiplier key should be cloud:type:feature, got: {key}"

    def test_entries_have_multiplier(self, multipliers):
        for key, info in list(multipliers.items())[:10]:
            assert "multiplier" in info, f"Missing multiplier in {key}"
            assert info["multiplier"] > 0, f"multiplier should be > 0 for {key}"


class TestFMAPIRatesFormat:
    """Validate FMAPI pricing files."""

    @pytest.fixture(scope="class")
    def fmapi_db(self):
        return _load_pricing("fmapi-databricks-rates.json")

    @pytest.fixture(scope="class")
    def fmapi_prop(self):
        return _load_pricing("fmapi-proprietary-rates.json")

    def test_databricks_keys_have_three_parts(self, fmapi_db):
        for key in list(fmapi_db.keys())[:10]:
            parts = key.split(":")
            assert len(parts) >= 3, f"FMAPI-DB key should be cloud:model:rate_type, got: {key}"

    def test_proprietary_keys_have_three_parts(self, fmapi_prop):
        for key in list(fmapi_prop.keys())[:10]:
            parts = key.split(":")
            assert len(parts) >= 3, f"FMAPI-prop key should have 3+ parts, got: {key}"

    def test_databricks_has_entries(self, fmapi_db):
        assert len(fmapi_db) > 0

    def test_proprietary_has_entries(self, fmapi_prop):
        assert len(fmapi_prop) > 0


class TestModelServingAndVectorSearch:
    """Validate model-serving-rates.json and vector-search-rates.json."""

    @pytest.fixture(scope="class")
    def ms_rates(self):
        return _load_pricing("model-serving-rates.json")

    @pytest.fixture(scope="class")
    def vs_rates(self):
        return _load_pricing("vector-search-rates.json")

    def test_model_serving_has_entries(self, ms_rates):
        assert len(ms_rates) > 0

    def test_vector_search_has_entries(self, vs_rates):
        assert len(vs_rates) > 0

    def test_model_serving_keys_format(self, ms_rates):
        for key in list(ms_rates.keys())[:10]:
            parts = key.split(":")
            assert len(parts) >= 2, f"MS key should be cloud:type, got: {key}"

    def test_vector_search_keys_format(self, vs_rates):
        for key in list(vs_rates.keys())[:10]:
            parts = key.split(":")
            assert len(parts) >= 2, f"VS key should be cloud:type, got: {key}"
