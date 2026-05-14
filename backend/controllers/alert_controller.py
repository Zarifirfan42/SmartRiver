"""
Alerts controller — Historical alerts, forecast alerts, persistent alert log, resolve (admin).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.auth.dependencies import require_admin
from backend.db.repository import (
    get_alerts,
    get_forecast_alerts,
    get_historical_alerts,
    list_alert_event_log,
    set_alert_event_log_status,
)

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


@router.get("/history")
def alert_history(
    limit: int = Query(200, ge=1, le=2000),
    status: str = Query(None, description="Filter: active | resolved"),
    source: str = Query(None, description="Filter: anomaly | forecast | historical"),
):
    """Persistent log of triggered alerts (SQLite): alert_id, timestamp, station, severity, parameter, WQI, status."""
    return {"items": list_alert_event_log(limit=limit, status=status, source=source)}


@router.patch("/history/{alert_id}/resolve")
def resolve_alert_history(alert_id: int, admin: dict = Depends(require_admin)):
    _ = admin
    if not set_alert_event_log_status(alert_id, "resolved"):
        raise HTTPException(status_code=404, detail="Alert log id not found")
    return {"ok": True, "alert_id": alert_id, "status": "resolved"}
