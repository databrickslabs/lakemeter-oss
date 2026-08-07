#!/usr/bin/env python3
"""Apply additive schema migrations to a deployed Lakemeter Lakebase database.

`deploy.sh` ships application code only — it does not re-run the installer notebooks. Without
this step, adding a column to the SQLAlchemy models breaks the deployed app at runtime: every
insert references a column the database does not have, and the API returns HTTP 500 ("Failed to
save"). This script closes that gap so schema changes ship alongside code.

Every statement is idempotent (``ADD COLUMN IF NOT EXISTS``), so it is safe to run on every
deploy and safe to re-run.

Usage:
    python scripts/migrate_schema.py --profile <cli-profile> [--instance NAME] [--db NAME]
    python scripts/migrate_schema.py --profile p --dry-run    # report only, change nothing

The instance/database are auto-detected from the app's Databricks secrets when not supplied.
"""
import argparse
import sys
import uuid

SCHEMA = "lakemeter"

# Columns that must exist on lakemeter.line_items. Keep in sync with
# backend/app/models/line_item.py and scripts/notebooks/02_create_database.py.
LINE_ITEM_COLUMNS = [
    # Lakehouse Federation (query-volume driven)
    ("federation_size", "VARCHAR(10)"),
    ("federation_num_users", "INT"),
    ("federation_queries_per_period", "NUMERIC(14,2)"),
    ("federation_query_period", "VARCHAR(10)"),
    ("federation_avg_query_seconds", "NUMERIC(10,2)"),
    ("federation_warehouse_size", "VARCHAR(20)"),
]

# Config-visibility flags that must exist on lakemeter.ref_workload_types.
WORKLOAD_TYPE_COLUMNS = [
    ("show_federation_config", "BOOLEAN DEFAULT false"),
]

GREEN, YELLOW, RED, CYAN, NC = "\033[0;32m", "\033[1;33m", "\033[0;31m", "\033[0;36m", "\033[0m"


def _secret(w, scope: str, key: str):
    """Read a Databricks secret, returning None if it is absent."""
    import base64
    try:
        resp = w.secrets.get_secret(scope=scope, key=key)
        return base64.b64decode(resp.value).decode()
    except Exception:
        return None


def resolve_target(w, instance: str, db: str, secrets_scope: str):
    """Fill in instance/database names from app secrets when not provided."""
    if not instance:
        instance = _secret(w, secrets_scope, "lakemeter-lakebase-instance")
    if not db:
        db = _secret(w, secrets_scope, "lakemeter-db-name") or "lakemeter_pricing"
    return instance, db


def migrate(profile: str, instance: str, db: str, secrets_scope: str, dry_run: bool) -> int:
    try:
        import psycopg2
        from databricks.sdk import WorkspaceClient
        from databricks.sdk.config import Config
    except ImportError as e:
        print(f"{RED}Missing dependency: {e}{NC}")
        print("  Install with: pip install databricks-sdk psycopg2-binary")
        return 1

    w = WorkspaceClient(config=Config(profile=profile)) if profile else WorkspaceClient()
    instance, db = resolve_target(w, instance, db, secrets_scope)
    if not instance:
        print(f"{RED}Could not determine the Lakebase instance name.{NC}")
        print("  Pass --instance NAME (or ensure the app's secret scope is readable).")
        return 1

    print(f"  Instance: {CYAN}{instance}{NC}   Database: {CYAN}{db}{NC}")

    inst = w.database.get_database_instance(instance)
    cred = w.database.generate_database_credential(
        request_id=str(uuid.uuid4()), instance_names=[instance]
    )
    conn = psycopg2.connect(
        host=inst.read_write_dns, port=5432, database=db,
        user=w.current_user.me().user_name, password=cred.token, sslmode="require",
    )
    conn.autocommit = True
    cur = conn.cursor()

    total_added = 0
    for table, columns in (("line_items", LINE_ITEM_COLUMNS),
                           ("ref_workload_types", WORKLOAD_TYPE_COLUMNS)):
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s",
            (SCHEMA, table),
        )
        existing = {r[0] for r in cur.fetchall()}
        if not existing:
            print(f"  {YELLOW}⚠ {SCHEMA}.{table} not found — skipping "
                  f"(run the installer to create the schema){NC}")
            continue

        missing = [(n, t) for n, t in columns if n not in existing]
        if not missing:
            print(f"  {GREEN}✓{NC} {SCHEMA}.{table}: up to date")
            continue

        if dry_run:
            print(f"  {YELLOW}would add {len(missing)} column(s) to {SCHEMA}.{table}:{NC}")
            for name, typ in missing:
                print(f"      + {name} {typ}")
            total_added += len(missing)
            continue

        print(f"  {YELLOW}adding {len(missing)} column(s) to {SCHEMA}.{table}…{NC}")
        for name, typ in missing:
            try:
                cur.execute(
                    f"ALTER TABLE {SCHEMA}.{table} ADD COLUMN IF NOT EXISTS {name} {typ}"
                )
                print(f"      {GREEN}+{NC} {name} {typ}")
                total_added += 1
            except Exception as e:
                print(f"      {RED}✗ {name}: {str(e)[:120]}{NC}")
                cur.close()
                conn.close()
                return 1

    cur.close()
    conn.close()

    if total_added == 0:
        print(f"  {GREEN}Schema already current — nothing to do.{NC}")
    elif dry_run:
        print(f"  {YELLOW}Dry run: {total_added} column(s) would be added.{NC}")
    else:
        print(f"  {GREEN}Migration complete: {total_added} column(s) added.{NC}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Apply additive Lakemeter schema migrations.")
    ap.add_argument("--profile", default="", help="Databricks CLI profile")
    ap.add_argument("--instance", default="", help="Lakebase instance name (auto-detected if omitted)")
    ap.add_argument("--db", default="", help="Database name (auto-detected if omitted)")
    ap.add_argument("--secrets-scope", default="lakemeter-secrets", help="Secret scope for auto-detection")
    ap.add_argument("--dry-run", action="store_true", help="Report pending changes without applying them")
    args = ap.parse_args()
    sys.exit(migrate(args.profile, args.instance, args.db, args.secrets_scope, args.dry_run))


if __name__ == "__main__":
    main()
