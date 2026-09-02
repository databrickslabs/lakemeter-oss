"""Idempotent first-start bootstrap for Marketplace Lakebase bindings."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any, Iterable

from app.version import APP_VERSION


logger = logging.getLogger(__name__)

_LOCK_ID = 5494756857658233925
_BOUNDARY = "-- LAKEMETER_STATEMENT_BOUNDARY"
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_SQL_DIR = Path(__file__).resolve().parent / "sql"
_PRICING_DIR = _BACKEND_DIR / "static" / "pricing"

_PRICING_LOADS = (
    (
        "dbu-rates.csv",
        "sync_pricing_dbu_rates",
        (
            "sku_name", "cloud", "tier", "product_type", "sku_region",
            "region", "usage_unit", "price_per_dbu", "currency_code",
            "pricing_type", "fetched_at",
        ),
    ),
    (
        "instance-dbu-rates.csv",
        "sync_ref_instance_dbu_rates",
        (
            "cloud", "instance_type", "vcpus", "memory_gb", "dbu_rate",
            "instance_family", "is_active", "source",
        ),
    ),
    (
        "dbu-multipliers.csv",
        "sync_ref_dbu_multipliers",
        ("cloud", "sku_type", "feature", "multiplier", "category"),
    ),
    (
        "dbsql-rates.csv",
        "sync_product_dbsql_rates",
        (
            "cloud", "warehouse_type", "warehouse_size", "sku_product_type",
            "dbu_per_hour", "includes_compute",
        ),
    ),
    (
        "dbsql-warehouse-config.csv",
        "sync_ref_dbsql_warehouse_config",
        (
            "cloud", "warehouse_size", "worker_count",
            "driver_instance_type", "worker_instance_type", "warehouse_type",
        ),
    ),
    (
        "serverless-rates.csv",
        "sync_product_serverless_rates",
        (
            "cloud", "product", "size_or_model", "rate_type", "dbu_rate",
            "input_divisor", "is_hourly", "sku_product_type", "description",
        ),
    ),
    (
        "fmapi-databricks-rates.csv",
        "sync_product_fmapi_databricks",
        (
            "cloud", "model", "rate_type", "dbu_rate", "input_divisor",
            "is_hourly", "sku_product_type",
        ),
    ),
    (
        "fmapi-proprietary-rates.csv",
        "sync_product_fmapi_proprietary",
        (
            "provider", "model", "endpoint_type", "context_length",
            "rate_type", "dbu_rate", "input_divisor", "is_hourly",
            "sku_product_type", "cloud",
        ),
    ),
    (
        "vm-costs.csv",
        "sync_pricing_vm_costs",
        (
            "cloud", "region", "instance_type", "pricing_tier",
            "payment_option", "cost_per_hour", "currency", "source",
            "fetched_at",
        ),
    ),
    (
        "sku-region-map.csv",
        "sync_ref_sku_region_map",
        ("cloud", "sku_region", "region_code"),
    ),
)


def _sql_statements(filename: str) -> list[str]:
    content = (_SQL_DIR / filename).read_text(encoding="utf-8")
    return [
        statement.strip()
        for statement in content.split(_BOUNDARY)
        if statement.strip()
    ]


def _pricing_paths(filename: str) -> list[Path]:
    path = _PRICING_DIR / filename
    if path.is_file():
        return [path]

    parts = sorted(_PRICING_DIR.glob(f"{path.stem}_part*.csv"))
    if not parts:
        raise RuntimeError(f"Required pricing file is missing: {path}")
    return parts


def _pricing_checksum() -> str:
    digest = hashlib.sha256()
    for filename, _, _ in _PRICING_LOADS:
        digest.update(filename.encode("utf-8"))
        for path in _pricing_paths(filename):
            digest.update(path.name.encode("utf-8"))
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
    return digest.hexdigest()


def _execute_statements(cursor: Any, statements: Iterable[str]) -> None:
    for statement in statements:
        cursor.execute(statement)


def _seed_reference_data(cursor: Any) -> None:
    import json

    seed_path = Path(__file__).resolve().parent / "seeds.json"
    seeds = json.loads(seed_path.read_text(encoding="utf-8"))

    workload_sql = """
        INSERT INTO lakemeter.ref_workload_types (
            workload_type, display_name, description,
            show_compute_config, show_serverless_toggle,
            show_serverless_performance_mode, show_photon_toggle,
            show_dlt_config, show_dbsql_config, show_serverless_product,
            show_fmapi_config, show_lakebase_config, show_vector_search_mode,
            show_vm_pricing, show_usage_hours, show_usage_runs,
            show_usage_tokens, sku_product_type_standard,
            sku_product_type_photon, sku_product_type_serverless, display_order
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (workload_type) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            description = EXCLUDED.description,
            show_compute_config = EXCLUDED.show_compute_config,
            show_serverless_toggle = EXCLUDED.show_serverless_toggle,
            show_serverless_performance_mode =
                EXCLUDED.show_serverless_performance_mode,
            show_photon_toggle = EXCLUDED.show_photon_toggle,
            show_dlt_config = EXCLUDED.show_dlt_config,
            show_dbsql_config = EXCLUDED.show_dbsql_config,
            show_serverless_product = EXCLUDED.show_serverless_product,
            show_fmapi_config = EXCLUDED.show_fmapi_config,
            show_lakebase_config = EXCLUDED.show_lakebase_config,
            show_vector_search_mode = EXCLUDED.show_vector_search_mode,
            show_vm_pricing = EXCLUDED.show_vm_pricing,
            show_usage_hours = EXCLUDED.show_usage_hours,
            show_usage_runs = EXCLUDED.show_usage_runs,
            show_usage_tokens = EXCLUDED.show_usage_tokens,
            sku_product_type_standard = EXCLUDED.sku_product_type_standard,
            sku_product_type_photon = EXCLUDED.sku_product_type_photon,
            sku_product_type_serverless = EXCLUDED.sku_product_type_serverless,
            display_order = EXCLUDED.display_order
    """
    cursor.executemany(workload_sql, seeds["workload_types"])

    cloud_sql = """
        INSERT INTO lakemeter.ref_cloud_tiers (
            cloud, tier, display_name, description, display_order, is_active
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (cloud, tier) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            description = EXCLUDED.description,
            display_order = EXCLUDED.display_order,
            is_active = EXCLUDED.is_active
    """
    cursor.executemany(cloud_sql, seeds["cloud_tiers"])


def _load_pricing(cursor: Any) -> None:
    for filename, table, columns in _PRICING_LOADS:
        cursor.execute(f"TRUNCATE TABLE lakemeter.{table}")
        column_list = ", ".join(columns)
        copy_sql = (
            f"COPY lakemeter.{table} ({column_list}) "
            "FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
        )
        for path in _pricing_paths(filename):
            with path.open(
                "r",
                encoding="utf-8",
            ) as handle:
                cursor.copy_expert(copy_sql, handle)


def _refresh_derived_reference_data(cursor: Any) -> None:
    cursor.execute("TRUNCATE TABLE lakemeter.ref_model_serving_gpu_types")
    cursor.execute("""
        INSERT INTO lakemeter.ref_model_serving_gpu_types (
            cloud, gpu_type, description, is_active
        )
        SELECT DISTINCT cloud, size_or_model, '', TRUE
        FROM lakemeter.sync_product_serverless_rates
        WHERE product = 'model_serving'
          AND LOWER(size_or_model) LIKE '%gpu%'
    """)

    cursor.execute("TRUNCATE TABLE lakemeter.ref_fmapi_databricks_models")
    cursor.execute("""
        INSERT INTO lakemeter.ref_fmapi_databricks_models (
            model_name, description, is_active
        )
        SELECT DISTINCT model, '', TRUE
        FROM lakemeter.sync_product_fmapi_databricks
    """)

    cursor.execute("TRUNCATE TABLE lakemeter.ref_fmapi_proprietary_models")
    cursor.execute("""
        INSERT INTO lakemeter.ref_fmapi_proprietary_models (
            provider, model_name, description, is_active
        )
        SELECT DISTINCT provider, model, '', TRUE
        FROM lakemeter.sync_product_fmapi_proprietary
    """)

    cursor.execute("""
        INSERT INTO lakemeter.sku_discount_mapping (
            sku, sku_display_name, discount_category, workload_group,
            description
        )
        SELECT DISTINCT
            sku_name, sku_name, 'dbu', product_type, product_type
        FROM lakemeter.sync_pricing_dbu_rates
        WHERE sku_name IS NOT NULL AND sku_name != ''
        ON CONFLICT (sku) DO UPDATE SET
            sku_display_name = EXCLUDED.sku_display_name,
            discount_category = EXCLUDED.discount_category,
            workload_group = EXCLUDED.workload_group,
            description = EXCLUDED.description
    """)
    for pattern in ("Model Serving%", "Model Training%", "%Proprietary%"):
        cursor.execute(
            """
            UPDATE lakemeter.sku_discount_mapping
            SET cross_service_eligible = FALSE
            WHERE sku LIKE %s
            """,
            (pattern,),
        )


def _pricing_is_present(cursor: Any) -> bool:
    cursor.execute("SELECT COUNT(*) FROM lakemeter.sync_pricing_dbu_rates")
    dbu_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM lakemeter.sync_pricing_vm_costs")
    vm_count = cursor.fetchone()[0]
    return dbu_count > 0 and vm_count > 0


def bootstrap_database(engine: Any | None = None) -> bool:
    """Bring an already-bound Lakebase database to the packaged app version.

    Returns ``True`` when bootstrap work was applied and ``False`` when the
    database was already current.
    """
    if engine is None:
        from app import database

        if database.engine is None and not database.refresh_engine():
            raise RuntimeError("Lakebase connection is unavailable for bootstrap")
        engine = database.engine

    checksum = _pricing_checksum()
    connection = engine.raw_connection()
    cursor = connection.cursor()
    locked = False
    try:
        cursor.execute("SELECT pg_advisory_lock(%s)", (_LOCK_ID,))
        locked = True

        _execute_statements(cursor, _sql_statements("schema.sql"))
        cursor.execute("""
            SELECT app_version, pricing_checksum
            FROM lakemeter.app_bootstrap_state
            WHERE singleton = TRUE
        """)
        current = cursor.fetchone()
        version_changed = current is None or current[0] != APP_VERSION
        pricing_changed = (
            current is None
            or current[1] != checksum
            or not _pricing_is_present(cursor)
        )

        if not version_changed and not pricing_changed:
            connection.commit()
            logger.info("Lakebase bootstrap is already current")
            return False

        if version_changed:
            _execute_statements(cursor, _sql_statements("functions.sql"))
            _seed_reference_data(cursor)

        if pricing_changed:
            _load_pricing(cursor)
            _refresh_derived_reference_data(cursor)

        cursor.execute(
            """
            INSERT INTO lakemeter.app_bootstrap_state (
                singleton, app_version, pricing_checksum, bootstrapped_at
            )
            VALUES (TRUE, %s, %s, NOW())
            ON CONFLICT (singleton) DO UPDATE SET
                app_version = EXCLUDED.app_version,
                pricing_checksum = EXCLUDED.pricing_checksum,
                bootstrapped_at = EXCLUDED.bootstrapped_at
            """,
            (APP_VERSION, checksum),
        )
        connection.commit()
        logger.info(
            "Lakebase bootstrap completed for app version %s",
            APP_VERSION,
        )
        return True
    except Exception:
        connection.rollback()
        logger.exception("Lakebase bootstrap failed")
        raise
    finally:
        if locked:
            try:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_ID,))
                connection.commit()
            except Exception:
                logger.exception("Failed to release Lakebase bootstrap lock")
        cursor.close()
        connection.close()
