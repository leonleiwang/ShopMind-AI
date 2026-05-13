"""
意图路由 Agent
"""

# backend/app/services/chatbot/agents/intent_router.py
from app.core.llm import get_llm

class IntentRouterAgent:
    def __init__(self):
        self.llm = get_llm()

    async def route(self, user_message: str) -> str:
        deterministic_intent = self._route_by_keywords(user_message)
        if deterministic_intent:
            return deterministic_intent

        prompt = f"""You are an intent router for a shopping assistant. Classify the user's intent into one of: search, compare, recommend, cart, order, plan, unknown.
If the user wants multiple actions (e.g., "recommend and add to cart" or "search and buy"), return "plan".
User: {user_message}
Intent:"""
        resp = await self.llm.ainvoke(prompt)
        intent = resp.content.strip().lower()
        valid = ["search", "compare", "recommend", "cart", "order", "plan"]
        return intent if intent in valid else "unknown"

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
