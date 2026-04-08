import json
import random
from datetime import date, timedelta
import sys
import os

sys.path.insert(0, os.path.abspath('.'))
from backend.db.repository import _store, status_from_wqi
from backend.services.dataset_loader import run_startup_data_load

run_startup_data_load()
readings = _store["readings"]

stations = ["Sungai Kulim", "Sungai Klang", "Sungai Gombak", "Sungai Perak", "Sungai Pinang"]

tomorrow = date.today() + timedelta(days=1)
end_date = date(2026, 12, 31)

baseline_wqi = {}
for station in stations:
    station_readings = [r for r in readings if r.get("station_name") == station]
    if station_readings:
        recent = sorted(station_readings, key=lambda x: x.get("reading_date"))[-10:]
        avg = sum(r.get("wqi", 50) for r in recent) / len(recent)
        baseline_wqi[station] = avg
    else:
        baseline_wqi[station] = 75.0 

# Inject trend changes
trends = {
    "Sungai Kulim": -0.01, # gradually decrease
    "Sungai Gombak": -0.05, # strongly decrease
    "Sungai Pinang": 0.0,
    "Sungai Perak": 0.0,
    "Sungai Klang": 0.0 
}

forecast_dataset = []
forecast_alerts = []
forecast_alert_stations = set()

current_date = tomorrow
day_count = 0
while current_date <= end_date:
    date_str = current_date.isoformat()
    day_count += 1
    
    for station in stations:
        base = baseline_wqi[station] + (trends[station] * day_count)
        base = max(40, base) # don't go below 40
        variation = random.choice([1, -1]) * random.uniform(2.0, 5.0)
        predicted_wqi = round(max(0.0, min(100.0, base + variation)), 2)
        
        if predicted_wqi >= 81:
            status = "Clean"
        elif predicted_wqi >= 60:
            status = "Slightly Polluted"
        else:
            status = "Polluted"
            
        forecast_dataset.append({
            "station_name": station,
            "date": date_str,
            "predicted_wqi": predicted_wqi,
            "status": status,
            "source": "Forecast"
        })
        
        if status in ["Slightly Polluted", "Polluted"] and station not in forecast_alert_stations:
            forecast_alerts.append({
                "station_name": station,
                "date": date_str,
                "wqi": predicted_wqi,
                "status": status,
                "alert_type": "Forecast"
            })
            forecast_alert_stations.add(station)

    current_date += timedelta(days=1)

historical_alerts = []
for station in stations:
    station_readings = [r for r in readings if r.get("station_name") == station and r.get("reading_date") <= date.today().isoformat()]
    if station_readings:
        latest = sorted(station_readings, key=lambda x: x.get("reading_date"))[-1]
        wqi = latest.get("wqi", 0)
        st = status_from_wqi(wqi)
        if st in ["slightly_polluted", "polluted"]:
            historical_alerts.append({
                "station_name": station,
                "date": latest.get("reading_date"),
                "wqi": wqi,
                "status": "Slightly Polluted" if st == "slightly_polluted" else "Polluted",
                "alert_type": "Historical"
            })

historical_alerts.sort(key=lambda x: x["date"], reverse=True)
forecast_alerts.sort(key=lambda x: x["date"])

all_alerts = historical_alerts + forecast_alerts

with open("forecast_dataset.json", "w") as f:
    json.dump(forecast_dataset, f, indent=2)
    
with open("alert_dataset.json", "w") as f:
    json.dump(all_alerts, f, indent=2)

print(f"Forecast records generated: {len(forecast_dataset)}")
print(f"Alerts generated: {len(all_alerts)}")
