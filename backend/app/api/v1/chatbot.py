"""
聊天 API 接口（SSE 流式）
"""

# backend/app/api/v1/chatbot.py
import json
import asyncio
from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.db.session import get_db
from app.services.chatbot.chat_service import ChatService
from app.services.observability import AgentObservability

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@router.post("/stream")
async def chatbot_stream(
    chat_input: ChatRequest,
    request: Request,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    async def event_generator():
        service = ChatService(db, current_user.id)
        async for event in service.process_message(chat_input.message):
            if await request.is_disconnected():
                break
            yield event
    return EventSourceResponse(event_generator())


@router.get("/metrics")
async def chatbot_metrics(current_user = Depends(get_current_user)):
    return AgentObservability.snapshot()
