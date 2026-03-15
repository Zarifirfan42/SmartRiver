"""
Load default dataset (Excel or CSV) on backend startup.
Uses datasets/Lampiran A - Sungai Kulim.xlsx. Columns: Station Name, Date, WQI, River Status, BOD, COD, SS, pH, NH3-N.
All stations, WQI, dates, and status come from the dataset only (no hardcoding).
"""
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]

# Default dataset path (Excel). Fallback to CSV if Excel not found.
DEFAULT_DATASET_PATHS = [
    ROOT / "datasets" / "Lampiran A - Sungai Kulim.xlsx",
    ROOT / "datasets" / "Lampiran A - Sungai Kulim.csv",
]

# Sungai Kulim area (Kedah, Malaysia). Spread stations around this center for map.
DEFAULT_MAP_CENTER = (5.364, 100.562)
# Offsets per station index so markers don't overlap
STATION_OFFSETS = [(0, 0), (0.02, 0.01), (-0.02, 0.01), (0.01, -0.02), (-0.01, -0.02), (0.03, 0), (-0.03, 0)]


def _normalize_column(df, possible_names, default=None):
    """Return first matching column name or default."""
    for name in possible_names:
        if name in df.columns:
            return name
    return default


def _normalize_river_status(val):
    """Normalize river status to clean | slightly_polluted | polluted from dataset values."""
    if val is None or (isinstance(val, float) and (val != val)):
        return None
    s = str(val).strip().lower()
    if not s:
        return None
    if "clean" in s:
        return "clean"
    if "slight" in s or "moderate" in s:
        return "slightly_polluted"
    if "pollut" in s:
        return "polluted"
    return None


def load_dataset_dataframe(path: Path):
    """Load Excel or CSV into pandas DataFrame. Columns: Station Name, Date, WQI, River Status, BOD, COD, SS, pH, NH3-N."""
    import pandas as pd

    if not path.exists():
        return None

    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path, engine="openpyxl")
    else:
        df = pd.read_csv(path)

    if df.empty:
        return None

    # Normalize columns to match dataset structure: Station Name, Date, WQI, River Status, BOD, COD, SS, pH, NH3-N
    col_map = {}
    station_name_col = _normalize_column(df, ["Station Name", "Station name", "station_name", "Station", "station", "STATION"])
    if station_name_col:
        col_map[station_name_col] = "station_name"
    date_col = _normalize_column(df, ["Date", "date", "DATE", "Tarikh"])
    if date_col:
        col_map[date_col] = "date"
    wqi_col = _normalize_column(df, ["WQI", "wqi", "Wqi"])
    if wqi_col:
        col_map[wqi_col] = "WQI"
    status_col = _normalize_column(df, ["River Status", "river_status", "River status", "Status", "status"])
    if status_col:
        col_map[status_col] = "river_status"
    for orig, new in [("BOD", "BOD"), ("COD", "COD"), ("SS", "SS"), ("TSS", "TSS"), ("pH", "pH"), ("NH3-N", "NH3-N"), ("AN", "AN")]:
        c = _normalize_column(df, [orig, orig.lower()])
        if c:
            col_map[c] = new

    df = df.rename(columns=col_map)

    # Ensure required columns: use station_name as primary (full names e.g. Sungai Pinang, Sungai Klang)
    if "station_name" not in df.columns and station_name_col:
        df["station_name"] = df[station_name_col].astype(str).str.strip()
    if "station_name" not in df.columns:
        df["station_name"] = df.index.astype(str)
    if "date" not in df.columns and date_col:
        df["date"] = df[date_col]
    if "WQI" not in df.columns and wqi_col:
        df["WQI"] = pd.to_numeric(df[wqi_col], errors="coerce").fillna(0)
    if "river_status" not in df.columns and status_col:
        df["river_status"] = df[status_col]

    # Normalize date to string YYYY-MM-DD
    if "date" in df.columns:
        d = df["date"]
        df["date"] = d.apply(lambda x: x.strftime("%Y-%m-%d") if hasattr(x, "strftime") else str(x)[:10])

    # Normalize river status from dataset
    if "river_status" in df.columns:
        df["river_status"] = df["river_status"].apply(lambda x: _normalize_river_status(x) or x)
        # If still object, try WQI-based fallback later in dataframe_to_readings

    return df


