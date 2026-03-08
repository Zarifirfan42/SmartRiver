"""
ML controller — Train and prediction API.
Flow: Preprocessed data → ML Engine (RF / LSTM / Isolation Forest) → save to DB → Prediction API.
"""
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Query

router = APIRouter()
ROOT = Path(__file__).resolve().parents[3]


def _ensure_path():
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))


@router.post("/train")
async def train_models(file: UploadFile = File(...)):
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
        path = ROOT / "ml_models" / "lstm"
        if not (path / "lstm_model.keras").exists():
            return {"forecast": [], "message": "LSTM not trained. Use POST /ml/train with TensorFlow."}
        from ml_models.lstm.train_lstm import build_sequences
        data = joblib.load(path / "scaler.joblib")
        scaler, seq_len, h = data["scaler"], data["seq_len"], min(horizon, data["horizon"])
        series_s = scaler.transform(np.array(series[-seq_len:]).reshape(-1, 1)).flatten()
        X = series_s.reshape(1, seq_len, 1)
        from tensorflow import keras
        model = keras.models.load_model(path / "lstm_model.keras")
        pred_s = model.predict(X, verbose=0)[0][:h]
        pred = scaler.inverse_transform(pred_s.reshape(-1, 1)).flatten().tolist()
        save_prediction_log("forecast", {"forecast": [{"wqi": v} for v in pred]}, model_name="lstm")
        return {"forecast": pred, "horizon": len(pred)}
    except ImportError:
        return {"forecast": [], "message": "TensorFlow required for LSTM forecast."}
    except Exception as e:
        return {"forecast": [], "error": str(e)}


@router.post("/predict/anomaly")
async def predict_anomaly(file: UploadFile = File(...)):
    """Run anomaly detection; store anomalies and create alerts in DB."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV file required")
    _ensure_path()
    import pandas as pd
    from backend.db.repository import save_prediction_log, save_alert
    df = pd.read_csv(file.file)
    try:
        import joblib
        path = ROOT / "ml_models" / "anomaly_detection" / "model.joblib"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Train anomaly model first (POST /ml/train)")
        data = joblib.load(path)
        model, features = data["model"], data["feature_columns"]
        X = df[[c for c in features if c in df.columns]].fillna(0)
        pred = model.predict(X)
        scores = model.decision_function(X)
        anomalies = []
        for i in range(len(df)):
            if pred[i] == -1:
                rec = {"index": i, "score": float(scores[i])}
                if "station_code" in df.columns:
                    rec["station_code"] = str(df.iloc[i]["station_code"])
                if "date" in df.columns:
                    rec["date"] = str(df.iloc[i]["date"])
                anomalies.append(rec)
                save_alert(rec.get("station_code", "?"), "Anomaly detected", "warning")
        save_prediction_log("anomaly", {"anomalies": anomalies, "count": len(anomalies)}, model_name="isolation_forest")
        return {"anomalies": anomalies, "count": len(anomalies)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
