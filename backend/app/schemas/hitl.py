from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ApprovalStatus = Literal["pending", "approved", "rejected", "executed", "expired"]


class ApprovalResponse(BaseModel):
    id: int
    user_id: int
    action_type: str
    status: ApprovalStatus
    risk_level: str
    risk_reasons: list[str] = []
    summary: str
    payload: dict[str, Any] = {}
    result: dict[str, Any] = {}
    created_at: datetime | None = None
    reviewed_at: datetime | None = None

    class Config:
        from_attributes = True


class ApprovalReviewRequest(BaseModel):
    note: str = ""
    payload_override: dict[str, Any] | None = Field(
        default=None,
        description="Optional edited draft payload before approving merchant AI operations.",
    )


class ApprovalAuditLogResponse(BaseModel):
    id: int
    approval_id: int
    user_id: int
    event: str
    details: dict[str, Any] = {}
    created_at: datetime | None = None

    class Config:
        from_attributes = True
