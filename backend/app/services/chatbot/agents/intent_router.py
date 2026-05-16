"""
意图路由 Agent
"""

# backend/app/services/chatbot/agents/intent_router.py
import json
from dataclasses import dataclass, field

from app.core.llm_gateway import llm_gateway
from app.services.chatbot.knowledge_base import BusinessKnowledgeRetriever
from app.services.chatbot.prompts import prompt_manager


@dataclass
class RouteDecision:
    """[反思1b-有依据路由] 路由结果必须携带置信度、依据和缺失槽位。"""

    intent: str
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
    required_slots: list[str] = field(default_factory=list)

class IntentRouterAgent:
    def __init__(self, tool_schemas: list[dict] | None = None):
        self.llm = llm_gateway
        self.tool_schemas = tool_schemas or []
        self.knowledge = BusinessKnowledgeRetriever()

    async def route(self, user_message: str) -> str:
        return (await self.route_decision(user_message)).intent

    async def route_decision(self, user_message: str) -> RouteDecision:
        deterministic_intent = self._route_by_keywords(user_message)
        if deterministic_intent:
            return RouteDecision(
                intent=deterministic_intent,
                confidence=0.86,
                evidence=["keyword_rule", f"matched intent {deterministic_intent}"],
            )

        fallback = json.dumps(
            {
                "intent": "clarify" if self._looks_ambiguous(user_message) else "unknown",
                "confidence": 0.35,
                "evidence": ["llm_gateway_fallback"],
                "required_slots": ["business_domain"] if self._looks_ambiguous(user_message) else [],
            },
            ensure_ascii=False,
        )
        prompt = prompt_manager.render(
            "intent_router",
            business_context=json.dumps(self.knowledge.retrieve(user_message), ensure_ascii=False),
            tool_schemas=json.dumps(self.tool_schemas, ensure_ascii=False),
            user_message=user_message,
        )
        resp = await self.llm.ainvoke(prompt, fallback_content=fallback)
        try:
            data = json.loads(resp.content)
        except json.JSONDecodeError:
            data = json.loads(fallback)

        valid = ["search", "compare", "recommend", "cart", "order", "plan", "clarify", "unknown"]
        intent = str(data.get("intent", "unknown")).lower()
        return RouteDecision(
            intent=intent if intent in valid else "unknown",
            confidence=float(data.get("confidence") or 0),
            evidence=list(data.get("evidence") or []),
            required_slots=list(data.get("required_slots") or []),
        )

    @staticmethod
    def _route_by_keywords(user_message: str) -> str | None:
        text = user_message.strip()
        negative_order = any(word in text for word in ["先别下单", "别下单", "不下单", "暂不下单", "先别购买", "不购买"])

        has_cart_action = any(word in text for word in ["购物车", "加入", "添加", "加购", "清空"])
        has_order_action = any(word in text for word in ["下单", "结算", "购买"])
        has_recommend = "推荐" in text
        has_search = any(word in text for word in ["找", "搜索", "有没有", "有哪些"])

        if not negative_order and sum([has_cart_action, has_order_action, has_recommend or has_search]) >= 2:
            return "plan"
        if any(word in text for word in ["对比", "比较"]):
            return "compare"
        if has_cart_action:
            return "cart"
        if has_order_action and not negative_order:
            return "order"
        if has_recommend:
            return "recommend"
        if has_search:
            return "search"
        return None

    @staticmethod
    def _looks_ambiguous(user_message: str) -> bool:
        return any(word in user_message for word in ["不好用", "不会用", "不能用", "怎么办", "有问题"])
