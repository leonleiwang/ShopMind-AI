# Governance 审批 API：提供审批列表、审计日志、详情、通过和拒绝操作。
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.hitl import ApprovalAuditLogResponse, ApprovalResponse, ApprovalReviewRequest
from app.services.hitl_service import ApprovalService

router = APIRouter()

# [反思5c-风险点接入HITL] 显示后台审核事项
@router.get("/", response_model=list[ApprovalResponse])
async def list_approvals(
    approval_status: str | None = Query(default=None, alias="status"),
    scope: str = Query(default="governance", pattern="^(governance|chat|all)$"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 查询审批列表，并按 governance/chat/all 分流展示。
    approvals = await ApprovalService.list_user_approvals(db, current_user.id, status=approval_status, limit=limit)
    if scope == "all":
        return approvals
    if scope == "chat":
        return [
            approval
            for approval in approvals
            if approval.action_type == ApprovalService.ORDER_ACTION
            and (approval.payload or {}).get("approval_channel") == "chat"
        ]
    return [
        approval
        for approval in approvals
        if approval.action_type != ApprovalService.ORDER_ACTION
        or (approval.payload or {}).get("approval_channel") == "governance"
    ]


@router.get("/audit", response_model=list[ApprovalAuditLogResponse])
async def list_audit_logs(
    limit: int = Query(80, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 查询当前用户审批审计日志。
    return await ApprovalService.list_audit_logs(db, current_user.id, limit=limit)


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 查询单个审批请求并限制只能访问自己的审批。
    approval = await ApprovalService.get(db, approval_id)
    if not approval or approval.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return approval


@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
async def approve_request(
    approval_id: int,
    review: ApprovalReviewRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 通过审批并执行对应业务动作，冲突状态返回 409。
    review = review or ApprovalReviewRequest()
    try:
        approval = await ApprovalService.approve(
            db,
            approval_id,
            current_user.id,
            note=review.note,
            payload_override=review.payload_override,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return approval


@router.post("/{approval_id}/reject", response_model=ApprovalResponse)
async def reject_request(
    approval_id: int,
    review: ApprovalReviewRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 拒绝审批，不执行业务动作。
    review = review or ApprovalReviewRequest()
    try:
        approval = await ApprovalService.reject(db, approval_id, current_user.id, note=review.note)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return approval
