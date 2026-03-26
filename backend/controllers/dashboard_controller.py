"""
Dashboard controller — metrics and series from the active river monitoring readings (River Monitoring Dataset on startup when present).
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
    get_readings_count,
    get_available_years,
)

router = APIRouter()


@router.get("/summary")
def dashboard_summary():
    return get_summary()


@router.get("/time-series")
def dashboard_time_series(
    station_code: str = Query(None, description="Station code or name from your monitoring data"),
    station_name: str = Query(None, description="Alias for station filter"),
    year: int = Query(None, description="Filter by year (2022, 2023, 2024)"),
    limit: int = Query(500, ge=1, le=2000),
):
    station = station_code or station_name
    from backend.db.repository import _today_str
    return {"series": get_time_series(station_code=station, station_name=station, year=year, limit=limit), "today": _today_str()}


@router.get("/forecast")
def dashboard_forecast(
    station_code: str = Query(None, description="Station name for forecast"),
    year_from: int = Query(None, description="Forecast year from (2025-2028)"),
    year_to: int = Query(None, description="Forecast year to (2025-2028)"),
    limit: int = Query(5000, ge=1, le=10000),
):
    """Forecast predictions: only dates > today. Historical data comes from time-series endpoint."""
    from backend.db.repository import _today_str
    return {"forecast": get_latest_forecast(station_code=station_code, limit=limit, year_from=year_from, year_to=year_to), "today": _today_str()}


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
    limit: int = Query(50, ge=1, le=100000),
    offset: int = Query(0, ge=0),
    data_type: str = Query(None, description="Filter by data_type: all, historical (date <= today), forecast (date > today)"),
):
    """Dataset table: Station Name, Date, WQI, River Status, data_type. data_type: all | historical | forecast."""
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
            offset=offset,
            data_type=data_type,
        )
    }


@router.get("/readings-count")
def dashboard_readings_count(
    station_name: str = Query(None),
    year: int = Query(None),
    status: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
    data_type: str = Query(None, description="all, historical, forecast"),
):
    """Total count of readings/forecast matching filters (for pagination)."""
    return {"total": get_readings_count(station_name=station_name, year=year, status=status, date_from=date_from, date_to=date_to, data_type=data_type)}


@router.get("/years")
def dashboard_years():
    """Available years in the dataset (for filter dropdowns)."""
    return {"years": get_available_years()}
