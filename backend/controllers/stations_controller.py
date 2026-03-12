"""
Stations controller — CRUD for river stations. Admin only for create/update/delete.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.auth.dependencies import require_admin, get_current_user
from backend.db.repository import (
    get_stations,
    create_station,
    update_station,
    delete_station,
    list_stations_admin,
)

router = APIRouter()


class StationCreate(BaseModel):
    station_code: str
    station_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    river_name: str | None = None
    state: str | None = None


class StationUpdate(BaseModel):
    station_code: str | None = None
    station_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    river_name: str | None = None
    state: str | None = None


@router.get("/")
def list_stations(user: dict | None = Depends(get_current_user)):
    """List stations with latest WQI (public)."""
    return {"stations": get_stations()}


@router.get("/admin")
def list_stations_admin_route(current_user: dict = Depends(require_admin)):
    """List all stations for admin management."""
    return {"stations": list_stations_admin()}


@router.post("/")
def create_station_route(
    body: StationCreate,
    current_user: dict = Depends(require_admin),
):
    """Create a new station. Admin only."""
    try:
        station = create_station(
            station_code=body.station_code,
            station_name=body.station_name,
            latitude=body.latitude,
            longitude=body.longitude,
            river_name=body.river_name,
            state=body.state,
        )
        return station
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{station_id}")
def update_station_route(
    station_id: int,
    body: StationUpdate,
    current_user: dict = Depends(require_admin),
):
    """Update a station. Admin only."""
    updated = update_station(
        station_id,
        station_code=body.station_code,
        station_name=body.station_name,
        latitude=body.latitude,
        longitude=body.longitude,
        river_name=body.river_name,
        state=body.state,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Station not found")
    return updated


@router.delete("/{station_id}")
def delete_station_route(
    station_id: int,
    current_user: dict = Depends(require_admin),
):
    """Delete a station. Admin only."""
    if not delete_station(station_id):
        raise HTTPException(status_code=404, detail="Station not found")
    return {"message": "Station deleted"}
