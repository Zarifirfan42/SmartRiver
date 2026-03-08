"""
Prediction service — Business logic for ML predictions.
Loads models from ml_models/, runs classification/forecast/anomaly, returns results.
"""
from pathlib import Path
from typing import Optional, List, Dict, Any

# TODO: import from modules.ml_engine and ml_models


def get_models_dir() -> Path:
    """Resolve ml_models directory (project root / ml_models)."""
    return Path(__file__).resolve().parents[2] / "ml_models"


def predict_river_status(data_path: str) -> List[Dict[str, Any]]:
    """
    Run classification model on preprocessed data.
    Returns list of { station_code, date, river_status }.
    """
    # TODO: load Random Forest from ml_models/random_forest, run predict
    return []


def predict_wqi_forecast(
    station_code: Optional[str] = None,
    horizon_days: int = 7,
) -> List[Dict[str, Any]]:
    """
    Run LSTM forecast for next horizon_days.
    Returns list of { date, wqi }.
    """
    # TODO: load LSTM from ml_models/lstm, run predict
    return []


def detect_anomalies(data_path: str) -> List[Dict[str, Any]]:
    """
    Run anomaly detection (Isolation Forest) on data.
    Returns list of { station_code, date, score, is_anomaly }.
    """
    # TODO: load model from ml_models/anomaly_detection
    return []
