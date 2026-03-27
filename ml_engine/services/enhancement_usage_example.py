"""
Example integration flow for SmartRiver enhancements (non-invasive).

This file is intentionally standalone so your original pipeline remains unchanged.
Use this as reference during presentation.
"""
from __future__ import annotations

import pandas as pd

from ml_engine.services.lstm_forecast_module import train_lstm_forecaster, predict_future_wqi
from ml_engine.services.isolation_forest_module import detect_anomalies
from modules.visualization_alert.enhanced_alerts import (
    build_threshold_alerts,
    build_anomaly_alerts,
    combine_alerts,
)


def run_enhancement_flow(
    df: pd.DataFrame,
    station_code: str | None = None,
    horizon_days: int = 14,
    threshold_wqi: float = 60.0,
):
    """
    End-to-end enhancement flow:
    1) LSTM train + forecast
    2) Isolation Forest anomaly detection
    3) Combined alerts
    """
    trained = train_lstm_forecaster(
        df=df,
        station_code=station_code,
        horizon_days=horizon_days,
        use_augmentation_if_small=True,
        min_rows_for_lstm=120,
    )
    forecast_df = predict_future_wqi(
        trained=trained,
        df=df,
        horizon_days=horizon_days,
        station_code=station_code,
    )

    # Keep station name for alert readability.
    if station_code and "station_name" not in forecast_df.columns:
        forecast_df["station_name"] = station_code

    anomaly_df = detect_anomalies(df)

    threshold_alerts = build_threshold_alerts(
        forecast_df=forecast_df,
        threshold_wqi=threshold_wqi,
        station_name=station_code or "All Stations",
    )
    anomaly_alerts = build_anomaly_alerts(
        anomaly_df=anomaly_df,
        station_name=station_code or "All Stations",
    )
    alerts = combine_alerts(threshold_alerts, anomaly_alerts)

    return {
        "forecast_df": forecast_df,
        "anomaly_df": anomaly_df,
        "alerts": alerts,
        "metrics": trained.get("metrics", {}),
        "training_error": trained.get("error"),
    }

