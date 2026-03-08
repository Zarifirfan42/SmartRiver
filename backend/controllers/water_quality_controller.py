"""
Water quality controller — HTTP endpoints for water quality data.
Serves dashboard: summary, time-series, stations from repository.
"""
from fastapi import APIRouter, Query
from backend.db.repository import get_summary, get_time_series, get_stations

router = APIRouter()


@router.get("/summary")
def get_dashboard_summary():
    """Dashboard summary: total stations, avg WQI, clean/polluted counts."""
    return get_summary()


@router.get("/time-series")
def get_wqi_time_series(
    station_code: str = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """WQI time series for charts."""
    return {"series": get_time_series(station_code=station_code, limit=limit)}


@router.get("/forecast")
def get_forecast(limit: int = Query(30, ge=1, le=100)):
    """Latest forecast from prediction_logs."""
    from backend.db.repository import get_latest_forecast
    return {"forecast": get_latest_forecast(limit=limit)}


@router.get("/stations")
def list_stations():
    """Stations with latest WQI and status."""
    return {"stations": get_stations()}
