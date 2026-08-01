"""Tests for app.yaml configuration validation.

Validates:
- app.yaml exists and is valid YAML
- Contains required valueFrom references for Databricks Apps
- Contains required hardcoded env vars
- Command starts uvicorn correctly
"""
import os
import re

import pytest
import yaml

APP_YAML_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "app.yaml"
)


@pytest.fixture(scope="module")
def app_yaml():
    with open(APP_YAML_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def app_yaml_raw():
    with open(APP_YAML_PATH) as f:
        return f.read()


@pytest.fixture(scope="module")
def env_vars(app_yaml):
    """Return env vars as a dict of name -> {value/valueFrom}."""
    result = {}
    for entry in app_yaml.get("env", []):
        name = entry.get("name")
        if name:
            result[name] = entry
    return result


class TestAppYamlExists:
    def test_file_exists(self):
        assert os.path.isfile(APP_YAML_PATH)

    def test_valid_yaml(self):
        with open(APP_YAML_PATH) as f:
            data = yaml.safe_load(f)
        assert data is not None


class TestCommand:
    def test_command_is_list(self, app_yaml):
        assert "command" in app_yaml
        assert isinstance(app_yaml["command"], list)

    def test_command_uses_bash(self, app_yaml):
        assert app_yaml["command"][0] == "/bin/bash"

    def test_command_runs_uvicorn(self, app_yaml):
        cmd_str = " ".join(app_yaml["command"])
        assert "uvicorn" in cmd_str

    def test_command_port_8000(self, app_yaml):
        cmd_str = " ".join(app_yaml["command"])
        assert "8000" in cmd_str

    def test_command_host_0000(self, app_yaml):
        cmd_str = " ".join(app_yaml["command"])
        assert "0.0.0.0" in cmd_str


class TestValueFromReferences:
    """Verify direct Autoscaling and database resource references exist."""

    EXPECTED_VALUE_FROM = {
        "LAKEBASE_PROJECT": "lakemeter-lakebase-project",
        "LAKEBASE_BRANCH": "lakemeter-lakebase-branch",
        "LAKEBASE_ENDPOINT": "lakemeter-lakebase-endpoint",
        "DB_HOST": "lakemeter-db-host",
        "DB_USER": "lakemeter-db-user",
        "DB_NAME": "lakemeter-db-name",
    }

    def test_has_direct_autoscaling_value_from_refs(self, env_vars):
        value_from_count = sum(
            1 for v in env_vars.values() if "valueFrom" in v
        )
        assert value_from_count >= 7, \
            f"Expected >= 7 valueFrom refs, got {value_from_count}"

    @pytest.mark.parametrize(
        "env_name,resource_name",
        list(EXPECTED_VALUE_FROM.items()),
    )
    def test_value_from_reference(self, env_vars, env_name, resource_name):
        assert env_name in env_vars, f"Missing env var: {env_name}"
        entry = env_vars[env_name]
        assert "valueFrom" in entry, f"{env_name} should use valueFrom, not value"
        assert entry["valueFrom"] == resource_name, \
            f"{env_name} valueFrom should be '{resource_name}', got '{entry.get('valueFrom')}'"


class TestHardcodedValues:
    """Verify required hardcoded env vars."""

    def test_environment_var(self, env_vars):
        assert "ENVIRONMENT" in env_vars
        assert env_vars["ENVIRONMENT"].get("value") == "production"

    def test_db_port(self, env_vars):
        assert "DB_PORT" in env_vars
        assert env_vars["DB_PORT"].get("value") == "5432"

    def test_db_sslmode(self, env_vars):
        assert "DB_SSLMODE" in env_vars
        assert env_vars["DB_SSLMODE"].get("value") == "require"

    def test_cors_origins_present(self, env_vars):
        assert "CORS_ORIGINS" in env_vars
