# 客服联络中心服务：负责转人工判定、AI 坐席辅助、工单生命周期、SLA、事件日志和订单快照。
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.order import Order
from app.models.support import SupportTicket, TicketAIAssist, TicketEvent
from app.schemas.support import HandoffEvaluationRequest, SupportTicketCreate, SupportTicketUpdate, TicketAIAssistCreate


VALID_STATUSES = {"open", "pending", "resolved", "escalated"}
HIGH_RISK_CATEGORIES = {"refund", "complaint", "legal", "chargeback"}


class LLMRoutingService:
    @staticmethod
    def route(
        *,
        intent: str,
        category: str = "general",
        risk_level: str = "low",
        confidence: float = 1.0,
        message: str = "",
    ) -> str:
        # 根据意图、风险、类别和置信度选择 RAG、SQL cache、Agent workflow 或人工接管。
        text = message.lower()
        if risk_level == "high" or category in {"complaint", "legal", "chargeback"}:
            return "human_handoff"
        if category == "refund" or intent in {"refund_request", "after_sales"}:
            return "agent_workflow"
        if intent in {"order_query", "order_status"} or any(term in text for term in ["order status", "物流", "快递"]):
            return "sql_cache"
        if intent in {"faq", "policy"} or any(term in text for term in ["policy", "faq", "规则", "政策"]):
            return "rag"
        if confidence < settings.HITL_INTENT_CONFIDENCE_THRESHOLD:
            return "agent_workflow"
        return "rag"


class HumanHandoffService:
    # 风险词与类别词用于确定性转人工评估，保证无模型环境下也能稳定运行。
    NEGATIVE_TERMS = {
        "angry",
        "terrible",
        "投诉",
        "差评",
        "生气",
        "愤怒",
        "垃圾",
        "欺骗",
        "骗子",
    }
    RISK_TERMS = {
        "refund": "refund",
        "退款": "refund",
        "complaint": "complaint",
        "投诉": "complaint",
        "lawyer": "legal",
        "legal": "legal",
        "法院": "legal",
        "律师": "legal",
        "起诉": "legal",
    }

    @classmethod
    def evaluate(cls, request: HandoffEvaluationRequest) -> dict[str, Any]:
        # 转人工核心评估：沉淀 reasons、risk_level、priority 和 routing_strategy。
        reasons: list[str] = []
        message = request.message.lower()
        category = request.category or cls.detect_category(request.message)
        risk_level = "low"

        if request.confidence < settings.HITL_INTENT_CONFIDENCE_THRESHOLD:
            reasons.append("low_confidence")
        if any(term in request.message or term in message for term in cls.NEGATIVE_TERMS):
            reasons.append("negative_sentiment")
            risk_level = "medium"
        if category in HIGH_RISK_CATEGORIES:
            reasons.append(f"{category}_risk")
            risk_level = "high" if category in {"complaint", "legal", "chargeback"} else "medium"
        if request.tool_failed:
            reasons.append("tool_failed")
            risk_level = "medium" if risk_level == "low" else risk_level
        if request.unresolved_turns >= 2:
            reasons.append("repeated_unresolved_followup")
            risk_level = "medium" if risk_level == "low" else risk_level

        should_handoff = bool(reasons)
        priority = cls.priority_for(risk_level, reasons)
        routing_strategy = LLMRoutingService.route(
            intent=request.intent,
            category=category,
            risk_level=risk_level,
            confidence=request.confidence,
            message=request.message,
        )
        if routing_strategy == "human_handoff":
            should_handoff = True

        return {
            "should_handoff": should_handoff,
            "reasons": reasons,
            "priority": priority,
            "risk_level": risk_level,
            "category": category,
            "routing_strategy": routing_strategy,
        }

    @classmethod
    def detect_category(cls, message: str) -> str:
        # 从用户消息中识别退款、投诉、法务、物流等客服工单类别。
        lower_message = message.lower()
        for term, category in cls.RISK_TERMS.items():
            if term in message or term in lower_message:
                return category
        if "invoice" in lower_message or "发票" in message:
            return "invoice"
        if "shipping" in lower_message or "物流" in message or "快递" in message:
            return "shipping"
        return "general"

    @staticmethod
    def priority_for(risk_level: str, reasons: list[str]) -> str:
        # 根据风险等级和原因映射客服优先级，供 SLA 和队列排序使用。
        if risk_level == "high" or "legal_risk" in reasons or "complaint_risk" in reasons:
            return "urgent"
        if risk_level == "medium" or reasons:
            return "high"
        return "normal"


