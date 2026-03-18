"""
Time-series forecast service: predict WQI for 2025-2028 per station.
Uses Random Forest regression on historical data (2023-2024 only).
Input: Date, Station, Historical WQI. Output: Predicted WQI.
Predictions are stored in prediction_logs; 2025-2028 are never treated as real measurements.
"""
from pathlib import Path
from typing import Optional
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]

# Forecast years: generate predictions for these years (not from dataset).
FORECAST_YEARS = [2025, 2026, 2027, 2028]

# Predicted river status from WQI (same rule as elsewhere).
def _predicted_status(wqi: float) -> str:
    if wqi >= 81:
        return "clean"
    if wqi >= 60:
        return "slightly_polluted"
    return "polluted"


def run_forecast() -> list[dict]:
    """
    Train a time-series forecast model on historical WQI (readings with year <= 2024).
    Generate predictions per station for 2025, 2026, 2027, 2028.
    Saves to prediction_logs and returns the forecast list.
    """
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from backend.db.repository import _store, save_prediction_log, save_alert

    readings = list(_store.get("readings", []))
    if not readings:
        return []

    try:
        import pandas as pd
        import numpy as np
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.preprocessing import LabelEncoder
    except ImportError:
        return []

    # Build training data: one row per (station, date) with WQI
    rows = []
    for r in readings:
        d = r.get("reading_date") or ""
        if len(d) < 10:
            continue
        try:
            year = int(d[:4])
            month = int(d[5:7])
            day = int(d[8:10])
        except (ValueError, TypeError):
            continue
        station = r.get("station_name") or r.get("station_code") or ""
        if not station:
            continue
        wqi = float(r.get("wqi", 0))
        rows.append({
            "station": station,
            "year": year,
            "month": month,
            "day": day,
            "day_of_year": month * 31 + day,  # simple ordinal
            "wqi": wqi,
        })

    if not rows:
        return []

    df = pd.DataFrame(rows)
    le = LabelEncoder()
    df["station_encoded"] = le.fit_transform(df["station"].astype(str))
    stations = list(le.classes_)

    X = df[["station_encoded", "year", "month", "day_of_year"]]
    y = df["wqi"]
    model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X, y)

    # Generate prediction dates: monthly from 2025-01 to 2028-12 (one point per month per station)
    forecast = []
    for station in stations:
        station_enc = le.transform([station])[0]
        for year in FORECAST_YEARS:
            for month in range(1, 13):
                day = 15  # mid-month
                day_of_year = month * 31 + 15
                date_str = f"{year}-{month:02d}-{day:02d}"
                X_pred = pd.DataFrame([{
                    "station_encoded": station_enc,
                    "year": year,
                    "month": month,
                    "day_of_year": day_of_year,
                }])
                pred_wqi = float(model.predict(X_pred)[0])
                pred_wqi = max(0.0, min(100.0, round(pred_wqi, 1)))
                status = _predicted_status(pred_wqi)
                forecast.append({
                    "date": date_str,
                    "station_code": station,
                    "station_name": station,
                    "wqi": pred_wqi,
                    "river_status": status,
                })

    forecast.sort(key=lambda x: (x["date"], x["station_code"]))

    # Save forecast prediction log first so alerts can reference it.
    log = save_prediction_log(
        "forecast",
        {"forecast": forecast, "model": "random_forest", "forecast_years": FORECAST_YEARS},
        model_name="random_forest",
    )

    # Create forecast-based alerts only for future dates (date > today).
    from backend.db.repository import _today_str
    today = _today_str()
    for rec in forecast:
        date_str = rec.get("date") or ""
        if date_str <= today:
            continue
        status = rec.get("river_status")
        if status not in ("slightly_polluted", "polluted"):
            continue
        station = rec.get("station_name") or rec.get("station_code") or "Unknown"
        wqi = rec.get("wqi")
        # Human-readable month/year for the message.
        try:
            when = datetime.fromisoformat(date_str).strftime("%B %Y")
        except Exception:
            when = date_str or "future period"
        status_label = "Slightly Polluted" if status == "slightly_polluted" else "Polluted"
        msg = f"Forecast Warning: {station} predicted to become {status_label} in {when}."
        severity = "warning" if status == "slightly_polluted" else "critical"
        save_alert(
            station_code=rec.get("station_code") or station,
            station_name=station,
            message=msg,
            severity=severity,
            prediction_log_id=log["id"],
            wqi=wqi,
            date_str=date_str,
            alert_type="forecast",
            river_status=status,
        )

    return forecast
