"""
Backfill service — fill missing daily WQI readings per station.

Goal:
- For each station, ensure a continuous daily series from earliest reading date up to today.
- Do NOT overwrite existing data; only insert missing dates.
- Backfilled records are tagged with source="simulated_backfill" and data_type="simulated_backfill".
"""
from datetime import date, datetime, timedelta
import random


def _wqi_to_status(wqi: float) -> str:
  """Classify WQI into river status."""
  if wqi >= 81:
    return "clean"
  if wqi >= 60:
    return "slightly_polluted"
  return "polluted"


def run_backfill() -> None:
  """
  For each station in readings:
  - Find earliest reading_date.
  - Loop from earliest date to today (inclusive).
  - If a date is missing, insert a backfilled record based on previous day's WQI.
  """
  from backend.db.repository import _store, append_reading, _today_str

  readings = list(_store.get("readings", []))
  if not readings:
    return

  today_str = _today_str()
  try:
    today = datetime.fromisoformat(today_str).date()
  except Exception:
    today = date.today()

  # Group readings by station (using station_name or station_code key)
  by_station: dict[str, list[dict]] = {}
  for r in readings:
    key = (r.get("station_name") or r.get("station_code") or "").strip()
    if not key:
      continue
    d_str = (r.get("reading_date") or "")[:10]
    if not d_str:
      continue
    # Only consider readings up to today for backfill base
    if d_str > today_str:
      continue
    by_station.setdefault(key, []).append(r)

  for station_key, rows in by_station.items():
    # Sort existing rows by date
    try:
      sorted_rows = sorted(
        rows,
        key=lambda x: (x.get("reading_date") or "")[:10],
      )
    except Exception:
      sorted_rows = rows

    # Determine earliest date for this station
    first_date_str = (sorted_rows[0].get("reading_date") or "")[:10]
    if not first_date_str:
      continue
    try:
      current = datetime.fromisoformat(first_date_str).date()
    except Exception:
      continue

    # Map of existing dates -> reading dict for quick lookup
    existing_by_date: dict[str, dict] = {}
    for r in sorted_rows:
      d_str = (r.get("reading_date") or "")[:10]
      if d_str:
        existing_by_date[d_str] = r

    # Track previous WQI as we iterate the calendar
    prev_wqi: float | None = None
    inserted_count = 0

    # Use the earliest existing day's WQI as starting prev_wqi
    base_rec = existing_by_date.get(first_date_str)
    if base_rec is not None:
      try:
        prev_wqi = float(base_rec.get("wqi", 0.0))
      except (TypeError, ValueError):
        prev_wqi = 0.0

    # Loop from earliest date up to yesterday.
    # Leave "today" for simulated live generation so we can label it as simulated_live
    # (and still keep daily continuity after live generation runs).
    while current < today:
      d_str = current.isoformat()
      if d_str in existing_by_date:
        # Use this actual reading as new prev_wqi
        try:
          prev_wqi = float(existing_by_date[d_str].get("wqi", prev_wqi or 0.0))
        except (TypeError, ValueError):
          pass
      else:
        # Missing date: only backfill if we have a previous WQI to continue from
        if prev_wqi is not None:
          step = random.uniform(-2.0, 2.0)
          new_wqi = prev_wqi + step
          # Clamp between 0 and 100
          new_wqi = max(0.0, min(100.0, round(new_wqi, 1)))
          status = _wqi_to_status(new_wqi)

          # Use known names from any existing row for this station
          ref = sorted_rows[0]
          station_code = (ref.get("station_code") or station_key or "").strip() or station_key
          station_name = (ref.get("station_name") or station_key or "").strip() or station_key

          rec = append_reading(
            dataset_id=ref.get("dataset_id") or 1,
            station_code=station_code,
            station_name=station_name,
            reading_date=d_str,
            wqi=new_wqi,
            river_status=status,
            source="simulated_backfill",
            data_type="simulated_backfill",
          )
          existing_by_date[d_str] = rec
          prev_wqi = new_wqi
          inserted_count += 1
      current += timedelta(days=1)

    if inserted_count > 0:
      print(f"Backfill completed for {station_key}, total inserted: {inserted_count} records")

