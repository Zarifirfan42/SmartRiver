"""
Load default dataset (Excel or CSV) on backend startup.
Primary file: datasets/River Monitoring Dataset.xlsx (or .csv). Expected columns include
Station Name, Date, WQI, River Status, BOD, COD, SS, pH, NH3-N where applicable.
Values come from the loaded file (or bundled sample) — not from UI copy.
"""
from pathlib import Path
from typing import Optional
import os

from backend.db.repository import status_from_wqi

ROOT = Path(__file__).resolve().parents[2]

# Default dataset paths.
# IMPORTANT: user request — use `sample_water_quality.csv` by default.
DEFAULT_DATASET_NAME = "River Monitoring Dataset"
DEFAULT_SAMPLE_CSV = ROOT / "datasets" / "sample_water_quality.csv"
DEFAULT_DATASET_PATHS = [
    DEFAULT_SAMPLE_CSV,
]

# Map station codes to display names for CSVs that have no Station Name (e.g. sample_water_quality.csv).
STATION_CODE_TO_NAME = {
    "S01": "Sungai Klang",
    "S02": "Sungai Gombak",
    "S03": "Sungai Pinang",
    "S04": "Sungai Kulim",
    "S05": "Sungai Perak",
}

# Historical data cutoff: only dates up to and including this year are treated as real measurements.
# Dates in the forecast horizon are NOT used as observations; they are generated as forecast predictions only.
#
# Requirement: remove 2025 from forecast (2025 is historical).
HISTORICAL_CUTOFF_YEAR = 2025

# Station coordinates for real river locations (used when station name is known).
STATION_COORDINATES = {
    # Sungai Kulim → Kedah
    "Sungai Kulim": (5.6710, 100.5660),
    # Sungai Klang → Selangor
    "Sungai Klang": (3.1390, 101.6869),
    # Sungai Gombak → Selangor
    "Sungai Gombak": (3.2330, 101.7240),
    # Sungai Perak → Perak
    "Sungai Perak": (4.5921, 101.0901),
    # Sungai Pinang → Penang
    "Sungai Pinang": (5.4141, 100.3288),
}

# Fallback: Sungai Kulim area (Kedah, Malaysia). Spread other stations around this center for map.
DEFAULT_MAP_CENTER = (5.364, 100.562)
# Offsets per station index so markers don't overlap (for stations without explicit coordinates).
STATION_OFFSETS = [(0, 0), (0.02, 0.01), (-0.02, 0.01), (0.01, -0.02), (-0.01, -0.02), (0.03, 0), (-0.03, 0)]


def _normalize_column(df, possible_names, default=None):
    """Return first matching column name or default."""
    for name in possible_names:
        if name in df.columns:
            return name
    return default


def _is_dataframe_quality_ok(df) -> bool:
    """
    Basic quality gate to avoid accepting broken intermediate exports.
    Requires usable station names and dates.
    """
    if df is None or df.empty:
        return False

    if "station_name" not in df.columns:
        return False
    if "date" not in df.columns:
        return False

    station_col = df["station_name"]
    date_col = df["date"]
    # If duplicate column names exist, pandas returns a DataFrame; pick first column.
    if hasattr(station_col, "columns"):
        station_col = station_col.iloc[:, 0]
    if hasattr(date_col, "columns"):
        date_col = date_col.iloc[:, 0]

    station_series = station_col.astype(str).str.strip()
    date_series = date_col.astype(str).str.strip()

    # at least some rows with non-empty date
    if (date_series != "").sum() == 0:
        return False

    # station names should contain letters for real river/station labels
    has_alpha = station_series.str.contains(r"[A-Za-z]", regex=True, na=False)
    if has_alpha.sum() == 0:
        return False

    return True


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


