"""
Database repository — Store and retrieve prediction results, alerts, readings, users.
Uses in-memory store by default; can be extended to PostgreSQL via database/db_connection.
Classification: record.date <= today → historical; record.date > today → forecast.
"""
from datetime import datetime, date
from typing import Any, Optional
import json
import os
import sqlite3
from pathlib import Path


def _today_str() -> str:
    """Current system date (YYYY-MM-DD) for classifying historical vs forecast."""
    return date.today().isoformat()

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

_SQLITE_PATH = os.environ.get("SMARTRIVER_SQLITE_PATH") or str(
    Path(__file__).resolve().parent / "smartriver.sqlite3"
)


def _sqlite_conn() -> sqlite3.Connection:
    """
    SQLite connection for persistent auth/user data.
    We keep analytics/readings in-memory for now, but users must persist across restarts.
    """
    conn = sqlite3.connect(_SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_sqlite_schema() -> None:
    with _sqlite_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              email TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              full_name TEXT NULL,
              role TEXT NOT NULL DEFAULT 'public',
              is_active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL
            )
            """
        )


_ensure_sqlite_schema()


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
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    with _sqlite_conn() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, full_name, role, is_active, created_at FROM users WHERE id = ?",
            (uid,),
        ).fetchone()
        if not row:
            return None
        return dict(row)


def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email (case-insensitive)."""
    email_lower = (email or "").strip().lower()
    if not email_lower:
        return None
    with _sqlite_conn() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, full_name, role, is_active, created_at FROM users WHERE lower(email) = ?",
            (email_lower,),
        ).fetchone()
        if not row:
            return None
        return dict(row)


def create_user(
    email: str,
    password_hash: str,
    full_name: Optional[str] = None,
    role: str = "public",
) -> dict:
    """Create a new user. Returns the created user dict."""
    if get_user_by_email(email):
        raise ValueError("Email already registered")
    email_norm = (email or "").strip().lower()
    if not email_norm:
        raise ValueError("Email required")
    role_norm = role if role in ("admin", "public") else "public"
    created_at = datetime.utcnow().isoformat()
    with _sqlite_conn() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO users (email, password_hash, full_name, role, is_active, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (email_norm, password_hash, (full_name or "").strip() or None, role_norm, created_at),
            )
        except sqlite3.IntegrityError:
            raise ValueError("Email already registered")
        user_id = int(cur.lastrowid)
    return {
        "id": user_id,
        "email": email_norm,
        "password_hash": password_hash,
        "full_name": (full_name or "").strip() or None,
        "role": role_norm,
        "is_active": 1,
        "created_at": created_at,
    }


def update_user_password_by_email(email: str, new_password_hash: str) -> bool:
    """Update password for user with given email. Returns True if updated, False if email not found."""
    email_lower = (email or "").strip().lower()
    if not email_lower:
        return False
    with _sqlite_conn() as conn:
        cur = conn.execute(
            "UPDATE users SET password_hash = ? WHERE lower(email) = ?",
            (new_password_hash, email_lower),
        )
        return cur.rowcount > 0


def save_readings(dataset_id: int, readings: list[dict]) -> None:
    """
    Save WQI readings from the dataset. Replaces all existing readings so dashboard
    reflects only the latest preprocessed data (station count and list match the dataset).
    Each reading may include station_code, date/reading_date, wqi, and optional station_name.
    """
    _store["readings"].clear()
    for r in readings:
        rec = {
            "id": _next_id("readings"),
            "dataset_id": dataset_id,
            "station_code": str(r.get("station_code", "S01")).strip(),
            "station_name": (r.get("station_name") or r.get("Station Name") or "").strip() or None,
            "reading_date": r.get("date", r.get("reading_date", "")),
            "wqi": float(r.get("wqi", 0)),
            "created_at": datetime.utcnow().isoformat(),
        }
        if r.get("river_status") is not None:
            rec["river_status"] = str(r.get("river_status")).strip() or None
        if r.get("source") is not None:
            rec["source"] = str(r.get("source")).strip()
        rec["data_type"] = str(r.get("data_type") or "historical").strip()
        _store["readings"].append(rec)


