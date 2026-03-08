"""
Alert system — Create and list alerts (e.g. from anomaly detection).
Used by dashboard and notification flow.
"""
from typing import List, Dict, Any
from datetime import datetime


def create_alert(
    station_code: str,
    message: str,
    severity: str = "warning",
    prediction_log_id: int | None = None,
) -> Dict[str, Any]:
    """Create an alert record (e.g. after anomaly detection). Persist to DB in production."""
    return {
        "id": None,
        "station_code": station_code,
        "message": message,
        "severity": severity,
        "prediction_log_id": prediction_log_id,
        "is_read": False,
        "created_at": datetime.utcnow().isoformat(),
    }


def list_alerts(
    unread_only: bool = False,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Return list of alerts. TODO: query database."""
    return []


def mark_read(alert_id: int) -> bool:
    """Mark alert as read. TODO: update database."""
    return True
