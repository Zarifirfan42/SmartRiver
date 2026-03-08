"""
Isolation Forest for anomaly detection (pollution spikes).
Fit on WQI/params, predict anomalies, return scores and flagged indices.
"""
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


RANDOM_STATE = 42


def get_anomaly_features(df: pd.DataFrame) -> list[str]:
    """Columns to use as features for anomaly detection."""
    prefer = ["WQI", "DO", "BOD", "COD", "AN", "TSS", "pH"]
    return [c for c in prefer if c in df.columns] or [c for c in df.columns if df[c].dtype in (np.float64, "float64", np.int64, "int64") and c not in ("date", "station_code")]


def train(
    df: pd.DataFrame,
    n_estimators: int = 100,
    contamination: float = 0.05,
    max_samples: Optional[int] = None,
    random_state: int = RANDOM_STATE,
) -> dict[str, Any]:
    """
    Fit Isolation Forest on WQI and parameters.
    Returns model, feature columns, and optional threshold from training.
    """
    feature_cols = get_anomaly_features(df)
    if not feature_cols:
        raise ValueError("No feature columns for anomaly detection")

    X = df[feature_cols].fillna(df[feature_cols].median())

    if max_samples is None:
        max_samples = min(256, len(X))

    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        max_samples=max_samples,
        random_state=random_state,
    )
    model.fit(X)

    pred = model.predict(X)
    scores = model.decision_function(X)

    return {
        "model": model,
        "feature_columns": feature_cols,
        "scores": scores,
        "predictions": pred,
    }


def predict(
    model: Any,
    df: pd.DataFrame,
    feature_columns: Optional[list[str]] = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Predict anomalies: 1 = normal, -1 = anomaly.
    Returns (predictions, decision_scores). Lower score = more anomalous.
    """
    if feature_columns is None:
        feature_columns = get_anomaly_features(df)
    X = df[feature_columns].fillna(0)
    pred = model.predict(X)
    scores = model.decision_function(X)
    return pred, scores


def detect_anomalies(
    model: Any,
    df: pd.DataFrame,
    feature_columns: Optional[list[str]] = None,
    date_col: str = "date",
    station_col: str = "station_code",
) -> list[dict]:
    """
    Return list of anomaly records: [{station_code, date, score, is_anomaly}, ...].
    """
    pred, scores = predict(model, df, feature_columns)
    out = []
    for i in range(len(df)):
        if pred[i] == -1:
            row = {"is_anomaly": True, "score": float(scores[i])}
            if date_col in df.columns:
                row["date"] = str(df.iloc[i][date_col])
            if station_col in df.columns:
                row["station_code"] = str(df.iloc[i][station_col])
            out.append(row)
    return out


def save_model(model: Any, feature_columns: list[str], path: str | Path) -> None:
    """Save Isolation Forest and metadata."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_columns": feature_columns}, path)


def load_model(path: str | Path) -> tuple[Any, list[str]]:
    """Load Isolation Forest and feature columns."""
    data = joblib.load(path)
    return data["model"], data.get("feature_columns", [])
