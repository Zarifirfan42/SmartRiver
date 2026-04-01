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

from backend.services.river_mapping import (
    forecast_point_matches_river,
    reading_matches_river,
    river_name_for_station,
)


def _today_str() -> str:
    """Current system date (YYYY-MM-DD) for classifying historical vs forecast."""
    return date.today().isoformat()


def status_from_wqi(wqi: float) -> str:
    """
    WQI → monitoring status (single source of truth for alerts and summaries).
    >= 81: Clean; 60 <= WQI < 81: Slightly Polluted; else: Polluted.
    """
    try:
        w = float(wqi)
    except (TypeError, ValueError):
        w = 0.0
    if w >= 81:
        return "clean"
    if w >= 60:
        return "slightly_polluted"
    return "polluted"


def _canonical_station_key(r: dict) -> str:
    """One group per station: prefer station_code, else station_name."""
    code = (r.get("station_code") or "").strip()
    name = (r.get("station_name") or "").strip()
    return code or name or ""

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


def get_clean_historical_readings() -> list[dict]:
    """
    Single source for in-store monitoring data used by Overview, River Health, summaries, and the
    default dataset table: reading_date <= today, excluding rows tagged data_type=='forecast'.
    ML forecast points stay in prediction_logs only, not here.
    """
    today = _today_str()
    out: list[dict] = []
    for r in _store["readings"]:
        if (r.get("reading_date") or "") > today:
            continue
        if (r.get("data_type") or "historical").strip().lower() == "forecast":
            continue
        out.append(r)
    return out

_SQLITE_PATH = os.environ.get("SMARTRIVER_SQLITE_PATH") or str(
    Path(__file__).resolve().parent / "smartriver.sqlite3"
)