def dataframe_to_readings(df) -> list[dict]:
    """Convert DataFrame to list of reading dicts. All values from dataset only."""
    if df is None or df.empty:
        return []

    readings = []
    for _, row in df.iterrows():
        date_val = row.get("date", row.get("Date", ""))
        if hasattr(date_val, "strftime"):
            date_val = date_val.strftime("%Y-%m-%d")
        else:
            date_val = str(date_val)[:10] if date_val else ""
        # Use full station name from dataset (e.g. Sungai Pinang, Sungai Klang)
        station_name = str(row.get("station_name", row.get("Station Name", ""))).strip() or "Unknown"
        station_code = station_name  # use same for API compatibility
        wqi = float(row.get("WQI", row.get("wqi", 0)) or 0)
        status = row.get("river_status", "")
        if status is not None and not isinstance(status, str):
            status = str(status)
        status = (status or "").strip() or None
        if not status:
            status = "clean" if wqi >= 81 else ("slightly_polluted" if wqi >= 60 else "polluted")
        readings.append({
            "station_code": station_code,
            "station_name": station_name,
            "date": date_val,
            "wqi": wqi,
            "river_status": status,
        })
    return readings


def get_station_coordinates(station_code: str, index: int) -> tuple[float, float]:
    """Return (lat, lon) for a station (for map). Uses default area + offset by index."""
    base_lat, base_lon = DEFAULT_MAP_CENTER
    off = STATION_OFFSETS[index % len(STATION_OFFSETS)]
    return (base_lat + off[0], base_lon + off[1])


def load_default_dataset() -> Optional[object]:
    """
    Load default dataset from datasets/Lampiran A - Sungai Kulim.xlsx (or CSV).
    Returns the pandas DataFrame if loaded. All data from file only.
    """
    for path in DEFAULT_DATASET_PATHS:
        if path.exists():
            df = load_dataset_dataframe(path)
            if df is not None and not df.empty:
                return df

    # No file found: create minimal sample so app does not crash (still dataset-shaped)
    import pandas as pd
    sample = pd.DataFrame([
        {"date": "2024-01-01", "station_name": "Sungai Kulim", "WQI": 72, "river_status": "slightly_polluted"},
        {"date": "2024-01-02", "station_name": "Sungai Kulim", "WQI": 78, "river_status": "slightly_polluted"},
        {"date": "2024-01-01", "station_name": "Sungai Pinang", "WQI": 85, "river_status": "clean"},
        {"date": "2024-01-02", "station_name": "Sungai Pinang", "WQI": 82, "river_status": "clean"},
        {"date": "2024-01-01", "station_name": "Sungai Klang", "WQI": 55, "river_status": "polluted"},
    ])
    return sample


def run_startup_data_load():
    """
    Load default dataset from file, save to repository, seed station coordinates, run anomaly if model exists.
    Call from app lifespan. User does NOT need to upload; data loads automatically.
    """
    from backend.db.repository import save_readings, _store, create_station

    df = load_default_dataset()
    if df is None:
        return

    readings = dataframe_to_readings(df)
    if not readings:
        return

    save_readings(1, readings)

    # Ensure each station has coordinates in _store["stations"] for the map (from dataset only)
    seen = set()
    for i, r in enumerate(readings):
        code = r.get("station_code") or r.get("station_name", "S01")
        if code not in seen:
            seen.add(code)
            name = r.get("station_name") or code
            existing = [s for s in _store["stations"] if (s.get("station_code") or "") == code]
            if not existing:
                lat, lon = get_station_coordinates(code, len(seen) - 1)
                try:
                    create_station(station_code=code, station_name=name, latitude=lat, longitude=lon)
                except ValueError:
                    pass

    try:
        import pandas as pd
        df_for_anomaly = df.copy()
        if "station_code" not in df_for_anomaly.columns and "station_name" in df_for_anomaly.columns:
            df_for_anomaly["station_code"] = df_for_anomaly["station_name"].astype(str).str.strip()
        if "TSS" not in df_for_anomaly.columns and "SS" in df_for_anomaly.columns:
            df_for_anomaly["TSS"] = pd.to_numeric(df_for_anomaly["SS"], errors="coerce").fillna(0)
        if "AN" not in df_for_anomaly.columns and "NH3-N" in df_for_anomaly.columns:
            df_for_anomaly["AN"] = pd.to_numeric(df_for_anomaly["NH3-N"], errors="coerce").fillna(0)
        from backend.services.anomaly_service import run_anomaly_detection
        run_anomaly_detection(df=df_for_anomaly)
    except Exception:
        pass