def append_reading(
    dataset_id: int,
    station_code: str,
    station_name: Optional[str],
    reading_date: str,
    wqi: float,
    river_status: str,
    source: Optional[str] = None,
    data_type: Optional[str] = None,
) -> dict:
    """
    Append a single reading without clearing existing data (e.g. simulated live data).
    Returns the created record. Use source='simulated_live', data_type='simulated_live' for auto-generated daily data.
    """
    rec = {
        "id": _next_id("readings"),
        "dataset_id": dataset_id,
        "station_code": str(station_code).strip(),
        "station_name": (station_name or station_code).strip() or None,
        "reading_date": str(reading_date)[:10],
        "wqi": float(wqi),
        "river_status": str(river_status).strip() if river_status else None,
        "created_at": datetime.utcnow().isoformat(),
    }
    if source:
        rec["source"] = str(source).strip()
    rec["data_type"] = (data_type or ("simulated_live" if source == "simulated_live" else "historical")).strip()
    _store["readings"].append(rec)
    return rec


def get_latest_reading_for_station(station_name_or_code: str) -> Optional[dict]:
    """
    Get the latest reading (by date) for a station with reading_date <= today.
    Used to continue simulated live from last value; never use future dates.
    """
    key = (station_name_or_code or "").strip()
    today = _today_str()
    if not key:
        return None
    candidates = [
        r for r in _store["readings"]
        if (r.get("station_name") or r.get("station_code") or "").strip() == key
        and (r.get("reading_date") or "") <= today
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda x: x.get("reading_date") or "")


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


def save_alert(
    station_code: str,
    message: str,
    severity: str = "warning",
    prediction_log_id: Optional[int] = None,
    wqi: Optional[float] = None,
    date_str: Optional[str] = None,
    alert_type: Optional[str] = None,
    river_status: Optional[str] = None,
    station_name: Optional[str] = None,
) -> dict:
    """Create an alert row. alert_type: 'historical' | 'forecast'. Optionally WQI, date, river_status, station_name."""
    row = {
        "id": _next_id("alerts"),
        "prediction_log_id": prediction_log_id,
        "station_code": station_code,
        "message": message,
        "is_read": False,
        "created_at": datetime.utcnow().isoformat(),
    }
    if alert_type:
        row["alert_type"] = str(alert_type).strip().lower()
    if wqi is not None:
        try:
            row["wqi"] = float(wqi)
        except (TypeError, ValueError):
            pass
    if date_str:
        row["date"] = str(date_str)[:10]
    if river_status:
        row["river_status"] = str(river_status).strip()
    if station_name:
        row["station_name"] = str(station_name).strip()
    _store["alerts"].append(row)
    return row


def get_summary() -> dict:
    """
    Dashboard summary using LATEST record per station only (reading_date <= today).
    For each station: find latest date <= today, use that row as current monitoring record.
    """
    from collections import defaultdict
    today = _today_str()
    readings = [r for r in _store["readings"] if (r.get("reading_date") or "") <= today]
    if not readings:
        return {
            "totalStations": 0,
            "avgWqi": 0,
            "cleanCount": 0,
            "slightlyPollutedCount": 0,
            "pollutedCount": 0,
            "recentAnomaliesCount": len([a for a in _store["alerts"] if not a.get("is_read")]),
            "predictedAvgWqi2025_2028": get_predicted_avg_wqi_2025_2028(),
            "today": today,
        }
    by_station = defaultdict(list)
    for r in readings:
        key = r.get("station_name") or r.get("station_code", "")
        if key:
            by_station[key].append(r)
    latest_records = []
    for _name, rows in by_station.items():
        rows = sorted(rows, key=lambda x: x.get("reading_date", ""))
        if rows:
            latest_records.append(rows[-1])
    if not latest_records:
        return {
            "totalStations": 0,
            "avgWqi": 0,
            "cleanCount": 0,
            "slightlyPollutedCount": 0,
            "pollutedCount": 0,
            "recentAnomaliesCount": len([a for a in _store["alerts"] if not a.get("is_read")]),
            "predictedAvgWqi2025_2028": get_predicted_avg_wqi_2025_2028(),
            "today": today,
        }
    wqis = [r["wqi"] for r in latest_records]
    clean = sum(1 for r in latest_records if _status_from_reading(r) == "clean")
    slight = sum(1 for r in latest_records if _status_from_reading(r) == "slightly_polluted")
    polluted = sum(1 for r in latest_records if _status_from_reading(r) == "polluted")
    return {
        "totalStations": len(latest_records),
        "avgWqi": sum(wqis) / len(wqis) if wqis else 0,
        "cleanCount": clean,
        "slightlyPollutedCount": slight,
        "pollutedCount": polluted,
        "recentAnomaliesCount": len([a for a in _store["alerts"] if not a.get("is_read")]),
        "predictedAvgWqi2025_2028": get_predicted_avg_wqi_2025_2028(),
        "today": today,
    }


