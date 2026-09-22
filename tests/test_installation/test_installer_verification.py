"""Regression coverage for source-install runtime verification."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "scripts" / "notebooks" / "07_verify_installation.py"


def test_verifier_is_executable_python():
    source = VERIFIER.read_text(encoding="utf-8")

    ast.parse(source)
    assert "# MAGIC %md" not in source


def test_verifier_authenticates_app_requests():
    source = VERIFIER.read_text(encoding="utf-8")

    assert "/oidc/v1/token" in source
    assert '"audience": app_info.oauth2_app_client_id' in source
    assert "token_response.json()['access_token']" in source
    assert "session.request(" in source


def test_verifier_checks_all_cloud_region_endpoints():
    source = VERIFIER.read_text(encoding="utf-8")

    assert 'expected_minimums = {"AWS": 17, "AZURE": 38, "GCP": 15}' in source
    assert 'f"/api/v1/regions?cloud={cloud}"' in source
    assert "/api/v1/reference/regions" not in source


def test_verifier_fails_the_job_on_failed_checks():
    source = VERIFIER.read_text(encoding="utf-8")

    assert "raise RuntimeError(" in source
    assert 'dbutils.notebook.exit(f"FAIL:' not in source
