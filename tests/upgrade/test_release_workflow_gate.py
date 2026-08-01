from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_WORKFLOW = (
    ROOT / ".github/workflows/release-candidate.yml"
).read_text()
RELEASE_WORKFLOW = (ROOT / ".github/workflows/release.yml").read_text()


def test_candidate_runs_cross_version_integration_before_tagging():
    required_commands = (
        "./scripts/install.sh",
        "scripts/release_integration.py seed",
        "./scripts/upgrade.sh apply",
        "python -m pytest tests/e2e",
        "scripts/release_integration.py verify",
        "./scripts/upgrade.sh rollback",
        "scripts/release_integration.py rollback",
    )
    for command in required_commands:
        assert command in CANDIDATE_WORKFLOW

    artifact_position = CANDIDATE_WORKFLOW.index(
        "Upload tested release assets"
    )
    tag_position = CANDIDATE_WORKFLOW.index(
        "Create immutable release tag"
    )
    assert artifact_position < tag_position


def test_final_release_only_publishes_matching_tested_artifacts():
    assert "gh run download" in RELEASE_WORKFLOW
    assert "dist/candidate.json" in RELEASE_WORKFLOW
    assert '"integration_status": "passed"' in RELEASE_WORKFLOW
    assert "sha256sum -c SHA256SUMS" in RELEASE_WORKFLOW
    assert "npm run build" not in RELEASE_WORKFLOW
    assert "pytest" not in RELEASE_WORKFLOW
