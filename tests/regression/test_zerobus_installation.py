"""Verify Zerobus remains registered in install and upgrade paths."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_fresh_install_seed_files_include_zerobus():
    for relative_path in (
        "scripts/install_lakemeter.py",
        "scripts/notebooks/02_create_database.py",
    ):
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        assert '("ZEROBUS", "Zerobus Ingest"' in source
        assert '"JOBS_SERVERLESS_COMPUTE", None, None, 19' in source


def test_database_sku_resolvers_include_zerobus():
    for relative_path in (
        "scripts/functions/01_Utility_Functions.py",
        "etl/lakebase_setup/functions/01_Utility_Functions.py",
    ):
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        marker = "WHEN 'ZEROBUS' THEN"
        assert marker in source
        assert source.index("JOBS_SERVERLESS_COMPUTE", source.index(marker)) > 0


def test_upgrade_seed_is_idempotent_and_registered():
    update_path = "scripts/upgrades/data_updates/027_zerobus.sql"
    source = (ROOT / update_path).read_text(encoding="utf-8")
    assert "'ZEROBUS'" in source
    assert "ON CONFLICT (workload_type) DO UPDATE" in source
    assert "ALTER TABLE" not in source.upper()

    manifest = json.loads(
        (ROOT / "scripts/upgrades/release.json").read_text(encoding="utf-8")
    )
    action = next(
        item
        for item in manifest["data_updates"]
        if item["id"] == "027-zerobus"
    )
    assert action["path"] == update_path
    assert len(action["sha256"]) == 64