def _compute_wqi_from_params(row) -> float:
    """Compute WQI from DO, BOD, COD, AN, TSS, pH when WQI column is missing (e.g. sample_water_quality.csv)."""
    try:
        do = float(row.get("DO", 7) or 7)
        bod = float(row.get("BOD", 2) or 2)
        cod = float(row.get("COD", 10) or 10)
        an = float(row.get("AN", 0.5) or row.get("NH3-N", 0.5) or 0.5)
        tss = float(row.get("TSS", 0) or row.get("SS", 0) or 0)
        ph = float(row.get("pH", 7) or 7)
        # Simplified proxy: better DO/pH increase score; higher BOD/COD/TSS/AN decrease it. Clamp 0-100.
        wqi = 100.0 - (bod * 3 + cod / 12 + tss / 4 + an * 8) + (do - 5) * 2 + (ph - 6) * 5
        return max(0.0, min(100.0, round(wqi, 1)))
    except (TypeError, ValueError):
        return 50.0


def load_dataset_dataframe(path: Path):
    """Load Excel or CSV into pandas DataFrame. Columns: Station Name, Date, WQI, River Status, BOD, COD, SS, pH, NH3-N."""
    import pandas as pd

    if not path.exists():
        return None

    if path.suffix.lower() in (".xlsx", ".xls"):
        # Let pandas select the engine (openpyxl is typical for .xlsx).
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    if df.empty:
        return None

    # Normalize columns to match dataset structure: Station Name, Date, WQI, River Status, BOD, COD, SS, pH, NH3-N
    col_map = {}
    station_name_col = _normalize_column(
        df,
        [
            # Prefer DOE labels first
            "SUNGAI",
            "Sungai",
            "LOCATION",
            "location",
            "Station Name",
            "Station name",
            "station_name",
            "Station",
            "station",
            "STATION",
        ],
    )
    station_code_col = _normalize_column(df, ["station_code", "Station Code", "station code", "ID STN (2016)", "ID STN BARU", "ID_STN"])
    if station_name_col:
        col_map[station_name_col] = "station_name"
    if station_code_col:
        col_map[station_code_col] = "station_code"
    date_col = _normalize_column(df, ["SMP-DAT", "SMP_DAT", "SMP-DAT\n", "Date", "date", "DATE", "Tarikh"])
    if date_col:
        col_map[date_col] = "date"
    wqi_col = _normalize_column(df, ["WQI", "wqi", "Wqi"])
    if wqi_col:
        col_map[wqi_col] = "WQI"
    status_col = _normalize_column(df, ["River Status", "river_status", "River status", "Status", "status", "RIVER\nSTATUS", "CLASS"])
    if status_col:
        col_map[status_col] = "river_status"
    for orig, new in [("BOD", "BOD"), ("COD", "COD"), ("SS", "SS"), ("TSS", "TSS"), ("pH", "pH"), ("NH3-N", "NH3-N"), ("AN", "AN")]:
        c = _normalize_column(df, [orig, orig.lower()])
        if c:
            col_map[c] = new

    df = df.rename(columns=col_map)
    # Keep first occurrence when renaming creates duplicate column names
    # (e.g. existing station_name plus SUNGAI mapped to station_name).
    if df.columns.duplicated().any():
        df = df.loc[:, ~df.columns.duplicated()].copy()

    # Ensure required columns: use station_name as primary (full names e.g. Sungai Pinang, Sungai Klang)
    if "station_name" not in df.columns and station_name_col:
        df["station_name"] = df[station_name_col].astype(str).str.strip()
    if "station_name" not in df.columns and "station_code" in df.columns:
        # Map station codes to names (e.g. sample_water_quality.csv: S01 -> Sungai Klang, S03 -> Sungai Pinang)
        df["station_name"] = df["station_code"].astype(str).str.strip().map(
            lambda c: STATION_CODE_TO_NAME.get(c, c)
        )
    if "station_name" not in df.columns:
        df["station_name"] = df.index.astype(str)
    if "date" not in df.columns and date_col:
        df["date"] = df[date_col]
    if "WQI" not in df.columns and wqi_col:
        df["WQI"] = pd.to_numeric(df[wqi_col], errors="coerce").fillna(0)
    if "WQI" not in df.columns:
        # Compute WQI from DO, BOD, COD, AN, TSS, pH (e.g. sample_water_quality.csv)
        df["WQI"] = df.apply(_compute_wqi_from_params, axis=1)
    if "river_status" not in df.columns and status_col:
        df["river_status"] = df[status_col]
    if "river_status" not in df.columns and "WQI" in df.columns:
        df["river_status"] = df["WQI"].apply(lambda w: status_from_wqi(float(w or 0)))

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
        # Always normalize to ISO date string so backend comparisons work.
        if date_val:
            if hasattr(date_val, "strftime"):
                date_val = date_val.strftime("%Y-%m-%d")
            else:
                try:
                    import pandas as pd
                    parsed = pd.to_datetime(date_val, errors="coerce")
                    date_val = parsed.strftime("%Y-%m-%d") if parsed is not None and parsed == parsed else str(date_val)[:10]
                except Exception:
                    date_val = str(date_val)[:10]
        else:
            date_val = ""
        # Use full station name from dataset (e.g. Sungai Pinang, Sungai Klang)
        station_name = str(row.get("station_name", row.get("Station Name", ""))).strip() or "Unknown"
        station_code = station_name  # use same for API compatibility
        wqi = float(row.get("WQI", row.get("wqi", 0)) or 0)
        status = status_from_wqi(wqi)
        readings.append({
            "station_code": station_code,
            "station_name": station_name,
            "date": date_val,
            "wqi": wqi,
            "river_status": status,
        })
    return readings


