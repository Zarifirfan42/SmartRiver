"""
Preprocessing controller — Run data pipeline and store results.
Admin only: trigger processing.
"""
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from backend.auth.dependencies import require_admin

router = APIRouter()

# Project root
ROOT = Path(__file__).resolve().parents[3]


@router.post("/run")
async def run_preprocessing(
    file: UploadFile = File(None),
    dataset_id: int = None,
    current_user: dict = Depends(require_admin),
):
    """
    Run preprocessing on uploaded CSV or existing dataset.
    Saves WQI readings to storage for dashboard and ML.
    """
    if not file and dataset_id is None:
        raise HTTPException(status_code=400, detail="Provide file or dataset_id")
    try:
        if file and file.filename:
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

    # Store readings for dashboard (replace all so count matches dataset)
    dataset_id = dataset_id or 1
    readings = []
    for _, row in df.head(2000).iterrows():
        d = row.get("date")
        if hasattr(d, "strftime"):
            d = d.strftime("%Y-%m-%d")
        station_code = str(row.get("station_code", "S01")).strip()
        station_name = row.get("station_name")
        if station_name is not None:
            station_name = str(station_name).strip() or None
        readings.append({
            "station_code": station_code,
            "station_name": station_name,
            "date": d or "",
            "wqi": float(row.get("WQI", 0)),
        })
    save_readings(dataset_id, readings)

    # Automatically rerun anomaly detection on the same dataset
    try:
        from backend.services.anomaly_service import run_anomaly_detection
        run_anomaly_detection(df=df)
    except Exception:
        pass  # Do not fail preprocessing if anomaly model is missing or fails

    return {
        "message": "Preprocessing complete",
        "rows_processed": len(df),
        "readings_stored": len(readings),
        "dataset_id": dataset_id,
    }