class AgentAssistService:
    @staticmethod
    def build_assist(
        *,
        message: str,
        intent: str,
        confidence: float,
        category: str,
        risk_level: str,
        routing_strategy: str,
        order_snapshot: dict[str, Any] | None = None,
    ) -> TicketAIAssistCreate:
        # 构建坐席辅助卡片：推荐回复、知识引用、下一步动作、风险与路由策略。
        refs = AgentAssistService.knowledge_refs_for(category)
        reply = AgentAssistService.recommended_reply_for(category, risk_level)
        return TicketAIAssistCreate(
            intent=intent,
            user_intent=message[:500],
            recommended_reply=reply,
            knowledge_refs=refs,
            order_snapshot=order_snapshot or {},
            risk_level=risk_level,
            next_best_action=AgentAssistService.next_action_for(category, risk_level),
            ai_confidence=confidence,
            routing_strategy=routing_strategy,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "source": "deterministic_v1"},
        )

    @staticmethod
    def knowledge_refs_for(category: str) -> list[dict[str, Any]]:
        # 按工单类别返回可解释知识来源，模拟 RAG evidence refs。
        refs = {
            "refund": [{"title": "Refund policy", "source": "policy_rag", "section": "after_sales.refund"}],
            "complaint": [{"title": "Complaint escalation SOP", "source": "support_playbook", "section": "risk"}],
            "legal": [{"title": "Legal risk handoff", "source": "support_playbook", "section": "legal"}],
            "shipping": [{"title": "Shipping delay FAQ", "source": "policy_rag", "section": "logistics"}],
        }
        return refs.get(category, [{"title": "General support FAQ", "source": "policy_rag", "section": "general"}])

    @staticmethod
    def recommended_reply_for(category: str, risk_level: str) -> str:
        # 生成客服建议话术，高风险场景避免自动承诺赔付或法律结论。
        if risk_level == "high":
            return "我先为你记录问题并转交人工客服继续处理，避免智能客服在高风险场景中过度承诺。"
        if category == "refund":
            return "我会先核对订单和退款政策，再为你创建售后工单，客服会继续确认可退款范围。"
        if category == "shipping":
            return "我会先核对订单物流状态，并把异常节点同步给客服坐席。"
        return "我已经保留上下文，客服会根据订单、政策和会话摘要继续处理。"

    @staticmethod
    def next_action_for(category: str, risk_level: str) -> str:
        # 根据类别和风险给坐席一个下一步处理动作。
        if risk_level == "high":
            return "Assign to senior support and avoid monetary or legal commitments."
        if category == "refund":
            return "Check order status, refund eligibility, and customer expectation."
        if category == "shipping":
            return "Check shipment timeline and carrier exception code."
        return "Review conversation summary and confirm the user's desired outcome."

    @staticmethod
    def intent_for_category(category: str) -> str:
        # 将客服类别映射成 AI Assist 的业务意图字段。
        return {
            "refund": "refund_request",
            "complaint": "complaint_escalation",
            "legal": "legal_risk",
            "shipping": "shipping_exception",
            "invoice": "invoice_request",
        }.get(category, "support_request")


