"""
Dashboard controller — All data from dataset (Lampiran A - Sungai Kulim.xlsx).
Summary, time-series, forecast, stations, anomalies, dataset table. No hardcoded values.
"""
from fastapi import APIRouter, Query
from backend.db.repository import (
    get_summary,
    get_time_series,
    get_latest_forecast,
    get_stations,
    get_latest_anomalies,
    get_wqi_data,
    get_readings_table,
    get_available_years,
)

router = APIRouter()


@router.get("/summary")
def dashboard_summary():
    return get_summary()


@router.get("/time-series")
def dashboard_time_series(
    station_code: str = Query(None, description="Station name (e.g. Sungai Pinang)"),
    station_name: str = Query(None, description="Alias for station filter"),
    year: int = Query(None, description="Filter by year (2022, 2023, 2024)"),
    limit: int = Query(500, ge=1, le=2000),
):
    station = station_code or station_name
    return {"series": get_time_series(station_code=station, station_name=station, year=year, limit=limit)}


@router.get("/forecast")
def dashboard_forecast(
    station_code: str = Query(None, description="Station name for forecast"),
    limit: int = Query(30, ge=1, le=100),
):
    return {"forecast": get_latest_forecast(station_code=station_code, limit=limit)}


@router.get("/stations")
def dashboard_stations():
    return {"stations": get_stations()}


@router.get("/anomalies")
def dashboard_anomalies(
    station_code: str = Query(None, description="Station name for anomalies"),
    limit: int = Query(500, ge=1, le=2000),
):
    return {"anomalies": get_latest_anomalies(station_code=station_code, limit=limit)}


@router.get("/wqi-data")
def dashboard_wqi_data(
    station_code: str = Query(None),
    station_name: str = Query(None),
    year: int = Query(None),
    limit: int = Query(2000, ge=1, le=5000),
):
    """WQI records: Station Name, Date, WQI, River Status. Filter by station and/or year."""
    station = station_code or station_name
    return {"data": get_wqi_data(station_code=station, station_name=station, year=year, limit=limit)}


@router.get("/readings-table")
def dashboard_readings_table(
    station_name: str = Query(None, description="Filter by station name"),
    year: int = Query(None, description="Filter by year"),
    status: str = Query(None, description="Filter by river status: clean, slightly_polluted, polluted"),
    date_from: str = Query(None, description="From date YYYY-MM-DD"),
    date_to: str = Query(None, description="To date YYYY-MM-DD"),
    sort_by: str = Query("date", description="Sort by 'date' or 'wqi'"),
    sort_order: str = Query("asc", description="'asc' or 'desc'"),
    limit: int = Query(2000, ge=1, le=5000),
):
    """Dataset table: Station Name, Date, WQI, River Status. For dashboard and River Health."""
    return {
        "data": get_readings_table(
            station_name=station_name,
            year=year,
            status=status,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
        )
    }


@router.get("/years")
def dashboard_years():
    """Available years in the dataset (for filter dropdowns)."""
    return {"years": get_available_years()}