def _sqlite_conn() -> sqlite3.Connection:
    """
    SQLite connection for persistent auth/user data.
    We keep analytics/readings in-memory for now, but users must persist across restarts.
    """
    # Ensure directory exists and use a timeout to reduce "database is locked" errors
    # when frontend and backend perform near-simultaneous auth writes.
    sqlite_path = Path(_SQLITE_PATH)
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(sqlite_path), timeout=15, check_same_thread=False)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        # Keep auth functional even if PRAGMA is not supported in current environment.
        pass
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback_reports (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NULL,
              name TEXT NULL,
              email TEXT NOT NULL,
              message TEXT NOT NULL,
              created_at TEXT NOT NULL,
              is_read INTEGER NOT NULL DEFAULT 0,
              read_at TEXT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS uploaded_datasets (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              file_path TEXT NOT NULL,
              file_size_bytes INTEGER NOT NULL DEFAULT 0,
              row_count INTEGER NOT NULL DEFAULT 0,
              uploaded_by INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              river_name TEXT NULL,
              station_codes_seen TEXT NULL,
              river_validation_warnings TEXT NULL
            )
            """
        )
        cols = {
            r["name"]
            for r in conn.execute("PRAGMA table_info(feedback_reports)").fetchall()
        }
        if "is_read" not in cols:
            conn.execute(
                "ALTER TABLE feedback_reports ADD COLUMN is_read INTEGER NOT NULL DEFAULT 0"
            )
        if "read_at" not in cols:
            conn.execute(
                "ALTER TABLE feedback_reports ADD COLUMN read_at TEXT NULL"
            )


_ensure_sqlite_schema()


def _next_id(table: str) -> int:
    n = _store["_id"][table]
    _store["_id"][table] += 1
    return n


def save_dataset(
    name: str,
    file_path: str,
    file_size: int,
    row_count: int,
    uploaded_by: int = 1,
    river_name: Optional[str] = None,
    station_codes_seen: Optional[list[str]] = None,
    river_validation_warnings: Optional[list[str]] = None,
) -> dict:
    """
    Register an uploaded or processed dataset.

    river_name: human-facing label (e.g. \"Sungai Klang\") derived from station_code mapping at upload.
    station_codes_seen: distinct codes found in CSV (audit / examiner traceability).
    river_validation_warnings: e.g. unknown station codes mapped to Unknown River.
    """
    with _sqlite_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO uploaded_datasets
            (name, file_path, file_size_bytes, row_count, uploaded_by, created_at, river_name, station_codes_seen, river_validation_warnings)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                file_path,
                int(file_size or 0),
                int(row_count or 0),
                int(uploaded_by or 1),
                datetime.utcnow().isoformat(),
                river_name,
                json.dumps(list(station_codes_seen or [])),
                json.dumps(list(river_validation_warnings or [])),
            ),
        )
        dataset_id = int(cur.lastrowid)

    row = {
        "id": dataset_id,
        "name": name,
        "file_path": file_path,
        "file_size_bytes": file_size,
        "row_count": row_count,
        "uploaded_by": uploaded_by,
        "created_at": datetime.utcnow().isoformat(),
    }
    if river_name:
        row["river_name"] = river_name
    if station_codes_seen is not None:
        row["station_codes_seen"] = list(station_codes_seen)
    if river_validation_warnings is not None:
        row["river_validation_warnings"] = list(river_validation_warnings)
    _store["datasets"].append(row)
    return row


def list_uploaded_datasets(limit: int = 2000) -> list[dict]:
    """Persistent dataset metadata list, newest first."""
    lim = max(1, min(int(limit), 5000))
    with _sqlite_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, name, file_path, file_size_bytes, row_count, uploaded_by, created_at,
                   river_name, station_codes_seen, river_validation_warnings
            FROM uploaded_datasets
            ORDER BY id DESC
            LIMIT ?
            """,
            (lim,),
        ).fetchall()
    items: list[dict] = []
    for r in rows:
        try:
            codes = json.loads(r["station_codes_seen"] or "[]")
        except Exception:
            codes = []
        try:
            warns = json.loads(r["river_validation_warnings"] or "[]")
        except Exception:
            warns = []
        items.append({
            "id": r["id"],
            "name": r["name"],
            "file_path": r["file_path"],
            "file_size_bytes": r["file_size_bytes"],
            "row_count": r["row_count"],
            "uploaded_by": r["uploaded_by"],
            "created_at": r["created_at"],
            "river_name": r["river_name"],
            "station_codes_seen": codes,
            "river_validation_warnings": warns,
        })
    _store["datasets"] = list(reversed(items))
    return items


def remove_readings_by_river_label(river_label: str) -> int:
    """
    Drop readings whose river_name matches river_label (case-insensitive).
    Returns number of rows removed.
    """
    label = (river_label or "").strip().lower()
    if not label:
        return 0
    before = len(_store["readings"])
    _store["readings"] = [
        r for r in _store["readings"]
        if (str(r.get("river_name") or "").strip().lower() != label)
    ]
    return before - len(_store["readings"])


def delete_dataset(dataset_id: int) -> dict:
    """
    Delete dataset metadata and its linked in-memory readings.
    Returns counts for admin UI feedback.
    """
    did = int(dataset_id)
    with _sqlite_conn() as conn:
        row = conn.execute(
            """
            SELECT id, name, file_path, file_size_bytes, row_count, uploaded_by, created_at,
                   river_name, station_codes_seen, river_validation_warnings
            FROM uploaded_datasets
            WHERE id = ?
            """,
            (did,),
        ).fetchone()
        if not row:
            raise ValueError("Dataset not found")
        conn.execute("DELETE FROM uploaded_datasets WHERE id = ?", (did,))

    ds = {
        "id": row["id"],
        "name": row["name"],
        "file_path": row["file_path"],
        "file_size_bytes": row["file_size_bytes"],
        "row_count": row["row_count"],
        "uploaded_by": row["uploaded_by"],
        "created_at": row["created_at"],
        "river_name": row["river_name"],
    }
    _store["datasets"] = [d for d in _store["datasets"] if int(d.get("id", -1)) != did]
    before = len(_store["readings"])
    _store["readings"] = [r for r in _store["readings"] if int(r.get("dataset_id") or -1) != did]
    removed_readings = before - len(_store["readings"])
    return {
        "dataset": ds,
        "removed_readings": removed_readings,
    }


def migrate_store_river_names() -> None:
    """
    Backfill river_name on readings and dataset records created before river-centric fields existed.
    Safe to call on every startup (idempotent for rows that already have river_name).
    """
    for r in _store["readings"]:
        if not r.get("river_name"):
            r["river_name"] = river_name_for_station(r.get("station_code"), r.get("station_name"))
    for d in _store["datasets"]:
        if d.get("river_name"):
            continue
        did = d.get("id")
        subs = [r for r in _store["readings"] if r.get("dataset_id") == did]
        if subs:
            rivers = sorted({river_name_for_station(x.get("station_code"), x.get("station_name")) for x in subs})
            d["river_name"] = rivers[0] if len(rivers) == 1 else "Multiple rivers"
        else:
            d["river_name"] = None


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
    river_name is stored for filtering and UI; derived from station_code via RIVER_MAPPING when omitted.
    """
    _store["readings"].clear()
    for r in readings:
        scode = str(r.get("station_code", "S01")).strip()
        sname = (r.get("station_name") or r.get("Station Name") or "").strip() or None
        rec = {
            "id": _next_id("readings"),
            "dataset_id": dataset_id,
            "station_code": scode,
            "station_name": sname,
            "reading_date": r.get("date", r.get("reading_date", "")),
            "wqi": float(r.get("wqi", 0)),
            "created_at": datetime.utcnow().isoformat(),
        }
        rec["river_name"] = (r.get("river_name") or "").strip() or river_name_for_station(scode, sname)
        if r.get("river_status") is not None:
            rec["river_status"] = str(r.get("river_status")).strip() or None
        if r.get("source") is not None:
            rec["source"] = str(r.get("source")).strip()
        rec["data_type"] = str(r.get("data_type") or "historical").strip()
        _store["readings"].append(rec)


def append_readings_with_dedup(dataset_id: int, readings: list[dict]) -> None:
    """
    Append WQI readings to the in-memory store, de-duplicating by (station, date).

    - Existing readings are kept unless a new row shares the same (station_code/station_name, date),
      in which case the new row replaces the old one.
    - Does NOT touch forecast data; dashboard still filters by reading_date <= today.
    """
    combined = list(_store["readings"])
    # Build records for new readings using the same shape as save_readings / append_reading.
    for r in readings:
        scode = str(r.get("station_code", "S01")).strip()
        sname = (r.get("station_name") or r.get("Station Name") or "").strip() or None
        rec = {
            "id": _next_id("readings"),
            "dataset_id": dataset_id,
            "station_code": scode,
            "station_name": sname,
            "reading_date": r.get("date", r.get("reading_date", "")),
            "wqi": float(r.get("wqi", 0)),
            "created_at": datetime.utcnow().isoformat(),
        }
        rec["river_name"] = (r.get("river_name") or "").strip() or river_name_for_station(scode, sname)
        if r.get("river_status") is not None:
            rec["river_status"] = str(r.get("river_status")).strip() or None
        if r.get("source") is not None:
            rec["source"] = str(r.get("source")).strip()
        rec["data_type"] = str(r.get("data_type") or "historical").strip()
        combined.append(rec)

    # De-duplicate by (station key, reading_date), keeping the last occurrence.
    seen = set()
    deduped_rev = []
    for rec in reversed(combined):
        key = _canonical_station_key(rec)
        d = rec.get("reading_date", "")
        k = (key, d)
        if k in seen:
            continue
        seen.add(k)
        deduped_rev.append(rec)

    _store["readings"] = list(reversed(deduped_rev))


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
    sc = str(station_code).strip()
    sn = (station_name or station_code).strip() or None
    rec = {
        "id": _next_id("readings"),
        "dataset_id": dataset_id,
        "station_code": sc,
        "station_name": sn,
        "reading_date": str(reading_date)[:10],
        "wqi": float(wqi),
        "river_status": str(river_status).strip() if river_status else None,
        "created_at": datetime.utcnow().isoformat(),
        "river_name": river_name_for_station(sc, sn),
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
    if not key:
        return None
    candidates = [
        r for r in get_clean_historical_readings()
        if (r.get("station_name") or r.get("station_code") or "").strip() == key
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


def get_summary(river_name: Optional[str] = None) -> dict:
    """
    Dashboard summary using LATEST record per station only (reading_date <= today).
    For each station: find latest date <= today, use that row as current monitoring record.
    Optional river_name narrows metrics to that river (entity-centric dashboard).
    """
    from collections import defaultdict
    today = _today_str()
    readings = list(get_clean_historical_readings())
    if river_name and str(river_name).strip():
        readings = [r for r in readings if reading_matches_river(r, str(river_name).strip())]
    if not readings:
        return {
            "totalStations": 0,
            "avgWqi": 0,
            "cleanCount": 0,
            "slightlyPollutedCount": 0,
            "pollutedCount": 0,
            "recentAnomaliesCount": len([a for a in _store["alerts"] if not a.get("is_read")]),
            "predictedAvgWqi2025_2028": get_predicted_avg_wqi_2025_2028(river_name=river_name),
            "today": today,
            "river_name": (river_name or "").strip() or None,
        }
    by_station = defaultdict(list)
    for r in readings:
        key = _canonical_station_key(r)
        if key:
            by_station[key].append(r)
    latest_records = []
    for _name, rows in by_station.items():
        rows = sorted(rows, key=lambda x: (x.get("reading_date") or "", x.get("id", 0)))
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
            "predictedAvgWqi2025_2028": get_predicted_avg_wqi_2025_2028(river_name=river_name),
            "today": today,
            "river_name": (river_name or "").strip() or None,
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
        "predictedAvgWqi2025_2028": get_predicted_avg_wqi_2025_2028(river_name=river_name),
        "today": today,
        "river_name": (river_name or "").strip() or None,
    }


def _status_from_reading(r: dict) -> str:
    """River status from WQI only (dataset text may disagree with numeric WQI)."""
    try:
        w = float(r.get("wqi", 0) or 0)
    except (TypeError, ValueError):
        w = 0.0
    return status_from_wqi(w)


def get_predicted_avg_wqi_2025_2028(river_name: Optional[str] = None) -> float:
    """Average of predicted WQI for 2025-2028 (from latest forecast run). Optional river_name scopes averages."""
    forecast = get_latest_forecast(limit=10000, river_name=river_name)
    if not forecast:
        return 0.0
    wqis = [float(f.get("wqi", 0)) for f in forecast if f.get("wqi") is not None]
    return sum(wqis) / len(wqis) if wqis else 0.0


def get_time_series(
    station_code: Optional[str] = None,
    station_name: Optional[str] = None,
    river_name: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = 100,
) -> list[dict]:
    """WQI time series for charts: only readings with reading_date <= today (historical + simulated_live)."""
    readings = list(get_clean_historical_readings())
    if river_name and str(river_name).strip():
        readings = [r for r in readings if reading_matches_river(r, str(river_name).strip())]
    if station_code or station_name:
        readings = [
            r for r in readings
            if (station_code and r.get("station_code") == station_code)
            or (station_name and (r.get("station_name") == station_name or r.get("station_code") == station_name))
        ]
    if year is not None:
        readings = [r for r in readings if r.get("reading_date", "")[:4] == str(year)]
    readings = sorted(readings, key=lambda x: (x.get("reading_date", ""), x.get("station_code", "")))
    # Dedupe by date for single-station view (keep last per date).
    # River-only filter counts as single-station when the river maps to one monitoring station in-store.
    single_station_focus = bool(station_code or station_name)
    if not single_station_focus and river_name and str(river_name).strip():
        kset = {_canonical_station_key(r) for r in readings if _canonical_station_key(r)}
        single_station_focus = len(kset) <= 1
    if single_station_focus:
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
            "river_name": r.get("river_name") or river_name_for_station(r.get("station_code"), r.get("station_name")),
        }
        if r.get("river_status") is not None:
            rec["river_status"] = r["river_status"]
        out.append(rec)
    return out


def get_wqi_data(
    station_code: Optional[str] = None,
    station_name: Optional[str] = None,
    river_name: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = 500,
) -> list[dict]:
    """WQI records (reading_date <= today): Date, Station Name, WQI, River Status. Filter by station and/or year."""
    readings = list(get_clean_historical_readings())
    if river_name and str(river_name).strip():
        readings = [r for r in readings if reading_matches_river(r, str(river_name).strip())]
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
        status = status_from_wqi(float(r.get("wqi", 0) or 0))
        out.append({
            "date": r["reading_date"],
            "station": r.get("station_name") or r.get("station_code"),
            "station_code": r.get("station_code"),
            "station_name": r.get("station_name") or r.get("station_code"),
            "river_name": r.get("river_name") or river_name_for_station(r.get("station_code"), r.get("station_name")),
            "wqi": r["wqi"],
            "river_status": status,
        })
    return out


def _apply_readings_filters(
    readings: list,
    station_name: Optional[str] = None,
    river_name: Optional[str] = None,
    year: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """Apply filters to readings list (in place). Returns filtered list."""
    if river_name and str(river_name).strip():
        readings = [r for r in readings if reading_matches_river(r, str(river_name).strip())]
    if station_name:
        readings = [r for r in readings if (r.get("station_name") or r.get("station_code")) == station_name]
    if year is not None:
        readings = [r for r in readings if (r.get("reading_date") or "")[:4] == str(year)]
    if status:
        def _status(r):
            return status_from_wqi(float(r.get("wqi", 0) or 0))
        status_norm = status.strip().lower().replace(" ", "_")
        readings = [r for r in readings if _status(r) == status_norm]
    if date_from:
        readings = [r for r in readings if (r.get("reading_date") or "") >= date_from[:10]]
    if date_to:
        readings = [r for r in readings if (r.get("reading_date") or "") <= date_to[:10]]
    return readings


def get_readings_count(
    station_name: Optional[str] = None,
    river_name: Optional[str] = None,
    year: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    data_type: Optional[str] = None,
) -> int:
    """Total count matching filters. data_type: 'historical' (default) | 'forecast'. Historical = in-store readings to today; forecast = prediction_logs."""
    if (data_type or "").strip().lower() == "forecast":
        forecast = get_latest_forecast(
            station_code=station_name,
            river_name=river_name,
            limit=100000,
        )
        if year is not None:
            forecast = [f for f in forecast if (f.get("date") or "")[:4] == str(year)]
        if date_from:
            forecast = [f for f in forecast if (f.get("date") or "") >= date_from[:10]]
        if date_to:
            forecast = [f for f in forecast if (f.get("date") or "") <= date_to[:10]]
        return len(forecast)
    readings = list(get_clean_historical_readings())
    readings = _apply_readings_filters(
        readings,
        station_name=station_name,
        river_name=river_name,
        year=year,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    return len(readings)


def get_readings_table(
    station_name: Optional[str] = None,
    river_name: Optional[str] = None,
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
        forecast = get_latest_forecast(
            station_code=station_name,
            river_name=river_name,
            limit=limit + offset,
            year_from=int(year) if year is not None else None,
            year_to=int(year) if year is not None else None,
        )
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
            st = status_from_wqi(float(r.get("wqi", 0) or 0))
            sc = r.get("station_code")
            sn = r.get("station_name") or r.get("station_code")
            out.append({
                "station_code": sc,
                "station_name": sn,
                "river_name": r.get("river_name") or river_name_for_station(sc, sn),
                "date": r.get("date"),
                "wqi": r.get("wqi"),
                "river_status": st,
                "data_type": "forecast",
            })
        return out
    readings = list(get_clean_historical_readings())
    readings = _apply_readings_filters(
        readings,
        station_name=station_name,
        river_name=river_name,
        year=year,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    key = "wqi" if sort_by == "wqi" else "reading_date"
    reverse = sort_order.lower() == "desc"
    readings = sorted(readings, key=lambda x: (x.get(key) if key == "wqi" else x.get(key) or ""), reverse=reverse)
    readings = readings[offset : offset + limit]
    out = []
    for r in readings:
        st = status_from_wqi(float(r.get("wqi", 0) or 0))
        out.append({
            "station_code": r.get("station_code"),
            "station_name": r.get("station_name") or r.get("station_code"),
            "river_name": r.get("river_name") or river_name_for_station(r.get("station_code"), r.get("station_name")),
            "date": r["reading_date"],
            "wqi": r["wqi"],
            "river_status": st,
            "data_type": r.get("data_type") or "historical",
        })
    return out


def get_available_years() -> list[int]:
    """Return distinct years from historical readings only (date <= today), aligned with Overview."""
    years = set()
    for r in get_clean_historical_readings():
        d = r.get("reading_date") or ""
        if len(d) >= 4:
            try:
                years.add(int(d[:4]))
            except ValueError:
                pass
    return sorted(years)


def get_unique_river_names() -> list[str]:
    """Distinct river_name from historical readings only (same slice as Overview / River Health)."""
    seen: set[str] = set()
    for r in get_clean_historical_readings():
        rn = (r.get("river_name") or "").strip() or river_name_for_station(r.get("station_code"), r.get("station_name"))
        if rn:
            seen.add(rn)
    return sorted(seen)


def get_latest_forecast(
    station_code: Optional[str] = None,
    river_name: Optional[str] = None,
    limit: int = 10000,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
) -> list[dict]:
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
    if river_name and str(river_name).strip():
        rn = str(river_name).strip()
        forecast = [f for f in forecast if forecast_point_matches_river(f, rn)]
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


def get_historical_alerts(limit: int = 100, river_name: Optional[str] = None) -> list[dict]:
    """
    Historical alerts (latest record per station):
    - Use readings with reading_date <= today
    - If latest status is slightly_polluted or polluted -> alert
    - No severity concept; message is computed from status.
    - Sorted by date: latest first.
    """
    # Latest reading per station (same historical slice as Overview).
    from collections import defaultdict
    by_station = defaultdict(list)
    for r in get_clean_historical_readings():
        if river_name and str(river_name).strip() and not reading_matches_river(r, str(river_name).strip()):
            continue
        key = _canonical_station_key(r)
        if key:
            by_station[key].append(r)

    latest_records: list[dict] = []
    for _, rows in by_station.items():
        rows = sorted(rows, key=lambda x: (x.get("reading_date") or "", x.get("id", 0)))
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
        rn = rec.get("river_name") or river_name_for_station(rec.get("station_code"), rec.get("station_name"))
        alerts.append({
            "station_code": rec.get("station_code"),
            "station_name": rec.get("station_name") or rec.get("station_code"),
            "river_name": rn,
            "date": date_str,
            "wqi": rec.get("wqi"),
            "river_status": status,
            "message": _message(status),
            "alert_type": "historical",
        })

    alerts.sort(key=lambda a: (a.get("date") or "", a.get("station_name") or a.get("station_code") or ""), reverse=True)
    return alerts[:limit]


def get_forecast_alerts(limit: int = 100, river_name: Optional[str] = None) -> list[dict]:
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
        try:
            wq = float(p.get("wqi", 0) or 0)
        except (TypeError, ValueError):
            wq = 0.0
        status = status_from_wqi(wq)
        if status not in ("slightly_polluted", "polluted"):
            continue
        if river_name and str(river_name).strip() and not forecast_point_matches_river(p, str(river_name).strip()):
            continue
        sc, sn = p.get("station_code"), p.get("station_name") or p.get("station_code")
        alerts.append({
            "station_code": sc,
            "station_name": sn,
            "river_name": p.get("river_name") or river_name_for_station(sc, sn),
            "date": date_str,
            "wqi": wq,
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


def get_latest_anomalies(
    station_code: Optional[str] = None,
    river_name: Optional[str] = None,
    limit: int = 500,
) -> list[dict]:
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
    if river_name and str(river_name).strip():
        rn = str(river_name).strip()
        anomalies = [a for a in anomalies if reading_matches_river(a, rn)]
    out = []
    for a in anomalies[:limit]:
        sc = a.get("station_code", "—")
        sn = a.get("station_name") or a.get("station_code", "—")
        out.append({
            "date": a.get("date", ""),
            "station_code": sc,
            "station_name": sn,
            "river_name": a.get("river_name") or river_name_for_station(sc, sn),
            "wqi": a.get("wqi"),
            "reason": a.get("reason", "Abnormal spike"),
        })
    return out


def get_stations() -> list[dict]:
    """Stations: latest WQI per station using only historical readings (same slice as Overview)."""
    from collections import defaultdict
    by_station = defaultdict(list)
    for r in get_clean_historical_readings():
        key = _canonical_station_key(r)
        if key:
            by_station[key].append(r)
    out = []
    for _key, rows in by_station.items():
        rows = sorted(rows, key=lambda x: (x.get("reading_date") or "", x.get("id", 0)))
        latest = rows[-1] if rows else {}
        code = (latest.get("station_code") or "").strip() or _key
        name = (latest.get("station_name") or "").strip() or code
        rn = latest.get("river_name") or river_name_for_station(code, name)
        wqi = latest.get("wqi", 0)
        try:
            wqf = float(wqi or 0)
        except (TypeError, ValueError):
            wqf = 0.0
        status = status_from_wqi(wqf)
        out.append({
            "station_code": code,
            "station_name": name,
            "river_name": rn,
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


def create_feedback_report(
    email: str,
    message: str,
    user_id: Optional[int] = None,
    name: Optional[str] = None,
) -> dict:
    """Persist user feedback / issue report (SQLite)."""
    email_norm = (email or "").strip().lower()
    if not email_norm:
        raise ValueError("Email required")
    msg = (message or "").strip()
    if not msg:
        raise ValueError("Message required")
    name_clean = (name or "").strip() or None
    created_at = datetime.utcnow().isoformat()
    uid = None
    if user_id is not None:
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            uid = None
    with _sqlite_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO feedback_reports (user_id, name, email, message, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (uid, name_clean, email_norm, msg, created_at),
        )
        rid = int(cur.lastrowid)
    return {
        "id": rid,
        "user_id": uid,
        "name": name_clean,
        "email": email_norm,
        "message": msg,
        "created_at": created_at,
        "is_read": False,
        "read_at": None,
    }


def list_feedback_reports(
    limit: int = 500,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    name: Optional[str] = None,
    email: Optional[str] = None,
    is_read: Optional[bool] = None,
) -> list[dict]:
    """All feedback rows (admin), with optional filters."""
    lim = max(1, min(int(limit), 2000))
    where: list[str] = []
    params: list = []
    if date_from:
        where.append("substr(created_at, 1, 10) >= ?")
        params.append(str(date_from).strip()[:10])
    if date_to:
        where.append("substr(created_at, 1, 10) <= ?")
        params.append(str(date_to).strip()[:10])
    if name:
        where.append("lower(coalesce(name, '')) LIKE ?")
        params.append(f"%{str(name).strip().lower()}%")
    if email:
        where.append("lower(email) LIKE ?")
        params.append(f"%{str(email).strip().lower()}%")
    if is_read is not None:
        where.append("is_read = ?")
        params.append(1 if bool(is_read) else 0)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    with _sqlite_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT id, user_id, name, email, message, created_at, is_read, read_at
            FROM feedback_reports
            {where_sql}
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            tuple(params + [lim]),
        ).fetchall()
    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "user_id": r["user_id"],
            "name": r["name"],
            "email": r["email"],
            "message": r["message"],
            "created_at": r["created_at"],
            "is_read": bool(r["is_read"] or 0),
            "read_at": r["read_at"],
        })
    return out


def mark_feedback_report_read(report_id: int, is_read: bool = True) -> Optional[dict]:
    """Set read/unread status for one feedback report and return the updated row."""
    rid = int(report_id)
    read_flag = 1 if is_read else 0
    read_at = datetime.utcnow().isoformat() if is_read else None
    with _sqlite_conn() as conn:
        exists = conn.execute(
            "SELECT id FROM feedback_reports WHERE id = ?",
            (rid,),
        ).fetchone()
        if not exists:
            return None
        conn.execute(
            """
            UPDATE feedback_reports
            SET is_read = ?, read_at = ?
            WHERE id = ?
            """,
            (read_flag, read_at, rid),
        )
        row = conn.execute(
            """
            SELECT id, user_id, name, email, message, created_at, is_read, read_at
            FROM feedback_reports
            WHERE id = ?
            """,
            (rid,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "name": row["name"],
        "email": row["email"],
        "message": row["message"],
        "created_at": row["created_at"],
        "is_read": bool(row["is_read"] or 0),
        "read_at": row["read_at"],
    }


def delete_feedback_report(report_id: int) -> bool:
    """Delete one feedback report by id."""
    rid = int(report_id)
    with _sqlite_conn() as conn:
        cur = conn.execute("DELETE FROM feedback_reports WHERE id = ?", (rid,))
    return cur.rowcount > 0


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
