"""
ML API: train/predict for classification, forecasting, anomaly detection.
Wire to FastAPI app with: include_router(ml_router, prefix="/api/v1/ml", tags=["ML"])
"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
import pandas as pd

router = APIRouter()

# Lazy init to avoid import errors when TF not installed
_training_result = None
_prediction_api = None


def _get_models_dir() -> Path:
    """Resolve ml_models directory (project root / ml_models)."""
    return Path(__file__).resolve().parents[2] / "ml_models"


def _get_prediction_api():
    global _prediction_api
    if _prediction_api is None:
        try:
            from ml_engine.services.prediction_api import get_prediction_api
            _prediction_api = get_prediction_api(models_dir=_get_models_dir())
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Prediction API not available: {e}")
    return _prediction_api


# --- Training (admin) ---

@router.post("/train")
def train_models(
    file: UploadFile = File(...),
    missing_strategy: str = "median",
    train_lstm: bool = True,
):
    """Run full training pipeline: preprocess CSV then train RF, LSTM, Isolation Forest."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")
    try:
        from data_preprocessing.services.pipeline import run_pipeline
        from ml_engine.services.training_pipeline import run_training_pipeline
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"ML modules unavailable: {e}")

    content = file.file.read()
    try:
        df = pd.read_csv(pd.io.common.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {e}")

    # Save temporarily and run pipeline
    tmp_path = Path("/tmp") / "smartriver_upload.csv"
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_bytes(content)
    output_dir = _get_models_dir()

    try:
        results = run_training_pipeline(
            tmp_path,
            output_dir,
            missing_strategy=missing_strategy,
            train_classification=True,
            train_forecasting=train_lstm,
            train_anomaly_detection=True,
        )
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

    # Reset prediction API so it reloads new models
    global _prediction_api
    _prediction_api = None

    return {
        "message": "Training completed",
        "metrics": {
            "classification": results.get("metrics_classification"),
            "forecasting": results.get("metrics_forecasting"),
            "anomaly": results.get("metrics_anomaly"),
        },
        "paths": results.get("paths", {}),
    }


# --- Prediction ---

@router.post("/predict/classification")
def predict_classification(file: UploadFile = File(...)):
    """Predict river status for each row. Send CSV file."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")
    content = file.file.read()
    df = pd.read_csv(pd.io.common.BytesIO(content))
    api = _get_prediction_api()
    predictions = api.predict_river_status(df)
    return {"predictions": predictions}


@router.post("/predict/forecast")
def predict_forecast(
    horizon: int = 7,
    station_code: Optional[str] = None,
    file: UploadFile = File(...),
):
    """Predict WQI for next horizon days. Send CSV with WQI time series."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")
    df = pd.read_csv(file.file)
    api = _get_prediction_api()
    forecast = api.predict_wqi_forecast(df, horizon=horizon, station_code=station_code)
    if forecast is None:
        raise HTTPException(status_code=422, detail="Insufficient data or model not loaded")
    return {"forecast": forecast, "horizon": horizon}


@router.post("/predict/anomaly")
def predict_anomaly(file: UploadFile = File(...)):
    """Detect anomalies in CSV. Returns list of anomalous rows."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")
    df = pd.read_csv(file.file)
    api = _get_prediction_api()
    anomalies = api.detect_anomalies(df)
    return {"anomalies": anomalies, "count": len(anomalies)}


# --- Metrics (from last training or from disk) ---

@router.get("/metrics")
def get_metrics():
    """Return last training metrics if available (classification accuracy, forecasting RMSE/MAE)."""
    return {
        "message": "Run POST /train to train and get metrics. Metrics are returned in the train response.",
    }
