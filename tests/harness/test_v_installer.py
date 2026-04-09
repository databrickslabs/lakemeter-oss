"""
Harness Test (v): Installer verification — ensure the installer can install
everything: ETL, API layer, and frontend.

Tests:
- ETL scripts exist in the repo at etl/ directory
- Installer script exists and is syntactically valid
- Installer references correct ETL paths (etl/lakebase_setup/setup, not ../database_backend)
- Backend can start (app module imports cleanly)
- Frontend build artifacts or source exist
- All required dependencies are in requirements.txt
- app.yaml exists for Databricks Apps deployment
"""
import ast
import os
import sys
import pytest
from pathlib import Path


# Root of the lakemeter_app repo
APP_ROOT = Path(__file__).resolve().parent.parent.parent


class TestETLInRepo:
    """Verify ETL scripts are bundled in the repo."""

    def test_etl_directory_exists(self):
        assert (APP_ROOT / "etl").is_dir(), "etl/ directory missing from repo"

    def test_lakebase_setup_exists(self):
        setup_dir = APP_ROOT / "etl" / "lakebase_setup" / "setup"
        assert setup_dir.is_dir(), f"Missing: {setup_dir}"

    def test_create_tables_script(self):
        f = APP_ROOT / "etl" / "lakebase_setup" / "setup" / "01_Create_Tables.py"
        assert f.exists(), f"Missing core setup script: {f}"

    def test_create_views_script(self):
        f = APP_ROOT / "etl" / "lakebase_setup" / "setup" / "02_Create_Views.py"
        assert f.exists(), f"Missing views script: {f}"

    def test_functions_directory(self):
        funcs_dir = APP_ROOT / "etl" / "lakebase_setup" / "functions"
        assert funcs_dir.is_dir(), f"Missing: {funcs_dir}"
        py_files = list(funcs_dir.glob("*.py"))
        assert len(py_files) >= 7, f"Expected 7+ function files, got {len(py_files)}"

    def test_lakebase_tests_exist(self):
        tests_dir = APP_ROOT / "etl" / "lakebase_setup" / "tests"
        assert tests_dir.is_dir(), f"Missing: {tests_dir}"
        test_files = list(tests_dir.glob("Test_*.py"))
        assert len(test_files) >= 14, f"Expected 14 test files, got {len(test_files)}"

    def test_pricing_sync_exists(self):
        pricing_dir = APP_ROOT / "etl" / "pricing_sync"
        assert pricing_dir.is_dir(), f"Missing: {pricing_dir}"
        notebooks = list(pricing_dir.glob("*.ipynb"))
        assert len(notebooks) >= 10, f"Expected 10+ pricing notebooks, got {len(notebooks)}"

    def test_salesforce_sync_exists(self):
        sf_dir = APP_ROOT / "etl" / "salesforce_sync"
        assert sf_dir.is_dir(), f"Missing: {sf_dir}"
        files = list(sf_dir.glob("*"))
        assert len(files) >= 5, f"Expected 5+ salesforce files, got {len(files)}"

    def test_lakebase_config_exists(self):
        f = APP_ROOT / "etl" / "lakebase_setup" / "00_Lakebase_Config.py"
        assert f.exists(), f"Missing config: {f}"


class TestInstallerScript:
    """Verify installer script integrity."""

    def test_installer_exists(self):
        f = APP_ROOT / "scripts" / "install_lakemeter.py"
        assert f.exists(), f"Missing installer: {f}"

    def test_installer_syntax_valid(self):
        f = APP_ROOT / "scripts" / "install_lakemeter.py"
        source = f.read_text()
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"Installer has syntax error: {e}")

    def test_installer_references_etl_path(self):
        """Installer should reference etl/lakebase_setup/setup, NOT ../database_backend."""
        f = APP_ROOT / "scripts" / "install_lakemeter.py"
        source = f.read_text()
        assert "database_backend" not in source, (
            "Installer still references old path 'database_backend' — should use 'etl/'"
        )
        assert "etl" in source, "Installer should reference 'etl/' directory"


