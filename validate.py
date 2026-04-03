import os
import sys
from collections import defaultdict
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.abspath('.'))

from backend.db.repository import (
    _store,
    get_summary,
    get_readings_table,
    get_historical_alerts,
    get_forecast_alerts,
    get_stations,
    get_time_series
)
from backend.services.dataset_loader import run_startup_data_load

# Initialize
run_startup_data_load()
readings = _store["readings"]

print("==== 1. DATASET VALIDATION ====")
total_records = len(readings)
stations = set(r.get("station_name") for r in readings)
expected_stations = {"Sungai Kulim", "Sungai Klang", "Sungai Gombak", "Sungai Perak", "Sungai Pinang"}

if not readings:
    print("FAIL")
    print("Issue: Dataset is empty.")
    print("Fix: Ensure the dataset file exists and is populated correctly.")
elif stations != expected_stations:
    print("FAIL")
    print(f"Issue: Expected {len(expected_stations)} stations, but got {len(stations)}.")
    print(f"Actual stations: {stations}")
    print("Fix: Clean up dataset to contain only the exactly 5 valid stations.")
else:
    print("PASS")


print("\n==== 2. FILTER LOGIC VALIDATION ====")
try:
    all_stations = get_readings_table()
    station_filtered = get_readings_table(station_name="Sungai Klang")
    year_filtered = get_readings_table(year=2024)
    data_type_filtered = get_readings_table(data_type="historical")

    if len(all_stations) != len(readings):
        print("FAIL")
        print("Issue: 'All' filter removes data")
        print("Fix: Ensure get_readings_table() defaults to no filter when arguments are None")
    elif len(station_filtered) == 0:
        print("FAIL")
        print("Issue: Station filtering returned empty result.")
        print("Fix: Check station column matching logic.")
    else:
        # Check Month/Date range explicitly if supported
        print("PASS")
except Exception as e:
    print("FAIL")
    print(f"Issue: Error during filtering: {e}")
    print("Fix: Ensure robust filtering logic for dates and strings.")


print("\n==== 3. DASHBOARD KPI VALIDATION ====")
summary = get_summary()
kpi_station_count = summary.get("totalStations")
latest_stations = get_stations()
latest_wqis = [s.get("latest_wqi", 0) for s in latest_stations]
calculated_avg = sum(latest_wqis) / len(latest_wqis) if latest_wqis else 0

if kpi_station_count != len(expected_stations):
    print("FAIL")
    print("Issue: KPI Station count does not match unique station count.")
    print("Fix: Base the station count KPI on exactly the unique loaded stations.")
elif abs(summary.get("avgWqi", 0) - calculated_avg) > 0.01:
    print("FAIL")
    print("Issue: Average WQI calculation error.")
    print(f"Expected: {calculated_avg}, Got: {summary.get('avgWqi')}")
    print("Fix: Calculate Avg WQI exclusively using the single latest record from each station.")
else:
    print("PASS")


print("\n==== 4. ALERT MONITORING VALIDATION ====")
try:
    hist_alerts = get_historical_alerts()
    fore_alerts = get_forecast_alerts()

    invalid_alerts = [a for a in hist_alerts if a.get("river_status") not in ("slightly_polluted", "polluted")]
    if invalid_alerts:
        print("FAIL")
        print("Issue: Alerts triggered for clean rivers.")
        print("Fix: Update alert condition to only trigger on slightly_polluted or polluted.")
    else:
        print("PASS")
except Exception as e:
    print("FAIL")
    print(f"Issue: Exception checking alerts: {e}")
    print("Fix: Check alert generation exceptions.")


print("\n==== 5. DATA TIMELINE VALIDATION ====")
timeline_fail = False
issue_msg = ""
today_str = date.today().isoformat()

# Group by station to check continuous
by_station = defaultdict(list)
for r in readings:
    d = r.get("reading_date")
    # check no overlap
    dt_type = r.get("data_type")
    if dt_type == "historical" and d > today_str:
        timeline_fail = True
        issue_msg = f"Historical data overlap: {d} > {today_str}"
    
    if d:
        try:
            dt = datetime.strptime(d[:10], "%Y-%m-%d").date()
            by_station[r.get("station_name")].append(dt)
        except:
            pass

if not timeline_fail:
    for st, dates in by_station.items():
        sorted_dates = sorted(dates)
        for i in range(1, len(sorted_dates)):
            diff = (sorted_dates[i] - sorted_dates[i-1]).days
            if diff > 1:
                timeline_fail = True
                issue_msg = f"Missing dates for {st}: difference of {diff} days between {sorted_dates[i-1]} and {sorted_dates[i]}"
                break

if timeline_fail:
    print("FAIL")
    print(f"Issue: {issue_msg}")
    print("Fix: Ensure continuous data sequence or backfiller runs properly.")
else:
    print("PASS")


print("\n==== 6. FRONTEND DISPLAY VALIDATION ====")
# We assume backend structural compliance is a prerequisite
has_station_field = any("station_name" in r for r in readings)
has_wqi_field = any("wqi" in r for r in readings)
if not has_station_field or not has_wqi_field:
    print("FAIL")
    print("Issue: Incorrect field mappings.")
    print("Fix: Align frontend field keys with backend JSON mapping (station_name, wqi).")
else:
    print("PASS")


print("\n==== 7. ERROR DETECTION ====")
parsing_errors = []
for r in readings:
    date_val = r.get("reading_date")
    if not date_val or not isinstance(date_val, str) or len(date_val) < 10:
        parsing_errors.append("Invalid date parsing")
        break

if parsing_errors:
    print("FAIL")
    print(f"Issue: {parsing_errors[0]}")
    print("Fix: Adjust date format parsing in dataset loader.")
else:
    print("PASS")