def get_station_coordinates(station_code: str, index: int) -> tuple[float, float]:
    """Return (lat, lon) for a station (for map).

    If the station matches a key in STATION_COORDINATES,
    use its real coordinates. Otherwise use the default area + offset by index
    so markers don't overlap.
    """
    name = station_code or ""
    # Station codes in readings use full station names (dataframe_to_readings sets station_code = station_name).
    if name in STATION_COORDINATES:
        return STATION_COORDINATES[name]

    base_lat, base_lon = DEFAULT_MAP_CENTER
    off = STATION_OFFSETS[index % len(STATION_OFFSETS)]
    return (base_lat + off[0], base_lon + off[1])


def load_default_dataset() -> Optional[object]:
    """
    Load default dataset from datasets/River Monitoring Dataset.xlsx (or .csv), else sample CSV.
    Returns the pandas DataFrame if loaded. All data from file only.
    """
    datasets_dir = ROOT / "datasets"

    # Candidate order: always start with sample_water_quality.csv (if present).
    candidates: list[Path] = []
    for p in DEFAULT_DATASET_PATHS:
        if p.exists():
            candidates.append(p)

    if not candidates:
        # If sample is missing, fall back to any other dataset file.
        print("Dataset loader: sample_water_quality.csv missing; falling back to other datasets.")
        named_csv = ROOT / "datasets" / f"{DEFAULT_DATASET_NAME}.csv"
        named_xlsx = ROOT / "datasets" / f"{DEFAULT_DATASET_NAME}.xlsx"
        for p in [named_csv, named_xlsx]:
            if p.exists():
                candidates.append(p)

        # Final fallback: newest CSV in datasets/
        if not candidates and datasets_dir.exists():
            csvs = sorted([p for p in datasets_dir.glob("*.csv") if p.is_file()], key=lambda x: x.stat().st_mtime, reverse=True)
            if csvs:
                candidates.append(csvs[0])

    if not candidates:
        print("Dataset loader: no dataset file found in datasets/.")
        return None

    last_err: Optional[str] = None
    for path in candidates:
        try:
            df = load_dataset_dataframe(path)
            if df is not None and not df.empty:
                if not _is_dataframe_quality_ok(df):
                    print(f"Dataset loader: rejected low-quality parse for {path.name}; trying next candidate.")
                    continue
                print(f"Dataset loader: selected {path.name} with shape={df.shape}")
                # If we successfully loaded Excel, also export a CSV copy so future runs
                # can load without requiring an Excel engine.
                try:
                    if path.suffix.lower() in (".xlsx", ".xls"):
                        csv_path = ROOT / "datasets" / f"{DEFAULT_DATASET_NAME}.csv"
                        if not csv_path.exists():
                            df.to_csv(csv_path, index=False)
                            print(f"Exported CSV copy: {csv_path}")
                except Exception as e:
                    print("CSV export skipped:", e)
                return df
        except Exception as e:
            last_err = str(e)
            print(f"Dataset loader: failed reading {path.name}: {e}")
            continue

    print(f"Dataset loader: all candidate datasets failed. Last error: {last_err}")
    return None


