"""
Time-series forecast service: predict WQI through end of 2026 per station (policy cap).

--- ML-PREDICTED WQI (calendar year 2026) ---
Daily WQI for 2026 is produced ONLY by the trained LSTM (stored under ml_models/lstm/).
Results are saved to prediction_logs; these dates are never ingested as CSV-derived readings.

Legacy RandomForest fallback was removed so 2026 cannot be populated by a non-LSTM heuristic.
"""
import logging
from pathlib import Path
from typing import Optional
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]

# Policy: only generate daily forecast for 2026 (no 2027+ — avoids speculative long-horizon questions).
FORECAST_YEARS = [2026]
FORECAST_END_DATE = datetime(2026, 12, 31).date()


def _load_lstm_artifacts(station_code: Optional[str] = None):
    """Return (model, scaler_bundle, config) for a station, with global fallback."""
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from ml_engine.services.forecasting_service import load_model as load_lstm_bundle

    candidates: list[Path] = []
    code = (station_code or "").strip()
    if code:
        candidates.append(ROOT / "ml_models" / "lstm" / "stations" / code)
    candidates.append(ROOT / "ml_models" / "lstm")

    for base in candidates:
        model_path = base / "lstm_model.keras"
        if not model_path.is_file():
            model_path = base / "model.keras"
        scaler_path = base / "lstm_scaler.joblib"
        if not scaler_path.is_file():
            scaler_path = base / "scaler.joblib"
        if not model_path.is_file() or not scaler_path.is_file():
            continue
        try:
            model, scaler_bundle, cfg = load_lstm_bundle(base)
            return model, scaler_bundle, cfg or {}
        except Exception:
            continue
    return None, None, None


def _readings_to_station_dataframe(readings: list[dict], station_label: str) -> Optional[object]:
    """Build a single-station DataFrame (date, WQI, station_code) from in-memory readings."""
    import pandas as pd

    from data_preprocessing.utils.wqi_calculator import MAX_DOE_FORMULA_CSV_YEAR

    rows = []
    for r in readings:
        if (r.get("data_type") or "historical").strip().lower() == "forecast":
            continue
        d = (r.get("reading_date") or r.get("date") or "")[:10]
        if len(d) < 10:
            continue
        try:
            if int(d[:4]) > MAX_DOE_FORMULA_CSV_YEAR:
                continue
        except ValueError:
            continue
        label = (r.get("station_name") or r.get("station_code") or "").strip()
        if label != station_label:
            continue
        try:
            wqi = float(r.get("wqi", 0))
        except (TypeError, ValueError):
            wqi = 0.0
        code = (r.get("station_code") or station_label or "S01").strip()
        rows.append({"date": d, "WQI": wqi, "station_code": code})

    if not rows:
        return None

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    df = df.drop_duplicates(subset=["date"], keep="last")
    return df


def _pad_history_for_seq_len(df, seq_len: int, station_code: str):
    """If shorter than seq_len, repeat earliest row backward (minimal bootstrap)."""
    import pandas as pd

    if len(df) >= seq_len:
        return df
    need = seq_len - len(df)
    first = df.iloc[:1].copy()
    pad_rows = []
    base_date = first["date"].iloc[0]
    for i in range(need, 0, -1):
        row = first.copy()
        row["date"] = base_date - pd.Timedelta(days=i)
        pad_rows.append(row)
    return pd.concat(pad_rows + [df], ignore_index=True).sort_values("date")


