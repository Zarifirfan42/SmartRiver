"""
ML controller — Train and prediction API.
Admin only: train. Authenticated users can run predictions (optional).
"""
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends

from backend.auth.dependencies import require_admin

router = APIRouter()
ROOT = Path(__file__).resolve().parents[2]


def _ensure_path():
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))


@router.post("/train")
async def train_models(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin),
):
    """
    Upload CSV → preprocess → train RF, LSTM, anomaly models. Save to ml_models/.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")
    _ensure_path()
    content = await file.read()
    path = ROOT / "datasets" / "uploads" / file.filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    try:
        from ml_models.random_forest.train_rf import train_rf
        from ml_models.anomaly_detection.isolation_forest import train_isolation_forest
        from modules.data_preprocessing.preprocess_dataset import load_dataset, data_cleaning, missing_value_handling, add_wqi
        from backend.db.repository import save_prediction_log
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"ML modules unavailable: {e}")
    try:
        df = load_dataset(path.parent, path.name)
        df = data_cleaning(df)
        df = missing_value_handling(df, strategy="median")
        df = add_wqi(df)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Preprocessing failed: {e}")
    out_dir = ROOT / "ml_models"
    metrics = {}
    try:
        m = train_rf(df, out_dir / "random_forest")
        metrics["classification"] = m
        save_prediction_log("classification", m, model_name="random_forest")
    except Exception as e:
        metrics["classification"] = {"error": str(e)}
    try:
        m = train_isolation_forest(df, out_dir / "anomaly_detection")
        metrics["anomaly"] = m
        save_prediction_log("anomaly", m, model_name="isolation_forest")
    except Exception as e:
        metrics["anomaly"] = {"error": str(e)}
    return {"message": "Training complete", "metrics": metrics}


@router.post("/train-uploaded")
def train_models_on_uploaded_csv(
    filename: str = Query(..., description="CSV file name in datasets/uploads (e.g. from last upload)"),
    lstm_epochs: int = Query(12, ge=1, le=200),
    current_user: dict = Depends(require_admin),
):
    """
    Train RF, LSTM (if TensorFlow installed), and Isolation Forest on an uploaded CSV
    using the same pipeline as ml_engine/train.py (data_preprocessing.services.pipeline).
    """
    _ensure_path()
    safe = Path(filename).name
    if safe != filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    csv_path = ROOT / "datasets" / "uploads" / safe
    if not csv_path.is_file():
        raise HTTPException(status_code=404, detail=f"Upload not found: {safe}")
    try:
        from ml_engine.train import run_training_from_paths
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"Training module unavailable: {e}")

    metrics = run_training_from_paths(
        [csv_path],
        lstm_epochs=lstm_epochs,
        lstm_verbose=0,
        write_metrics_json=True,
        print_summary=False,
    )
    lstm_info = metrics.get("lstm_regression") or {}
    return {
        "success": True,
        "message": "Upload successful: data loaded, models trained, and saved under ml_models/.",
        "filename": safe,
        "metrics": metrics,
        "lstm_trained": "error" not in lstm_info,
    }


@router.post("/predict/classification")
async def predict_classification(file: UploadFile = File(...)):
    """Run classification; store result in DB."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")
    _ensure_path()
    import pandas as pd
    from backend.db.repository import save_prediction_log
    df = pd.read_csv(file.file)
    try:
        from ml_models.random_forest.train_rf import train_rf
        import joblib
        model_path = ROOT / "ml_models" / "random_forest" / "model.joblib"
        if not model_path.exists():
            raise HTTPException(status_code=404, detail="Train classification model first (POST /ml/train)")
        data = joblib.load(model_path)
        model, features = data["model"], data.get("feature_columns", ["WQI"])
        X = df[[c for c in features if c in df.columns]].fillna(0) if features else df.fillna(0)
        pred = model.predict(X)
        labels = ["clean", "slightly_polluted", "polluted"]
        results = [{"index": i, "river_status": labels[int(p)]} for i, p in enumerate(pred)]
        save_prediction_log("classification", {"predictions": results}, model_name="random_forest")
        return {"predictions": results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict/forecast")
async def predict_forecast(
    horizon: int = Query(7, ge=1, le=30),
    file: UploadFile = File(None),
):
    """Return WQI forecast; store in DB. Send CSV with WQI column or use latest readings."""
    _ensure_path()
    from backend.db.repository import get_time_series, get_latest_forecast, save_prediction_log
    if file and file.filename:
        import pandas as pd
        df = pd.read_csv(file.file)
        if "WQI" not in df.columns:
            raise HTTPException(status_code=400, detail="CSV must contain WQI column")
        series = df["WQI"].astype(float).values
    else:
        series_data = get_time_series(limit=60)
        if not series_data:
            return {"forecast": [], "message": "No data. Run preprocessing first."}
        series = [r["wqi"] for r in series_data]
    try:
        import joblib
        import numpy as np
        import pandas as pd
        from tensorflow import keras

        path = ROOT / "ml_models" / "lstm"
        model_path = path / "lstm_model.keras" if (path / "lstm_model.keras").exists() else path / "model.keras"
        scaler_path = path / "scaler.joblib"
        if not model_path.exists() or not scaler_path.exists():
            return {"forecast": [], "message": "LSTM not trained. Use POST /ml/train with TensorFlow."}

        data = joblib.load(scaler_path)
        scaler_bundle = data.get("scaler")
        cfg = data.get("config") if isinstance(data.get("config"), dict) else {}
        seq_len = int(cfg.get("seq_len", data.get("seq_len", 30)))
        h_max = int(cfg.get("horizon", data.get("horizon", 7)))
        h = min(horizon, h_max)

        model = keras.models.load_model(model_path)

        if isinstance(scaler_bundle, dict) and "scaler_X" in scaler_bundle and "scaler_y" in scaler_bundle:
            from ml_engine.services.forecasting_service import build_prediction_window, predict as lstm_predict

            if file and file.filename:
                df_fc = pd.read_csv(file.file)
                if "WQI" not in df_fc.columns:
                    if "wqi" in df_fc.columns:
                        df_fc["WQI"] = df_fc["wqi"].astype(float)
                    else:
                        raise HTTPException(status_code=400, detail="CSV must contain WQI column")
                else:
                    df_fc["WQI"] = df_fc["WQI"].astype(float)
                if "date" not in df_fc.columns and "reading_date" not in df_fc.columns:
                    df_fc["date"] = pd.date_range(
                        end=pd.Timestamp.utcnow().normalize(), periods=len(df_fc), freq="D"
                    )
                else:
                    df_fc["date"] = pd.to_datetime(
                        df_fc["date"] if "date" in df_fc.columns else df_fc["reading_date"], errors="coerce"
                    )
            else:
                series_data = get_time_series(limit=max(seq_len + 60, 120))
                if not series_data:
                    return {"forecast": [], "message": "No data. Run preprocessing first."}
                df_fc = pd.DataFrame(series_data)
                if "WQI" not in df_fc.columns and "wqi" in df_fc.columns:
                    df_fc["WQI"] = df_fc["wqi"].astype(float)
                df_fc["date"] = pd.to_datetime(df_fc["date"], errors="coerce")
                df_fc = df_fc.dropna(subset=["date", "WQI"])

            window = build_prediction_window(
                df_fc,
                station_code=None,
                seq_len=seq_len,
                date_col="date",
                add_month_cyclical=bool(cfg.get("add_month_cyclical", False)),
                extra_param_columns=tuple(cfg.get("extra_param_columns") or ()),
            )
            pred = lstm_predict(model, scaler_bundle, window, horizon=h).tolist()
        else:
            scaler = scaler_bundle
            series_s = scaler.transform(np.array(series[-seq_len:]).reshape(-1, 1)).flatten()
            X = series_s.reshape(1, seq_len, 1)
            pred_s = model.predict(X, verbose=0)[0][:h]
            pred = scaler.inverse_transform(pred_s.reshape(-1, 1)).flatten().tolist()
        # Use a distinct type so dashboard get_latest_forecast (dated RF series) is not shadowed by this log.
        save_prediction_log("forecast_lstm", {"forecast": [{"wqi": v} for v in pred]}, model_name="lstm")
        return {"forecast": pred, "horizon": len(pred)}
    except ImportError:
        return {"forecast": [], "message": "TensorFlow required for LSTM forecast."}
    except Exception as e:
        return {"forecast": [], "error": str(e)}


@router.post("/predict/anomaly")
async def predict_anomaly(file: UploadFile = File(None)):
    """
    Run anomaly detection on uploaded CSV or on the latest uploaded dataset.
    Uses latest dataset if no file is provided. Stores anomalies with date, station, WQI, reason.
    """
    _ensure_path()
    import pandas as pd
    from backend.db.repository import get_latest_dataset
    from backend.services.anomaly_service import run_anomaly_detection

    if file and file.filename and file.filename.lower().endswith(".csv"):
        content = await file.read()
        import io
        df = pd.read_csv(io.BytesIO(content))
    else:
        ds = get_latest_dataset()
        if not ds:
            raise HTTPException(status_code=400, detail="No dataset. Upload a CSV or provide a file.")
        input_path = ROOT / ds["file_path"] if not Path(ds["file_path"]).is_absolute() else Path(ds["file_path"])
        if not input_path.exists():
            raise HTTPException(status_code=404, detail="Dataset file not found")
        df = pd.read_csv(input_path)

    model_path = ROOT / "ml_models" / "anomaly_detection" / "model.joblib"
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Train anomaly model first (POST /ml/train)")

    anomalies = run_anomaly_detection(df=df)
    return {"anomalies": anomalies, "count": len(anomalies)}


@router.get("/anomalies")
def get_anomalies(limit: int = Query(500, ge=1, le=2000)):
    """Return latest anomaly run: list of { date, station_code, wqi, reason }."""
    from backend.db.repository import get_latest_anomalies
    return {"anomalies": get_latest_anomalies(limit=limit)}
