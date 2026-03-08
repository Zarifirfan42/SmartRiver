"""
Database repository — Store and retrieve prediction results, alerts, readings.
Uses in-memory store by default; can be extended to PostgreSQL via database/db_connection.
"""
from datetime import datetime, date
from typing import Any, Optional
import json

# In-memory store (mirrors DB tables). Replace with SQL when DATABASE_URL is set.
_store = {
    "datasets": [],
    "readings": [],       # WQI time series for dashboard
    "prediction_logs": [],
    "alerts": [],
    "_id": {"datasets": 1, "readings": 1, "prediction_logs": 1, "alerts": 1},
}


def _next_id(table: str) -> int:
    n = _store["_id"][table]
    _store["_id"][table] += 1
    return n


def save_dataset(name: str, file_path: str, file_size: int, row_count: int, uploaded_by: int = 1) -> dict:
    row = {
        "id": _next_id("datasets"),
        "name": name,
        "file_path": file_path,
        "file_size_bytes": file_size,
        "row_count": row_count,
        "uploaded_by": uploaded_by,
        "created_at": datetime.utcnow().isoformat(),
    }
    _store["datasets"].append(row)
    return row


def save_readings(dataset_id: int, readings: list[dict]) -> None:
    """Save WQI readings (station_code, reading_date, wqi) for dashboard time-series."""
    for r in readings:
        _store["readings"].append({
            "id": _next_id("readings"),
            "dataset_id": dataset_id,
            "station_code": r.get("station_code", "S01"),
            "reading_date": r.get("date", r.get("reading_date", "")),
            "wqi": float(r.get("wqi", 0)),
            "created_at": datetime.utcnow().isoformat(),
        })


def save_prediction_log(
    prediction_type: str,
    result_json: dict,
    dataset_id: Optional[int] = None,
    station_code: Optional[str] = None,
    reference_date: Optional[date] = None,
    model_name: Optional[str] = None,
) -> dict:
    """Save classification, forecast, or anomaly result for dashboard and history."""
    row = {
        "id": _next_id("prediction_logs"),
        "dataset_id": dataset_id,
        "prediction_type": prediction_type,
        "model_name": model_name,
        "station_code": station_code,
        "reference_date": reference_date.isoformat() if reference_date else None,
        "result_json": result_json,
        "created_at": datetime.utcnow().isoformat(),
    }
    _store["prediction_logs"].append(row)
    return row


def save_alert(station_code: str, message: str, severity: str = "warning", prediction_log_id: Optional[int] = None) -> dict:
    row = {
        "id": _next_id("alerts"),
        "prediction_log_id": prediction_log_id,
        "station_code": station_code,
        "message": message,
        "severity": severity,
        "is_read": False,
        "created_at": datetime.utcnow().isoformat(),
    }
    _store["alerts"].append(row)
    return row


def get_summary() -> dict:
    """Dashboard summary from readings and prediction_logs."""
    readings = _store["readings"]
    if not readings:
        return {
            "totalStations": 0,
            "avgWqi": 0,
            "cleanCount": 0,
            "slightlyPollutedCount": 0,
            "pollutedCount": 0,
            "recentAnomaliesCount": len([a for a in _store["alerts"] if not a.get("is_read")]),
        }
    stations = set(r["station_code"] for r in readings)
    wqis = [r["wqi"] for r in readings]
    clean = sum(1 for w in wqis if w >= 81)
    slight = sum(1 for w in wqis if 60 <= w < 81)
    polluted = sum(1 for w in wqis if w < 60)
    return {
        "totalStations": len(stations),
        "avgWqi": sum(wqis) / len(wqis) if wqis else 0,
        "cleanCount": clean,
        "slightlyPollutedCount": slight,
        "pollutedCount": polluted,
        "recentAnomaliesCount": len([a for a in _store["alerts"] if not a.get("is_read")]),
    }


def get_time_series(station_code: Optional[str] = None, limit: int = 100) -> list[dict]:
    """WQI time series for charts."""
    readings = _store["readings"]
    if station_code:
        readings = [r for r in readings if r["station_code"] == station_code]
    readings = sorted(readings, key=lambda x: x.get("reading_date", ""))[-limit:]
    return [{"date": r["reading_date"], "wqi": r["wqi"], "station_code": r["station_code"]} for r in readings]


def get_latest_forecast(limit: int = 30) -> list[dict]:
    """Latest forecast from prediction_logs (type=forecast)."""
    logs = [l for l in _store["prediction_logs"] if l["prediction_type"] == "forecast"]
    if not logs:
        return []
    latest = sorted(logs, key=lambda x: x["created_at"])[-1]
    forecast = latest.get("result_json", {}).get("forecast", [])
    return forecast[:limit]


def get_alerts(unread_only: bool = False, limit: int = 50) -> list[dict]:
    alerts = _store["alerts"]
    if unread_only:
        alerts = [a for a in alerts if not a.get("is_read")]
    return sorted(alerts, key=lambda x: x["created_at"], reverse=True)[:limit]


def get_stations() -> list[dict]:
    """Stations with latest WQI from readings."""
    from collections import defaultdict
    by_station = defaultdict(list)
    for r in _store["readings"]:
        by_station[r["station_code"]].append(r)
    out = []
    for code, rows in by_station.items():
        rows = sorted(rows, key=lambda x: x.get("reading_date", ""))
        latest = rows[-1] if rows else {}
        wqi = latest.get("wqi", 0)
        status = "clean" if wqi >= 81 else ("slightly_polluted" if wqi >= 60 else "polluted")
        out.append({
            "station_code": code,
            "latest_wqi": wqi,
            "river_status": status,
            "last_reading_date": latest.get("reading_date"),
        })
    return out
