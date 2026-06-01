"""意图路由 Agent。"""
# Intent Router Agent：优先用规则稳定识别高频购物意图，必要时再调用 LLM 输出置信度和证据。

# backend/app/services/chatbot/agents/intent_router.py
import json
import re
from dataclasses import dataclass, field

from app.core.llm_gateway import llm_gateway
from app.services.chatbot.knowledge_base import BusinessKnowledgeRetriever
from app.services.chatbot.prompts import prompt_manager


@dataclass
class RouteDecision:
    """带置信度和证据的路由结果。"""

    intent: str
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
    required_slots: list[str] = field(default_factory=list)


class IntentRouterAgent:
    def __init__(self, tool_schemas: list[dict] | None = None):
        # 注入工具 schema 和业务知识检索器，用于 LLM 路由提示词。
        self.llm = llm_gateway
        self.tool_schemas = tool_schemas or []
        self.knowledge = BusinessKnowledgeRetriever()

    async def route(self, user_message: str) -> str:
        # 兼容旧调用方的轻量入口，只返回 intent。
        return (await self.route_decision(user_message)).intent

    async def route_decision(self, user_message: str) -> RouteDecision:
        # 路由主入口：先走确定性关键词规则，再走 LLM + fallback JSON。
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
        # 关键词路由覆盖搜索、推荐、对比、购物车、下单和复杂规划高频场景。
        text = user_message.strip()
        lower_text = text.lower()

        remove_cart = any(word in text for word in ["取消购物车", "从购物车移除", "移除购物车", "删除购物车", "购物车里的"])
        if remove_cart:
            return "plan"

        selection_into_cart = any(word in text for word in ["最便宜", "最低价", "评分最高", "性价比", "这三个", "这几个", "刚才推荐"])
        selection_into_cart = selection_into_cart and any(word in text for word in ["加入", "加进", "加到", "购物车"])
        if selection_into_cart:
            return "plan"

        negative_order = any(word in text for word in ["先别下单", "别下单", "不下单", "暂不下单", "先别购买", "不购买"])
        has_cart_action = any(word in text for word in ["购物车", "加入", "添加", "加购", "清空"])
        has_order_action = any(word in text for word in ["下单", "结算", "购买", "买"])
        has_recommend = "推荐" in text or "recommend" in lower_text
        has_search = any(word in text for word in ["找", "搜索", "有没有", "有哪些"]) or any(
            word in lower_text for word in ["find", "search", "show me"]
        )
        has_product_resolution = any(
            word in text
            for word in ["最便宜", "最低价", "评分最高", "性价比", "最划算", "第一", "第二", "第三", "低延迟", "中延迟", "高延迟", "Pro", "Lite"]
        )
        has_product_hint = any(
            word in text
            for word in ["耳机", "手机", "平板", "电脑", "键盘", "鼠标", "显示器", "相机", "电视", "冰箱", "空调", "扫地机器人"]
        )
        has_explicit_product_id = bool(re.search(r"(?:商品|product|id)\s*#?\s*\d+|#\s*\d+", text, re.IGNORECASE))

        if not negative_order and sum([has_cart_action, has_order_action, has_recommend or has_search]) >= 2:
            return "plan"
        if has_order_action and has_product_hint and not has_explicit_product_id and not negative_order:
            return "plan"
        if has_cart_action and has_product_hint and (has_product_resolution or not has_explicit_product_id):
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
        # 判断是否属于泛化求助/问题不清晰场景，触发澄清而不是误调用工具。
        return any(word in user_message for word in ["不好用", "不会用", "不能用", "怎么办", "有问题"])
