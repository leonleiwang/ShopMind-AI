# app/services/chatbot/agents/schema.py
from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentMessage(BaseModel):
    """A2A 协议消息"""
    id: str
    from_agent: str
    to_agent: str | None = None  # None 表示广播
    type: Literal["task", "result", "error", "query"]
    payload: Any
    context: dict = Field(default_factory=dict)
