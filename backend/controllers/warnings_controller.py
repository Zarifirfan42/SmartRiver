"""Admin-posted public warnings (banner) for all authenticated users."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.auth.dependencies import require_admin
from backend.db.repository import (
    create_admin_warning,
    deactivate_admin_warning,
    list_active_admin_warnings,
    list_all_admin_warnings_admin,
)

router = APIRouter()


class AdminWarningCreate(BaseModel):
    message: str = Field(..., min_length=3, max_length=2000)


@router.get("/active")
def get_active_warnings():
    """Public (no auth): landing could use; dashboard uses with auth. Safe to expose messages only."""
    return {"items": list_active_admin_warnings()}


@router.post("/", status_code=status.HTTP_201_CREATED)
def post_admin_warning(body: AdminWarningCreate, admin: dict = Depends(require_admin)):
    try:
        row = create_admin_warning(body.message.strip(), int(admin["id"]))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return row


@router.get("/admin/list")
def list_warnings_admin(admin: dict = Depends(require_admin), limit: int = 100):
    _ = admin
    return {"items": list_all_admin_warnings_admin(limit=limit)}


@router.patch("/{warning_id}/deactivate")
def deactivate_warning(warning_id: int, admin: dict = Depends(require_admin)):
    _ = admin
    if not deactivate_admin_warning(warning_id):
        raise HTTPException(status_code=404, detail="Warning not found")
    return {"ok": True}
