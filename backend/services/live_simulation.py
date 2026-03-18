"""
Simulated live data for SmartRiver.
Generates daily WQI per station from 2025 onwards, continuing from the latest available value
(historical 2023–2024 or forecast 2025–2028). Uses trend-following steps and optional seasonal variation.
"""
import random
from datetime import date

# All stations that receive simulated live data (must match names in dataset/readings).
SIMULATED_LIVE_STATIONS = [
    "Sungai Kulim",
    "Sungai Klang",
    "Sungai Gombak",
    "Sungai Perak",
    "Sungai Pinang",
]

# WQI step range: new_wqi = previous_wqi + random(-3, +3) for realistic continuity.
WQI_STEP_MIN = -3.0
WQI_STEP_MAX = 3.0

# Malaysia: rainy season roughly Nov–Mar (higher runoff, can slightly lower WQI); dry Apr–Oct.
RAINY_MONTHS = {1, 2, 3, 10, 11, 12}
SEASONAL_DELTA_RAINY = -0.5   # slight decrease in WQI during rainy season
SEASONAL_DELTA_DRY = 0.3      # slight increase in dry season

DATASET_ID_SIMULATED = 1
SOURCE_SIMULATED_LIVE = "simulated_live"


def wqi_to_status(wqi: float) -> str:
    """Classify WQI into river status. >= 81 Clean, 60–80 Slightly Polluted, < 60 Polluted."""
    if wqi >= 81:
        return "clean"
    if wqi >= 60:
        return "slightly_polluted"
    return "polluted"


def seasonal_delta(month: int) -> float:
    """Return a small WQI adjustment by season (rainy vs dry)."""
    if month in RAINY_MONTHS:
        return SEASONAL_DELTA_RAINY
    return SEASONAL_DELTA_DRY


def generate_daily_simulated_readings() -> list[dict]:
    """
    For each station: if today's data does not exist, generate one record from latest WQI.
    Returns list of newly appended reading dicts (for logging/alerts).
    """
    from backend.db.repository import (
        get_latest_reading_for_station,
        append_reading,
        get_stations,
    )

    today_str = date.today().isoformat()
    month = date.today().month
    delta_season = seasonal_delta(month)

    # Use station list from repository (from dataset); fallback to fixed list if empty.
    stations_from_repo = [s.get("station_name") or s.get("station_code") for s in get_stations()]
    station_names = [s for s in stations_from_repo if s] if stations_from_repo else SIMULATED_LIVE_STATIONS

    created = []
    for station_name in station_names:
        latest = get_latest_reading_for_station(station_name)
        if not latest:
            continue
        latest_date = (latest.get("reading_date") or "")[:10]
        if latest_date >= today_str:
            # Today's data already exists for this station; do nothing.
            continue

        prev_wqi = float(latest.get("wqi", 0))
        step = random.uniform(WQI_STEP_MIN, WQI_STEP_MAX)
        new_wqi = prev_wqi + step + delta_season
        new_wqi = max(0.0, min(100.0, round(new_wqi, 1)))
        status = wqi_to_status(new_wqi)

        rec = append_reading(
            dataset_id=DATASET_ID_SIMULATED,
            station_code=station_name,
            station_name=station_name,
            reading_date=today_str,
            wqi=new_wqi,
            river_status=status,
            source=SOURCE_SIMULATED_LIVE,
            data_type="simulated_live",
        )
        created.append(rec)
        print(f"Generated live WQI for {station_name} on {today_str}: {new_wqi}")

    return created


def _create_historical_alert_for_reading(rec: dict) -> None:
    """If the reading is slightly_polluted or polluted, create a historical alert."""
    status = (rec.get("river_status") or "").strip().lower().replace(" ", "_")
    if status not in ("slightly_polluted", "polluted"):
        return
    from backend.db.repository import save_alert
    station_name = rec.get("station_name") or rec.get("station_code") or "Unknown"
    wqi = rec.get("wqi", 0)
    date_str = rec.get("reading_date", "")
    status_label = "Slightly Polluted" if status == "slightly_polluted" else "Polluted"
    severity = "warning" if status == "slightly_polluted" else "critical"
    msg = f"{station_name} water quality is {status_label} (WQI: {wqi:.1f}) on {date_str}."
    save_alert(
        station_code=station_name,
        station_name=station_name,
        message=msg,
        severity=severity,
        wqi=wqi,
        date_str=date_str,
        alert_type="historical",
        river_status=status,
    )


def run_simulated_live_data() -> int:
    """
    Generate today's simulated WQI for each station if not already present.
    Creates historical alerts for any new simulated reading that is slightly polluted or polluted.
    Returns the number of new readings generated.
    """
    created = generate_daily_simulated_readings()
    for rec in created:
        _create_historical_alert_for_reading(rec)
    return len(created)


def start_daily_scheduler() -> None:
    """
    Start a background thread that runs simulated live data once now and then every 24 hours
    so that data updates daily even if the server does not restart.
    """
    import threading
    import time

    def _run_at_interval():
        # Run once shortly after startup (dataset already loaded).
        time.sleep(2)
        try:
            n = run_simulated_live_data()
            if n > 0:
                print(f"Live simulation: generated {n} readings for {date.today().isoformat()}.")
        except Exception as e:
            print("Live simulation run failed:", e)

        # Then run every 24 hours (at same time next day).
        while True:
            time.sleep(86400)
            try:
                n = run_simulated_live_data()
                if n > 0:
                    print(f"Live simulation: generated {n} readings for {date.today().isoformat()}.")
            except Exception as e:
                print("Live simulation run failed:", e)

    t = threading.Thread(target=_run_at_interval, daemon=True)
    t.start()
    print("Live simulation scheduler started (runs daily).")
