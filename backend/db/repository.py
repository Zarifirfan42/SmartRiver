"""
Database repository — Store and retrieve prediction results, alerts, readings, users.
Uses in-memory store by default; can be extended to PostgreSQL via database/db_connection.
"""
from datetime import datetime, date
from typing import Any, Optional
import json

# In-memory store (mirrors DB tables). Replace with SQL when DATABASE_URL is set.
_store = {
    "users": [],
    "datasets": [],
    "readings": [],       # WQI time series for dashboard
    "prediction_logs": [],
    "alerts": [],
    "stations": [],       # river_stations (admin-managed)
    "_id": {"users": 1, "datasets": 1, "readings": 1, "prediction_logs": 1, "alerts": 1, "stations": 1},
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


# ---------- Users (for auth) ----------
def get_user_by_id(user_id: int) -> Optional[dict]:
    """Get user by primary key."""
    for u in _store["users"]:
        if u["id"] == user_id:
            return dict(u)
    return None


def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email (case-insensitive)."""
    email_lower = (email or "").strip().lower()
    for u in _store["users"]:
        if (u.get("email") or "").strip().lower() == email_lower:
            return dict(u)
    return None


def create_user(
    email: str,
    password_hash: str,
    full_name: Optional[str] = None,
    role: str = "public",
) -> dict:
    """Create a new user. Returns the created user dict."""
    if get_user_by_email(email):
        raise ValueError("Email already registered")
    user_id = _next_id("users")
    row = {
        "id": user_id,
        "email": email.strip().lower(),
        "password_hash": password_hash,
        "full_name": (full_name or "").strip() or None,
        "role": role if role in ("admin", "public") else "public",
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
    }
    _store["users"].append(row)
    return dict(row)


def save_readings(dataset_id: int, readings: list[dict]) -> None:
    """
    Save WQI readings from the dataset. Replaces all existing readings so dashboard
    reflects only the latest preprocessed data (station count and list match the dataset).
    Each reading may include station_code, date/reading_date, wqi, and optional station_name.
    """
    _store["readings"].clear()
    for r in readings:
        _store["readings"].append({
            "id": _next_id("readings"),
            "dataset_id": dataset_id,
            "station_code": str(r.get("station_code", "S01")).strip(),
            "station_name": (r.get("station_name") or r.get("Station Name") or "").strip() or None,
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
    """Dashboard summary from readings. Station count = unique stations in dataset (no fixed list)."""
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
    unique_station_codes = set(r["station_code"] for r in readings)
    wqis = [r["wqi"] for r in readings]
    clean = sum(1 for w in wqis if w >= 81)
    slight = sum(1 for w in wqis if 60 <= w < 81)
    polluted = sum(1 for w in wqis if w < 60)
    return {
        "totalStations": len(unique_station_codes),
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


def get_latest_dataset() -> Optional[dict]:
    """Return the most recently added dataset (by id)."""
    if not _store["datasets"]:
        return None
    return max(_store["datasets"], key=lambda d: d["id"])


def get_latest_anomalies(limit: int = 500) -> list[dict]:
    """
    Return latest anomaly run as list of { date, station_code, wqi, reason }.
    From most recent prediction_log with prediction_type='anomaly'.
    """
    logs = [l for l in _store["prediction_logs"] if l.get("prediction_type") == "anomaly"]
    if not logs:
        return []
    latest = max(logs, key=lambda x: x.get("created_at", ""))
    anomalies = latest.get("result_json", {}).get("anomalies", [])
    out = []
    for a in anomalies[:limit]:
        out.append({
            "date": a.get("date", ""),
            "station_code": a.get("station_code", "—"),
            "wqi": a.get("wqi"),
            "reason": a.get("reason", "Abnormal spike"),
        })
    return out


def get_stations() -> list[dict]:
    """Stations with latest WQI from readings (dataset-driven). Names from dataset when available."""
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
            "station_name": latest.get("station_name") or code,
            "latest_wqi": wqi,
            "river_status": status,
            "last_reading_date": latest.get("reading_date"),
        })
    # Merge with admin-managed stations (by code) for extra metadata only
    admin_codes = {s["station_code"]: s for s in _store["stations"]}
    for rec in out:
        if rec["station_code"] in admin_codes:
            adm = admin_codes[rec["station_code"]]
            if adm.get("station_name"):
                rec["station_name"] = adm["station_name"]
            if adm.get("latitude") is not None:
                rec["latitude"] = adm["latitude"]
            if adm.get("longitude") is not None:
                rec["longitude"] = adm["longitude"]
    for code, s in admin_codes.items():
        if not any(r["station_code"] == code for r in out):
            out.append({
                "station_code": s.get("station_code", code),
                "station_name": s.get("station_name") or code,
                "latitude": s.get("latitude"),
                "longitude": s.get("longitude"),
                "latest_wqi": s.get("latest_wqi"),
                "river_status": s.get("river_status", "clean"),
                "last_reading_date": s.get("last_reading_date"),
            })
    return out


def create_station(
    station_code: str,
    station_name: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    river_name: Optional[str] = None,
    state: Optional[str] = None,
) -> dict:
    """Create a station (admin)."""
    code = (station_code or "").strip()
    if not code:
        raise ValueError("station_code required")
    for s in _store["stations"]:
        if (s.get("station_code") or "").strip() == code:
            raise ValueError("Station code already exists")
    sid = _next_id("stations")
    row = {
        "id": sid,
        "station_code": code,
        "station_name": (station_name or "").strip() or None,
        "latitude": latitude,
        "longitude": longitude,
        "river_name": (river_name or "").strip() or None,
        "state": (state or "").strip() or None,
        "created_at": datetime.utcnow().isoformat(),
    }
    _store["stations"].append(row)
    return dict(row)


def update_station(
    station_id: int,
    station_code: Optional[str] = None,
    station_name: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    river_name: Optional[str] = None,
    state: Optional[str] = None,
) -> Optional[dict]:
    """Update a station (admin)."""
    for s in _store["stations"]:
        if s["id"] == station_id:
            if station_code is not None:
                s["station_code"] = str(station_code).strip()
            if station_name is not None:
                s["station_name"] = str(station_name).strip() or None
            if latitude is not None:
                s["latitude"] = latitude
            if longitude is not None:
                s["longitude"] = longitude
            if river_name is not None:
                s["river_name"] = str(river_name).strip() or None
            if state is not None:
                s["state"] = str(state).strip() or None
            return dict(s)
    return None


def delete_station(station_id: int) -> bool:
    """Delete a station (admin)."""
    for i, s in enumerate(_store["stations"]):
        if s["id"] == station_id:
            _store["stations"].pop(i)
            return True
    return False


def list_stations_admin() -> list[dict]:
    """List all stations for admin (full list from _store['stations'] + derived from readings)."""
    return get_stations()


def seed_default_admin() -> Optional[dict]:
    """
    Create default admin user if not present.
    email: admin@smartriver.com, password: admin123
    Call from app startup (e.g. main.py lifespan).
    """
    from backend.auth.auth_service import hash_password
    existing = get_user_by_email("admin@smartriver.com")
    if existing:
        return None
    return create_user(
        email="admin@smartriver.com",
        password_hash=hash_password("admin123"),
        full_name="SmartRiver Admin",
        role="admin",
    )
