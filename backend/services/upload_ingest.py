"""
Ingest uploaded monitoring CSVs into in-memory readings (dashboard) with the same
preprocessing as POST /preprocessing/run. Used on upload, on server startup (rehydrate),
and optionally from the preprocessing route.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]


def _ensure_root_on_path() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))


def _reading_date_iso(d) -> str:
    if d is None or (isinstance(d, float) and pd.isna(d)):
        return ""
    if hasattr(d, "strftime"):
        try:
            return d.strftime("%Y-%m-%d")
        except (ValueError, OSError):
            return ""
    s = str(d).strip()
    return s[:10] if s else ""


def _dataframe_to_reading_dicts(df: pd.DataFrame) -> list[dict]:
    readings: list[dict] = []
    for _, row in df.head(200000).iterrows():
        d = _reading_date_iso(row.get("date"))
        station_code = str(row.get("station_code", "S01")).strip()
        station_name = row.get("station_name")
        if station_name is not None:
            station_name = str(station_name).strip() or None
        river_csv = row.get("river_name")
        river_name = str(river_csv).strip() if river_csv is not None and str(river_csv).strip() else None
        try:
            wqi = float(row.get("WQI", 0))
        except (TypeError, ValueError):
            wqi = 0.0
        readings.append(
            {
                "station_code": station_code,
                "station_name": station_name,
                "river_name": river_name,
                "date": d or "",
                "wqi": wqi,
            }
        )
    return readings


def ensure_stations_for_reading_dicts(readings: list[dict]) -> None:
    """Create map entries for stations seen in readings (same idea as dataset_loader startup)."""
    if not readings:
        return
    _ensure_root_on_path()
    from backend.db.repository import _store, create_station
    from backend.services.dataset_loader import get_station_coordinates

    seen: set[str] = set()
    idx = 0
    for r in readings:
        code = str(r.get("station_code") or r.get("station_name") or "S01").strip()
        if not code or code in seen:
            continue
        seen.add(code)
        name = (r.get("station_name") or code).strip() or code
        existing = [s for s in _store["stations"] if (s.get("station_code") or "") == code]
        if not existing:
            lat, lon = get_station_coordinates(code, idx)
            idx += 1
            try:
                create_station(station_code=code, station_name=name, latitude=lat, longitude=lon)
            except ValueError:
                pass


def ingest_upload_csv_path(
    csv_path: Path,
    dataset_id: int,
    *,
    run_anomaly_forecast: bool = True,
) -> dict[str, Any]:
    """
    Preprocess CSV at csv_path and append readings with (station, date) deduplication.
    Optionally run anomaly + forecast (skip when batching startup rehydrate).
    """
    _ensure_root_on_path()
    csv_path = Path(csv_path)
    if not csv_path.is_file():
        return {"ok": False, "error": "file_not_found", "readings_stored": 0, "rows_processed": 0}

    from modules.data_preprocessing.preprocess_dataset import (
        load_dataset,
        data_cleaning,
        missing_value_handling,
        add_wqi,
    )
    from backend.db.repository import append_readings_with_dedup

    datasets_dir = csv_path.parent
    filename = csv_path.name
    try:
        df = load_dataset(datasets_dir, filename=filename)
        df = data_cleaning(df)
        df = missing_value_handling(df, strategy="median")
        df = add_wqi(df)
    except Exception as e:
        logger.exception("upload ingest preprocess failed path=%s", csv_path)
        return {"ok": False, "error": str(e), "readings_stored": 0, "rows_processed": 0}

    readings = _dataframe_to_reading_dicts(df)
    if not readings:
        return {"ok": False, "error": "no_rows", "readings_stored": 0, "rows_processed": 0}

    append_readings_with_dedup(int(dataset_id), readings)
    ensure_stations_for_reading_dicts(readings)

    if run_anomaly_forecast:
        try:
            from backend.services.anomaly_service import run_anomaly_detection

            df_an = df.copy()
            if "station_code" not in df_an.columns and "station_name" in df_an.columns:
                df_an["station_code"] = df_an["station_name"].astype(str).str.strip()
            if "TSS" not in df_an.columns and "SS" in df_an.columns:
                df_an["TSS"] = pd.to_numeric(df_an["SS"], errors="coerce").fillna(0)
            if "AN" not in df_an.columns and "NH3-N" in df_an.columns:
                df_an["AN"] = pd.to_numeric(df_an["NH3-N"], errors="coerce").fillna(0)
            run_anomaly_detection(df=df_an)
        except Exception:
            logger.debug("anomaly after ingest skipped", exc_info=True)

        try:
            from backend.services.forecast_service import run_forecast

            run_forecast()
        except Exception:
            logger.debug("forecast after ingest skipped", exc_info=True)

        try:
            from backend.services.dataset_refresh import refresh_forecast_after_readings_change

            refresh_forecast_after_readings_change()
        except Exception:
            pass

    logger.info(
        "ingest_upload_csv_path dataset_id=%s file=%s readings=%s rows_df=%s",
        dataset_id,
        filename,
        len(readings),
        len(df),
    )
    return {
        "ok": True,
        "readings_stored": len(readings),
        "rows_processed": len(df),
        "dataset_id": int(dataset_id),
    }


def rehydrate_readings_from_registered_uploads() -> dict[str, Any]:
    """
    After default dataset is loaded into readings, merge all CSVs registered in SQLite
    `uploaded_datasets` (newest files on disk). Skips missing paths.
    Runs a single forecast at the end if any row was ingested.
    """
    _ensure_root_on_path()
    from backend.db.repository import list_uploaded_datasets

    items = list_uploaded_datasets(limit=5000)
    numeric = [it for it in items if isinstance(it.get("id"), int)]
    numeric.sort(key=lambda x: int(x["id"]))

    total_readings = 0
    ingested_any = False
    for it in numeric:
        fp = (it.get("file_path") or "").strip().replace("\\", "/")
        if not fp:
            continue
        full = ROOT / fp
        if not full.is_file():
            logger.warning("rehydrate skip missing file id=%s path=%s", it.get("id"), fp)
            continue
        did = int(it["id"])
        res = ingest_upload_csv_path(full, did, run_anomaly_forecast=False)
        if res.get("ok"):
            ingested_any = True
            total_readings += int(res.get("readings_stored") or 0)

    if ingested_any:
        try:
            from backend.services.forecast_service import run_forecast

            run_forecast()
        except Exception:
            logger.debug("forecast after rehydrate batch skipped", exc_info=True)
        try:
            from backend.services.dataset_refresh import refresh_forecast_after_readings_change

            refresh_forecast_after_readings_change()
        except Exception:
            pass

    msg = f"Rehydrated uploads: {len(numeric)} registered, ~{total_readings} rows processed this pass"
    print(msg)
    return {
        "ok": True,
        "registered": len(numeric),
        "readings_rows_touched": total_readings,
        "message": msg,
    }


def schedule_background_train_upload(filename: str) -> None:
    """Best-effort train RF/LSTM/anomaly from one uploads/ CSV (non-blocking caller)."""
    safe = Path(filename).name
    if safe != filename or ".." in filename:
        return
    csv_path = ROOT / "datasets" / "uploads" / safe
    if not csv_path.is_file():
        return
    _ensure_root_on_path()
    try:
        from ml_engine.train import run_training_from_paths

        run_training_from_paths(
            [csv_path],
            lstm_epochs=8,
            lstm_verbose=0,
            write_metrics_json=True,
            print_summary=False,
        )
        logger.info("Background ML training finished for %s", safe)
    except Exception:
        logger.exception("Background ML training failed for %s", safe)
