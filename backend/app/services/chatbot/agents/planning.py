# backend/app/services/chatbot/agents/planning.py
import json
import re

from app.core.llm_gateway import llm_gateway
from app.services.chatbot.prompts import prompt_manager


class PlanningAgent:
    def __init__(self):
        self.llm = llm_gateway

    async def create_plan(self, user_message: str) -> list[dict]:
        deterministic_plan = self._create_deterministic_plan(user_message)
        if deterministic_plan:
            return deterministic_plan

        prompt = prompt_manager.render("planning", user_message=user_message)
        resp = await self.llm.ainvoke(prompt, fallback_content="[]")
        try:
            content = resp.content.strip()
            if content.startswith("```"):
                content = content.strip("`")
                if content.startswith("json"):
                    content = content[4:].strip()
            plan = json.loads(content)
            return plan
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _create_deterministic_plan(user_message: str) -> list[dict]:
        text = user_message.strip()
        plan: list[dict] = []

        if "清空购物车" in text or "清空" in text:
            plan.append({"intent": "clear_cart", "description": "清空购物车", "params": {}})

        product_match = re.search(r"(?:商品|product|id)\s*#?\s*(\d+)|#\s*(\d+)", text, re.IGNORECASE)
        product_id = None
        if product_match:
            product_id = int(next(group for group in product_match.groups() if group))

        if product_id and any(word in text for word in ["加入", "添加", "加购", "放进", "加进去"]):
            plan.append({
                "intent": "cart",
                "description": f"将商品 {product_id} 加入购物车",
                "params": {"product_id": product_id, "quantity": 1}
            })

        if "下单" in text or "结算" in text or "购买" in text:
            plan.append({"intent": "order", "description": "提交订单", "params": {}})

        return plan if len(plan) > 1 else []
