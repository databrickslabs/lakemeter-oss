"""DLT reference endpoints."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/dlt/editions", tags=["DLT"])
def get_dlt_editions():
    editions = [
        {"id": "CORE", "name": "Core"},
        {"id": "PRO", "name": "Pro"},
        {"id": "ADVANCED", "name": "Advanced"},
    ]
    return {
        "success": True,
        "data": {"count": len(editions), "editions": editions},
    }
