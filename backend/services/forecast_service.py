"""
Time-series forecast service: predict WQI through end of 2026 per station (policy cap for demo / examiner risk).
Uses Random Forest regression on historical data.
Predictions are stored in prediction_logs; forecast dates are never treated as real measurements.
"""
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[2]

# Policy: only generate daily forecast for 2026 (no 2027+ — avoids speculative long-horizon questions).
FORECAST_YEARS = [2026]
FORECAST_END_DATE = datetime(2026, 12, 31).date()

def run_forecast() -> list[dict]:
    """
    Train a time-series forecast model on historical WQI (readings dated on or before today, excluding forecast rows).
    Generate daily predictions per station from 2026-01-01 through 2026-12-31 only.
    Saves to prediction_logs and returns the forecast list.
    """
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from backend.db.repository import (
        _store,
        save_prediction_log,
        save_alert,
        status_from_wqi,
        _today_str,
        clear_forecast_alerts,
    )
    from backend.services.river_mapping import river_name_for_station

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

    clear_forecast_alerts()

    today = _today_str()
    # Build training data: one row per (station, date) with WQI — historical only (no future-dated CSV rows).
    rows = []
    for r in readings:
        d = r.get("reading_date") or ""
        if len(d) < 10:
            continue
        if d > today:
            continue
        if (r.get("data_type") or "historical").strip().lower() == "forecast":
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
        # Use correct day-of-year so seasonality works across all month lengths.
        try:
            day_of_year = datetime(year, month, day).timetuple().tm_yday
        except Exception:
            day_of_year = month * 31 + day  # fallback
        rows.append({
            "station": station,
            "year": year,
            "month": month,
            "day": day,
            "day_of_year": day_of_year,
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

    # Generate prediction dates: daily for each forecast year.
    forecast = []
    for station in stations:
        station_enc = le.transform([station])[0]
        for year in FORECAST_YEARS:
            start_date = datetime(year, 1, 1).date()
            end_date = min(datetime(year, 12, 31).date(), FORECAST_END_DATE)
            current = start_date
            while current <= end_date:
                month = current.month
                day = current.day
                day_of_year = current.timetuple().tm_yday
                date_str = current.isoformat()
                X_pred = pd.DataFrame([{
                    "station_encoded": station_enc,
                    "year": year,
                    "month": month,
                    "day_of_year": day_of_year,
                }])
                pred_wqi = float(model.predict(X_pred)[0])
                pred_wqi = max(0.0, min(100.0, round(pred_wqi, 1)))
                status = status_from_wqi(pred_wqi)
                # station here is the label encoded from training (usually station_name, e.g. Sungai Klang).
                forecast.append({
                    "date": date_str,
                    "station_code": station,
                    "station_name": station,
                    "river_name": river_name_for_station(station, station),
                    "wqi": pred_wqi,
                    "river_status": status,
                })
                current = current + timedelta(days=1)

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
        save_alert(
            station_code=rec.get("station_code") or station,
            station_name=station,
            message=msg,
            prediction_log_id=log["id"],
            wqi=wqi,
            date_str=date_str,
            alert_type="forecast",
            river_status=status,
        )

    return forecast
