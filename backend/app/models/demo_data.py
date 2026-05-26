from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    preferred_categories = Column(JSON, nullable=False, default=list)
    preferred_brands = Column(JSON, nullable=False, default=list)
    preferred_tags = Column(JSON, nullable=False, default=list)
    disliked_tags = Column(JSON, nullable=False, default=list)
    budget_min = Column(Float, nullable=True)
    budget_max = Column(Float, nullable=True)
    shipping_city = Column(String(80), default="")
    notes = Column(Text, default="")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AgentExecutionLog(Base):
    __tablename__ = "agent_execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    conversation_id = Column(String(80), nullable=False, index=True)
    user_message = Column(Text, nullable=False)
    intent = Column(String(40), nullable=False, index=True)
    plan = Column(JSON, nullable=False, default=list)
    tool_calls = Column(JSON, nullable=False, default=list)
    status = Column(String(30), nullable=False, default="success", index=True)
    failure_reason = Column(Text, nullable=False, default="")
    latency_ms = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
