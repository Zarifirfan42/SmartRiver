"""
Prediction API: load trained models and run classification, forecast, and anomaly detection.
"""
from pathlib import Path
from typing import Optional, Any

import numpy as np
import pandas as pd

from ml_engine.services.classification_service import load_model as load_rf, predict_labels as rf_predict_labels
from ml_engine.services.forecasting_service import load_model as load_lstm, predict as lstm_predict, get_wqi_series
from ml_engine.services.anomaly_service import load_model as load_anomaly, detect_anomalies


def get_models_dir(base_path: Optional[str | Path] = None) -> Path:
    """Resolve ml_models directory."""
    if base_path is not None:
        return Path(base_path)
    # Default: project root / ml_models
    return Path(__file__).resolve().parents[2] / "ml_models"


class PredictionAPI:
    """
    Load and run all three models. Use after training_pipeline has saved artifacts.
    """

    def __init__(self, models_dir: Optional[str | Path] = None):
        self.models_dir = Path(models_dir or get_models_dir())
        self._rf_model = None
        self._rf_features = None
        self._lstm_model = None
        self._lstm_scaler = None
        self._lstm_config = None
        self._anomaly_model = None
        self._anomaly_features = None

    def load_classification_model(self) -> bool:
        """Load Random Forest from ml_models/random_forest/model.joblib."""
        path = self.models_dir / "random_forest" / "model.joblib"
        if not path.exists():
            return False
        self._rf_model, self._rf_features = load_rf(path)
        return True

    def load_forecasting_model(self) -> bool:
        """Load LSTM from ml_models/lstm/."""
        path = self.models_dir / "lstm"
        if not (path / "lstm_model.keras").exists():
            return False
        self._lstm_model, self._lstm_scaler, self._lstm_config = load_lstm(path)
        return True

    def load_anomaly_model(self) -> bool:
        """Load Isolation Forest from ml_models/isolation_forest/model.joblib."""
        path = self.models_dir / "isolation_forest" / "model.joblib"
        if not path.exists():
            return False
        self._anomaly_model, self._anomaly_features = load_anomaly(path)
        return True

    def load_all(self) -> dict[str, bool]:
        """Load all available models. Returns {classification, forecasting, anomaly}."""
        return {
            "classification": self.load_classification_model(),
            "forecasting": self.load_forecasting_model(),
            "anomaly": self.load_anomaly_model(),
        }

    # --- Classification ---

    def predict_river_status(
        self,
        df: pd.DataFrame,
        feature_columns: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Predict river status for each row. Returns list of {index, river_status}.
        """
        if self._rf_model is None:
            if not self.load_classification_model():
                return []
        features = feature_columns or self._rf_features
        if not features:
            return []
        labels = rf_predict_labels(self._rf_model, df, feature_columns=features)
        return [{"index": i, "river_status": l} for i, l in enumerate(labels)]

    # --- Forecasting ---

    def predict_wqi_forecast(
        self,
        df: pd.DataFrame,
        horizon: Optional[int] = None,
        station_code: Optional[str] = None,
    ) -> Optional[list[float]]:
        """
        Predict next horizon days of WQI. Uses last seq_len values from df.
        Returns list of WQI values or None if model not available.
        """
        if self._lstm_model is None:
            if not self.load_forecasting_model():
                return None
        seq_len = self._lstm_config.get("seq_len", 30)
        horizon = horizon or self._lstm_config.get("horizon", 7)
        series = get_wqi_series(df, station_code=station_code)
        if len(series) < seq_len:
            return None
        last_seq = series[-seq_len:]
        pred = lstm_predict(
            self._lstm_model,
            self._lstm_scaler,
            last_seq,
            horizon=horizon,
        )
        return pred.tolist()

    # --- Anomaly ---

    def detect_anomalies(
        self,
        df: pd.DataFrame,
        date_col: str = "date",
        station_col: str = "station_code",
    ) -> list[dict]:
        """Return list of detected anomalies: {station_code, date, score, is_anomaly}."""
        if self._anomaly_model is None:
            if not self.load_anomaly_model():
                return []
        return detect_anomalies(
            self._anomaly_model,
            df,
            feature_columns=self._anomaly_features,
            date_col=date_col,
            station_col=station_col,
        )


# Singleton for easy use in API
_default_api: Optional[PredictionAPI] = None


def get_prediction_api(models_dir: Optional[str | Path] = None) -> PredictionAPI:
    """Get or create the default PredictionAPI instance."""
    global _default_api
    if _default_api is None:
        _default_api = PredictionAPI(models_dir=models_dir)
        _default_api.load_all()
    return _default_api
