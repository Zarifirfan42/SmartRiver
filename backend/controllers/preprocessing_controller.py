"""
Preprocessing controller — Run data pipeline and store results.
Admin only: trigger processing.
"""
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query

from backend.auth.dependencies import require_admin

router = APIRouter()

# Project root
ROOT = Path(__file__).resolve().parents[3]


def _reading_date_iso(d) -> str:
    """Coerce pandas/Excel dates to YYYY-MM-DD without throwing on NaT."""
    if d is None or (isinstance(d, float) and pd.isna(d)):
        return ""
    if hasattr(d, "strftime"):
        try:
            return d.strftime("%Y-%m-%d")
        except (ValueError, OSError):
            return ""
    s = str(d).strip()
    return s[:10] if s else ""


@router.post("/run")
async def run_preprocessing(
    file: Optional[UploadFile] = File(None),
    dataset_id: Optional[int] = Query(None),
    current_user: dict = Depends(require_admin),
):
    """
    Run preprocessing on uploaded CSV or existing dataset.
    Saves WQI readings to storage for dashboard and ML.
    """
    has_file = file is not None and bool(getattr(file, "filename", None))
    if not has_file and dataset_id is None:
        raise HTTPException(status_code=400, detail="Provide file or dataset_id")
    try:
        if has_file:
            content = await file.read()
            path = ROOT / "datasets" / "uploads" / file.filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            input_path = path
        else:
            # Load path from stored dataset by dataset_id
            from backend.db.repository import _store
            ds = next((d for d in _store["datasets"] if d["id"] == dataset_id), None)
            if not ds:
                raise HTTPException(status_code=404, detail="Dataset not found")
            input_path = Path(ds["file_path"])
            if not input_path.is_absolute():
                input_path = ROOT / input_path
        if not Path(input_path).exists():
            raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Run preprocessing pipeline
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from modules.data_preprocessing.preprocess_dataset import (
        load_dataset,
        data_cleaning,
        missing_value_handling,
        add_wqi,
    )
    from backend.db.repository import save_readings

    try:
        datasets_dir = input_path.parent
        filename = input_path.name
        df = load_dataset(datasets_dir, filename=filename)
        df = data_cleaning(df)
        df = missing_value_handling(df, strategy="median")
        df = add_wqi(df)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Preprocessing failed: {e}")

    # Resolve dataset_id: prefer explicit query param (from upload response); else match by filename
    if dataset_id is None and has_file:
        from backend.db.repository import _store
        fn = file.filename
        for drec in reversed(_store.get("datasets", [])):
            fp = (drec.get("file_path") or "").replace("\\", "/")
            if (drec.get("name") or "") == fn or fp.endswith(fn):
                dataset_id = int(drec["id"])
                break
    if dataset_id is None:
        dataset_id = 1

    readings = []
    for _, row in df.head(200000).iterrows():
        d = _reading_date_iso(row.get("date"))
        station_code = str(row.get("station_code", "S01")).strip()
        station_name = row.get("station_name")
        if station_name is not None:
            station_name = str(station_name).strip() or None
        river_csv = row.get("river_name")
        river_name = str(river_csv).strip() if river_csv is not None and str(river_csv).strip() else None
        readings.append({
            "station_code": station_code,
            "station_name": station_name,
            "river_name": river_name,
            "date": d or "",
            "wqi": float(row.get("WQI", 0)),
        })
    if not readings:
        raise HTTPException(status_code=422, detail="Preprocessing produced no rows — check CSV columns (date, station).")
    save_readings(int(dataset_id), readings)

    # Automatically rerun anomaly detection on the same dataset
    try:
        from backend.services.anomaly_service import run_anomaly_detection
        run_anomaly_detection(df=df)
    except Exception:
        pass  # Do not fail preprocessing if anomaly model is missing or fails

    try:
        from backend.services.forecast_service import run_forecast
        run_forecast()
    except Exception:
        pass

    return {
        "message": "Preprocessing complete",
        "rows_processed": len(df),
        "readings_stored": len(readings),
        "dataset_id": dataset_id,
    }
