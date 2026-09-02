"""Contracts for the self-contained Marketplace app source."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


def test_marketplace_manifest_declares_required_resources():
    manifest = yaml.safe_load((BACKEND / "manifest.yaml").read_text())
    resources = {
        resource["name"]: resource
        for resource in manifest["resource_specs"]
    }

    assert resources["postgres"]["postgres_spec"]["permission"] == (
        "CAN_CONNECT_AND_CREATE"
    )
    assert resources["claude-endpoint"]["serving_endpoint_spec"][
        "permission"
    ] == "CAN_QUERY"
    assert all("secret_spec" not in resource for resource in resources.values())


def test_marketplace_app_config_is_workspace_neutral():
    app_config_path = BACKEND / "app.yaml"
    source = app_config_path.read_text()
    config = yaml.safe_load(source)
    env = {item["name"]: item for item in config["env"]}
    command = " ".join(config["command"])

    assert "fe-vm-lakemeter" not in source
    assert "DATABRICKS_SECRETS_SCOPE" not in env
    assert "SP_CLIENT_ID_KEY" not in env
    assert "SP_SECRET_KEY" not in env
    assert env["LAKEBASE_ENDPOINT"]["valueFrom"] == "postgres"
    assert env["CLAUDE_MODEL_ENDPOINT"]["valueFrom"] == "claude-endpoint"
    assert env["LAKEMETER_DATABASE_AUTH_MODE"]["value"] == "oauth_only"
    assert env["LAKEMETER_BOOTSTRAP_DATABASE"]["value"] == "true"
    assert "${DATABRICKS_APP_PORT:-8000}" in command
    assert "cd backend" not in command
    assert "../.venv" not in command


def test_marketplace_bootstrap_assets_are_self_contained():
    schema = (BACKEND / "app/bootstrap/sql/schema.sql").read_text()
    functions = (BACKEND / "app/bootstrap/sql/functions.sql").read_text()
    seeds = BACKEND / "app/bootstrap/seeds.json"

    assert "CREATE SCHEMA IF NOT EXISTS lakemeter" in schema
    assert "CREATE TABLE IF NOT EXISTS lakemeter.app_bootstrap_state" in schema
    assert "ADD COLUMN IF NOT EXISTS display_order INT" in schema
    assert "calculate_line_item_costs" in functions
    assert "get_product_type_for_pricing" in functions
    assert seeds.is_file()

    required_pricing_files = {
        "dbu-rates.csv",
        "instance-dbu-rates.csv",
        "dbu-multipliers.csv",
        "dbsql-rates.csv",
        "dbsql-warehouse-config.csv",
        "serverless-rates.csv",
        "fmapi-databricks-rates.csv",
        "fmapi-proprietary-rates.csv",
        "sku-region-map.csv",
    }
    pricing_files = list((BACKEND / "static/pricing").glob("*.csv"))
    pricing_names = {path.name for path in pricing_files}
    assert required_pricing_files <= pricing_names
    assert (
        "vm-costs.csv" in pricing_names
        or {
            "vm-costs_part1.csv",
            "vm-costs_part2.csv",
        } <= pricing_names
    )
    assert all(path.stat().st_size < 10 * 1024 * 1024 for path in pricing_files)


def test_token_manager_prefers_marketplace_postgres_environment(monkeypatch):
    from app.auth.token_manager import LakebaseTokenManager

    monkeypatch.setenv("PGHOST", "marketplace.example")
    monkeypatch.setenv("PGPORT", "5433")
    monkeypatch.setenv("PGDATABASE", "marketplace")
    monkeypatch.setenv("PGUSER", "app-service-principal")
    monkeypatch.setenv("PGSSLMODE", "require")
    monkeypatch.setenv("DB_HOST", "legacy.example")
    monkeypatch.setattr(
        LakebaseTokenManager,
        "_init_workspace_client",
        lambda self: None,
    )
    monkeypatch.setattr(
        LakebaseTokenManager,
        "get_token",
        lambda self: "oauth-token",
    )

    manager = LakebaseTokenManager()
    params = manager.get_connection_params()

    assert params == {
        "host": "marketplace.example",
        "port": 5433,
        "user": "app-service-principal",
        "password": "oauth-token",
        "dbname": "marketplace",
        "sslmode": "require",
    }


class _BootstrapCursor:
    def __init__(self, current_state):
        self.current_state = current_state
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def executemany(self, sql, params):
        self.executed.append((sql, list(params)))

    def fetchone(self):
        return self.current_state

    def close(self):
        return None


class _BootstrapConnection:
    def __init__(self, current_state):
        self.cursor_instance = _BootstrapCursor(current_state)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        return None


class _BootstrapEngine:
    def __init__(self, current_state):
        self.connection = _BootstrapConnection(current_state)

    def raw_connection(self):
        return self.connection


def test_marketplace_bootstrap_skips_current_database(monkeypatch):
    from app.bootstrap import runner

    engine = _BootstrapEngine((runner.APP_VERSION, "pricing-checksum"))
    applied = []
    monkeypatch.setattr(
        runner,
        "_pricing_checksum",
        lambda: "pricing-checksum",
    )
    monkeypatch.setattr(runner, "_pricing_is_present", lambda cursor: True)
    monkeypatch.setattr(
        runner,
        "_sql_statements",
        lambda filename: [filename],
    )
    monkeypatch.setattr(
        runner,
        "_execute_statements",
        lambda cursor, statements: applied.extend(statements),
    )

    assert runner.bootstrap_database(engine) is False
    assert applied == ["schema.sql"]
    assert engine.connection.rollbacks == 0


def test_marketplace_bootstrap_initializes_empty_database(monkeypatch):
    from app.bootstrap import runner

    engine = _BootstrapEngine(None)
    applied = []
    calls = []
    monkeypatch.setattr(
        runner,
        "_pricing_checksum",
        lambda: "pricing-checksum",
    )
    monkeypatch.setattr(
        runner,
        "_sql_statements",
        lambda filename: [filename],
    )
    monkeypatch.setattr(
        runner,
        "_execute_statements",
        lambda cursor, statements: applied.extend(statements),
    )
    monkeypatch.setattr(
        runner,
        "_seed_reference_data",
        lambda cursor: calls.append("seeds"),
    )
    monkeypatch.setattr(
        runner,
        "_load_pricing",
        lambda cursor: calls.append("pricing"),
    )
    monkeypatch.setattr(
        runner,
        "_refresh_derived_reference_data",
        lambda cursor: calls.append("derived"),
    )

    assert runner.bootstrap_database(engine) is True
    assert applied == ["schema.sql", "functions.sql"]
    assert calls == ["seeds", "pricing", "derived"]
    assert engine.connection.rollbacks == 0
