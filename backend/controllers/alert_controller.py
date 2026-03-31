"""
Alerts controller — Historical alerts (latest monitoring) and Forecast alerts (predictions).
"""
from fastapi import APIRouter, Query
from backend.db.repository import get_alerts, get_historical_alerts, get_forecast_alerts

router = APIRouter()


@router.get("/")
def list_alerts(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
):
    """Legacy: all alerts in one list (e.g. for dashboard notification)."""
    return {"items": get_alerts(unread_only=unread_only, limit=limit)}


@router.get("/by-type")
def list_alerts_by_type(
    limit: int = Query(100, ge=1, le=500),
    river_name: str = Query(None, description="Show alerts only for this river (e.g. Sungai Klang)"),
):
    """Historical alerts (latest date first) and Forecast alerts (earliest forecast date first)."""
    return {
        "historical": get_historical_alerts(limit=limit, river_name=river_name),
        "forecast": get_forecast_alerts(limit=limit, river_name=river_name),
    }
