"""DLT reference endpoints."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/dlt/editions", tags=["DLT"])
def get_dlt_editions():
    editions = ["CORE", "PRO", "ADVANCED"]
    return {
        "success": True,
        "data": {"count": len(editions), "editions": editions},
    }
