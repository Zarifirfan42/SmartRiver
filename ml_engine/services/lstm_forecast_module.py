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
from sklearn.metrics import mean_absolute_error, mean_squared_error

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


def train_lstm(
    df: pd.DataFrame,
    station_code: Optional[str] = None,
    horizon_days: int = 7,
) -> dict[str, Any]:
    """
    Backward-compatible alias with the requested function name.
    """
    return train_lstm_forecaster(
        df=df,
        station_code=station_code,
        horizon_days=horizon_days,
        use_augmentation_if_small=True,
        min_rows_for_lstm=120,
    )


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


def predict_wqi(
    trained: dict[str, Any],
    df: pd.DataFrame,
    horizon_days: int = 7,
    station_code: Optional[str] = None,
) -> pd.DataFrame:
    """
    Backward-compatible alias with the requested function name.
    """
    return predict_future_wqi(
        trained=trained,
        df=df,
        horizon_days=horizon_days,
        station_code=station_code,
    )


def evaluate_model(y_test: np.ndarray, y_pred: np.ndarray, train_info: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Evaluate forecast quality using proper y_test vs y_pred comparison.
    Returns RMSE, MAE, and optional training loss traces.
    """
    y_true = np.asarray(y_test, dtype=float).flatten()
    y_hat = np.asarray(y_pred, dtype=float).flatten()
    n = min(len(y_true), len(y_hat))
    if n == 0:
        return {"rmse": None, "mae": None, "train_loss": [], "val_loss": []}
    y_true = y_true[:n]
    y_hat = y_hat[:n]
    rmse = float(np.sqrt(mean_squared_error(y_true, y_hat)))
    mae = float(mean_absolute_error(y_true, y_hat))
    out = {"rmse": rmse, "mae": mae, "train_loss": [], "val_loss": []}
    if train_info:
        out["train_loss"] = list(train_info.get("train_loss", []))
        out["val_loss"] = list(train_info.get("val_loss", []))
    return out


def explain_forecast_trend(forecast_df: pd.DataFrame) -> dict[str, str]:
    """
    Create non-technical interpretation text for forecast behavior.
    """
    if forecast_df is None or len(forecast_df) == 0:
        return {
            "trend": "No trend available",
            "explanation": "No forecast data is available yet.",
        }
    vals = forecast_df["predicted_wqi"].astype(float).values
    delta = float(vals[-1] - vals[0])
    if delta > 1.0:
        trend = "Increasing"
        explanation = "Predicted WQI is generally improving over the selected period, indicating better water quality conditions."
    elif delta < -1.0:
        trend = "Decreasing"
        explanation = "Predicted WQI is generally declining over the selected period, suggesting potential deterioration in water quality."
    else:
        trend = "Stable"
        explanation = "Predicted WQI remains relatively stable, with only small day-to-day fluctuations."
    return {"trend": trend, "explanation": explanation}


def prepare_actual_vs_predicted_data(
    actual_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    actual_date_col: str = "date",
    actual_wqi_col: str = "WQI",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prepare clean dataframes for Actual vs Predicted visualization.
    """
    a = actual_df.copy()
    f = forecast_df.copy()
    if "reading_date" in a.columns and actual_date_col not in a.columns:
        a[actual_date_col] = a["reading_date"]
    if "wqi" in a.columns and actual_wqi_col not in a.columns:
        a[actual_wqi_col] = a["wqi"]
    a[actual_date_col] = pd.to_datetime(a[actual_date_col], errors="coerce")
    f["date"] = pd.to_datetime(f["date"], errors="coerce")
    a = a.dropna(subset=[actual_date_col]).sort_values(actual_date_col)
    f = f.dropna(subset=["date"]).sort_values("date")
    return a, f

