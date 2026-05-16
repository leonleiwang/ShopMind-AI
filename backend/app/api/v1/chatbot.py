"""
聊天 API 接口（SSE 流式）Chat API 现在支持 conversation_id，SSE 断链/异常时会返回降级消息，而不是直接炸给用户
"""

# backend/app/api/v1/chatbot.py
import json

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_current_user
from app.db.session import get_db
from app.services.chatbot.chat_service import ChatService
from app.services.observability import AgentObservability

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None

@router.post("/stream")
async def chatbot_stream(
    chat_input: ChatRequest,
    request: Request,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    async def event_generator():
        service = ChatService(db, current_user.id, chat_input.conversation_id)
        try:
            async for event in service.process_message(chat_input.message):
                if await request.is_disconnected():
                    break
                yield event
        except Exception:
            yield {
                "event": "final",
                "data": json.dumps(
                    {
                        "content": "当前智能客服链路繁忙，我先为你保留上下文。请稍后重试或转人工处理。",
                        "degraded": True,
                    },
                    ensure_ascii=False,
                ),
            }
    return EventSourceResponse(event_generator())


@router.get("/metrics")
async def chatbot_metrics(current_user = Depends(get_current_user)):
    return AgentObservability.snapshot()