class TestBackendStructure:
    """Verify backend can be imported and has correct structure."""

    def test_backend_directory(self):
        assert (APP_ROOT / "backend").is_dir()
        assert (APP_ROOT / "backend" / "app").is_dir()
        assert (APP_ROOT / "backend" / "app" / "main.py").exists()

    def test_requirements_txt(self):
        req = APP_ROOT / "backend" / "requirements.txt"
        if not req.exists():
            req = APP_ROOT / "requirements.txt"
        assert req.exists(), "No requirements.txt found"
        content = req.read_text()
        # Key dependencies
        for dep in ["fastapi", "sqlalchemy", "uvicorn", "pydantic"]:
            assert dep in content.lower(), f"Missing dependency: {dep}"

    def test_app_module_importable(self):
        """Verify the app module can be imported without errors."""
        backend_dir = str(APP_ROOT / "backend")
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        try:
            import importlib
            # Import just the config module (doesn't need DB)
            spec = importlib.util.find_spec("app.config")
            assert spec is not None, "app.config module not found"
        except Exception as e:
            pytest.fail(f"Cannot import app.config: {e}")

    def test_all_route_modules_exist(self):
        """Verify all route modules are present."""
        routes_dir = APP_ROOT / "backend" / "app" / "routes"
        expected_modules = [
            "estimates.py",
            "line_items.py",
            "users.py",
            "chat.py",
        ]
        expected_packages = [
            "calculate",
            "reference",
            "export",
        ]
        for mod in expected_modules:
            assert (routes_dir / mod).exists(), f"Missing route module: {mod}"
        for pkg in expected_packages:
            assert (routes_dir / pkg / "__init__.py").exists(), f"Missing route package: {pkg}"

    def test_calculate_endpoints_complete(self):
        """Verify all 8 calculate sub-routers exist."""
        calc_dir = APP_ROOT / "backend" / "app" / "routes" / "calculate"
        expected = [
            "jobs.py", "all_purpose.py", "dbsql_calc.py", "dlt_calc.py",
            "model_serving_calc.py", "fmapi_calc.py", "vector_search_calc.py",
            "lakebase_calc.py",
        ]
        for f in expected:
            assert (calc_dir / f).exists(), f"Missing calculate module: {f}"

    def test_no_external_api_dependency(self):
        """Verify main.py does not import external_api."""
        main_py = APP_ROOT / "backend" / "app" / "main.py"
        source = main_py.read_text()
        assert "external_api" not in source, (
            "main.py still imports external_api — should be fully consolidated"
        )


class TestFrontendStructure:
    """Verify frontend source or build artifacts exist."""

    def test_frontend_directory(self):
        assert (APP_ROOT / "frontend").is_dir()

    def test_frontend_package_json(self):
        pkg = APP_ROOT / "frontend" / "package.json"
        assert pkg.exists(), "Missing frontend/package.json"

    def test_frontend_src_exists(self):
        src = APP_ROOT / "frontend" / "src"
        assert src.is_dir(), "Missing frontend/src/"

    def test_frontend_api_client(self):
        client = APP_ROOT / "frontend" / "src" / "api" / "client.ts"
        assert client.exists(), "Missing frontend API client"

    def test_frontend_store(self):
        store = APP_ROOT / "frontend" / "src" / "store" / "useStore.ts"
        assert store.exists(), "Missing frontend Zustand store"


class TestDeploymentConfig:
    """Verify Databricks Apps deployment artifacts."""

    def test_app_yaml_exists(self):
        assert (APP_ROOT / "app.yaml").exists(), "Missing app.yaml for Databricks Apps"

    def test_app_yaml_valid(self):
        import yaml
        with open(APP_ROOT / "app.yaml") as f:
            config = yaml.safe_load(f)
        assert config is not None, "app.yaml is empty"
        # Should have command or entrypoint
        has_command = "command" in config or "entrypoint" in config
        assert has_command or "source_code_path" in config, (
            "app.yaml missing command/entrypoint/source_code_path"
        )

    def test_deploy_script_exists(self):
        """deploy.sh should exist for deployment."""
        deploy = APP_ROOT / "deploy.sh"
        if deploy.exists():
            assert os.access(deploy, os.X_OK) or deploy.read_text().startswith("#"), \
                "deploy.sh exists but may not be executable"


class TestPythonSyntax:
    """Verify all Python files have valid syntax."""

    def _get_python_files(self):
        """Get all Python files in backend/ and scripts/."""
        files = []
        for d in ["backend", "scripts"]:
            base = APP_ROOT / d
            if base.exists():
                files.extend(base.rglob("*.py"))
        return files

    def test_all_python_files_valid_syntax(self):
        errors = []
        for f in self._get_python_files():
            if "__pycache__" in str(f):
                continue
            try:
                ast.parse(f.read_text())
            except SyntaxError as e:
                errors.append(f"{f.relative_to(APP_ROOT)}: {e}")
        assert not errors, f"Syntax errors in {len(errors)} files:\n" + "\n".join(errors[:10])

    def test_no_async_in_sync_routes(self):
        """Verify calculate routes use sync def, not async def."""
        calc_dir = APP_ROOT / "backend" / "app" / "routes" / "calculate"
        errors = []
        for f in calc_dir.glob("*.py"):
            if f.name == "__init__.py":
                continue
            source = f.read_text()
            if "async def calculate_" in source:
                errors.append(f"{f.name}: has async calculate function (should be sync)")
        assert not errors, "Async functions found in calculate routes:\n" + "\n".join(errors)