def _status_from_reading(r: dict) -> str:
    """Normalize river status from a reading (explicit or from WQI)."""
    st = r.get("river_status")
    if st:
        s = str(st).strip().lower().replace(" ", "_")
        if s in ("clean", "slightly_polluted", "polluted"):
            return s
    w = r.get("wqi", 0)
    return "clean" if w >= 81 else ("slightly_polluted" if w >= 60 else "polluted")


def get_predicted_avg_wqi_2025_2028() -> float:
    """Average of predicted WQI for 2025-2028 (from latest forecast run)."""
    forecast = get_latest_forecast(limit=10000)
    if not forecast:
        return 0.0
    wqis = [float(f.get("wqi", 0)) for f in forecast if f.get("wqi") is not None]
    return sum(wqis) / len(wqis) if wqis else 0.0


def get_time_series(station_code: Optional[str] = None, station_name: Optional[str] = None, year: Optional[int] = None, limit: int = 100) -> list[dict]:
    """WQI time series for charts: only readings with reading_date <= today (historical + simulated_live)."""
    today = _today_str()
    readings = [r for r in _store["readings"] if (r.get("reading_date") or "") <= today]
    if station_code or station_name:
        readings = [
            r for r in readings
            if (station_code and r.get("station_code") == station_code)
            or (station_name and (r.get("station_name") == station_name or r.get("station_code") == station_name))
        ]
    if year is not None:
        readings = [r for r in readings if r.get("reading_date", "")[:4] == str(year)]
    readings = sorted(readings, key=lambda x: (x.get("reading_date", ""), x.get("station_code", "")))
    # Dedupe by date for single-station view (keep last per date)
    if station_code or station_name:
        seen = set()
        out = []
        for r in reversed(readings):
            d = r.get("reading_date", "")
            if d not in seen:
                seen.add(d)
                out.append(r)
        readings = list(reversed(out))
    readings = readings[-limit:]
    out = []
    for r in readings:
        rec = {
            "date": r["reading_date"],
            "wqi": r["wqi"],
            "station_code": r.get("station_code"),
            "station_name": r.get("station_name") or r.get("station_code"),
        }
        if r.get("river_status") is not None:
            rec["river_status"] = r["river_status"]
        out.append(rec)
    return out


def get_wqi_data(
    station_code: Optional[str] = None,
    station_name: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = 500,
) -> list[dict]:
    """WQI records (reading_date <= today): Date, Station Name, WQI, River Status. Filter by station and/or year."""
    today = _today_str()
    readings = [r for r in _store["readings"] if (r.get("reading_date") or "") <= today]
    if station_code or station_name:
        readings = [
            r for r in readings
            if (station_code and r.get("station_code") == station_code)
            or (station_name and (r.get("station_name") == station_name or r.get("station_code") == station_name))
        ]
    if year is not None:
        readings = [r for r in readings if r.get("reading_date", "")[:4] == str(year)]
    readings = sorted(readings, key=lambda x: x.get("reading_date", ""))[-limit:]
    out = []
    for r in readings:
        status = r.get("river_status")
        if status is None:
            w = r.get("wqi", 0)
            status = "clean" if w >= 81 else ("slightly_polluted" if w >= 60 else "polluted")
        out.append({
            "date": r["reading_date"],
            "station": r.get("station_name") or r.get("station_code"),
            "station_code": r.get("station_code"),
            "station_name": r.get("station_name") or r.get("station_code"),
            "wqi": r["wqi"],
            "river_status": status,
        })
    return out


