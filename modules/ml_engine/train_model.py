"""
Train model — Orchestrate training for classification, forecasting, and anomaly detection.
Loads preprocessed data, trains RF / LSTM / Isolation Forest, saves to ml_models/.
"""
from pathlib import Path
from typing import Optional

# TODO: import from data_preprocessing (pipeline), then call ml_models trainers
# from modules.data_preprocessing.cleaning import clean
# from modules.data_management.data_loader import load_csv


def train_all(
    data_path: str | Path,
    output_dir: str | Path = "ml_models",
    train_classification: bool = True,
    train_forecasting: bool = True,
    train_anomaly: bool = True,
) -> dict:
    """
    Run full training pipeline: preprocess data, then train RF, LSTM, Isolation Forest.
    Returns dict with metrics (accuracy, RMSE, MAE, anomaly count) and saved paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    # 1. Load and preprocess (use modules.data_preprocessing and data_management)
    # df = load_csv(data_path)
    # df = clean(df)
    # add WQI, features, etc.

    # 2. Train Random Forest (classification)
    if train_classification:
        # from ml_models.random_forest.train_rf import train_rf
        # results["classification"] = train_rf(df, output_dir / "random_forest")
        results["classification"] = {"accuracy": 0, "path": str(output_dir / "random_forest")}

    # 3. Train LSTM (forecasting)
    if train_forecasting:
        # from ml_models.lstm.train_lstm import train_lstm
        # results["forecasting"] = train_lstm(df, output_dir / "lstm")
        results["forecasting"] = {"rmse": 0, "mae": 0, "path": str(output_dir / "lstm")}

    # 4. Train Isolation Forest (anomaly)
    if train_anomaly:
        # from ml_models.anomaly_detection.isolation_forest import train_anomaly
        # results["anomaly"] = train_anomaly(df, output_dir / "anomaly_detection")
        results["anomaly"] = {"n_anomalies": 0, "path": str(output_dir / "anomaly_detection")}

    return results
