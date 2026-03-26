"""
Feedback / issue reports — public submit, admin list.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator

from backend.auth.dependencies import get_current_user, require_admin
from backend.db.repository import create_feedback_report, list_feedback_reports

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
def get_feedback_reports(_admin: dict = Depends(require_admin)):
    """Admin-only list of all submitted reports."""
    return {"reports": list_feedback_reports(limit=500)}
