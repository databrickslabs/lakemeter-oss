"""Tests for SDP/DLT reference values consumed by the frontend."""

from app.routes.reference.dlt import get_dlt_editions


def test_dlt_editions_have_select_option_shape():
    response = get_dlt_editions()

    assert response["data"]["editions"] == [
        {"id": "CORE", "name": "Core"},
        {"id": "PRO", "name": "Pro"},
        {"id": "ADVANCED", "name": "Advanced"},
    ]
