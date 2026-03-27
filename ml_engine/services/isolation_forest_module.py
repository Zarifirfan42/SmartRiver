"""
Isolation Forest add-on for SmartRiver anomaly inference.

This module reuses the trained Isolation Forest artifact and returns
simple labels for presentation:
- normal
- anomaly
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import joblib
import numpy as np
import pandas as pd


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "wqi" in out.columns and "WQI" not in out.columns:
        out["WQI"] = out["wqi"]
    if "reading_date" in out.columns and "date" not in out.columns:
        out["date"] = out["reading_date"]
    return out


def detect_anomalies(
    df: pd.DataFrame,
    model_path: str | Path = "ml_models/anomaly_detection/model.joblib",
) -> pd.DataFrame:
    """
    Run anomaly detection and return table with anomaly labels.
    """
    base = _normalize_columns(df)
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Isolation Forest model not found: {path}")

    payload = joblib.load(path)
    model = payload["model"]
    feature_columns = payload.get("feature_columns", ["WQI"])
    missing_cols = [c for c in feature_columns if c not in base.columns]
    if missing_cols:
        raise ValueError(f"Input data missing required columns: {missing_cols}")

    X = base[feature_columns].fillna(base[feature_columns].median())
    pred = model.predict(X)  # -1 anomaly, 1 normal
    score = model.decision_function(X)

    out = base.copy()
    out["anomaly_raw"] = pred
    out["anomaly_label"] = np.where(out["anomaly_raw"] == -1, "anomaly", "normal")
    out["anomaly_score"] = score
    return out