def _compute_lstm_forecast(
    *,
    readings: list[dict],
    station_labels: list[str],
    start_d: date,
    end_d: date,
    build_prediction_window,
    predict,
    pd,
) -> list[dict]:
    """Run per-station LSTM inference for 2026 using multi-day horizon chunks (faster than 1-day steps)."""
    from backend.db.repository import status_from_wqi
    from backend.services.river_mapping import river_name_for_station

    forecast: list[dict] = []

    for station in station_labels:
        df_hist = _readings_to_station_dataframe(readings, station)
        if df_hist is None or df_hist.empty:
            continue
        scode = str(df_hist["station_code"].iloc[-1])

        model, scaler_bundle, cfg = _load_lstm_artifacts(scode)
        if model is None or scaler_bundle is None:
            logger.warning("Forecast: no LSTM model for station %s (%s) — skipping.", scode, station)
            continue

        seq_len = int(cfg.get("seq_len", 30))
        model_horizon = max(1, int(cfg.get("horizon", 7)))
        add_month_cyclical = bool(cfg.get("add_month_cyclical", False))
        extra_param_columns = tuple(cfg.get("extra_param_columns") or ())

        df_hist = _pad_history_for_seq_len(df_hist, seq_len, station)
        df_walk = df_hist.copy()
        current = start_d
        fallback_wqi = float(df_walk["WQI"].iloc[-1])

        while current <= end_d:
            days_left = (end_d - current).days + 1
            step_h = min(model_horizon, days_left)
            try:
                window = build_prediction_window(
                    df_walk,
                    station_code=scode,
                    seq_len=seq_len,
                    date_col="date",
                    add_month_cyclical=add_month_cyclical,
                    extra_param_columns=extra_param_columns,
                )
                pred = predict(model, scaler_bundle, window, horizon=step_h, config=cfg)
                values = [float(v) for v in pred.flatten()[:step_h]]
                if not values or any(v != v for v in values):
                    raise ValueError("LSTM prediction is NaN")
            except Exception:
                logger.exception(
                    "LSTM forecast chunk failed for station=%s date=%s; using last WQI.",
                    station,
                    current.isoformat(),
                )
                values = [fallback_wqi] * step_h

            new_rows = []
            for i, wqi_raw in enumerate(values):
                day = current + timedelta(days=i)
                wqi_next = max(0.0, min(100.0, round(float(wqi_raw), 1)))
                fallback_wqi = wqi_next
                st = status_from_wqi(wqi_next)
                rn = river_name_for_station(scode, station)
                forecast.append(
                    {
                        "date": day.isoformat(),
                        "station_code": scode,
                        "station_name": rn,
                        "river_name": rn,
                        "wqi": wqi_next,
                        "river_status": st,
                    }
                )
                new_rows.append({"date": pd.Timestamp(day), "WQI": wqi_next, "station_code": scode})

            if new_rows:
                df_walk = pd.concat([df_walk, pd.DataFrame(new_rows)], ignore_index=True).sort_values("date")
            current += timedelta(days=step_h)

    print(f"_compute_lstm_forecast: generated {len(forecast)} points for {len(station_labels)} stations.")
    return forecast