class SupportTicketService:
    @staticmethod
    async def create_ticket(
        db: AsyncSession,
        payload: SupportTicketCreate,
        actor_id: int,
    ) -> SupportTicket:
        # 手动创建工单入口：生成 ticket_id、SLA、初始事件和可选 AI Assist。
        customer_id = payload.customer_id or actor_id
        ticket = SupportTicket(
            ticket_id=SupportTicketService.new_ticket_id(),
            user_id=customer_id,
            customer_id=customer_id,
            conversation_id=payload.conversation_id,
            channel=payload.channel,
            order_id=payload.order_id,
            category=payload.category,
            priority=payload.priority,
            status=payload.status,
            assigned_agent=payload.assigned_agent,
            subject=payload.summary[:255],
            description=payload.summary,
            summary=payload.summary,
            risk_level=payload.risk_level,
            handoff_reason=payload.handoff_reason,
            resolution=payload.resolution,
            details=payload.metadata,
            sla_deadline=SupportTicketService.sla_deadline(payload.priority, payload.risk_level),
            closed_at=datetime.now(timezone.utc) if payload.status == "resolved" else None,
        )
        db.add(ticket)
        await db.flush()
        await SupportTicketService.add_event(
            db,
            ticket.id,
            actor_id,
            "created",
            to_status=ticket.status,
            details={"priority": ticket.priority, "category": ticket.category, "channel": ticket.channel},
        )
        await db.commit()
        await db.refresh(ticket)
        return ticket

    @staticmethod
    async def create_from_handoff(
        db: AsyncSession,
        *,
        customer_id: int,
        actor_id: int,
        request: HandoffEvaluationRequest,
        evaluation: dict[str, Any],
    ) -> tuple[SupportTicket, TicketAIAssist]:
        # 从 Chat 转人工结果自动创建升级工单，并同步生成 AI Assist 建议。
        summary = SupportTicketService.summary_for_handoff(request.message, evaluation["reasons"])
        ticket = await SupportTicketService.create_ticket(
            db,
            SupportTicketCreate(
                customer_id=customer_id,
                conversation_id=request.conversation_id,
                category=evaluation["category"],
                priority=evaluation["priority"],
                status="escalated",
                summary=summary,
                channel=request.channel,
                order_id=request.order_id,
                risk_level=evaluation["risk_level"],
                handoff_reason=", ".join(evaluation["reasons"]),
                metadata={"intent": request.intent, "confidence": request.confidence},
            ),
            actor_id=actor_id,
        )
        assist = AgentAssistService.build_assist(
            message=request.message,
            intent=request.intent,
            confidence=request.confidence,
            category=evaluation["category"],
            risk_level=evaluation["risk_level"],
            routing_strategy=evaluation["routing_strategy"],
            order_snapshot=await SupportTicketService.order_snapshot(db, request.order_id),
        )
        assist.conversation_id = request.conversation_id
        ai_assist = await SupportTicketService.create_ai_assist(db, ticket.id, assist)
        await SupportTicketService.add_event(
            db,
            ticket.id,
            actor_id,
            "human_handoff",
            from_status="open",
            to_status="escalated",
            details={"reasons": evaluation["reasons"], "routing_strategy": evaluation["routing_strategy"]},
            commit=True,
        )
        return ticket, ai_assist

    @staticmethod
    async def update_ticket(
        db: AsyncSession,
        ticket: SupportTicket,
        payload: SupportTicketUpdate,
        actor_id: int,
    ) -> SupportTicket:
        # 更新工单状态和字段，同时写入状态流转/更新事件。
        before_status = ticket.status
        data = payload.model_dump(exclude_unset=True)
        metadata_value = data.pop("metadata", None)
        for key, value in data.items():
            setattr(ticket, key, value)
            if key == "summary" and value:
                ticket.subject = value[:255]
                ticket.description = value
        if metadata_value is not None:
            ticket.details = metadata_value
        if ticket.status == "resolved" and not ticket.closed_at:
            ticket.closed_at = datetime.now(timezone.utc)
        if ticket.status != "resolved":
            ticket.closed_at = None
        await SupportTicketService.add_event(
            db,
            ticket.id,
            actor_id,
            "updated" if before_status == ticket.status else "status_changed",
            from_status=before_status,
            to_status=ticket.status,
            details=data,
        )
        await db.commit()
        await db.refresh(ticket)
        return ticket

    @staticmethod
    async def list_tickets(
        db: AsyncSession,
        *,
        customer_id: int | None = None,
        status: str | None = None,
        risk_level: str | None = None,
        limit: int = 50,
    ) -> list[SupportTicket]:
        # 按客户、状态和风险过滤工单，支撑客服控制台列表。
        query = select(SupportTicket).order_by(SupportTicket.created_at.desc()).limit(limit)
        if customer_id:
            query = query.where(SupportTicket.customer_id == customer_id)
        if status:
            query = query.where(SupportTicket.status == status)
        if risk_level:
            query = query.where(SupportTicket.risk_level == risk_level)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_ticket(db: AsyncSession, ticket_pk: int) -> SupportTicket | None:
        # 通过内部主键读取单个工单。
        result = await db.execute(select(SupportTicket).where(SupportTicket.id == ticket_pk))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_events(db: AsyncSession, ticket_pk: int) -> list[TicketEvent]:
        # 返回工单操作日志，支持审计和客服交接。
        result = await db.execute(
            select(TicketEvent).where(TicketEvent.ticket_id == ticket_pk).order_by(TicketEvent.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_ai_assist(
        db: AsyncSession,
        ticket_pk: int,
        payload: TicketAIAssistCreate,
    ) -> TicketAIAssist:
        # 写入 AI 坐席辅助结果，并追加 ai_assist_generated 事件。
        assist = TicketAIAssist(ticket_id=ticket_pk, **payload.model_dump())
        db.add(assist)
        await db.flush()
        await SupportTicketService.add_event(
            db,
            ticket_pk,
            None,
            "ai_assist_generated",
            details={"intent": payload.intent, "routing_strategy": payload.routing_strategy},
        )
        await db.commit()
        await db.refresh(assist)
        return assist

    @staticmethod
    async def generate_ai_assist_for_ticket(db: AsyncSession, ticket: SupportTicket) -> TicketAIAssist:
        # 根据现有工单重新生成 AI Assist，用于客服手动刷新建议。
        order_snapshot = await SupportTicketService.order_snapshot(db, ticket.order_id)
        confidence = float((ticket.details or {}).get("confidence") or 0.82)
        intent = str((ticket.details or {}).get("intent") or AgentAssistService.intent_for_category(ticket.category))
        routing_strategy = LLMRoutingService.route(
            intent=intent,
            category=ticket.category,
            risk_level=ticket.risk_level,
            confidence=confidence,
            message=ticket.summary or ticket.description,
        )
        assist = AgentAssistService.build_assist(
            message=ticket.summary or ticket.description,
            intent=intent,
            confidence=confidence,
            category=ticket.category,
            risk_level=ticket.risk_level,
            routing_strategy=routing_strategy,
            order_snapshot=order_snapshot,
        )
        assist.conversation_id = ticket.conversation_id
        return await SupportTicketService.create_ai_assist(db, ticket.id, assist)

    @staticmethod
    async def latest_ai_assist(db: AsyncSession, conversation_id: str) -> TicketAIAssist | None:
        # 按 conversation_id 获取最近一次 AI Assist，供 Chat/客服侧复用。
        result = await db.execute(
            select(TicketAIAssist)
            .where(TicketAIAssist.conversation_id == conversation_id)
            .order_by(TicketAIAssist.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def add_event(
        db: AsyncSession,
        ticket_pk: int,
        actor_id: int | None,
        event_type: str,
        *,
        from_status: str = "",
        to_status: str = "",
        details: dict[str, Any] | None = None,
        commit: bool = False,
    ) -> TicketEvent:
        # 统一写入工单事件日志，可选择立即提交或跟随外层事务提交。
        event = TicketEvent(
            ticket_id=ticket_pk,
            actor_id=actor_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            details=details or {},
        )
        db.add(event)
        if commit:
            await db.commit()
            await db.refresh(event)
        return event

    @staticmethod
    async def order_snapshot(db: AsyncSession, order_id: int | None) -> dict[str, Any]:
        # 为 AI Assist 提供轻量订单快照，避免直接暴露完整订单对象。
        if not order_id:
            return {}
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if not order:
            return {}
        return {"order_id": order.id, "status": order.status, "total_amount": order.total_amount}

    @staticmethod
    def serialize_ticket(ticket: SupportTicket) -> dict[str, Any]:
        # 工单序列化出口，保证 API 和 Chat handoff 返回字段一致。
        return {
            "id": ticket.id,
            "ticket_id": ticket.ticket_id,
            "customer_id": ticket.customer_id,
            "conversation_id": ticket.conversation_id,
            "category": ticket.category,
            "priority": ticket.priority,
            "status": ticket.status,
            "assigned_agent": ticket.assigned_agent,
            "summary": ticket.summary or ticket.subject,
            "channel": ticket.channel,
            "order_id": ticket.order_id,
            "risk_level": ticket.risk_level,
            "handoff_reason": ticket.handoff_reason,
            "resolution": ticket.resolution,
            "metadata": ticket.details or {},
            "sla_deadline": ticket.sla_deadline,
            "closed_at": ticket.closed_at,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
        }

    @staticmethod
    def new_ticket_id() -> str:
        # 生成客服可读 ticket id，包含日期和短随机后缀。
        return f"TCK-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    @staticmethod
    def sla_deadline(priority: str, risk_level: str) -> datetime:
        # 根据优先级和风险等级计算 SLA 截止时间。
        hours = 24
        if priority == "urgent" or risk_level == "high":
            hours = 2
        elif priority == "high" or risk_level == "medium":
            hours = 8
        elif priority == "low":
            hours = 48
        return datetime.now(timezone.utc) + timedelta(hours=hours)

    @staticmethod
    def summary_for_handoff(message: str, reasons: list[str]) -> str:
        # 转人工工单摘要，保留触发原因和用户原始问题片段。
        reason_text = ", ".join(reasons) if reasons else "manual_review"
        return f"Human handoff required ({reason_text}): {message[:220]}"
