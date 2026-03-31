"""
Compatibility endpoints (simple aliases).

Required endpoints for integration:
- POST /predict
- POST /forecast
- POST /anomaly
- POST /upload-dataset
- GET  /dashboard-summary

These wrap existing services/controllers but expose a simpler surface.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends

from backend.auth.dependencies import require_admin
from backend.db.repository import get_summary, save_dataset
from backend.services.river_mapping import dataset_upload_metadata_from_csv

router = APIRouter()
ROOT = Path(__file__).resolve().parents[2]


@router.get("/dashboard-summary")
def dashboard_summary_alias(river_name: str = Query(None)):
    """Alias for dashboard summary. Optional river_name filters KPIs to one river."""
    return get_summary(river_name=river_name)


@router.post("/upload-dataset")
async def upload_dataset_alias(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin),
):
    """Alias for dataset upload (admin). Saves to datasets/uploads/ and registers metadata."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")
    content = await file.read()
    path = ROOT / "datasets" / "uploads" / file.filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    try:
        rel = path.relative_to(ROOT)
        file_path = str(rel)
    except ValueError:
        file_path = str(path)

    meta = dataset_upload_metadata_from_csv(content)
    if meta.get("reject"):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "upload_rejected",
                "message": meta.get("reject_detail"),
                "warnings": meta.get("warnings", []),
            },
        )

    row = save_dataset(
        name=file.filename,
        file_path=file_path,
        file_size=len(content),
        row_count=0,
        uploaded_by=current_user["id"],
        river_name=meta.get("river_name"),
        station_codes_seen=meta.get("station_codes_seen") or [],
        river_validation_warnings=meta.get("warnings") or [],
    )
    return {
        "success": True,
        "dataset": row,
        "river_name": row.get("river_name"),
        "warnings": meta.get("warnings", []),
        "message": "Upload saved.",
    }


def _load_csv_upload(file: UploadFile) -> "object":
    import pandas as pd
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")
    try:
        return pd.read_csv(file.file)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to read CSV: {e}")


@router.post("/predict")
async def predict_alias(file: UploadFile = File(...)):
    """Alias for classification prediction. Requires trained Random Forest artifact."""
    import joblib

    df = _load_csv_upload(file)
    model_path = ROOT / "ml_models" / "random_forest" / "model.joblib"
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Random Forest model not found. Train first (ml_engine/train.py).")

    data = joblib.load(model_path)
    model = data["model"]
    features = data.get("feature_columns", []) or []
    X = df[[c for c in features if c in df.columns]].fillna(0) if features else df.select_dtypes("number").fillna(0)
    pred = model.predict(X)
    labels = data.get("classes") or ["clean", "slightly_polluted", "polluted"]
    results = [{"index": i, "river_status": labels[int(p)]} for i, p in enumerate(pred)]
    return {"predictions": results}


@router.post("/forecast")
async def forecast_alias(
    horizon: int = Query(7, ge=1, le=30),
    file: Optional[UploadFile] = File(None),
):
    """Alias for WQI forecasting using LSTM artifact at ml_models/lstm/model.keras."""
    try:
        import numpy as np
        import joblib
        from tensorflow import keras
    except Exception:
        raise HTTPException(status_code=503, detail="TensorFlow + joblib are required for forecasting")

    model_file = ROOT / "ml_models" / "lstm" / "model.keras"
    scaler_file = ROOT / "ml_models" / "lstm" / "scaler.joblib"
    if not model_file.exists() or not scaler_file.exists():
        raise HTTPException(status_code=404, detail="LSTM model not found. Train first (ml_engine/train.py).")

    if file and file.filename:
        df = _load_csv_upload(file)
        if "WQI" not in df.columns:
            raise HTTPException(status_code=400, detail="CSV must contain WQI column for forecast input")
        series = df["WQI"].astype(float).values.tolist()
    else:
        # Fallback: use latest monitoring series from repository
        from backend.db.repository import get_time_series

        series_data = get_time_series(limit=180)
        series = [float(r.get("wqi", 0)) for r in series_data] if series_data else []

    meta = joblib.load(scaler_file)
    scaler = meta.get("scaler")
    cfg = meta.get("config") or {}
    seq_len = int(cfg.get("seq_len", 30))
    if scaler is None:
        raise HTTPException(status_code=500, detail="Invalid scaler metadata")
    if len(series) < seq_len:
        raise HTTPException(status_code=422, detail=f"Need at least {seq_len} WQI points for forecast")

    model = keras.models.load_model(model_file)
    last = np.array(series[-seq_len:], dtype=float).reshape(-1, 1)
    last_scaled = scaler.transform(last).astype("float32").reshape(1, seq_len, 1)
    pred_scaled = model.predict(last_scaled, verbose=0)[0][:horizon]
    pred = scaler.inverse_transform(pred_scaled.reshape(-1, 1)).flatten().tolist()
    return {"forecast": [{"step": i + 1, "wqi": float(v)} for i, v in enumerate(pred)], "horizon": len(pred)}


@router.post("/anomaly")
async def anomaly_alias(file: UploadFile = File(...)):
    """Alias for anomaly detection using Isolation Forest artifact at ml_models/anomaly_detection/model.joblib."""
    df = _load_csv_upload(file)

    model_path = ROOT / "ml_models" / "anomaly_detection" / "model.joblib"
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Anomaly model not found. Train first (ml_engine/train.py).")

    from ml_engine.services.anomaly_service import load_model, get_anomaly_features

    model, feature_cols = load_model(model_path)
    if not feature_cols:
        feature_cols = get_anomaly_features(df)
    if not feature_cols:
        raise HTTPException(status_code=400, detail="No numeric feature columns found for anomaly detection")

    X = df[[c for c in feature_cols if c in df.columns]].fillna(0)
    pred = model.predict(X)
    scores = model.decision_function(X)

    anomalies = []
    for i in range(len(df)):
        if int(pred[i]) == -1:
            anomalies.append({"index": i, "score": float(scores[i])})
    return {"anomalies": anomalies, "count": len(anomalies)}

