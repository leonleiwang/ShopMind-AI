from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


TicketStatus = Literal["open", "pending", "resolved", "escalated"]
TicketPriority = Literal["low", "normal", "high", "urgent"]
RiskLevel = Literal["low", "medium", "high"]


class SupportTicketCreate(BaseModel):
    customer_id: int | None = None
    conversation_id: str = ""
    category: str = "general"
    priority: TicketPriority = "normal"
    status: TicketStatus = "open"
    assigned_agent: str = ""
    summary: str
    channel: str = "web"
    order_id: int | None = None
    risk_level: RiskLevel = "low"
    handoff_reason: str = ""
    resolution: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class SupportTicketUpdate(BaseModel):
    category: str | None = None
    priority: TicketPriority | None = None
    status: TicketStatus | None = None
    assigned_agent: str | None = None
    summary: str | None = None
    risk_level: RiskLevel | None = None
    handoff_reason: str | None = None
    resolution: str | None = None
    metadata: dict[str, Any] | None = None


class TicketEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    actor_id: int | None = None
    event_type: str
    from_status: str = ""
    to_status: str = ""
    details: dict[str, Any] = {}
    created_at: datetime | None = None


class SupportTicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: str
    customer_id: int
    conversation_id: str = ""
    category: str
    priority: str
    status: str
    assigned_agent: str = ""
    summary: str
    channel: str = "web"
    order_id: int | None = None
    risk_level: str = "low"
    handoff_reason: str = ""
    resolution: str = ""
    metadata: dict[str, Any] = {}
    sla_deadline: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class HandoffEvaluationRequest(BaseModel):
    message: str
    conversation_id: str = ""
    intent: str = "unknown"
    confidence: float = 0.0
    tool_failed: bool = False
    unresolved_turns: int = 0
    category: str | None = None
    order_id: int | None = None
    channel: str = "chat"
    create_ticket: bool = True


class HandoffEvaluationResponse(BaseModel):
    should_handoff: bool
    reasons: list[str]
    priority: TicketPriority
    risk_level: RiskLevel
    category: str
    routing_strategy: str
    ticket: SupportTicketResponse | None = None


class TicketAIAssistCreate(BaseModel):
    conversation_id: str = ""
    intent: str = ""
    user_intent: str = ""
    recommended_reply: str = ""
    knowledge_refs: list[dict[str, Any]] = Field(default_factory=list)
    order_snapshot: dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = "low"
    next_best_action: str = ""
    ai_confidence: float = 0.0
    routing_strategy: str = "rag"
    llm_cost: float = 0.0
    token_usage: dict[str, Any] = Field(default_factory=dict)


class TicketAIAssistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    conversation_id: str = ""
    intent: str = ""
    user_intent: str = ""
    recommended_reply: str = ""
    knowledge_refs: list[dict[str, Any]] = []
    order_snapshot: dict[str, Any] = {}
    risk_level: str = "low"
    next_best_action: str = ""
    ai_confidence: float = 0.0
    routing_strategy: str = "rag"
    llm_cost: float = 0.0
    token_usage: dict[str, Any] = {}
    created_at: datetime | None = None
