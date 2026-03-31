"""
Feedback / issue reports — public submit, admin list.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from pydantic import BaseModel, EmailStr, Field, field_validator

from backend.auth.dependencies import get_current_user, require_admin
from backend.db.repository import (
    create_feedback_report,
    list_feedback_reports,
    mark_feedback_report_read,
    delete_feedback_report,
)

router = APIRouter()

SUCCESS_MESSAGE = "Your report has been submitted successfully."


class FeedbackSubmit(BaseModel):
    name: Optional[str] = None
    email: EmailStr
    message: str = Field(..., min_length=1, max_length=8000)

    @field_validator("name", mode="before")
    @classmethod
    def empty_name_to_none(cls, v):
        if v is None:
            return None
        s = str(v).strip()
        return s or None


@router.post("")
def submit_feedback(
    body: FeedbackSubmit,
    user: Optional[dict] = Depends(get_current_user),
):
    """Anyone may submit; optional Bearer token attaches user_id."""
    try:
        uid = user["id"] if user else None
        create_feedback_report(
            email=str(body.email),
            message=body.message,
            user_id=uid,
            name=body.name,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"success": True, "message": SUCCESS_MESSAGE}


@router.get("")
def get_feedback_reports(
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    name: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    _admin: dict = Depends(require_admin),
):
    """Admin-only list of submitted reports with optional filters."""
    return {
        "reports": list_feedback_reports(
            limit=limit,
            date_from=date_from,
            date_to=date_to,
            name=name,
            email=email,
            is_read=is_read,
        )
    }


class FeedbackReadUpdate(BaseModel):
    is_read: bool = True


@router.patch("/{report_id}/read")
def update_feedback_read_status(
    report_id: int = Path(..., ge=1),
    body: FeedbackReadUpdate = FeedbackReadUpdate(),
    _admin: dict = Depends(require_admin),
):
    updated = mark_feedback_report_read(report_id, is_read=body.is_read)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return {"success": True, "report": updated}


@router.post("/{report_id}/read")
def update_feedback_read_status_post(
    report_id: int = Path(..., ge=1),
    body: FeedbackReadUpdate = FeedbackReadUpdate(),
    _admin: dict = Depends(require_admin),
):
    """
    Compatibility alias for clients/proxies that cannot send PATCH.
    """
    updated = mark_feedback_report_read(report_id, is_read=body.is_read)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return {"success": True, "report": updated}


@router.delete("/{report_id}")
def remove_feedback_report(
    report_id: int = Path(..., ge=1),
    _admin: dict = Depends(require_admin),
):
    ok = delete_feedback_report(report_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return {"success": True}
