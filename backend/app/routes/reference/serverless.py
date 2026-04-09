"""Serverless mode reference endpoints."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/serverless/modes", tags=["Serverless Multipliers"])
def get_serverless_modes():
    modes = [
        {"mode": "standard", "multiplier": 1, "description": "Standard performance (default)"},
        {"mode": "performance", "multiplier": 2, "description": "Enhanced performance (2x cost)"},
    ]
    return {
        "success": True,
        "data": {
            "count": len(modes),
            "modes": modes,
            "note": "Serverless mode multipliers are the same across all clouds",
        },
    }
