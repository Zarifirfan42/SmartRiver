"""
Alerts controller — List and mark alerts (from anomaly detection).
"""
from fastapi import APIRouter, Query
from backend.db.repository import get_alerts

router = APIRouter()


@router.get("/")
def list_alerts(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
):
    return {"items": get_alerts(unread_only=unread_only, limit=limit)}
