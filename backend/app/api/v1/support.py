# 客服联络中心 API：提供工单列表/详情/状态流转、转人工评估、AI Assist 生成和会话辅助查询。
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.support import (
    HandoffEvaluationRequest,
    HandoffEvaluationResponse,
    SupportTicketCreate,
    SupportTicketResponse,
    SupportTicketUpdate,
    TicketAIAssistCreate,
    TicketAIAssistResponse,
    TicketEventResponse,
)
from app.services.support_service import HumanHandoffService, SupportTicketService

router = APIRouter()


def _is_support_user(user: User) -> bool:
    # support/admin/superuser 拥有客服控制台权限。
    return user.role in {"support", "admin"} or bool(user.is_superuser)


def _can_view_ticket(user: User, customer_id: int) -> bool:
    # 客服可看全部工单，普通用户只能看自己的工单。
    return _is_support_user(user) or user.id == customer_id


@router.get("/tickets", response_model=list[SupportTicketResponse])
async def list_tickets(
    ticket_status: str | None = Query(default=None, alias="status"),
    risk_level: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 工单列表接口，普通用户自动限制为自己的 customer_id。
    customer_id = None if _is_support_user(current_user) else current_user.id
    tickets = await SupportTicketService.list_tickets(
        db,
        customer_id=customer_id,
        status=ticket_status,
        risk_level=risk_level,
        limit=limit,
    )
    return [SupportTicketService.serialize_ticket(ticket) for ticket in tickets]


@router.post("/tickets", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: SupportTicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 创建客服工单，非客服用户不能替其他客户创建。
    if payload.customer_id and payload.customer_id != current_user.id and not _is_support_user(current_user):
        raise HTTPException(status_code=403, detail="Only support users can create tickets for another customer")
    ticket = await SupportTicketService.create_ticket(db, payload, actor_id=current_user.id)
    return SupportTicketService.serialize_ticket(ticket)


@router.get("/tickets/{ticket_pk}", response_model=SupportTicketResponse)
async def get_ticket(
    ticket_pk: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 查询单个工单并做访问控制。
    ticket = await SupportTicketService.get_ticket(db, ticket_pk)
    if not ticket or not _can_view_ticket(current_user, ticket.customer_id):
        raise HTTPException(status_code=404, detail="Ticket not found")
    return SupportTicketService.serialize_ticket(ticket)


@router.patch("/tickets/{ticket_pk}", response_model=SupportTicketResponse)
async def update_ticket(
    ticket_pk: int,
    payload: SupportTicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 客服侧更新工单状态、分配人、解决方案等字段。
    if not _is_support_user(current_user):
        raise HTTPException(status_code=403, detail="Only support users can update tickets")
    ticket = await SupportTicketService.get_ticket(db, ticket_pk)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    updated = await SupportTicketService.update_ticket(db, ticket, payload, actor_id=current_user.id)
    return SupportTicketService.serialize_ticket(updated)


@router.get("/tickets/{ticket_pk}/events", response_model=list[TicketEventResponse])
async def list_ticket_events(
    ticket_pk: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 查询工单事件时间线，用于审计和交接。
    ticket = await SupportTicketService.get_ticket(db, ticket_pk)
    if not ticket or not _can_view_ticket(current_user, ticket.customer_id):
        raise HTTPException(status_code=404, detail="Ticket not found")
    return await SupportTicketService.list_events(db, ticket_pk)


@router.post("/handoff/evaluate", response_model=HandoffEvaluationResponse)
async def evaluate_handoff(
    payload: HandoffEvaluationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 转人工评估接口，可按需自动创建升级工单和 AI Assist。
    evaluation = HumanHandoffService.evaluate(payload)
    ticket_payload = None
    if evaluation["should_handoff"] and payload.create_ticket:
        ticket, _ = await SupportTicketService.create_from_handoff(
            db,
            customer_id=current_user.id,
            actor_id=current_user.id,
            request=payload,
            evaluation=evaluation,
        )
        ticket_payload = SupportTicketService.serialize_ticket(ticket)
    return {**evaluation, "ticket": ticket_payload}


@router.post("/tickets/{ticket_pk}/ai-assists", response_model=TicketAIAssistResponse, status_code=status.HTTP_201_CREATED)
async def create_ai_assist(
    ticket_pk: int,
    payload: TicketAIAssistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 手动写入 AI Assist 记录，供客服系统集成或测试使用。
    if not _is_support_user(current_user):
        raise HTTPException(status_code=403, detail="Only support users can create AI assist records")
    ticket = await SupportTicketService.get_ticket(db, ticket_pk)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return await SupportTicketService.create_ai_assist(db, ticket_pk, payload)


@router.post(
    "/tickets/{ticket_pk}/ai-assists/generate",
    response_model=TicketAIAssistResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_ai_assist(
    ticket_pk: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 根据现有工单自动生成 AI Assist 建议。
    if not _is_support_user(current_user):
        raise HTTPException(status_code=403, detail="Only support users can generate AI assist records")
    ticket = await SupportTicketService.get_ticket(db, ticket_pk)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return await SupportTicketService.generate_ai_assist_for_ticket(db, ticket)


@router.get("/conversations/{conversation_id}/agent-assist", response_model=TicketAIAssistResponse | None)
async def get_agent_assist(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 按会话 id 获取最近一次 AI Assist，方便客服接入聊天上下文。
    if not _is_support_user(current_user):
        raise HTTPException(status_code=403, detail="Only support users can view agent assist records")
    return await SupportTicketService.latest_ai_assist(db, conversation_id)