def _apply_readings_filters(
    readings: list,
    station_name: Optional[str] = None,
    year: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """Apply filters to readings list (in place). Returns filtered list."""
    if station_name:
        readings = [r for r in readings if (r.get("station_name") or r.get("station_code")) == station_name]
    if year is not None:
        readings = [r for r in readings if (r.get("reading_date") or "")[:4] == str(year)]
    if status:
        def _status(r):
            st = r.get("river_status")
            if st:
                return str(st).strip().lower().replace(" ", "_")
            w = r.get("wqi", 0)
            return "clean" if w >= 81 else ("slightly_polluted" if w >= 60 else "polluted")
        status_norm = status.strip().lower().replace(" ", "_")
        readings = [r for r in readings if _status(r) == status_norm]
    if date_from:
        readings = [r for r in readings if (r.get("reading_date") or "") >= date_from[:10]]
    if date_to:
        readings = [r for r in readings if (r.get("reading_date") or "") <= date_to[:10]]
    return readings


def get_readings_count(
    station_name: Optional[str] = None,
    year: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    data_type: Optional[str] = None,
) -> int:
    """Total count matching filters. data_type: 'all' | 'historical' | 'forecast'. historical = date <= today, forecast = from prediction_logs date > today."""
    today = _today_str()
    if (data_type or "").strip().lower() == "forecast":
        forecast = get_latest_forecast(station_code=station_name, limit=100000)
        if year is not None:
            forecast = [f for f in forecast if (f.get("date") or "")[:4] == str(year)]
        if date_from:
            forecast = [f for f in forecast if (f.get("date") or "") >= date_from[:10]]
        if date_to:
            forecast = [f for f in forecast if (f.get("date") or "") <= date_to[:10]]
        return len(forecast)
    readings = list(_store["readings"])
    if (data_type or "").strip().lower() == "historical":
        readings = [r for r in readings if (r.get("reading_date") or "") <= today]
    readings = _apply_readings_filters(readings, station_name=station_name, year=year, status=status, date_from=date_from, date_to=date_to)
    return len(readings)


def get_readings_table(
    station_name: Optional[str] = None,
    year: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort_by: str = "date",
    sort_order: str = "asc",
    limit: int = 100000,
    offset: int = 0,
    data_type: Optional[str] = None,
) -> list[dict]:
    """Dataset table: Station Name, Date, WQI, River Status, data_type. data_type: 'all' | 'historical' (date <= today) | 'forecast' (date > today from prediction_logs)."""
    today = _today_str()
    if (data_type or "").strip().lower() == "forecast":
        forecast = get_latest_forecast(station_code=station_name, limit=limit + offset, year_from=int(year) if year is not None else None, year_to=int(year) if year is not None else None)
        if date_from:
            forecast = [f for f in forecast if (f.get("date") or "") >= date_from[:10]]
        if date_to:
            forecast = [f for f in forecast if (f.get("date") or "") <= date_to[:10]]
        key = "wqi" if sort_by == "wqi" else "date"
        reverse = sort_order.lower() == "desc"
        forecast = sorted(forecast, key=lambda x: (x.get(key) if key == "wqi" else x.get(key) or ""), reverse=reverse)
        forecast = forecast[offset : offset + limit]
        out = []
        for r in forecast:
            st = r.get("river_status")
            if st is None:
                w = r.get("wqi", 0)
                st = "clean" if w >= 81 else ("slightly_polluted" if w >= 60 else "polluted")
            out.append({
                "station_name": r.get("station_name") or r.get("station_code"),
                "date": r.get("date"),
                "wqi": r.get("wqi"),
                "river_status": st,
                "data_type": "forecast",
            })
        return out
    readings = list(_store["readings"])
    if (data_type or "").strip().lower() == "historical":
        readings = [r for r in readings if (r.get("reading_date") or "") <= today]
    readings = _apply_readings_filters(readings, station_name=station_name, year=year, status=status, date_from=date_from, date_to=date_to)
    key = "wqi" if sort_by == "wqi" else "reading_date"
    reverse = sort_order.lower() == "desc"
    readings = sorted(readings, key=lambda x: (x.get(key) if key == "wqi" else x.get(key) or ""), reverse=reverse)
    readings = readings[offset : offset + limit]
    out = []
    for r in readings:
        st = r.get("river_status")
        if st is None:
            w = r.get("wqi", 0)
            st = "clean" if w >= 81 else ("slightly_polluted" if w >= 60 else "polluted")
        out.append({
            "station_name": r.get("station_name") or r.get("station_code"),
            "date": r["reading_date"],
            "wqi": r["wqi"],
            "river_status": st,
            "data_type": r.get("data_type") or "historical",
        })
    return out


def get_available_years() -> list[int]:
    """Return distinct years from readings (from dataset)."""
    years = set()
    for r in _store["readings"]:
        d = r.get("reading_date") or ""
        if len(d) >= 4:
            try:
                years.add(int(d[:4]))
            except ValueError:
                pass
    return sorted(years)


def get_latest_forecast(station_code: Optional[str] = None, limit: int = 10000, year_from: Optional[int] = None, year_to: Optional[int] = None) -> list[dict]:
    """Forecast from prediction_logs: only dates > today (starts from tomorrow). Optional filter by station and year range."""
    today = _today_str()
    logs = [l for l in _store["prediction_logs"] if l["prediction_type"] == "forecast"]
    if not logs:
        return []
    latest = sorted(logs, key=lambda x: x["created_at"])[-1]
    forecast = latest.get("result_json", {}).get("forecast", [])
    forecast = [f for f in forecast if (f.get("date") or "") > today]
    if station_code:
        forecast = [f for f in forecast if f.get("station_code") == station_code or f.get("station_name") == station_code]
    if year_from is not None:
        forecast = [f for f in forecast if (f.get("date") or "")[:4] and int((f.get("date") or "0")[:4]) >= year_from]
    if year_to is not None:
        forecast = [f for f in forecast if (f.get("date") or "")[:4] and int((f.get("date") or "0")[:4]) <= year_to]
    return forecast[:limit]


def clear_historical_alerts() -> None:
    """Remove all alerts with alert_type='historical'. Used when regenerating from dataset."""
    _store["alerts"] = [
        a for a in _store["alerts"]
        if (a.get("alert_type") or "").lower() != "historical"
    ]


def get_alerts(unread_only: bool = False, limit: int = 50) -> list[dict]:
    """Return all alerts sorted by event date (latest first). Prefer alert date, fallback to created_at."""
    alerts = _store["alerts"]
    if unread_only:
        alerts = [a for a in alerts if not a.get("is_read")]
    def _key(a: dict) -> str:
        return (a.get("date") or a.get("created_at") or "")
    return sorted(alerts, key=_key, reverse=True)[:limit]


def get_historical_alerts(limit: int = 100) -> list[dict]:
    """
    Historical alerts (latest record per station):
    - Use readings with reading_date <= today
    - If latest status is slightly_polluted or polluted -> alert
    - No severity concept; message is computed from status.
    - Sorted by date: latest first.
    """
    today = _today_str()
    # Latest reading per station.
    from collections import defaultdict
    by_station = defaultdict(list)
    for r in _store["readings"]:
        if (r.get("reading_date") or "") <= today:
            key = r.get("station_name") or r.get("station_code", "")
            if key:
                by_station[key].append(r)

    latest_records: list[dict] = []
    for _, rows in by_station.items():
        rows = sorted(rows, key=lambda x: x.get("reading_date", ""))
        if rows:
            latest_records.append(rows[-1])

    def _message(status: str) -> str:
        if status == "slightly_polluted":
            return "Monitor closely"
        if status == "polluted":
            return "Immediate attention required"
        return ""

    alerts: list[dict] = []
    for rec in latest_records:
        status = _status_from_reading(rec)
        if status not in ("slightly_polluted", "polluted"):
            continue
        date_str = rec.get("reading_date")
        alerts.append({
            "station_code": rec.get("station_code"),
            "station_name": rec.get("station_name") or rec.get("station_code"),
            "date": date_str,
            "wqi": rec.get("wqi"),
            "river_status": status,
            "message": _message(status),
            "alert_type": "historical",
        })

    alerts.sort(key=lambda a: a.get("date") or "", reverse=True)
    return alerts[:limit]


def get_forecast_alerts(limit: int = 100) -> list[dict]:
    """
    Forecast alerts (future prediction points):
    - Read from latest forecast prediction_logs
    - Use only dates > today (so forecast starts strictly from tomorrow)
    - Keep slightly_polluted or polluted
    - No severity concept; message computed from status
    - Sorted by earliest forecast date first
    """
    today = _today_str()
    logs = [l for l in _store["prediction_logs"] if l.get("prediction_type") == "forecast"]
    if not logs:
        return []
    latest = sorted(logs, key=lambda x: x.get("created_at", ""))[-1]
    forecast_points = latest.get("result_json", {}).get("forecast", [])

    def _message(status: str) -> str:
        if status == "slightly_polluted":
            return "Monitor closely"
        if status == "polluted":
            return "Immediate attention required"
        return ""

    alerts: list[dict] = []
    for p in forecast_points:
        date_str = p.get("date") or ""
        if not date_str or date_str <= today:
            continue
        status = p.get("river_status")
        if status not in ("slightly_polluted", "polluted"):
            continue
        alerts.append({
            "station_code": p.get("station_code"),
            "station_name": p.get("station_name") or p.get("station_code"),
            "date": date_str,
            "wqi": p.get("wqi"),
            "river_status": status,
            "message": _message(status),
            "alert_type": "forecast",
        })

    alerts.sort(key=lambda a: a.get("date") or "")
    return alerts[:limit]


def get_latest_dataset() -> Optional[dict]:
    """Return the most recently added dataset (by id)."""
    if not _store["datasets"]:
        return None
    return max(_store["datasets"], key=lambda d: d["id"])


def get_latest_anomalies(station_code: Optional[str] = None, limit: int = 500) -> list[dict]:
    """
    Return latest anomaly run as list of { date, station_code, station_name, wqi, reason }.
    Filter by station if station_code (or station_name) provided.
    """
    logs = [l for l in _store["prediction_logs"] if l.get("prediction_type") == "anomaly"]
    if not logs:
        return []
    latest = max(logs, key=lambda x: x.get("created_at", ""))
    anomalies = latest.get("result_json", {}).get("anomalies", [])
    if station_code:
        anomalies = [a for a in anomalies if (a.get("station_code") or a.get("station_name")) == station_code]
    out = []
    for a in anomalies[:limit]:
        out.append({
            "date": a.get("date", ""),
            "station_code": a.get("station_code", "—"),
            "station_name": a.get("station_name") or a.get("station_code", "—"),
            "wqi": a.get("wqi"),
            "reason": a.get("reason", "Abnormal spike"),
        })
    return out


def get_stations() -> list[dict]:
    """Stations: latest WQI per station using only readings with reading_date <= today."""
    from collections import defaultdict
    today = _today_str()
    by_station = defaultdict(list)
    for r in _store["readings"]:
        if (r.get("reading_date") or "") > today:
            continue
        key = r.get("station_name") or r.get("station_code", "")
        if key:
            by_station[key].append(r)
    out = []
    for name, rows in by_station.items():
        rows = sorted(rows, key=lambda x: x.get("reading_date", ""))
        latest = rows[-1] if rows else {}
        wqi = latest.get("wqi", 0)
        status = latest.get("river_status")
        if status is None:
            status = "clean" if wqi >= 81 else ("slightly_polluted" if wqi >= 60 else "polluted")
        out.append({
            "station_code": name,
            "station_name": name,
            "latest_wqi": wqi,
            "river_status": status,
            "last_reading_date": latest.get("reading_date"),
        })
    # Merge admin-managed coordinates only (by station_code/name)
    admin_codes = {s.get("station_code") or s.get("station_name"): s for s in _store["stations"]}
    for rec in out:
        key = rec.get("station_code") or rec.get("station_name")
        if key and key in admin_codes:
            adm = admin_codes[key]
            if adm.get("latitude") is not None:
                rec["latitude"] = adm["latitude"]
            if adm.get("longitude") is not None:
                rec["longitude"] = adm["longitude"]
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
