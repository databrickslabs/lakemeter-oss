import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _line_item_orm_columns() -> list[str]:
    module = ast.parse((ROOT / "backend/app/models/line_item.py").read_text())
    line_item = next(
        node for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "LineItem"
    )

    columns = []
    for stmt in line_item.body:
        if not (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
        ):
            continue
        value = stmt.value
        if isinstance(value, ast.Call) and getattr(value.func, "id", "") == "Column":
            columns.append(stmt.targets[0].id)
    return columns


def _installer_columns(relative_path: str) -> set[str]:
    text = (ROOT / relative_path).read_text()
    create_match = re.search(
        r"CREATE TABLE IF NOT EXISTS (?:\{SCHEMA\}|lakemeter)\.line_items \((.*?)\)\"\"\"",
        text,
        re.S,
    )

    columns = set()
    if create_match:
        for raw in create_match.group(1).splitlines():
            line = raw.strip().rstrip(",")
            if not line or line.startswith(("FOREIGN", "PRIMARY")):
                continue
            columns.add(line.split()[0])

    columns.update(re.findall(r'\("([a-zA-Z0-9_]+)",\s*"[^"]+"\)', text))
    return columns


def test_create_database_has_all_line_item_orm_columns():
    orm_columns = _line_item_orm_columns()
    installer_columns = _installer_columns("scripts/notebooks/02_create_database.py")
    missing = [column for column in orm_columns if column not in installer_columns]

    assert missing == []


def test_install_script_has_all_line_item_orm_columns():
    orm_columns = _line_item_orm_columns()
    installer_columns = _installer_columns("scripts/install_lakemeter.py")
    missing = [column for column in orm_columns if column not in installer_columns]

    assert missing == []
