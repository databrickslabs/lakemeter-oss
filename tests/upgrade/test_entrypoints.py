import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_upgrade_shell_is_valid_bash():
    subprocess.run(
        ["bash", "-n", str(ROOT / "scripts/upgrade.sh")],
        check=True,
    )


def test_upgrade_job_is_separate_and_single_run():
    bundle = yaml.safe_load((ROOT / "scripts/databricks.yml").read_text())
    job = bundle["resources"]["jobs"]["lakemeter_upgrade"]

    assert job["max_concurrent_runs"] == 1
    assert job["tasks"][0]["notebook_task"]["notebook_path"].endswith(
        "08_upgrade_lakemeter.py"
    )
    assert "upgrade_payload/**" in bundle["sync"]["include"]
    assert "upgrader/**" in bundle["sync"]["include"]

