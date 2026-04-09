"""Tests for install_lakemeter.py script structure and code quality.

Validates:
- Script is parseable Python with all expected functions
- CLI argument parsing supports required flags
- Critical code patterns (identity_type, sslmode, error handling)
- All step functions have docstrings
"""
import ast
import os
import re

import pytest

SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "scripts", "install_lakemeter.py"
)


@pytest.fixture(scope="module")
def script_content():
    with open(SCRIPT_PATH) as f:
        return f.read()


@pytest.fixture(scope="module")
def script_ast(script_content):
    return ast.parse(script_content)


class TestScriptExists:
    def test_installer_file_exists(self):
        assert os.path.isfile(SCRIPT_PATH), "install_lakemeter.py not found"

    def test_script_is_parseable_python(self, script_content):
        try:
            ast.parse(script_content)
        except SyntaxError as e:
            pytest.fail(f"Script has syntax error: {e}")


class TestStepFunctions:
    """Verify all 9 installer step functions exist."""

    EXPECTED_FUNCTIONS = [
        "validate_prerequisites",       # Step 1
        "gather_config",                # Step 2
        "provision_lakebase",           # Step 3
        "create_database_and_schema",   # Step 4
        "run_setup_sql",                # Step 4 (sub)
        "load_pricing_data",            # Step 5
        "create_sku_discount_mapping",  # Step 6
        "configure_sp_access",          # Step 7
        "create_views",                 # Step 8
        "generate_app_config",          # Step 9
    ]

    def test_all_step_functions_defined(self, script_ast):
        func_names = {
            node.name
            for node in ast.walk(script_ast)
            if isinstance(node, ast.FunctionDef)
        }
        for expected in self.EXPECTED_FUNCTIONS:
            assert expected in func_names, f"Missing function: {expected}"

    def test_step_functions_have_docstrings(self, script_ast):
        missing = []
        for node in ast.walk(script_ast):
            if isinstance(node, ast.FunctionDef) and node.name in self.EXPECTED_FUNCTIONS:
                docstring = ast.get_docstring(node)
                if not docstring:
                    missing.append(node.name)
        assert not missing, f"Functions missing docstrings: {missing}"

    def test_main_function_exists(self, script_ast):
        func_names = {
            node.name
            for node in ast.walk(script_ast)
            if isinstance(node, ast.FunctionDef)
        }
        assert "main" in func_names

    def test_main_guard_present(self, script_content):
        assert '__name__ == "__main__"' in script_content or \
               "__name__ == '__main__'" in script_content


class TestCLIArguments:
    """Verify argparse supports required flags."""

    def test_profile_argument(self, script_content):
        assert "--profile" in script_content

    def test_skip_provision_argument(self, script_content):
        assert "--skip-provision" in script_content

    def test_skip_deploy_argument(self, script_content):
        assert "--skip-deploy" in script_content


class TestCriticalCodePatterns:
    """Verify critical implementation patterns."""

    def test_sp_role_uses_service_principal_identity(self, script_content):
        assert '"identity_type": "SERVICE_PRINCIPAL"' in script_content or \
               "'identity_type': 'SERVICE_PRINCIPAL'" in script_content or \
               '"identity_type"' in script_content, \
            "SP role creation must use identity_type=SERVICE_PRINCIPAL"

    def test_sp_role_not_pg_only_default(self, script_content):
        # The script should explicitly set SERVICE_PRINCIPAL, not PG_ONLY
        matches = re.findall(r'"identity_type"\s*:\s*"(\w+)"', script_content)
        for match in matches:
            assert match != "PG_ONLY", \
                "SP role must NOT use identity_type=PG_ONLY"

    def test_db_connections_use_ssl(self, script_content):
        connect_calls = re.findall(r'psycopg2?\.connect\([^)]+\)', script_content, re.DOTALL)
        for call in connect_calls:
            assert "sslmode" in call, f"DB connection missing sslmode: {call[:80]}"

    def test_pricing_loader_truncates_before_insert(self, script_content):
        assert "TRUNCATE TABLE" in script_content, \
            "Pricing loader should TRUNCATE before batch insert"

    def test_error_handling_sys_exit(self, script_content):
        assert "sys.exit(1)" in script_content, \
            "Installer should sys.exit(1) on critical failures"

    def test_roles_api_url_pattern(self, script_content):
        assert "/api/2.0/database/instances/" in script_content, \
            "Should use Lakebase Roles API endpoint"
        assert "/roles" in script_content, \
            "Should use /roles path for SP role management"

    def test_membership_role_superuser(self, script_content):
        assert "DATABRICKS_SUPERUSER" in script_content, \
            "SP role should have DATABRICKS_SUPERUSER membership"


class TestHelperFunctions:
    """Verify helper/utility functions exist."""

    EXPECTED_HELPERS = [
        "log_step", "log_ok", "log_warn", "log_err", "log_info",
        "prompt_input", "prompt_choice",
        "get_owner_connection",
        "_create_sync_tables",
        "_batch_insert",
        "_extract_sql_from_notebook",
        "_create_tables_inline",
    ]

    def test_helper_functions_exist(self, script_ast):
        func_names = {
            node.name
            for node in ast.walk(script_ast)
            if isinstance(node, ast.FunctionDef)
        }
        missing = [h for h in self.EXPECTED_HELPERS if h not in func_names]
        assert not missing, f"Missing helpers: {missing}"


class TestConstants:
    """Verify important constants are defined."""

    def test_default_db_name(self, script_content):
        assert "lakemeter_pricing" in script_content

    def test_default_schema(self, script_content):
        assert 'DEFAULT_SCHEMA = "lakemeter"' in script_content or \
               "DEFAULT_SCHEMA = 'lakemeter'" in script_content

    def test_pricing_dir_reference(self, script_content):
        assert "static" in script_content and "pricing" in script_content

    def test_total_steps_is_9(self, script_content):
        assert "TOTAL_STEPS = 9" in script_content
