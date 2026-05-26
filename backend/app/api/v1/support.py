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
    return user.role in {"support", "admin"} or bool(user.is_superuser)


def _can_view_ticket(user: User, customer_id: int) -> bool:
    return _is_support_user(user) or user.id == customer_id


@router.get("/tickets", response_model=list[SupportTicketResponse])
async def list_tickets(
    ticket_status: str | None = Query(default=None, alias="status"),
    risk_level: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    if not _is_support_user(current_user):
        raise HTTPException(status_code=403, detail="Only support users can view agent assist records")
    return await SupportTicketService.latest_ai_assist(db, conversation_id)
