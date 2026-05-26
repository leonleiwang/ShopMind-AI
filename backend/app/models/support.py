from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base import Base
from app.models.order import Order  # noqa: F401 - ensure FK target is registered
from app.models.user import User  # noqa: F401 - ensure FK target is registered


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(40), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    conversation_id = Column(String(80), nullable=False, default="", index=True)
    channel = Column(String(40), nullable=False, default="web", index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True)
    category = Column(String(40), nullable=False, index=True)
    priority = Column(String(20), nullable=False, default="normal", index=True)
    status = Column(String(20), nullable=False, default="open", index=True)
    assigned_agent = Column(String(100), nullable=False, default="", index=True)
    subject = Column(String(255), nullable=False, default="")
    description = Column(Text, nullable=False, default="")
    summary = Column(Text, nullable=False, default="")
    risk_level = Column(String(20), nullable=False, default="low", index=True)
    handoff_reason = Column(Text, nullable=False, default="")
    resolution = Column(Text, nullable=False, default="")
    details = Column("metadata", JSON, nullable=False, default=dict)
    sla_deadline = Column(DateTime(timezone=True), nullable=True, index=True)
    closed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TicketEvent(Base):
    __tablename__ = "ticket_events"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    event_type = Column(String(40), nullable=False, index=True)
    from_status = Column(String(20), nullable=False, default="")
    to_status = Column(String(20), nullable=False, default="")
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TicketAIAssist(Base):
    __tablename__ = "ticket_ai_assists"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False, index=True)
    conversation_id = Column(String(80), nullable=False, default="", index=True)
    intent = Column(String(60), nullable=False, default="", index=True)
    user_intent = Column(Text, nullable=False, default="")
    recommended_reply = Column(Text, nullable=False, default="")
    knowledge_refs = Column(JSON, nullable=False, default=list)
    order_snapshot = Column(JSON, nullable=False, default=dict)
    risk_level = Column(String(20), nullable=False, default="low", index=True)
    next_best_action = Column(Text, nullable=False, default="")
    ai_confidence = Column(Float, nullable=False, default=0.0)
    routing_strategy = Column(String(40), nullable=False, default="rag", index=True)
    llm_cost = Column(Float, nullable=False, default=0.0)
    token_usage = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
