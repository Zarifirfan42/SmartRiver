"""
Unified training pipeline: run preprocessing → train RF, LSTM, Isolation Forest → save models and metrics.
"""
from pathlib import Path
from typing import Optional, Literal

import pandas as pd

from data_preprocessing.services.pipeline import run_pipeline
from ml_engine.services.classification_service import train as train_rf, save_model as save_rf, get_feature_columns
from ml_engine.services.forecasting_service import train as train_lstm, save_model as save_lstm
from ml_engine.services.anomaly_service import train as train_anomaly, save_model as save_anomaly


def run_training_pipeline(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    missing_strategy: Literal["mean", "median", "drop"] = "median",
    train_classification: bool = True,
    train_forecasting: bool = True,
    train_anomaly_detection: bool = True,
    lstm_station: Optional[str] = None,
    lstm_seq_len: int = 30,
    lstm_horizon: int = 7,
    lstm_epochs: int = 50,
) -> dict:
    """
    Full pipeline:
    1. Ingest + clean + impute + WQI + feature engineering
    2. Train Random Forest → save + metrics (Accuracy, F1, confusion matrix)
    3. Train LSTM → save + metrics (RMSE, MAE)
    4. Train Isolation Forest → save

    Returns dict with keys: preprocessed_df, metrics_classification, metrics_forecasting, metrics_anomaly, paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Preprocessing
    df = run_pipeline(
        input_path,
        output_path=None,
        missing_strategy=missing_strategy,
        remove_duplicates=True,
        rolling_window=7,
        lag_days=(1, 7, 14),
        normalize=True,
    )

    # Ensure we have river_status for classification
    if "river_status" not in df.columns:
        from data_preprocessing.utils.wqi_calculator import add_wqi_and_status
        df = add_wqi_and_status(df)

    results = {
        "preprocessed_df": df,
        "metrics_classification": None,
        "metrics_forecasting": None,
        "metrics_anomaly": None,
        "paths": {},
    }

    # 2. Random Forest
    if train_classification and "river_status" in df.columns:
        rf_out = train_rf(df, test_size=0.2, n_estimators=150, max_depth=15, min_samples_leaf=5)
        rf_path = output_dir / "random_forest" / "model.joblib"
        save_rf(rf_out["model"], rf_out["feature_columns"], rf_path)
        results["metrics_classification"] = rf_out["metrics"]
        results["paths"]["random_forest"] = str(rf_path)

    # 3. LSTM
    if train_forecasting and "WQI" in df.columns:
        lstm_out = train_lstm(
            df,
            station_code=lstm_station,
            seq_len=lstm_seq_len,
            horizon=lstm_horizon,
            test_ratio=0.2,
            epochs=lstm_epochs,
            verbose=0,
        )
        if "error" not in lstm_out:
            lstm_dir = output_dir / "lstm"
            save_lstm(
                lstm_out["model"],
                lstm_out["scaler"],
                {"seq_len": lstm_seq_len, "horizon": lstm_horizon},
                lstm_dir,
            )
            results["metrics_forecasting"] = lstm_out["metrics"]
            results["paths"]["lstm"] = str(lstm_dir)

    # 4. Isolation Forest
    if train_anomaly_detection:
        an_out = train_anomaly(df, n_estimators=100, contamination=0.05)
        an_path = output_dir / "isolation_forest" / "model.joblib"
        an_path.parent.mkdir(parents=True, exist_ok=True)
        save_anomaly(an_out["model"], an_out["feature_columns"], an_path)
        results["metrics_anomaly"] = {
            "n_samples": len(df),
            "n_anomalies": int((an_out["predictions"] == -1).sum()),
        }
        results["paths"]["isolation_forest"] = str(an_path)

    return results
