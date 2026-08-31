import ast
import re
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.schemas.line_item import (
    LineItemCreate,
    LineItemResponse,
    LineItemUpdate,
    map_ai_parse_api_fields,
)


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


def _estimate_orm_columns() -> list[str]:
    module = ast.parse((ROOT / "backend/app/models/estimate.py").read_text())
    estimate = next(
        node for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "Estimate"
    )

    columns = []
    for stmt in estimate.body:
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


def _estimate_installer_columns(relative_path: str) -> set[str]:
    text = (ROOT / relative_path).read_text()
    create_match = re.search(
        r"CREATE TABLE IF NOT EXISTS (?:\{SCHEMA\}|lakemeter)\.estimates \((.*?)\)\"\"\"",
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

    columns.update(
        re.findall(
            r"ALTER TABLE (?:\{SCHEMA\}|lakemeter)\.estimates\s+"
            r"ADD COLUMN IF NOT EXISTS ([a-zA-Z0-9_]+)",
            text,
            re.S,
        )
    )
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


def test_create_database_has_all_estimate_orm_columns():
    orm_columns = _estimate_orm_columns()
    installer_columns = _estimate_installer_columns(
        "scripts/notebooks/02_create_database.py"
    )
    missing = [column for column in orm_columns if column not in installer_columns]

    assert missing == []


def test_ai_parse_create_fields_map_to_existing_storage_columns():
    line_item = LineItemCreate.model_validate({
        "estimate_id": uuid4(),
        "workload_name": "Contract Scanner",
        "workload_type": "AI_PARSE",
        "ai_parse_mode": "pages",
        "ai_parse_complexity": "high",
        "ai_parse_pages_thousands": 200,
    })

    storage_data = map_ai_parse_api_fields(
        line_item.model_dump(),
        line_item.model_fields_set,
    )

    assert "ai_parse_mode" not in storage_data
    assert "ai_parse_pages_thousands" not in storage_data
    assert storage_data["ai_parse_calculation_method"] == "pages_based"
    assert storage_data["ai_parse_num_pages"] == 200_000


def test_ai_parse_update_can_clear_existing_page_configuration():
    line_item = LineItemUpdate.model_validate({
        "ai_parse_mode": None,
        "ai_parse_pages_thousands": None,
    })

    storage_data = map_ai_parse_api_fields(
        line_item.model_dump(exclude_unset=True),
        line_item.model_fields_set,
    )

    assert storage_data["ai_parse_calculation_method"] is None
    assert storage_data["ai_parse_num_pages"] is None


def test_ai_parse_response_hydrates_frontend_fields_from_storage():
    line_item_id = uuid4()
    estimate_id = uuid4()
    now = datetime.now()
    stored_item = SimpleNamespace(
        line_item_id=line_item_id,
        estimate_id=estimate_id,
        workload_name="Contract Scanner",
        workload_type="AI_PARSE",
        ai_parse_calculation_method="pages_based",
        ai_parse_complexity="high",
        ai_parse_num_pages=200_000,
        created_at=now,
        updated_at=now,
    )

    response = LineItemResponse.model_validate(stored_item)

    assert response.ai_parse_mode == "pages"
    assert response.ai_parse_pages_thousands == 200
    assert response.ai_parse_num_pages == 200_000
