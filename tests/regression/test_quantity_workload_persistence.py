from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.routes.export.excel_item_helpers import calc_item_values
from app.schemas import LineItemCreate, LineItemResponse
from app.schemas.line_item import map_ai_parse_api_fields


def test_shutterstock_frontend_field_maps_to_storage_and_response():
    line_item = LineItemCreate(
        estimate_id=uuid4(),
        workload_name="Image generation",
        workload_type="SHUTTERSTOCK_IMAGEAI",
        shutterstock_images=500,
    )

    data = map_ai_parse_api_fields(
        line_item.model_dump(),
        line_item.model_fields_set,
    )

    assert data["shutterstock_imageai_num_images"] == 500
    assert "shutterstock_images" not in data

    response = LineItemResponse.model_validate({
        **data,
        "line_item_id": uuid4(),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    assert response.shutterstock_images == 500


@pytest.mark.parametrize(
    ("item", "expected_dbus"),
    [
        (
            SimpleNamespace(
                workload_type="AI_PARSE",
                ai_parse_complexity="high",
                ai_parse_num_pages=10_000,
            ),
            875,
        ),
        (
            SimpleNamespace(
                workload_type="SHUTTERSTOCK_IMAGEAI",
                shutterstock_imageai_num_images=500,
            ),
            428.5,
        ),
    ],
)
def test_excel_uses_canonical_quantity_storage_fields(item, expected_dbus):
    _, _, _, total_dbus, _ = calc_item_values(
        item,
        is_fmapi_token=False,
        is_fmapi_provisioned=False,
        dbu_per_hour=0,
        cloud="aws",
        auto_notes=[],
    )

    assert total_dbus == pytest.approx(expected_dbus)
