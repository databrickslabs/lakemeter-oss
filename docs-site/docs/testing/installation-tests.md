---
sidebar_position: 13
---

# Installation Validation Tests

The installation test suite (`tests/test_installation/`) validates the Lakemeter installer, pricing data files, and app configuration without requiring network access. All 91 tests run locally in under 1 second.

## Test Files

### `test_installer_script.py` (21 tests)

Static analysis of `scripts/install_lakemeter.py` — verifies the installer's structure without executing it.

| Test Area | Tests | What It Checks |
|-----------|-------|----------------|
| Script structure | 3 | File exists, parseable Python, all 10 step functions defined |
| Step functions | 2 | Each function has a docstring, all helpers exist (12 functions) |
| CLI arguments | 3 | `--profile`, `--skip-provision`, `--skip-deploy` flags present |
| Critical patterns | 4 | `identity_type=SERVICE_PRINCIPAL`, SSL connections, TRUNCATE before insert |
| Roles API | 2 | Correct URL pattern, `DATABRICKS_SUPERUSER` membership |
| Constants | 3 | `lakemeter_pricing` DB name, `DEFAULT_SCHEMA`, `TOTAL_STEPS = 9` |
| Error handling | 4 | `sys.exit` patterns, helper function signatures |

### `test_pricing_data.py` (49 tests)

Validates all 9 pricing JSON files in `backend/static/pricing/`:

| Pricing File | Tests | Validations |
|-------------|-------|-------------|
| `manifest.json` | 3 | Lists all 9 files, total entries > 4000, all files present |
| `dbu_rates.json` | 5 | Valid JSON, entries present, `cloud:region:tier` key format, valid clouds |
| `instance_dbu_rates.json` | 5 | Top-level cloud keys, entries have `dbu_rate > 0` and `vcpus` |
| `dbu_multipliers.json` | 5 | `cloud:type:feature` format, `multiplier > 0` |
| `dbsql_rates.json` | 5 | `cloud:type:size` format, `dbu_per_hour > 0` |
| `dbsql_warehouse_config.json` | 5 | Entries present, correct key format |
| `model_serving_rates.json` | 5 | Entries present, key format valid |
| `vector_search_rates.json` | 5 | Entries present, key format valid |
| `fmapi_databricks_rates.json` | 5 | `cloud:model:rate_type` format |
| `fmapi_proprietary_rates.json` | 6 | `cloud:model:rate_type` format, provider names valid |

### `test_app_config.py` (21 tests)

Validates the `app.yaml` Databricks App configuration:

| Test Area | Tests | What It Checks |
|-----------|-------|----------------|
| YAML validity | 1 | File parses as valid YAML |
| Command | 2 | Runs uvicorn on `0.0.0.0:8000` via bash |
| `valueFrom` references | 6 | All 5 resource references match expected names (parametrized) |
| Hardcoded values | 3 | `ENVIRONMENT=production`, `DB_PORT=5432`, `DB_SSLMODE=require` |
| Template variables | 2 | `DATABRICKS_HOST` uses `{{databricks_host}}` template |
| SP credentials | 2 | `SP_CLIENT_ID_KEY` and `SP_SECRET_KEY` present |
| Resource names | 5 | Each `valueFrom` maps to the correct resource name |

## Running the Tests

```bash
cd "/path/to/lakemeter_app"
source .venv/bin/activate

# Run all installation tests
python -m pytest tests/test_installation/ -v

# Run a specific file
python -m pytest tests/test_installation/test_pricing_data.py -v
python -m pytest tests/test_installation/test_app_config.py -v
```

## Key Validations

### Installer Uses Correct SP Identity Type

The most critical validation: the installer must create SP roles with `identity_type=SERVICE_PRINCIPAL`, not `PG_ONLY`. Two dedicated tests verify this:

- `test_sp_role_uses_service_principal_identity` — checks the string `identity_type=SERVICE_PRINCIPAL` or `"identity_type": "SERVICE_PRINCIPAL"` appears in the installer source
- `test_sp_role_not_pg_only_default` — checks that `PG_ONLY` is not used as the default identity type

The installer handles SP role creation automatically with the correct `identity_type=SERVICE_PRINCIPAL`.

### Pricing Data Integrity

Every pricing file is validated for:

1. **Existence** — File exists in `backend/static/pricing/`
2. **Valid JSON** — Parses without errors
3. **Non-empty** — Has at least one entry
4. **Key format** — Keys follow the expected `cloud:dimension:dimension` pattern
5. **Value ranges** — Numeric values (rates, multipliers) are positive

### App Configuration Correctness

The `app.yaml` tests verify:

- The 5 `valueFrom` references point to the correct Databricks App resource names
- Hardcoded values match production defaults (port 5432, SSL required)
- The `DATABRICKS_HOST` uses the `{{databricks_host}}` template (not a hardcoded URL)