def run_startup_data_load():
    """
    Load default dataset from file. Only records with year <= HISTORICAL_CUTOFF_YEAR (2024) are stored as historical.
    Dates 2025-2028 are NOT treated as real measurements; they are generated by the forecast model.
    Seed station coordinates, run anomaly on historical data, then run forecast to generate 2025-2028 predictions.
    """
    from backend.db.repository import save_readings, _store, create_station, save_alert, clear_historical_alerts

    df = load_default_dataset()
    if df is None:
        return

    # Use only historical data (2023-2024). Do not treat 2025-2028 as observed values.
    if "date" in df.columns:
        try:
            years = df["date"].astype(str).str[:4].astype(int)
            df = df[years <= HISTORICAL_CUTOFF_YEAR].copy()
        except (ValueError, TypeError):
            pass
    if df.empty:
        return

    readings = dataframe_to_readings(df)
    if not readings:
        return

    save_readings(1, readings)
    print(f"Dataset loaded readings count: {len(readings)}")

    # Ensure each station has coordinates in _store["stations"] for the map
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

    # Historical alerts: from LATEST record per station only. Trigger when River Status is Slightly Polluted or Polluted.
    # Clear existing historical alerts so we regenerate from current dataset (forecast alerts are kept).
    try:
        from collections import defaultdict
        clear_historical_alerts()
        by_station = defaultdict(list)
        for r in readings:
            key = r.get("station_name") or r.get("station_code")
            if key:
                by_station[key].append(r)
        for name, rows in by_station.items():
            rows = sorted(rows, key=lambda x: x.get("date", ""))
            if not rows:
                continue
            latest = rows[-1]
            date_str = latest.get("date")
            wqi = float(latest.get("wqi", 0))
            status = status_from_wqi(wqi)
            if status not in ("slightly_polluted", "polluted"):
                continue
            status_label = "Slightly Polluted" if status == "slightly_polluted" else "Polluted"
            severity = "warning" if status == "slightly_polluted" else "critical"
            msg = f"{name} water quality is {status_label} (WQI: {wqi:.1f}) on {date_str}."
            save_alert(
                station_code=name,
                station_name=name,
                message=msg,
                severity=severity,
                wqi=wqi,
                date_str=date_str,
                alert_type="historical",
                river_status=status,
            )
    except Exception:
        pass

    # Heavy startup tasks (anomaly/forecast/backfill/live) are optional.
    # They can make app startup slow and block API availability.
    run_heavy = os.environ.get("SMARTRIVER_RUN_HEAVY_STARTUP", "false").strip().lower() == "true"
    if not run_heavy:
        print("Heavy startup tasks skipped (set SMARTRIVER_RUN_HEAVY_STARTUP=true to enable).")
        return

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

    # Generate forecast predictions for 2025-2028 (per station). Do not use dataset 2025-2028 as real data.
    try:
        from backend.services.forecast_service import run_forecast
        run_forecast()
    except Exception:
        pass

    # Backfill missing daily readings per station up to today (simulated_backfill).
    try:
        from backend.services.backfill_service import run_backfill
        run_backfill()
    except Exception as e:
        print("Backfill skipped:", e)

    # Simulated live data: generate today's WQI per station (continues from latest historical/forecast).
    try:
        from backend.services.live_simulation import run_simulated_live_data
        n = run_simulated_live_data()
        if n > 0:
            print(f"Simulated live data: generated {n} readings for today.")
    except Exception as e:
        print("Live simulation skipped:", e)
