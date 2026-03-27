"""
Professional-but-simple LSTM forecasting add-on for SmartRiver.

Design goals:
- Keep existing pipeline untouched (additive module only)
- Reuse existing forecasting_service LSTM utilities
- Support small dataset via optional augmentation (in-memory only)
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Optional
import numpy as np
import pandas as pd

from ml_engine.services import forecasting_service
from ml_engine.services.data_augmentation import augment_wqi_series


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize basic columns without changing source files."""
    out = df.copy()
    if "wqi" in out.columns and "WQI" not in out.columns:
        out["WQI"] = out["wqi"]
    if "reading_date" in out.columns and "date" not in out.columns:
        out["date"] = out["reading_date"]
    return out


def train_lstm_forecaster(
    df: pd.DataFrame,
    station_code: Optional[str] = None,
    horizon_days: int = 7,
    use_augmentation_if_small: bool = True,
    min_rows_for_lstm: int = 120,
) -> dict[str, Any]:
    """
    Train LSTM model for one station (or global if station_code is None).

    horizon_days must be between 7 and 30 as requested.
    """
    if horizon_days < 7 or horizon_days > 30:
        raise ValueError("horizon_days must be in range 7..30")

    base = _normalize_columns(df)
    train_df = base
    if use_augmentation_if_small:
        train_df = augment_wqi_series(base, min_rows=min_rows_for_lstm)

    # Sequence length is kept simple and explainable.
    # 30-day context is a common baseline for daily environmental signals.
    result = forecasting_service.train(
        train_df,
        station_code=station_code,
        seq_len=30,
        horizon=horizon_days,
        epochs=30,
        batch_size=16,
        verbose=0,
    )
    return result


def predict_future_wqi(
    trained: dict[str, Any],
    df: pd.DataFrame,
    horizon_days: int = 7,
    station_code: Optional[str] = None,
) -> pd.DataFrame:
    """
    Predict next N days WQI (7..30) and return forecast table.
    """
    if horizon_days < 7 or horizon_days > 30:
        raise ValueError("horizon_days must be in range 7..30")

    if not trained or trained.get("error"):
        raise RuntimeError(trained.get("error", "LSTM model is not trained"))

    model = trained["model"]
    scaler = trained["scaler"]
    seq_len = int(trained.get("seq_len", 30))

    base = _normalize_columns(df)
    series = forecasting_service.get_wqi_series(base, station_code=station_code)
    if len(series) < seq_len:
        raise ValueError(f"Need at least {seq_len} WQI points for prediction")

    last_seq_raw = series[-seq_len:]
    # Scale last sequence with the same training scaler.
    last_seq_scaled = scaler.transform(last_seq_raw.reshape(-1, 1)).flatten().astype(np.float32)
    pred = forecasting_service.predict(model, scaler, last_seq_scaled, horizon=horizon_days)
    pred = np.clip(pred, 0.0, 100.0)

    # Build future dates from latest available date.
    date_col = "date" if "date" in base.columns else "reading_date"
    latest_date = pd.to_datetime(base[date_col], errors="coerce").dropna().max()
    if pd.isna(latest_date):
        latest_date = pd.Timestamp.today().normalize()
    future_dates = [(latest_date + timedelta(days=i + 1)).date().isoformat() for i in range(horizon_days)]

    out = pd.DataFrame({
        "date": future_dates,
        "predicted_wqi": [float(round(v, 2)) for v in pred[:horizon_days]],
    })
    out["status"] = out["predicted_wqi"].apply(
        lambda v: "Clean" if v >= 81 else ("Slightly Polluted" if v >= 60 else "Polluted")
    )
    return out

