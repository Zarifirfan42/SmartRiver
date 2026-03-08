"""
Dashboard controller — Aggregates for visualization.
Serves summary, time-series, forecast from repository (same as water-quality; alias for clarity).
"""
from fastapi import APIRouter, Query
from backend.db.repository import get_summary, get_time_series, get_latest_forecast, get_stations

router = APIRouter()


@router.get("/summary")
def dashboard_summary():
    return get_summary()


@router.get("/time-series")
def dashboard_time_series(
    station_code: str = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    return {"series": get_time_series(station_code=station_code, limit=limit)}


@router.get("/forecast")
def dashboard_forecast(limit: int = Query(30, ge=1, le=100)):
    return {"forecast": get_latest_forecast(limit=limit)}


@router.get("/stations")
def dashboard_stations():
    return {"stations": get_stations()}
