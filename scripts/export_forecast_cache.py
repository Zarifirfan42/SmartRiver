"""Export bundled LSTM 2026 forecast cache for production (fast Render startup)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.dataset_loader import run_startup_data_load
from backend.services.forecast_cache import CACHE_PATH, save_forecast_cache
from backend.services.forecast_service import _compute_lstm_forecast
from backend.db.repository import _store
from ml_engine.services.forecasting_service import build_prediction_window, predict
import pandas as pd
from datetime import date


def main() -> None:
    print("Loading dataset…")
    run_startup_data_load()
    readings = list(_store.get("readings", []))
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

    print(f"Computing LSTM forecast for {len(station_labels)} stations…")
    forecast = _compute_lstm_forecast(
        readings=readings,
        station_labels=station_labels,
        start_d=date(2026, 1, 1),
        end_d=date(2026, 12, 31),
        build_prediction_window=build_prediction_window,
        predict=predict,
        pd=pd,
    )
    save_forecast_cache(forecast)
    print(f"Done: {len(forecast)} points -> {CACHE_PATH}")


if __name__ == "__main__":
    main()
