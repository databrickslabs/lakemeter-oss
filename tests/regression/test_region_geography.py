"""Regression coverage for cloud region geography grouping."""

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = (
    ROOT / "frontend" / "src" / "data" / "region-geographies.json"
)
DBU_RATES_PATH = (
    ROOT / "backend" / "static" / "pricing" / "dbu-rates.json"
)


@pytest.fixture(scope="module")
def geography_catalog():
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def test_provider_group_order_matches_ui_spec(geography_catalog):
    assert geography_catalog["aws"]["group_order"] == [
        "North America",
        "South America",
        "Europe",
        "Middle East",
        "Africa",
        "Asia Pacific",
        "Australia and New Zealand",
        "Other Regions",
    ]
    assert geography_catalog["azure"]["group_order"] == [
        "Americas",
        "Europe",
        "Middle East",
        "Africa",
        "Asia Pacific",
        "Other Regions",
    ]
    assert geography_catalog["gcp"]["group_order"] == [
        "North America",
        "South America",
        "APAC",
        "Europe",
        "Middle East",
        "Africa",
        "Other Regions",
    ]


def test_every_bundled_region_has_one_explicit_group(geography_catalog):
    dbu_rates = json.loads(DBU_RATES_PATH.read_text(encoding="utf-8"))
    bundled_regions = {"aws": set(), "azure": set(), "gcp": set()}
    for key in dbu_rates:
        cloud, region, _tier = key.split(":", 2)
        bundled_regions[cloud].add(region)

    for cloud, regions in bundled_regions.items():
        mapped_regions = set(geography_catalog[cloud]["regions"])
        assert mapped_regions == regions


def test_all_region_assignments_use_declared_groups(geography_catalog):
    for cloud_config in geography_catalog.values():
        allowed_groups = set(cloud_config["group_order"])
        assigned_groups = set(cloud_config["regions"].values())
        assert assigned_groups <= allowed_groups
        assert "Other Regions" not in assigned_groups


@pytest.mark.parametrize(
    ("cloud", "region", "expected_group"),
    [
        ("aws", "us-east-1", "North America"),
        ("aws", "sa-east-1", "South America"),
        ("aws", "eu-west-1", "Europe"),
        ("aws", "ap-southeast-1", "Asia Pacific"),
        (
            "aws",
            "ap-southeast-2",
            "Australia and New Zealand",
        ),
        ("azure", "eastus2", "Americas"),
        ("azure", "westeurope", "Europe"),
        ("azure", "qatarcentral", "Middle East"),
        ("azure", "southafricanorth", "Africa"),
        ("azure", "australiaeast", "Asia Pacific"),
        ("gcp", "us-central1", "North America"),
        ("gcp", "southamerica-east1", "South America"),
        ("gcp", "asia-southeast1", "APAC"),
        ("gcp", "europe-west1", "Europe"),
        ("gcp", "me-central2", "Middle East"),
    ],
)
def test_representative_region_assignment(
    geography_catalog,
    cloud,
    region,
    expected_group,
):
    assert geography_catalog[cloud]["regions"][region] == expected_group


def test_grouping_utility_keeps_unknown_regions_selectable():
    source = (
        ROOT / "frontend" / "src" / "utils" / "regionGeography.ts"
    ).read_text(encoding="utf-8")
    assert "?? OTHER_REGIONS_GROUP" in source
    assert "value: region.region_code" in source


def test_all_user_facing_region_selectors_use_shared_groups():
    calculator = (
        ROOT / "frontend" / "src" / "pages" / "Calculator.tsx"
    ).read_text(encoding="utf-8")
    sku_explorer = (
        ROOT / "frontend" / "src" / "components" / "SkuExplorer.tsx"
    ).read_text(encoding="utf-8")
    fmapi_helper = (
        ROOT / "frontend" / "src" / "components" / "FmapiTokenHelper.tsx"
    ).read_text(encoding="utf-8")

    assert "groupRegionOptions(" in calculator
    assert "<optgroup" in calculator
    assert "getRegionGeographyOrder(cloud)" in sku_explorer
    assert "grouped" in sku_explorer
    assert "optionGroups={dollarRegionOptionGroups}" in fmapi_helper
