"""
Water quality controller — HTTP endpoints for water quality data.
Serves dashboard: summary, time-series, stations from repository.
"""
from pathlib import Path

from fastapi import APIRouter, Query
from backend.db.repository import get_summary, get_time_series, get_stations, get_latest_forecast

router = APIRouter()

@router.get("")
@router.get("/")
def get_water_quality():
    """
    Return all dataset readings currently loaded in memory.

    Fields:
    - station_name
    - date
    - wqi
    - status (clean / slightly_polluted / polluted)
    """
    from backend.db.repository import _store, status_from_wqi, save_readings

    def _load_sample_and_replace() -> None:
        """
        Directly load `datasets/sample_water_quality.csv` and replace in-memory readings.
        This avoids needing a backend restart when the app is running a stale loader.
        """
        import pandas as pd
        from backend.db.repository import _today_str  # keep side-effects consistent

        # Map station codes -> exact display names requested.
        code_to_name = {
            "S01": "Sungai Klang",
            "S02": "Sungai Gombak",
            "S03": "Sungai Pinang",
            "S04": "Sungai Kulim",
            "S05": "Sungai Perak",
        }

        # WQI proxy formula (same as loader fallback).
        def _compute_wqi(do, bod, cod, an, tss, ph) -> float:
            try:
                wqi = 100.0 - (bod * 3 + cod / 12 + tss / 4 + an * 8) + (do - 5) * 2 + (ph - 6) * 5
                return max(0.0, min(100.0, round(float(wqi), 1)))
            except Exception:
                return 50.0

        root = Path(__file__).resolve().parents[2]
        sample_path = root / "datasets" / "sample_water_quality.csv"
        if not sample_path.exists():
            raise FileNotFoundError(f"Sample dataset missing: {sample_path}")

        df = pd.read_csv(sample_path)
        if df.empty:
            raise ValueError("Sample dataset is empty")

        readings = []
        for _, row in df.iterrows():
            date_val = str(row.get("date", "") or "")[:10]
            code = str(row.get("station_code", "") or "").strip()
            station_name = code_to_name.get(code, code or "Unknown")
            do = float(row.get("DO", 0) or 0)
            bod = float(row.get("BOD", 0) or 0)
            cod = float(row.get("COD", 0) or 0)
            an = float(row.get("AN", 0) or 0)
            tss = float(row.get("TSS", 0) or 0)
            ph = float(row.get("pH", 0) or 0)
            wqi = _compute_wqi(do, bod, cod, an, tss, ph)
            status = status_from_wqi(wqi)

            readings.append(
                {
                    "station_code": code or station_name,
                    "station_name": station_name,
                    "date": date_val,
                    "wqi": wqi,
                    "river_status": status,
                }
            )

        # Replace entire in-memory store readings.
        save_readings(1, readings)
        print(f"Water quality endpoint: sample reloaded; readings={len(readings)}")

    # Self-heal: detect invalid station names (numeric 0..29 style) and replace with sample CSV.
    try:
        sample = _store.get("readings", [])[:50]
        if sample:
            names = [str(r.get("station_name") or "").strip() for r in sample]
            all_numeric = all((n.isdigit() for n in names if n != ""))
            if all_numeric:
                _load_sample_and_replace()
    except Exception as e:
        print("Water quality endpoint: sample reload failed:", e)

    items = []
    for r in _store.get("readings", []):
        wqi = r.get("wqi")
        try:
            wqf = float(wqi) if wqi is not None else None
        except (TypeError, ValueError):
            wqf = None
        items.append(
            {
                "station_code": r.get("station_code"),
                "station_name": r.get("station_name") or r.get("station_code"),
                "river_name": r.get("river_name"),
                "date": r.get("reading_date"),
                "wqi": wqf,
                "status": status_from_wqi(wqf or 0),
            }
        )
    items.sort(key=lambda x: (x.get("date") or "", x.get("station_name") or ""), reverse=True)
    return {"items": items, "total": len(items)}


@router.get("/summary")
def get_dashboard_summary(river_name: str = Query(None)):
    """Dashboard summary: total stations, avg WQI, clean/polluted counts."""
    return get_summary(river_name=river_name)


@router.get("/time-series")
def get_wqi_time_series(
    station_code: str = Query(None),
    river_name: str = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """WQI time series for charts."""
    return {
        "series": get_time_series(
            station_code=station_code,
            station_name=station_code,
            river_name=river_name,
            limit=limit,
        )
    }


@router.get("/forecast")
def get_forecast(
    river_name: str = Query(None),
    limit: int = Query(30, ge=1, le=100),
):
    """Latest forecast from prediction_logs."""
    return {"forecast": get_latest_forecast(river_name=river_name, limit=limit)}


@router.get("/stations")
def list_stations():
    """Stations with latest WQI and status."""
    return {"stations": get_stations()}
