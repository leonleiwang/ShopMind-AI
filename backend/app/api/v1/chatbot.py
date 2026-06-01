# Chat API：提供 SSE 流式对话、conversation_id 延续和 AgentOps 指标快照。
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
    # 前端提交的用户消息和可选会话 id。
    message: str
    conversation_id: str | None = None

@router.post("/stream")
async def chatbot_stream(
    chat_input: ChatRequest,
    request: Request,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # SSE 主入口：逐步返回 intent/action/observation/final 等 Agent 事件。
    async def event_generator():
        # 断开连接或异常时优雅结束，并返回可读降级消息。
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
    # 返回对话链路观测快照，供工程观测页展示。
    return AgentObservability.snapshot()