def run_forecast() -> list[dict]:
    """
    Train/infer: use the trained LSTM on historical WQI (≤ MAX_DOE_FORMULA_CSV_YEAR) per station,
    then recursively forecast daily WQI for 2026-01-01 .. 2026-12-31.

    Saves to prediction_logs and returns the forecast list.
    """
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    try:
        from ml_engine.services.forecasting_service import TF_AVAILABLE

        if not TF_AVAILABLE:
            logger.error("run_forecast: TensorFlow not available — trying bundled forecast cache.")
            print("run_forecast: TensorFlow not available — trying cache.")
    except Exception as exc:
        logger.exception("run_forecast: TensorFlow import check failed: %s", exc)
        TF_AVAILABLE = False

    from backend.db.repository import (
        _store,
        save_prediction_log,
        save_alert,
        status_from_wqi,
        _today_str,
        clear_forecast_alerts,
    )
    from backend.services.river_mapping import river_name_for_station
    from ml_engine.services.forecasting_service import build_prediction_window, predict
    import pandas as pd

    readings = list(_store.get("readings", []))
    if not readings:
        return []

    clear_forecast_alerts()

    # Unique station labels (same convention previously used for RF: name or code string).
    seen: set[str] = set()
    station_labels: list[str] = []
    for r in readings:
        if (r.get("data_type") or "historical").strip().lower() == "forecast":
            continue
        d = (r.get("reading_date") or "")[:10]
        if len(d) < 10:
            continue
        lab = (r.get("station_name") or r.get("station_code") or "").strip()
        if not lab or lab in seen:
            continue
        seen.add(lab)
        station_labels.append(lab)

    today = _today_str()
    start_d = date(2026, 1, 1)
    end_d = FORECAST_END_DATE
    if start_d > end_d:
        print(f"Forecast: empty window (start={start_d} > policy end={end_d}).")
        return []

    from backend.services.forecast_cache import load_forecast_cache, save_forecast_cache

    forecast = load_forecast_cache()
    if forecast is None:
        if not TF_AVAILABLE:
            print("run_forecast: no cache and no TensorFlow — forecast empty.")
            return []
        forecast = _compute_lstm_forecast(
            readings=readings,
            station_labels=station_labels,
            start_d=start_d,
            end_d=end_d,
            build_prediction_window=build_prediction_window,
            predict=predict,
            pd=pd,
        )
        if forecast:
            save_forecast_cache(forecast)

    if not forecast:
        return []

    forecast.sort(key=lambda x: (x["date"], x["station_code"]))

    log = save_prediction_log(
        "forecast",
        {
            "forecast": forecast,
            "model": "lstm",
            "forecast_years": FORECAST_YEARS,
            "generated_from": start_d.isoformat(),
            "generated_through": end_d.isoformat(),
            "policy_today": today,
        },
        model_name="lstm",
    )

    # Forecast alerts: only when LSTM predicts poor WQI within the next 7 days (tomorrow .. today+7).
    try:
        today_d = date.fromisoformat(today)
        horizon_end = today_d + timedelta(days=7)
    except ValueError:
        today_d = date.today()
        horizon_end = today_d + timedelta(days=7)

    by_station: dict[str, list[dict]] = {}
    for rec in forecast:
        d_raw = (rec.get("date") or "")[:10]
        try:
            rd = date.fromisoformat(d_raw)
        except ValueError:
            continue
        if rd <= today_d or rd > horizon_end:
            continue
        if rd > FORECAST_END_DATE:
            continue
        st = rec.get("river_status") or status_from_wqi(float(rec.get("wqi") or 0))
        if st not in ("slightly_polluted", "polluted"):
            continue
        lab = str(rec.get("station_code") or rec.get("station_name") or "").strip()
        if not lab:
            continue
        by_station.setdefault(lab, []).append(rec)

    for station, pts in by_station.items():
        pts.sort(key=lambda x: (x.get("date") or ""))
        first = pts[0]
        date_str = (first.get("date") or "")[:10]
        wqi = first.get("wqi")
        status = first.get("river_status") or status_from_wqi(float(wqi or 0))
        status_label = "Slightly Polluted" if status == "slightly_polluted" else "Polluted"
        try:
            when = datetime.fromisoformat(date_str).strftime("%d %b %Y")
        except Exception:
            when = date_str or "upcoming"
        msg = (
            f"LSTM 7-day window: {station} predicted {status_label} (WQI {float(wqi or 0):.1f}) "
            f"first on {when}. Further dates in window may also require monitoring."
        )
        save_alert(
            station_code=first.get("station_code") or station,
            station_name=station,
            message=msg,
            severity="warning" if status == "slightly_polluted" else "critical",
            prediction_log_id=log["id"],
            wqi=wqi,
            date_str=date_str,
            alert_type="forecast",
            river_status=status,
            parameter_triggered="LSTM WQI forecast (7-day horizon)",
            trigger_source="forecast",
        )

    try:
        from backend.db.repository import upsert_water_quality_records

        pred_rows = []
        for rec in forecast:
            pred_rows.append(
                {
                    "date": rec.get("date"),
                    "station_code": str(rec.get("station_code") or "").strip(),
                    "station_name": rec.get("station_name"),
                    "WQI": float(rec.get("wqi") or 0),
                    "pollution_status": rec.get("river_status"),
                    "data_source": "lstm_forecast",
                    "is_predicted": True,
                }
            )
        upsert_water_quality_records(pred_rows)
    except Exception:
        logger.exception("forecast: persisting water_quality_records failed")

    return forecast
